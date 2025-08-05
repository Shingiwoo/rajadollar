import os
import sys
import pickle
from pathlib import Path
import pandas as pd
import importlib
from types import SimpleNamespace
from unittest.mock import patch, mock_open

import utils.ml_logger as ml_logger
import ml.training as training
import ml.historical_trainer as historical_trainer
import strategies.scalping_strategy as ss
import notifications.command_handler as ch
import main



def test_ml_logger_log_bar(tmp_path):
    logger = ml_logger.MLLogger(window_size=100, data_dir=str(tmp_path))
    for i in range(150):
        bar = {
            "timestamp": i,
            "open": i,
            "high": i + 1,
            "low": i - 1,
            "close": i,
            "volume": 10,
        }
        logger.log_bar("BTCUSDT", bar)
    # bar dengan NaN
    logger.log_bar("BTCUSDT", {"timestamp": 151, "close": None})
    # bar kosong
    logger.log_bar("BTCUSDT", {})
    csv_path = tmp_path / "BTCUSDT.csv"
    assert csv_path.exists()
    df = pd.read_csv(csv_path)
    assert list(df.columns) == [
        "timestamp",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "ema",
        "sma",
        "macd",
        "rsi",
        "atr",
        "bb_width",
    ]
    assert len(df) == 152



def setup_training_env(tmp_path, monkeypatch):
    monkeypatch.setattr(training, "DATA_DIR", str(tmp_path / "data/training_data"))
    monkeypatch.setattr(training, "MODEL_DIR", str(tmp_path / "models"))
    monkeypatch.setattr(training, "MIN_DATA", 20)
    monkeypatch.setattr(training, "MIN_ACCURACY", 0.0)
    monkeypatch.setattr(training, "kirim_notifikasi_ml_training", lambda msg: None)
    os.makedirs(training.DATA_DIR, exist_ok=True)
    os.makedirs(training.MODEL_DIR, exist_ok=True)
    return training.DATA_DIR, training.MODEL_DIR


def make_dataset(path, rows):
    df = pd.DataFrame({
        "ema": range(rows),
        "sma": range(rows),
        "macd": range(rows),
        "rsi": [i % 100 for i in range(rows)],
        "atr": range(rows),
        "bb_width": [0.1] * rows,
        "volume": range(rows),
        "label": [1 if i >= rows / 2 else 0 for i in range(rows)],
    })
    df.to_csv(path, index=False)


def test_train_model_valid_data(tmp_path, monkeypatch):
    data_dir, model_dir = setup_training_env(tmp_path, monkeypatch)
    csv_path = os.path.join(data_dir, "BTCUSDT_5m.csv")
    make_dataset(csv_path, 200)
    acc = training.train_model("BTCUSDT", "5m")
    model_path = os.path.join(model_dir, "BTCUSDT_scalping_5m.pkl")
    assert os.path.exists(model_path)
    assert acc >= 0.5


def test_train_model_insufficient_data(tmp_path, monkeypatch):
    data_dir, model_dir = setup_training_env(tmp_path, monkeypatch)
    csv_path = os.path.join(data_dir, "BTCUSDT_5m.csv")
    make_dataset(csv_path, 10)
    acc = training.train_model("BTCUSDT", "5m")
    assert acc == 0.0
    assert not os.listdir(model_dir)


def test_train_model_auto_label(tmp_path, monkeypatch):
    data_dir, model_dir = setup_training_env(tmp_path, monkeypatch)
    csv_path = os.path.join(data_dir, "BTCUSDT_5m.csv")
    pd.DataFrame({
        "ema": range(30),
        "sma": range(30),
        "macd": range(30),
        "rsi": range(30),
        "atr": range(30),
        "bb_width": [0.1] * 30,
        "volume": range(30),
    }).to_csv(csv_path, index=False)
    called = {}

    def fake_label(symbol, tf=None):
        df = pd.DataFrame({
            "ema": [0] * 15 + [1] * 15,
            "sma": [0] * 15 + [1] * 15,
            "macd": [0] * 15 + [1] * 15,
            "rsi": [0] * 15 + [1] * 15,
            "atr": [0] * 30,
            "bb_width": [0.1] * 30,
            "volume": [1] * 30,
            "label": [0] * 15 + [1] * 15,
        })
        df.to_csv(csv_path, index=False)
        called["x"] = True
        return True

    monkeypatch.setattr(historical_trainer, "label_and_save", fake_label)
    acc = training.train_model("BTCUSDT", "5m")
    assert called.get("x")
    model_path = os.path.join(model_dir, "BTCUSDT_scalping_5m.pkl")
    assert os.path.exists(model_path)
    assert acc > 0


