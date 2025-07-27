from utils.resume_helper import handle_resume


def test_handle_resume_with_active(monkeypatch):
    monkeypatch.setattr("utils.resume_helper.load_state", lambda: [{"symbol": "BTC"}])
    sent = {}
    def send(msg):
        sent["msg"] = msg
    monkeypatch.setattr("utils.resume_helper.kirim_notifikasi_telegram", send)

    active = handle_resume(True, True)
    assert len(active) == 1
    assert sent["msg"] == "🔄 Bot resumed with 1 active positions"


def test_handle_resume_no_notify(monkeypatch):
    monkeypatch.setattr("utils.resume_helper.load_state", lambda: [])
    called = {}
    monkeypatch.setattr("utils.resume_helper.kirim_notifikasi_telegram", lambda msg: called.setdefault("msg", msg))

    active = handle_resume(True, True)
    assert active == []
    assert "msg" not in called
