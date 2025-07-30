import streamlit as st
import os, json, timeit
from utils.binance_helper import create_client
from utils.trading_controller import start_bot, stop_bot
import utils.bot_flags as bot_flags
from utils.logger import setup_logger
import asyncio
nest_asyncio.apply()

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
if "bot_running" not in st.session_state:
    st.session_state.bot_running = False
    st.session_state.handles = {}
    st.session_state.stop_signal = False

mode = st.sidebar.selectbox("Mode", ["testnet", "real"], index=0)

# --- API Key ---
client = create_client(mode)
if client:
    api_key = client.API_KEY
    api_secret = client.API_SECRET
else:
    api_key = api_secret = ""

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
loss_limit = st.sidebar.number_input("Batas Loss Harian (USDT)", -1000.0, 0.0, -50.0, step=10.0)
resume_flag = st.sidebar.checkbox("Resume Otomatis", True)
notif_entry = st.sidebar.checkbox("Notifikasi Entry", True)
notif_exit = st.sidebar.checkbox("Notifikasi Exit", True)
notif_error = st.sidebar.checkbox("Notifikasi Error", True)
notif_resume = st.sidebar.checkbox("Notifikasi Resume", True)
lat = ping_latency(client) if client else None
st.sidebar.markdown(f"📶 Latency: `{lat} ms`" if lat else "❌ Ping gagal")

col1, col2 = st.columns(2)
with col1:
    start_clicked = st.button("START", disabled=st.session_state.bot_running)
with col2:
    stop_clicked = st.button("STOP", disabled=not st.session_state.bot_running)

st.sidebar.write(
    "Status: " + ("🟢 Bot running" if st.session_state.bot_running else "🔴 Bot stopped")
)

if start_clicked and not st.session_state.bot_running:
    if not api_key or not api_secret:
        st.error("API key kosong")
    else:
        cfg = {
            "api_key": api_key,
            "api_secret": api_secret,
            "client": client,
            "symbols": multi_symbols,
            "strategy_params": strategy_params,
            "auto_sync": auto_sync,
            "leverage": leverage,
            "risk_pct": risk_pct / 100 if risk_pct > 1 else risk_pct,
            "max_pos": max_pos,
            "max_sym": max_sym,
            "max_slip": max_slip,
            "notif_entry": notif_entry,
            "notif_error": notif_error,
            "notif_exit": notif_exit,
            "loss_limit": loss_limit,
            "resume_flag": resume_flag,
            "notif_resume": notif_resume,
        }
        st.session_state.stop_signal = False
        st.session_state.handles = start_bot(cfg)
        if bot_flags.IS_READY:
            st.session_state.bot_running = True
            st.success("✅ Bot berjalan")
        else:
            st.error("Gagal sync saldo Binance")

if stop_clicked and st.session_state.bot_running:
    st.session_state.stop_signal = True
    stop_bot(st.session_state.handles)
    st.session_state.bot_running = False
    st.success("🛑 Bot dihentikan")
