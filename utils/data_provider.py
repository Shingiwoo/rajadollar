import pandas as pd
import streamlit as st
import json
from typing import Dict, List, Optional, Union
from binance.client import Client
from utils.safe_api import safe_api_call_with_retry
from utils.bot_flags import set_ready
from utils.notifikasi import kirim_notifikasi_telegram

def fetch_latest_data(symbol: str, client: Client, interval: str = '5m', limit: int = 100) -> pd.DataFrame:
    """
    Fetch OHLCV data dengan penanganan error lebih baik.
    Returns:
        DataFrame dengan kolom: timestamp, open, high, low, close, volume
    """
    try:
        klines = safe_api_call_with_retry(
            client.futures_klines,
            symbol=symbol,
            interval=interval,
            limit=limit
        )
        
        if not klines or isinstance(klines, str):
            st.warning(f"Gagal mendapatkan data untuk {symbol}")
            return pd.DataFrame()

        df = pd.DataFrame(klines, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_asset_volume', 'trades', 
            'taker_buy_base', 'taker_buy_quote', 'ignored'
        ])
        
        # Konversi tipe data
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        numeric_cols = ['open', 'high', 'low', 'close', 'volume']
        df[numeric_cols] = df[numeric_cols].astype(float)
        
        return df[['timestamp', 'open', 'high', 'low', 'close', 'volume']].set_index('timestamp')

    except Exception as e:
        st.error(f"Error processing data for {symbol}: {str(e)}")
        return pd.DataFrame()

def load_symbol_filters(client, coins):
    """Load trading filters dengan error handling lebih baik"""
    try:
        info = safe_api_call_with_retry(client.futures_exchange_info)
        if not info:
            st.warning("Gagal mendapatkan info exchange dari Binance")
            return {}

        symbol_filters = {}
        for s in info.get('symbols', []):
            if s.get('symbol') in coins:
                try:
                    # Cari filter LOT_SIZE
                    lot_filter = next(
                        (f for f in s.get('filters', []) 
                         if f.get('filterType') == 'LOT_SIZE'),
                        None
                    )
                    
                    # Cari filter NOTIONAL
                    notional_filter = next(
                        (f for f in s.get('filters', [])
                         if f.get('filterType') in ['MIN_NOTIONAL', 'NOTIONAL']),
                        None
                    )

                    if lot_filter and notional_filter:
                        step_size = float(lot_filter.get('stepSize', 0))
                        symbol_filters[s['symbol']] = {
                            'minQty': float(lot_filter.get('minQty', 0)),
                            'stepSize': step_size,
                            'step': step_size,
                            'minNotional': float(
                                notional_filter.get('minNotional', notional_filter.get('notional', 0))
                            )
                        }
                except Exception as e:
                    st.warning(f"Error processing filters for {s.get('symbol')}: {str(e)}")
                    continue

        return symbol_filters

    except Exception as e:
        st.error(f"Error loading symbol filters: {str(e)}")
        return {}

def get_futures_balance(client):
    try:
        func = getattr(client, "futures_account", None)
        if func is None:
            func = getattr(client, "futures_account_balance", None)
        if func is None:
            raise AttributeError("no futures account method")
        response = safe_api_call_with_retry(func)
        
        if isinstance(response, str) and "<html" in response.lower():
            raise ValueError("Binance returned HTML page instead of JSON")

        if isinstance(response, list):
            assets = response
        elif isinstance(response, dict):
            assets = response.get("assets", [])
        else:
            raise ValueError("Invalid response format")
        if not assets:
            raise ValueError("empty response")

        usdt = next((a for a in assets if a.get("asset") == "USDT"), None)
        if usdt is None:
            raise ValueError("USDT asset not found")

        bal = usdt.get("walletBalance") or usdt.get("balance")
        balance = float(bal)
        set_ready(True)
        return balance

    except Exception as e:
        import traceback
        st.error(f"Gagal sync saldo Binance: {e}")
        kirim_notifikasi_telegram(f"❌ Gagal sync saldo Binance: {e}")
        set_ready(False)
        return 0.0
