import sqlite3
import pandas as pd
import os
from datetime import datetime, UTC

DB_PATH = './runtime_state/signal_history.db'

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT,
            time TEXT,
            direction TEXT,
            score REAL
        )''')


def log_signal(symbol: str, direction: str, score: float) -> None:
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute(
            'INSERT INTO signals (symbol, time, direction, score) VALUES (?,?,?,?)',
            (symbol, datetime.now(UTC).isoformat(), direction, score),
        )
        conn.commit()


def get_signals_today() -> pd.DataFrame:
    today = datetime.now(UTC).date().isoformat()
    with sqlite3.connect(DB_PATH) as conn:
        query = (
            "SELECT symbol, time, direction, score FROM signals "
            "WHERE DATE(time) = ? ORDER BY time DESC"
        )
        df = pd.read_sql_query(query, conn, params=(today,))
    return df
