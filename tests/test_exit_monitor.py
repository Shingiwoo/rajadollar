from unittest.mock import MagicMock, patch
from models.trade import Trade
from utils.state_manager import save_state, load_state, delete_state
from execution.ws_listener import clear_prices, update_price
from execution import exit_monitor


def test_monitor_exit_closes_position(monkeypatch):
    # Setup
    delete_state()
    trade = Trade(
        symbol="BTCUSDT",
        side="long",
        entry_time="2020-01-01T00:00:00",
        entry_price=100.0,
        size=0.1,
        sl=95.0,
        tp=104.0,
        trailing_sl=95.0,
        order_id="1",
    )
    save_state([trade.to_dict()])

    # Clear and set price data
    clear_prices()
    update_price("BTCUSDT", 105.0)  # Perbaikan di sini: gunakan fungsi dengan parameter

    # Mock dependencies
    mock_close = MagicMock(return_value={"avgPrice": 105.0})
    mock_log = MagicMock()
    mock_notif = MagicMock()
    
    monkeypatch.setattr(exit_monitor, "safe_close_order_market", mock_close)
    monkeypatch.setattr(exit_monitor, "log_trade", mock_log)
    monkeypatch.setattr(exit_monitor, "kirim_notifikasi_exit", mock_notif)

    # Exercise
    exit_monitor.check_and_close_positions(
        MagicMock(), 
        {"BTCUSDT": {"step": 0.001}}, 
        notif_exit=True
    )

    # Verify
    assert load_state() == []
    mock_close.assert_called_once()
    mock_log.assert_called_once()
    mock_notif.assert_called_once()