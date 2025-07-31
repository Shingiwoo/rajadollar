from utils.resume_helper import sync_with_binance
from unittest.mock import patch

class DummyClient:
    def futures_position_information(self):
        return []


def test_sync_ignore_orphan(monkeypatch):
    monkeypatch.setattr('utils.resume_helper.load_state', lambda: [{"symbol":"BTCUSDT","side":"long"}])
    saved = []
    monkeypatch.setattr('utils.resume_helper.save_state', lambda x: saved.extend(x))
    notes = []
    monkeypatch.setattr('utils.resume_helper.kirim_notifikasi_telegram', lambda m: notes.append(m))

    result = sync_with_binance(DummyClient())
    assert result == []
    assert saved == []
    assert any("Orphan" in n for n in notes)
