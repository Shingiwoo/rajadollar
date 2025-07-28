import pandas as pd
from datetime import datetime, timezone
import threading
from unittest.mock import MagicMock

from risk_management.circuit_breaker import CircuitBreaker


def test_circuit_breaker_trigger(monkeypatch):
    df = pd.DataFrame({
        'entry_time': [datetime.now(timezone.utc).isoformat()],
        'pnl': [-60.0],
    })
    monkeypatch.setattr('risk_management.circuit_breaker.get_all_trades', lambda: df)
    monkeypatch.setattr('risk_management.circuit_breaker.load_state', lambda: [
        {'symbol': 'BTCUSDT', 'side': 'long', 'size': 0.1}
    ])
    closed = []
    def mock_close(client, symbol, side, size, steps):
        closed.append((symbol, side, size))
    monkeypatch.setattr('risk_management.circuit_breaker.safe_close_order_market', mock_close)
    dummy_ws = MagicMock()
    monkeypatch.setattr('risk_management.circuit_breaker.ws_signal_listener', MagicMock(ws_manager=dummy_ws))
    monkeypatch.setattr('risk_management.circuit_breaker.kirim_notifikasi_telegram', lambda msg: None)

    cb = CircuitBreaker(loss_limit=-50)
    stop_event = threading.Event()
    triggered = cb.check(MagicMock(), {'BTCUSDT': {'step': 0.001}}, stop_event)

    assert triggered is True
    assert stop_event.is_set()
    assert closed
    dummy_ws.stop.assert_called_once()
