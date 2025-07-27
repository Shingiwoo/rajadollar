import streamlit as st
import time, threading, os, json, timeit, logging
import pandas as pd
from datetime import datetime, date
from typing import cast, Tuple

from binance.client import Client
from execution.ws_listener import start_price_stream, shared_price
from execution.ws_signal_listener import start_signal_stream, register_signal_handler
from utils.logger import setup_logger

# --- Modular Imports ---
from config import BINANCE_KEYS
from notifications.notifier import (
    kirim_notifikasi_telegram,
    kirim_notifikasi_entry,
    kirim_notifikasi_exit,
)
from utils.state_manager import save_state, load_state
from utils.safe_api import safe_api_call_with_retry
from strategies.scalping_strategy import apply_indicators, generate_signals
from execution.order_router import safe_futures_create_order, adjust_quantity_to_min, get_mark_price
from execution.slippage_handler import verify_price_before_order
from risk_management.position_manager import (
    apply_trailing_sl, can_open_new_position, update_open_positions,
    check_exit_condition, is_position_open
)
from risk_management.risk_checker import is_liquidation_risk
from risk_management.risk_calculator import calculate_order_qty
from database.sqlite_logger import log_trade, init_db, get_all_trades
from models.trade import Trade
from utils.data_provider import fetch_latest_data, load_symbol_filters, get_futures_balance

setup_logger()

def ping_latency(client):
    try:
        t0 = timeit.default_timer()
        client.ping()
        t1 = timeit.default_timer()
        return round((t1 - t0) * 1000, 2)
    except:
        return None

# --- UI Setup ---
st.set_page_config(page_title="RajaDollar Trading", layout="wide")
init_db()
mode = st.sidebar.selectbox("MODE Trading", ["Testnet (Simulasi)", "Real Trading"], index=0)

# --- API Key ---
api_key, api_secret = "", ""
if mode == "Real Trading":
    api_key = BINANCE_KEYS["real"]["API_KEY"]
    api_secret = BINANCE_KEYS["real"]["API_SECRET"]
    client = Client(api_key, api_secret)
elif mode == "Testnet (Simulasi)":
    api_key = BINANCE_KEYS["testnet"]["API_KEY"]
    api_secret = BINANCE_KEYS["testnet"]["API_SECRET"]
    client = Client(api_key, api_secret, testnet=True)
    client.API_URL = 'https://testnet.binancefuture.com/fapi'
else:
    client = None

# --- Load Strategy Config ---
STRAT_PATH = "config/strategy_params.json"
if not os.path.exists(STRAT_PATH):
    with open(STRAT_PATH, "w") as f:
        json.dump({}, f)
with open(STRAT_PATH, "r") as f:
    strategy_params = json.load(f)

st.sidebar.subheader("Strategi per Symbol")
if st.sidebar.checkbox("Edit strategy_params.json (Expert)"):
    txt = st.sidebar.text_area("JSON", json.dumps(strategy_params, indent=2), height=250)
    if st.sidebar.button("Save"):
        with open(STRAT_PATH, "w") as f: f.write(txt)
        st.sidebar.success("Tersimpan, reload app!")
        st.stop()

uploaded_file = st.sidebar.file_uploader("📥 Import Config .json", type=["json"])
if uploaded_file is not None:
    strategy_params = json.load(uploaded_file)
    with open(STRAT_PATH, "w") as f:
        json.dump(strategy_params, f, indent=2)
    st.sidebar.success("✅ Config diimpor, reload app!")
    st.stop()

st.sidebar.download_button("📤 Download strategy_params.json", json.dumps(strategy_params, indent=2), file_name="strategy_params.json")

# --- Trading Settings ---
multi_symbols = st.sidebar.multiselect("Pilih Symbols", list(strategy_params.keys()), default=list(strategy_params.keys()))
auto_sync = st.sidebar.checkbox("Sync Modal Binance", True)
leverage = st.sidebar.slider("Leverage", 1, 50, 20)
risk_pct = st.sidebar.number_input("Risk per Trade (%)", 0.01, 1.0, 0.02)
max_pos = st.sidebar.slider("Max Posisi", 1, 8, 4)
max_sym = st.sidebar.slider("Max Symbols Concurrent", 1, 4, 2)
max_slip = st.sidebar.number_input("Max Slippage (%)", 0.1, 1.0, 0.5)
resume_flag = st.sidebar.checkbox("Resume Otomatis", True)
notif_entry = st.sidebar.checkbox("Notifikasi Entry", True)
notif_exit = st.sidebar.checkbox("Notifikasi Exit", True)
notif_error = st.sidebar.checkbox("Notifikasi Error", True)
notif_resume = st.sidebar.checkbox("Notifikasi Resume", True)
lat = ping_latency(client)
st.sidebar.markdown(f"📶 Latency: `{lat} ms`" if lat else "❌ Ping gagal")

start_price_stream(api_key, api_secret, multi_symbols)
start_signal_stream(api_key, api_secret, client, multi_symbols, strategy_params)

# --- WebSocket Signal Handler ---
def on_signal(symbol, row):
    try:
        params = strategy_params[symbol]
        filters = load_symbol_filters(client, [symbol])
        active = load_state()
        open_pos = []
        price = shared_price.get(symbol, row['close'])

        for side in ['long', 'short']:
            sig = row['long_signal'] if side == 'long' else row['short_signal']
            if not sig or not can_open_new_position(symbol, max_pos, max_sym, open_pos):
                continue
            if is_position_open(active, symbol, side) or is_liquidation_risk(price, side, leverage):
                continue
            if not verify_price_before_order(client, symbol, "BUY" if side == 'long' else "SELL", price, max_slip / 100):
                continue

            qty = calculate_order_qty(symbol, price, price*(0.99 if side=='long' else 1.01),
                                       get_futures_balance(client) if auto_sync else 1000, risk_pct, leverage)
            qty = adjust_quantity_to_min(symbol, qty, price, filters)
            order = safe_api_call_with_retry(safe_futures_create_order, client, symbol,
                                             "BUY" if side == 'long' else "SELL", "MARKET", qty, filters)
            if order:
                oid = order.get("orderId", str(int(time.time())))
                now = datetime.utcnow().isoformat()
                sl = price * (0.99 if side == 'long' else 1.01)
                tp = price * (1.02 if side == 'long' else 0.98)
                trade = Trade(symbol, side, now, price, qty, sl, tp, sl, order_id=oid,
                              trailing_offset=params.get("trailing_offset", 0.25),
                              trigger_threshold=params.get("trigger_threshold", 0.5))
                active.append(trade.to_dict())
                save_state(active)
                update_open_positions(symbol, side, qty, price, 'open', open_pos)
                if notif_entry:
                    kirim_notifikasi_entry(symbol, price, sl, tp, qty, oid)
    except Exception as e:
        if notif_error:
            kirim_notifikasi_telegram(f"⚠ [WebSocket Entry] {symbol} error: {e}")

# Register handler
for sym in multi_symbols:
    register_signal_handler(sym, on_signal)

st.success("✅ Bot siap, WebSocket signal aktif")
