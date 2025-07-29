import pandas as pd
import streamlit as st
from utils.safe_api import safe_api_call_with_retry
from utils.bot_flags import set_ready

def fetch_latest_data(symbol, client, interval='5m', limit=100):
    klines = safe_api_call_with_retry(
        client.futures_klines, symbol=symbol, interval=interval, limit=limit
    )
    if klines is None:
        return pd.DataFrame()
    df = pd.DataFrame(klines, columns=[
        'timestamp', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_asset_volume', 'trades', 'taker_buy_base', 'taker_buy_quote', 'ignored'
    ])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = df[col].astype(float)
    df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']].set_index('timestamp')
    return df

def load_symbol_filters(client, coins):
    symbol_filters = {}
    info = safe_api_call_with_retry(client.futures_exchange_info)
    if not info:
        return symbol_filters
    for s in info['symbols']:
        if s['symbol'] in coins:
            lot = next(f for f in s['filters'] if f['filterType'] == 'LOT_SIZE')
            min_qty = float(lot['minQty'])
            step_size = float(lot['stepSize'])
            notional_filter = next((f for f in s['filters'] if f['filterType'] in ['MIN_NOTIONAL','NOTIONAL']), None)
            min_notional = float(notional_filter.get('minNotional', notional_filter.get('notional', 0.0))) if notional_filter else 0.0
            symbol_filters[s['symbol']] = {'minQty': min_qty, 'stepSize': step_size, 'minNotional': min_notional}
    return symbol_filters

def get_futures_balance(client):
    balance = safe_api_call_with_retry(client.futures_account())
    if not balance:
        st.warning("Gagal sync saldo Binance")
        set_ready(False)
        return 0.0
    set_ready(True)
    for asset in balance:
        if asset['asset'] == 'USDT':
            return float(asset['balance'])
    return 0.0

