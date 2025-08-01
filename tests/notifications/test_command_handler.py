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
        df = pd.DataFrame({
            "symbol": ["BTC"],
            "side": ["long"],
            "pnl": [1.0]
        })
        with patch("notifications.command_handler.requests.post") as mock_post, \
             patch.object(ch, "get_all_trades", return_value=df):
            bot_state = {"positions": ["BTC"]}
            ch.handle_command("/status", "chat", bot_state)
            assert mock_post.call_count == 1
            data = mock_post.call_args.kwargs["data"]
            assert "Equity" in data["text"] and "1" in data["text"]


def test_entry_command():
    with patch.dict(os.environ, base_env()):
        ch = reload_module()
        with patch("notifications.command_handler.requests.post") as mock_post:
            bot_state = {}
            ch.handle_command("/entry BTC", "chat", bot_state)
            assert bot_state["manual_entry_flag"]["BTC"] is True
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


def test_mltrain_symbol_command():
    with patch.dict(os.environ, base_env()):
        ch = reload_module()
        with patch.object(ch, "_train_symbol", return_value=0.95) as mock_train, \
             patch("notifications.command_handler.requests.post") as mock_post:
            bot_state = {}
            ch.handle_command("/mltrain BTCUSDT", "chat", bot_state)
            mock_train.assert_called_with("BTCUSDT")
            assert mock_post.call_count == 2
            data = mock_post.call_args.kwargs["data"]
            assert "Akurasi" in data["text"]


def test_mltrain_all_command():
    with patch.dict(os.environ, base_env()):
        ch = reload_module()
        with patch.object(ch, "_train_symbol", return_value=0.9) as mock_train, \
             patch.object(ch, "glob") as mock_glob, \
             patch("notifications.command_handler.requests.post") as mock_post:
            mock_glob.glob.return_value = ["data/training_data/BTC.csv", "data/training_data/ETH.csv"]
            bot_state = {}
            ch.handle_command("/mltrain all", "chat", bot_state)
            assert mock_train.call_count == 2
            data = mock_post.call_args.kwargs["data"]
            assert "Semua model selesai" in data["text"]


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


def test_pnl_command():
    with patch.dict(os.environ, base_env()):
        ch = reload_module()
        df = pd.DataFrame({"pnl": [5.0, -2.0]})
        with patch.object(ch, "get_all_trades", return_value=df), \
             patch("notifications.command_handler.requests.post") as mock_post:
            bot_state = {}
            ch.handle_command("/pnl", "chat", bot_state)
            data = mock_post.call_args.kwargs["data"]
            assert "PnL" in data["text"]


def test_export_command(tmp_path):
    with patch.dict(os.environ, base_env()):
        ch = reload_module()
        df = pd.DataFrame({"pnl": [1.0]})
        with patch.object(ch, "get_all_trades", return_value=df), \
             patch("notifications.command_handler.export_trades_csv", return_value=str(tmp_path/"export.csv")) as mock_exp, \
             patch("notifications.command_handler.requests.post") as mock_post, \
             patch("builtins.open", mock_open(read_data="csv")):
            bot_state = {}
            ch.handle_command("/export", "chat", bot_state)
            assert mock_exp.call_count == 1
            # called twice: sendDocument then sendMessage
            assert mock_post.call_count == 2

