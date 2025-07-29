import pandas as pd
import streamlit as st
from utils.safe_api import safe_api_call_with_retry
from utils.bot_flags import set_ready
from utils.notifikasi import kirim_notifikasi_telegram

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
    try:
        response = safe_api_call_with_retry(client.futures_account)
        if isinstance(response, str) and "<html" in response.lower():
            raise ValueError("Binance returned HTML, likely due to invalid base URL")
        if not response:
            st.warning("❌ Gagal sync saldo Binance")
            kirim_notifikasi_telegram("❌ Gagal sync saldo Binance")
            set_ready(False)
            return 0.0

        set_ready(True)
        assets = response.get('assets', [])
        usdt = next((a for a in assets if a['asset'] == 'USDT'), None)
        return float(usdt['balance']) if usdt else 0.0

    except Exception as e:
        st.error(f"Gagal mengambil saldo Binance Futures: {e}")
        kirim_notifikasi_telegram(f"🔴 Gagal sync saldo: {e}")
        set_ready(False)
        return 0.0


