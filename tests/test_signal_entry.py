import pandas as pd
from unittest.mock import MagicMock
from execution.signal_entry import on_signal

def test_on_signal_entry_trigger(monkeypatch):
    symbol = "BTCUSDT"
    test_row = pd.Series({
        "close": 100,
        "long_signal": True,
        "short_signal": False
    })

    strategy_params = {
        symbol: {
            "trailing_offset": 0.25,
            "trigger_threshold": 0.5
        }
    }

    # Mock dependencies
    monkeypatch.setattr("execution.signal_entry.load_symbol_filters", lambda *a, **kw: {})
    monkeypatch.setattr("execution.signal_entry.shared_price", {symbol: 100})
    monkeypatch.setattr("execution.signal_entry.load_state", lambda: [])
    monkeypatch.setattr("execution.signal_entry.save_state", MagicMock())
    monkeypatch.setattr("execution.signal_entry.update_open_positions", MagicMock())
    monkeypatch.setattr("execution.signal_entry.calculate_order_qty", lambda *a, **kw: 0.1)
    monkeypatch.setattr("execution.signal_entry.adjust_quantity_to_min", lambda *a, **kw: 0.1)
    monkeypatch.setattr("execution.signal_entry.verify_price_before_order", lambda *a, **kw: True)
    monkeypatch.setattr("execution.signal_entry.safe_futures_create_order", lambda *a, **kw: {"orderId": "123456"})
    monkeypatch.setattr("execution.signal_entry.kirim_notifikasi_entry", MagicMock())
    monkeypatch.setattr("execution.signal_entry.kirim_notifikasi_telegram", MagicMock())

    client = MagicMock()
    on_signal(
        symbol=symbol,
        row=test_row,
        client=client,
        strategy_params=strategy_params,
        capital=1000.0,
        leverage=20,
        risk_pct=0.02,
        max_pos=4,
        max_sym=2,
        max_slip=0.5,
        notif_entry=True,
        notif_error=True
    )
