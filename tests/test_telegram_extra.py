import importlib
import os
from unittest.mock import patch
import pandas as pd


def reload_module():
    import notifications.command_handler as ch
    importlib.reload(ch)
    return ch


def env():
    return {"TELEGRAM_TOKEN": "token", "TELEGRAM_CHAT_ID": "chat"}


def test_status_equity_and_position(monkeypatch):
    with patch.dict(os.environ, env()):
        ch = reload_module()
        df = pd.DataFrame({
            "symbol": ["BTC"],
            "side": ["long"],
            "pnl": [3.0]
        })
        with patch("notifications.command_handler.requests.post") as mock_post:
            monkeypatch.setattr(ch, "get_all_trades", lambda: df)
            bot_state = {"positions": ["BTC"]}
            ch.handle_command("/status", "chat", bot_state)
            text = mock_post.call_args.kwargs["data"]["text"]
            assert "Equity" in text and "3.0" in text


def test_entry_sets_flag(monkeypatch):
    with patch.dict(os.environ, env()):
        ch = reload_module()
        with patch("notifications.command_handler.requests.post"):
            bot_state = {}
            ch.handle_command("/entry BTCUSDT", "chat", bot_state)
            assert bot_state["manual_entry_flag"]["BTCUSDT"] is True
