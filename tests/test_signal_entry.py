import pytest
from unittest.mock import MagicMock
from execution.signal_entry import on_signal

def test_on_signal_entry_trigger(monkeypatch):
    """Test entry signal dengan kondisi long"""
    # Setup
    symbol = "BTCUSDT"
    test_row = {
        "close": 100.0,
        "long_signal": True,
        "short_signal": False
    }

    strategy_params = {
        symbol: {
            "trailing_offset": 0.25,
            "trigger_threshold": 0.5,
            "sl": 0.95,  # Tambahkan stop loss
            "tp": 1.05   # Tambahkan take profit
        }
    }

    # Mock dependencies
    mock_filters = {
        "BTCUSDT": {
            "minQty": 0.001,
            "stepSize": 0.001,
            "minNotional": 5.0
        }
    }
    
    mock_positions = []
    mock_create_order = MagicMock(return_value={"orderId": "123"})
    
    # Mock semua kondisi untuk memastikan order ter-trigger
    monkeypatch.setattr("execution.signal_entry.load_symbol_filters", lambda *a, **kw: mock_filters)
    monkeypatch.setattr("execution.signal_entry.get_price", lambda s: 100.0)
    monkeypatch.setattr("execution.signal_entry.safe_futures_create_order", mock_create_order)
    monkeypatch.setattr("execution.signal_entry.save_state", MagicMock())
    monkeypatch.setattr("execution.signal_entry.kirim_notifikasi_entry", MagicMock())
    monkeypatch.setattr("execution.signal_entry.can_open_new_position", lambda *a, **kw: True)
    monkeypatch.setattr("execution.signal_entry.is_position_open", lambda *a, **kw: False)
    monkeypatch.setattr("execution.signal_entry.is_liquidation_risk", lambda *a, **kw: False)
    monkeypatch.setattr("execution.signal_entry.verify_price_before_order", lambda *a, **kw: True)
    monkeypatch.setattr("execution.signal_entry.update_open_positions", lambda *a, **kw: mock_positions)

    # Exercise
    on_signal(
        symbol=symbol,
        row=test_row,
        client=MagicMock(),
        strategy_params=strategy_params,
        capital=10000,  # Pastikan cukup untuk min notional
        leverage=10,
        risk_pct=1.0,   # Risk percentage yang cukup
        max_pos=5,
        max_sym=3,
        max_slip=0.5
    )

    # Verify
    mock_create_order.assert_called_once()


def test_on_signal_invalid_price(monkeypatch):
    symbol = "BTCUSDT"
    test_row = {"close": None, "long_signal": True, "short_signal": False}
    monkeypatch.setattr("execution.signal_entry.load_symbol_filters", lambda *a, **kw: {})
    monkeypatch.setattr("execution.signal_entry.get_price", lambda s: None)
    called = {}
    monkeypatch.setattr("execution.signal_entry.laporkan_error", lambda msg: called.setdefault("msg", msg))
    monkeypatch.setattr("execution.signal_entry.catat_error", lambda msg: called.setdefault("msg", msg))
    mock_safe = MagicMock()
    monkeypatch.setattr("execution.signal_entry.safe_futures_create_order", mock_safe)

    on_signal(
        symbol=symbol,
        row=test_row,
        client=MagicMock(),
        strategy_params={},
        capital=1000,
        leverage=10,
        risk_pct=1.0,
        max_pos=1,
        max_sym=1,
        max_slip=0.5,
        notif_error=True,
    )

    assert "invalid" in called.get("msg", "")
    mock_safe.assert_not_called()