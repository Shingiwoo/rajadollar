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

    active = handle_resume(True, True)
    assert len(active) == 1
    # Update expected message sesuai implementasi
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
    
    # Verify
    assert len(result) == 2  # Should contain both positions
    assert any(t["symbol"] == "BTCUSDT" for t in result)
    assert any(t["symbol"] == "ETHUSDT" for t in result)
    assert "BTCUSDT" in notifications[0]  # Verify notification

