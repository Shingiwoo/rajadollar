import os
from unittest.mock import MagicMock
from models.trade import Trade
from utils.state_manager import save_state, load_state, delete_state
from execution.ws_listener import shared_price
from execution import exit_monitor


def test_monitor_exit_closes_position(monkeypatch):
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

    shared_price.clear()
    shared_price["BTCUSDT"] = 105.0

    monkeypatch.setattr(
        exit_monitor, "safe_close_order_market", MagicMock(return_value={"avgPrice": 105.0})
    )
    monkeypatch.setattr(exit_monitor, "log_trade", MagicMock())
    monkeypatch.setattr(exit_monitor, "kirim_notifikasi_exit", MagicMock())

    exit_monitor.check_and_close_positions(MagicMock(), {"BTCUSDT": {"step": 0.001}}, notif_exit=True)
    assert load_state() == []