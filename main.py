import streamlit as st
import os, json, timeit
from binance.client import Client
from execution.ws_listener import start_price_stream
from execution.ws_signal_listener import start_signal_stream, register_signal_handler
from execution.exit_monitor import start_exit_monitor
from utils.data_provider import load_symbol_filters
from utils.logger import setup_logger
from execution.signal_entry import on_signal
from utils.resume_helper import handle_resume, sync_with_binance

# --- Modular Imports ---
from config import BINANCE_KEYS
from database.sqlite_logger import init_db

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
api_key, api_secret = "", ""
start_price_stream(api_key, api_secret, multi_symbols)
active_positions = handle_resume(resume_flag, notif_resume)
if resume_flag:
    sync_with_binance(client)
if resume_flag and active_positions:
    st.sidebar.success(f"Resume {len(active_positions)} posisi aktif")
start_signal_stream(api_key, api_secret, client, multi_symbols, strategy_params)
symbol_steps = load_symbol_filters(client, multi_symbols)
start_exit_monitor(client, symbol_steps, notif_exit=notif_exit)

# --- WebSocket Signal Handler ---


# Register handler
for sym in multi_symbols:
    register_signal_handler(sym, on_signal)

st.success("✅ Bot siap, WebSocket signal aktif")
