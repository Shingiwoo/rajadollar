import importlib
import os
from unittest.mock import patch, mock_open

def test_laporkan_error():
    with patch.dict(os.environ, {"TELEGRAM_TOKEN": "token", "TELEGRAM_CHAT_ID": "chat"}):
        import notifications.notifier as notifier
        importlib.reload(notifier)
        m = mock_open()
        with patch("notifications.notifier.open", m), \
             patch("notifications.notifier.requests.post") as mock_post:
            notifier.laporkan_error("kesalahan fatal")
            m.assert_called_once_with(os.path.join("logs", "error.log"), "a")
            handle = m()
            assert "kesalahan fatal" in handle.write.call_args[0][0]
            mock_post.assert_called_once()
