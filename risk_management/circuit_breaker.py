from datetime import datetime, timezone, date
from typing import Optional, Set
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
        self.last_seen_ids: Set[str] = set()

    def check(self, client, symbol_steps, stop_event: threading.Event) -> bool:
        today = datetime.now(timezone.utc).date()
        if today != self.last_check_date:
            self.last_check_date = today
            self.cumulative_loss = 0.0
            self.last_seen_ids.clear()

        new_trades = self._get_today_trades()
        if not new_trades.empty:
            if 'order_id' not in new_trades.columns:
                new_trades['order_id'] = new_trades['entry_time'].astype(str)  # fallback id

            unseen_trades = new_trades[~new_trades['order_id'].isin(self.last_seen_ids)]

            if not unseen_trades.empty:
                self.cumulative_loss += unseen_trades['pnl'].sum()
                self.last_seen_ids.update(unseen_trades['order_id'].tolist())

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
        now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
        kirim_notifikasi_telegram(
            f"🔴 Circuit Breaker Activated at {now} UTC\nLoss: {self.cumulative_loss:.2f} USDT"
        )
        stop_event.set()

        try:
            manager = getattr(ws_signal_listener, 'ws_manager', None)
            if manager and hasattr(manager, 'stop'):
                manager.stop()
        except Exception as e:
            kirim_notifikasi_telegram(f"⚠️ Gagal stop ws_manager: {e}")

        for trade in load_state():
            result = safe_close_order_market(
                client,
                trade['symbol'],
                'SELL' if trade['side'] == 'long' else 'BUY',
                trade['size'],
                symbol_steps,
            )
            if not result:
                kirim_notifikasi_telegram(f"❌ Gagal close posisi {trade['symbol']}")
