from datetime import datetime, timezone, date
from typing import Optional
import pandas as pd
import threading

from database.sqlite_logger import get_all_trades
from utils.state_manager import load_state
from notifications.notifier import kirim_notifikasi_telegram
from execution.order_router import safe_close_order_market
import execution.ws_signal_listener as ws_signal_listener

class CircuitBreaker:
    def __init__(self, loss_limit: float = -50.0):
        self.loss_limit = loss_limit
        self.last_check_date: Optional[date] = None
        self.cumulative_loss = 0.0

    def check(self, client, symbol_steps, stop_event: threading.Event) -> bool:
        today = datetime.now(timezone.utc).date()
        if today != self.last_check_date:
            self.last_check_date = today
            self.cumulative_loss = 0.0

        new_trades = self._get_today_trades()
        if not new_trades.empty:
            self.cumulative_loss += new_trades['pnl'].sum()

        if self.cumulative_loss <= self.loss_limit:
            self._trigger_actions(client, symbol_steps, stop_event)
            return True
        return False

    def _get_today_trades(self) -> pd.DataFrame:
        df = get_all_trades()
        if df.empty:
            return pd.DataFrame()
        today = datetime.now(timezone.utc).date()
        df['entry_date'] = pd.to_datetime(df['entry_time']).dt.date
        return df[df['entry_date'] == today]

    def _trigger_actions(self, client, symbol_steps, stop_event: threading.Event):
        kirim_notifikasi_telegram(
            f"🔴 Circuit Breaker Activated!\nLoss: {self.cumulative_loss:.2f} USDT"
        )
        stop_event.set()
        if hasattr(ws_signal_listener, 'ws_manager'):
            ws_signal_listener.ws_manager.stop()

        for trade in load_state():
            safe_close_order_market(
                client,
                trade['symbol'],
                'SELL' if trade['side'] == 'long' else 'BUY',
                trade['size'],
                symbol_steps,
            )
