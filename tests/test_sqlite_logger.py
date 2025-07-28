import os
import pandas as pd
from models.trade import Trade
from database import sqlite_logger as sl


def setup_db(tmp_path):
    sl.DB_PATH = str(tmp_path / "history.db")
    sl.init_db()
    trade = Trade(
        symbol="BTC",
        side="long",
        entry_time="2023-01-01T00:00:00",
        entry_price=100.0,
        exit_time="2023-01-01T01:00:00",
        exit_price=105.0,
        pnl=5.0,
        size=0.1,
        sl=95.0,
        tp=110.0,
    )
    sl.log_trade(trade)


def test_get_trades_filtered(tmp_path):
    setup_db(tmp_path)
    df = sl.get_trades_filtered(symbol="BTC")
    assert len(df) == 1
    df2 = sl.get_trades_filtered(symbol="ETH")
    assert df2.empty


def test_export_trades_csv(tmp_path):
    setup_db(tmp_path)
    path = sl.export_trades_csv(str(tmp_path / "out.csv"))
    assert os.path.exists(path)
    df = pd.read_csv(path)
    assert not df.empty
