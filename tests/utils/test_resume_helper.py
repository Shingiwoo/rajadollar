import pandas as pd
from utils.resume_helper import handle_resume, sync_with_binance

def test_handle_resume_with_active(monkeypatch):
    # Data test harus lengkap sesuai kebutuhan fungsi
    monkeypatch.setattr(
        "utils.resume_helper.load_state", 
        lambda: [{"symbol": "BTC", "side": "long"}]  # Tambahkan field required
    )
    sent = {}
    def send(msg):
        sent["msg"] = msg
    monkeypatch.setattr("utils.resume_helper.kirim_notifikasi_telegram", send)
    from unittest.mock import mock_open
    m = mock_open(read_data="{\"BTC\": {}}")
    monkeypatch.setattr("builtins.open", m)
    monkeypatch.setattr("json.load", lambda f: {"BTC": {}})

    active = handle_resume(True, True)
    assert len(active) == 1
    assert "🔄 Resumed" in sent["msg"] and "BTC long" in sent["msg"]


def test_handle_resume_no_notify(monkeypatch):
    monkeypatch.setattr("utils.resume_helper.load_state", lambda: [])
    called = {}
    monkeypatch.setattr("utils.resume_helper.kirim_notifikasi_telegram", lambda msg: called.setdefault("msg", msg))

    active = handle_resume(True, True)
    assert active == []
    assert "msg" not in called

def test_sync_with_binance_warn(monkeypatch, capsys):
    class DummyClient:
        def futures_position_information(self):
            return [
                {
                    "symbol": "BTCUSDT", 
                    "positionAmt": "0.5", 
                    "entryPrice": "100",
                    "updateTime": "123"
                }
            ]

    client = DummyClient()
    
    # Mock local state to be different from remote
    monkeypatch.setattr(
        "utils.resume_helper.load_state", 
        lambda: [{"symbol": "ETHUSDT", "side": "long"}]
    )
    
    # Mock save_state to capture changes
    saved = []
    monkeypatch.setattr("utils.resume_helper.save_state", lambda x: saved.extend(x))
    
    # Mock notification function
    notifications = []
    monkeypatch.setattr(
        "utils.resume_helper.kirim_notifikasi_telegram",
        lambda msg: notifications.append(msg)
    )
    
    # Execute
    result = sync_with_binance(client)

    assert len(result) == 1
    assert result[0]["symbol"] == "BTCUSDT"
    assert "Added" in notifications[0]

