from datetime import datetime, timezone
import pandas as pd
from database.sqlite_logger import get_all_trades
from notifications.notifier import kirim_notifikasi_telegram
from risk_management.resume_state import save_resume_state, load_resume_state
from utils import bot_flags


class CircuitBreaker:
    def __init__(self, max_drawdown: float, max_losses: int):
        self.max_drawdown = max_drawdown
        self.max_losses = max_losses
        state = load_resume_state()
        self.daily_drawdown = state.get("daily_drawdown", 0.0)
        self.consecutive_losses = state.get("consecutive_losses", 0)
        self.paused = state.get("paused", False)
        if self.paused:
            bot_flags.set_paused(True)

    def check(self) -> bool:
        df = self._get_today_trades()
        if not df.empty:
            self.daily_drawdown = max(0.0, -df["pnl"].sum())
            loss_flags = (df["pnl"] < 0).tolist()[::-1]
            cnt = 0
            for flag in loss_flags:
                if flag:
                    cnt += 1
                else:
                    break
            self.consecutive_losses = cnt
        triggered = (
            self.daily_drawdown >= self.max_drawdown
            or self.consecutive_losses >= self.max_losses
        )
        if triggered and not self.paused:
            kirim_notifikasi_telegram(
                "Circuit breaker aktif: trading dijeda"
            )
            self.paused = True
            bot_flags.set_paused(True)
        save_resume_state(
            {
                "daily_drawdown": self.daily_drawdown,
                "consecutive_losses": self.consecutive_losses,
                "paused": self.paused,
            }
        )
        return self.paused

    def _get_today_trades(self) -> pd.DataFrame:
        df = get_all_trades()
        if df.empty:
            return pd.DataFrame()
        today = datetime.now(timezone.utc).date()
        df["entry_date"] = pd.to_datetime(df["entry_time"]).dt.date
        return df[df["entry_date"] == today]
