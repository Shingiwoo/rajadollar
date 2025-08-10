import threading
from unittest.mock import MagicMock, patch
from utils.trading_controller import start_bot, stop_bot
from utils.bot_flags import set_ready


def dummy_cfg():
    return {
        "api_key": "k",
        "api_secret": "s",
        "client": MagicMock(),
        "symbols": ["BTCUSDT"],
        "strategy_params": {"BTCUSDT": {}},
        "auto_sync": False,
        "leverage": 10,
        "risk_pct": 0.01,
        "max_pos": 1,
        "max_sym": 1,
        "max_slip": 0.5,
        "notif_entry": True,
        "notif_error": True,
        "notif_exit": True,
        "loss_limit": -50.0,
        "resume_flag": False,
        "notif_resume": False,
        "capital": 1000.0,
    }


def test_start_stop_toggle(monkeypatch):
    ev = threading.Event()
    set_ready(True)
    monkeypatch.setattr("utils.trading_controller.start_price_stream", lambda *a, **k: "ws")
    monkeypatch.setattr("utils.trading_controller.start_signal_stream", lambda *a, **k: None)
    monkeypatch.setattr("utils.trading_controller.start_exit_monitor", lambda *a, **k: (ev, None, MagicMock(paused=False)))
    monkeypatch.setattr("utils.trading_controller.load_symbol_filters", lambda *a, **k: {})
    monkeypatch.setattr("utils.trading_controller.handle_resume", lambda *a, **k: [])
    monkeypatch.setattr("utils.trading_controller.sync_with_binance", lambda *a, **k: None)
    monkeypatch.setattr("utils.trading_controller.register_signal_handler", lambda *a, **k: None)
    monkeypatch.setattr("utils.trading_controller.get_futures_balance", lambda *a, **k: 1000.0)

    handles = start_bot(dummy_cfg())
    assert handles.get("price_ws") == "ws"
    assert not ev.is_set()

    stop_bot(handles)
    assert ev.is_set()
