import importlib
import os
from unittest.mock import patch
import pandas as pd


def reload_module():
    import notifications.command_handler as ch
    importlib.reload(ch)
    return ch


def env():
    return {"TELEGRAM_TOKEN": "tok", "TELEGRAM_CHAT_ID": "chat"}


def test_authorized_status_command():
    with patch.dict(os.environ, env()):
        ch = reload_module()
        df = pd.DataFrame({
            "symbol": ["BTC"],
            "side": ["long"],
            "pnl": [2.0]
        })
        with patch("notifications.command_handler.requests.post") as mock_post, \
             patch.object(ch, "get_all_trades", return_value=df):
            bot_state = {"positions": ["BTC"]}
            ch.handle_command("/status", "chat", bot_state)
            data = mock_post.call_args.kwargs["data"]
            assert "Equity" in data["text"] and "2" in data["text"]

def test_entry_command_flag():
    with patch.dict(os.environ, env()):
        ch = reload_module()
        with patch("notifications.command_handler.requests.post") as mock_post:
            bot_state = {}
            ch.handle_command("/entry BTCUSDT", "chat", bot_state)
            assert bot_state["manual_entry_flag"]["BTCUSDT"] is True


def test_unauthorized_command():
    with patch.dict(os.environ, env()):
        ch = reload_module()
        with patch("notifications.command_handler.requests.post") as mock_post:
            ch.handle_command("/status", "other", {})
            data = mock_post.call_args.kwargs["data"]
            assert "Akses ditolak" in data["text"]
