from unittest.mock import MagicMock
from execution.monitor_exit_worker import process_exit_positions


def test_process_exit_positions(monkeypatch):
    trade = {
        "symbol": "BTCUSDT",
        "side": "long",
        "entry_time": "2021-01-01T00:00:00",
        "entry_price": 100.0,
        "size": 0.1,
        "sl": 95.0,
        "tp": 105.0,
        "trailing_sl": 95.0,
        "order_id": "1",
        "trailing_offset": 0.25,
        "trigger_threshold": 0.5,
    }

    monkeypatch.setattr(
        "execution.monitor_exit_worker.shared_price", {"BTCUSDT": 105.0}
    )
    monkeypatch.setattr(
        "execution.monitor_exit_worker.load_state", lambda: [trade.copy()]
    )
    saved = {}

    def save_state_stub(data):
        saved["data"] = data

    monkeypatch.setattr(
        "execution.monitor_exit_worker.save_state", save_state_stub
    )
    monkeypatch.setattr(
        "execution.monitor_exit_worker.safe_close_order_market", lambda *a, **kw: None
    )
    notif = MagicMock()
    monkeypatch.setattr(
        "execution.monitor_exit_worker.kirim_notifikasi_exit", notif
    )
    log = MagicMock()
    monkeypatch.setattr("execution.monitor_exit_worker.log_trade", log)

    process_exit_positions(MagicMock(), {})

    assert saved["data"] == []
    assert notif.called
    assert log.called
