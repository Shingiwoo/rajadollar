import importlib
import os
from unittest.mock import patch, mock_open
import pandas as pd


def reload_module():
    import notifications.command_handler as ch
    importlib.reload(ch)
    return ch


def base_env():
    return {
        "TELEGRAM_TOKEN": "token",
        "TELEGRAM_CHAT_ID": "chat"
    }


def test_status_command():
    with patch.dict(os.environ, base_env()):
        ch = reload_module()
        with patch("notifications.command_handler.requests.post") as mock_post:
            bot_state = {"positions": []}
            ch.handle_command("/status", "chat", bot_state)
            assert mock_post.call_count == 1
            data = mock_post.call_args.kwargs["data"]
            assert "Bot Aktif" in data["text"]


def test_entry_command():
    with patch.dict(os.environ, base_env()):
        ch = reload_module()
        with patch("notifications.command_handler.requests.post") as mock_post:
            bot_state = {}
            ch.handle_command("/entry BTC", "chat", bot_state)
            assert bot_state["manual_entry"] == "BTC"
            data = mock_post.call_args.kwargs["data"]
            assert "ENTRY" in data["text"]


def test_stop_command():
    with patch.dict(os.environ, base_env()):
        ch = reload_module()
        with patch("notifications.command_handler.requests.post") as mock_post:
            bot_state = {}
            ch.handle_command("/stop", "chat", bot_state)
            assert bot_state["force_exit"] is True
            data = mock_post.call_args.kwargs["data"]
            assert "STOP" in data["text"]


def test_restart_command():
    with patch.dict(os.environ, base_env()):
        ch = reload_module()
        with patch("notifications.command_handler.requests.post") as mock_post:
            bot_state = {}
            ch.handle_command("/restart", "chat", bot_state)
            assert bot_state["force_restart"] is True
            data = mock_post.call_args.kwargs["data"]
            assert "RESTART" in data["text"]


def test_mltrain_command():
    with patch.dict(os.environ, base_env()):
        ch = reload_module()
        with patch.object(ch, "train_model") as mock_train, \
             patch.object(ch, "glob") as mock_glob, \
             patch("notifications.command_handler.requests.post") as mock_post, \
             patch("builtins.open", mock_open(read_data="ok")):
            mock_glob.glob.return_value = ["logs/ml_training_1.txt"]
            bot_state = {}
            ch.handle_command("/mltrain", "chat", bot_state)
            assert mock_train.call_count == 1
            data = mock_post.call_args.kwargs["data"]
            assert "ML retraining" in data["text"]


def test_log_command():
    with patch.dict(os.environ, base_env()):
        ch = reload_module()
        df = pd.DataFrame({
            "symbol": ["BTC"],
            "side": ["long"],
            "entry": [100.0],
            "exit": [110.0],
            "pnl": [10.0],
        })
        with patch.object(ch, "get_all_trades", return_value=df), \
             patch("notifications.command_handler.requests.post") as mock_post:
            bot_state = {}
            ch.handle_command("/log", "chat", bot_state)
            data = mock_post.call_args.kwargs["data"]
            assert "Trade Terakhir" in data["text"]


def test_summary_command():
    with patch.dict(os.environ, base_env()):
        ch = reload_module()
        df = pd.DataFrame({
            "symbol": ["BTC"],
            "side": ["long"],
            "entry": [100.0],
            "exit": [110.0],
            "pnl": [10.0],
        })
        with patch.object(ch, "get_all_trades", return_value=df), \
             patch("notifications.command_handler.requests.post") as mock_post:
            bot_state = {}
            ch.handle_command("/summary", "chat", bot_state)
            data = mock_post.call_args.kwargs["data"]
            assert "Ringkasan Trading" in data["text"]

