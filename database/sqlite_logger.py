import sqlite3
import pandas as pd
import os
from models.trade import Trade

DB_PATH = './runtime_state/trade_history.db'

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT, side TEXT,
            entry_time TEXT, entry REAL,
            exit_time TEXT, exit REAL,
            pnl REAL, size REAL
        )''')

def log_trade(trade: Trade):
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute('''INSERT INTO trades (symbol, side, entry_time, entry, exit_time, exit, pnl, size)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                  (trade.symbol, trade.side, trade.entry_time, trade.entry_price,
                   trade.exit_time, trade.exit_price, trade.pnl, trade.size))
        conn.commit()

def get_all_trades():
    with sqlite3.connect(DB_PATH) as conn:
        return pd.read_sql_query("SELECT * FROM trades ORDER BY entry_time DESC", conn)

def get_trades_filtered(symbol: str | None = None, start: str | None = None, end: str | None = None) -> pd.DataFrame:
    """Ambil histori trade dengan filter optional."""
    df = get_all_trades()
    if df.empty:
        return df
    if symbol:
        df = df[df['symbol'] == symbol.upper()]
    if start:
        df = df[pd.to_datetime(df['entry_time']) >= pd.to_datetime(start)]
    if end:
        df = df[pd.to_datetime(df['entry_time']) <= pd.to_datetime(end)]
    return df

def export_trades_csv(path: str) -> str:
    """Export seluruh histori trade ke CSV dan kembalikan path."""
    df = get_all_trades()
    if df.empty:
        df.to_csv(path, index=False)
    else:
        df.to_csv(path, index=False)
    return path
