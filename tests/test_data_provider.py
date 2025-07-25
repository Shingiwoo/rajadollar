import os
import sys
import pandas as pd
from config import BINANCE_KEYS
from utils.data_provider import fetch_latest_data, load_symbol_filters
from binance.client import Client

def test_fetch_latest_data():
    client = Client(
        BINANCE_KEYS["testnet"]["API_KEY"],
        BINANCE_KEYS["testnet"]["API_SECRET"],
        testnet=True
    )
    df = fetch_latest_data("BTCUSDT", client, interval='1m', limit=10)
    assert not df.empty
    assert "close" in df.columns
    print(df.tail())

def test_load_symbol_filters():
    client = Client(
        BINANCE_KEYS["testnet"]["API_KEY"],
        BINANCE_KEYS["testnet"]["API_SECRET"],
        testnet=True
    )
    filters = load_symbol_filters(client, ["BTCUSDT"])
    assert "BTCUSDT" in filters
    assert "minQty" in filters["BTCUSDT"]
    print(filters["BTCUSDT"])

if __name__ == "__main__":
    test_fetch_latest_data()
    test_load_symbol_filters()
