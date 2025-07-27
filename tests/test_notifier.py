import importlib
import os
from unittest.mock import patch


def test_notifier():
    with patch.dict(os.environ, {"TELEGRAM_TOKEN": "token", "TELEGRAM_CHAT_ID": "chat"}):
        import notifications.notifier as notifier
        importlib.reload(notifier)

        with patch("notifications.notifier.requests.post") as mock_post:
            msg = "📈 *UNIT TEST* Notifikasi bot RajaDollar!"
            notifier.kirim_notifikasi_telegram(msg)

            expected_url = "https://api.telegram.org/bottoken/sendMessage"
            expected_data = {
                "chat_id": "chat",
                "text": msg,
                "parse_mode": "Markdown",
            }
            mock_post.assert_called_once_with(expected_url, data=expected_data)


if __name__ == "__main__":
    test_notifier()