def test_training_cli(monkeypatch):
    with patch.object(training, "train_model") as tm, patch.object(training, "train_all") as ta:
        monkeypatch.setattr(sys, "argv", ["training.py", "--symbol", "BTCUSDT", "--timeframe", "5m"])
        training.main()
        tm.assert_called_once_with("BTCUSDT", "5m")
        monkeypatch.setattr(sys, "argv", ["training.py", "--symbol", "all", "--timeframe", "5m"])
        training.main()
        ta.assert_called()


def test_labeling_and_cutoff(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(training, "DATA_DIR", "data/training_data")
    monkeypatch.setattr(training, "MODEL_DIR", "models")
    monkeypatch.setattr(training, "MIN_DATA", 10)
    monkeypatch.setattr(training, "MIN_ACCURACY", 0.0)
    monkeypatch.setattr(training, "kirim_notifikasi_ml_training", lambda m: None)
    os.makedirs("data/training_data", exist_ok=True)
    os.makedirs("models", exist_ok=True)

    def dummy_fetch(symbol, tf, start, end):
        start_old = pd.Timestamp.utcnow().tz_localize(None) - pd.Timedelta(days=10)
        start_new = pd.Timestamp.utcnow().tz_localize(None) - pd.Timedelta(days=1)
        old = pd.date_range(start_old, periods=40, freq="min")
        new = pd.date_range(start_new, periods=20, freq="min")
        times = old.append(new)
        close = [100] * len(times)
        high = []
        low = []
        for i in range(len(times)):
            if i % 10 == 0:
                high.append(101.0)
            else:
                high.append(100.0)
            low.append(99.0)
        df = pd.DataFrame({
            "open": close,
            "high": high,
            "low": low,
            "close": close,
            "volume": [10] * len(times),
        }, index=times)
        df.index.name = "timestamp"
        return df

    monkeypatch.setattr(historical_trainer, "load_historical_data", dummy_fetch)
    monkeypatch.setattr(historical_trainer, "accuracy_score", lambda y, p: 1.0)
    end = pd.Timestamp.utcnow().date().isoformat()
    start = (pd.Timestamp.utcnow() - pd.Timedelta(days=5)).date().isoformat()
    info = historical_trainer.train_from_history("BTCUSDT", "5m", start, end)
    assert info and info["train_accuracy"] > 0
    assert info["model"] and os.path.exists(info["model"])
    csv_path = Path("data/training_data/BTCUSDT_5m.csv")
    assert csv_path.exists()
    df_saved = pd.read_csv(csv_path)
    cutoff = pd.Timestamp.utcnow().tz_localize(None) - pd.Timedelta(days=7)
    assert (pd.to_datetime(df_saved["time"]) >= cutoff).any()
    df_labeled = historical_trainer._label_data(
        historical_trainer._apply_indicators(dummy_fetch("BTCUSDT", "5m", start, end))
    )
    labels = df_labeled["label"].dropna().unique().tolist()
    assert 1 in labels and 0 in labels


def test_generate_ml_signal(monkeypatch):
    df = pd.DataFrame(
        {
            "ema": [1],
            "sma": [1],
            "macd": [1],
            "rsi": [50],
            "atr": [1],
            "bb_width": [0.1],
            "volume": [100],
        }
    )
    class Dummy:
        def predict(self, X):
            return [0]
    monkeypatch.setattr(ss, "load_ml_model", lambda s: Dummy())
    out = ss.generate_ml_signal(df.copy(), "BTCUSDT")
    assert out["ml_signal"].iloc[-1] == 0
    monkeypatch.setattr(ss, "load_ml_model", lambda s: None)
    out = ss.generate_ml_signal(df.copy(), "BTCUSDT")
    assert out["ml_signal"].iloc[-1] == 1


def test_load_ml_model_cache(tmp_path, monkeypatch):
    model = {"x": 1}
    model_path = tmp_path / "BTCUSDT_scalping_5m.pkl"
    with open(model_path, "wb") as f:
        pickle.dump(model, f)
    ss._ml_models.clear()
    monkeypatch.setattr(ss, "_get_model_path", lambda s, tf=None: str(model_path))
    monkeypatch.setattr(ss.os.path, "exists", lambda p: p == str(model_path))
    m = ss.load_ml_model("BTCUSDT")
    assert m == model
    open_mock = mock_open(read_data=b"")
    monkeypatch.setattr("builtins.open", open_mock)
    m2 = ss.load_ml_model("BTCUSDT")
    open_mock.assert_not_called()
    assert m2 is m


def reload_ch():
    importlib.reload(ch)
    return ch


def env():
    return {"TELEGRAM_TOKEN": "tok", "TELEGRAM_CHAT_ID": "chat"}


def test_mltrain_commands(monkeypatch):
    with patch.dict(os.environ, env()):
        chm = reload_ch()
        called = []
        monkeypatch.setattr(chm, "_train_symbol", lambda s, tf=None: called.append((s, tf)) or 0.9)
        with patch("notifications.command_handler.requests.post") as mock_post:
            chm.handle_command("/mltrain BTCUSDT", "chat", {})
            assert called == [("BTCUSDT", "5m")]
            assert mock_post.call_count >= 2
        called.clear()
        monkeypatch.setattr(chm, "glob", SimpleNamespace(glob=lambda p: ["data/training_data/BTC_5m.csv", "data/training_data/ETH_5m.csv"]))
        with patch("notifications.command_handler.requests.post") as mock_post:
            chm.handle_command("/mltrain all", "chat", {})
            assert set(x[0] for x in called) == {"BTC", "ETH"}
            assert mock_post.call_count >= 1
        with patch("notifications.command_handler.requests.post") as mock_post:
            chm.handle_command("/mltrain btc$", "chat", {})
            assert "tidak valid" in mock_post.call_args.kwargs["data"]["text"]


def test_streamlit_train_button(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    os.makedirs("data/training_data", exist_ok=True)
    os.makedirs("models", exist_ok=True)

    class DummyStatus:
        def __enter__(self):
            return self
        def __exit__(self, *a):
            pass
        def update(self, label=None):
            pass
    msgs = {}
    dummy_st = SimpleNamespace(
        status=lambda *a, **k: DummyStatus(),
        success=lambda m: msgs.setdefault("success", m),
        table=lambda df: msgs.setdefault("table", df),
    )
    monkeypatch.setattr(main, "st", dummy_st)

    def fake_train(sym, tf):
        path = os.path.join("models", f"{sym}_scalping_{tf}.pkl")
        with open(path, "wb") as f:
            f.write(b"0")
        return 0.8

    monkeypatch.setattr(main, "training", SimpleNamespace(train_model=fake_train, MIN_DATA=0))

    def fake_hist(sym, tf, start, end):
        path = os.path.join("models", f"{sym}_scalping_{tf}.pkl")
        with open(path, "wb") as f:
            f.write(b"1")
        return {"train_accuracy": 0.7, "model": path}

    monkeypatch.setattr(
        main, "historical_trainer", SimpleNamespace(train_from_history=fake_hist)
    )
    main.train_selected_symbols(["BTCUSDT", "ETHUSDT"])
    assert msgs.get("success")
    assert os.path.exists("models/BTCUSDT_scalping_5m.pkl")
    assert len(msgs.get("table")) == 2
