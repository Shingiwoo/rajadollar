import pandas as pd
import streamlit as st
import json
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
        
        # Debug: Cetak tipe dan isi response
        print(f"Response type: {type(response)}")
        print(f"Response content: {response}")
        
        # Penanganan response tidak valid
        if isinstance(response, str):
            if "<html" in response.lower():
                raise ValueError("Binance returned HTML, likely due to invalid base URL")
            try:
                # Coba parse string sebagai JSON
                response = json.loads(response)
            except json.JSONDecodeError:
                raise ValueError(f"Invalid API response: {response}")
        
        if not response or not isinstance(response, dict):
            st.warning("❌ Gagal sync saldo Binance (invalid response format)")
            kirim_notifikasi_telegram("❌ Gagal sync saldo Binance: invalid response format")
            set_ready(False)
            return 0.0

        set_ready(True)
        
        # Struktur response yang mungkin:
        # 1. Untuk futures_account: {'assets': [{'asset': 'USDT', 'balance': '100.00'}]}
        # 2. Untuk futures_account_balance: [{'asset': 'USDT', 'balance': '100.00'}]
        
        # Cek kedua kemungkinan struktur response
        if 'assets' in response:  # Jika response adalah futures_account
            assets = response.get('assets', [])
        else:  # Jika response adalah futures_account_balance
            assets = response if isinstance(response, list) else []
        
        usdt = next((a for a in assets if a.get('asset') == 'USDT'), None)
        return float(usdt.get('balance', 0)) if usdt else 0.0

    except Exception as e:
        st.error(f"Gagal mengambil saldo Binance Futures: {str(e)}")
        kirim_notifikasi_telegram(f"🔴 Gagal sync saldo: {str(e)}")
        set_ready(False)
        return 0.0


