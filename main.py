import streamlit as st
import os, json, timeit, asyncio
import pandas as pd
import nest_asyncio
import logging

from dotenv import load_dotenv
from utils.logger import setup_logger
from utils.binance_helper import create_client
from utils.trading_controller import start_bot, stop_bot
import utils.bot_flags as bot_flags
from database.sqlite_logger import init_db
from ml import training, historical_trainer
from utils.config_loader import load_global_config, save_global_config
from utils.historical_data import MAX_DAYS

# === SETUP ===
nest_asyncio.apply()
setup_logger()
load_dotenv()
init_db()

# === UTIL ===
def build_cfg(api_key, api_secret, client, symbols, strategy_params, auto_sync,
              leverage, risk_pct, max_pos, max_sym, max_slip, loss_limit,
              notif_entry, notif_exit, notif_error, notif_resume, resume_flag,
              timeframe="5m"):
    return {
        "api_key": api_key,
        "api_secret": api_secret,
        "client": client,
        "symbols": list(symbols),
        "strategy_params": strategy_params,
        "auto_sync": auto_sync,
        "leverage": int(leverage),
        "risk_pct": float(risk_pct),
        "max_pos": int(max_pos),
        "max_sym": int(max_sym),
        "max_slip": float(max_slip),
        "loss_limit": float(loss_limit),
        "notif_entry": notif_entry,
        "notif_exit": notif_exit,
        "notif_error": notif_error,
        "notif_resume": notif_resume,
        "resume_flag": resume_flag,
        "timeframe": timeframe,
    }

# === STREAMLIT CONFIG ===
st.set_page_config(page_title="RajaDollar Trading", layout="wide")
st.title("🤖 RajaDollar Bot")

if "bot_running" not in st.session_state:
    st.session_state.bot_running = False
    st.session_state.handles = {}
    st.session_state.stop_signal = False

# === MODE & API KEY ===
mode = st.sidebar.selectbox("Mode", ["testnet", "real"], index=0)
client = create_client(mode)
if client:
    api_key = client.API_KEY
    api_secret = client.API_SECRET
else:
    api_key = api_secret = ""

# === Latency Ping ===
def ping_latency(client):
    try:
        t0 = timeit.default_timer()
        client.ping()
        t1 = timeit.default_timer()
        return round((t1 - t0) * 1000, 2)
    except:
        return None

lat = ping_latency(client) if client else None
st.sidebar.markdown(f"📶 Latency: `{lat} ms`" if lat else "❌ Ping gagal")

# === STRATEGY CONFIG ===
STRAT_PATH = "config/strategy_params.json"
if not os.path.exists(STRAT_PATH):
    with open(STRAT_PATH, "w") as f: json.dump({}, f)
with open(STRAT_PATH, "r") as f:
    strategy_params = json.load(f)

cfg_global = load_global_config()
tf_options = ["1m", "5m", "15m"]
tf = st.sidebar.selectbox("Pilih Timeframe", tf_options, index=tf_options.index(cfg_global.get("selected_timeframe", "5m")))
if tf != cfg_global.get("selected_timeframe"):
    if not save_global_config({"selected_timeframe": tf}):
        st.sidebar.error("Tidak bisa menyimpan config global")

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
    with open(STRAT_PATH, "w") as f: json.dump(strategy_params, f, indent=2)
    st.sidebar.success("✅ Config diimpor, reload app!")
    st.stop()

st.sidebar.download_button("📤 Download strategy_params.json", json.dumps(strategy_params, indent=2), file_name="strategy_params.json")

# === TRADING SETTINGS ===
multi_symbols = st.sidebar.multiselect("Pilih Symbols", list(strategy_params.keys()), default=list(strategy_params.keys()))
auto_sync = st.sidebar.checkbox("Sync Modal Binance", True)
leverage = st.sidebar.slider("Leverage", 1, 50, 20)
risk_pct = st.sidebar.number_input("Risk per Trade (%) (scalp)", 0.01, 1.0, 0.01)
max_pos = st.sidebar.slider("Max Posisi", 1, 8, 4)
max_sym = st.sidebar.slider("Max Symbols Concurrent", 1, 4, 2)
max_slip = st.sidebar.number_input("Max Slippage (%)", 0.1, 1.0, 0.5)
score_threshold = st.sidebar.number_input("Ambang Skor", 0.0, 3.0, 1.8, 0.1)
ml_conf_threshold = st.sidebar.slider("Ambang Kepercayaan ML", 0.0, 1.0, 0.7, 0.05)
hybrid_fallback = st.sidebar.checkbox("Hybrid Fallback", True)
only_trend_15m = st.sidebar.checkbox("Hanya entry searah trend 15m", True)
loss_limit = st.sidebar.number_input("Batas Loss Harian (USDT)", -1000.0, 0.0, -50.0, step=10.0)
resume_flag = st.sidebar.checkbox("Resume Otomatis", True)
notif_entry = st.sidebar.checkbox("Notifikasi Entry", True)
notif_exit = st.sidebar.checkbox("Notifikasi Exit", True)
notif_error = st.sidebar.checkbox("Notifikasi Error", True)
notif_resume = st.sidebar.checkbox("Notifikasi Resume", True)

st.sidebar.subheader("Status Model ML")
for sym in strategy_params.keys():
    model_path = os.path.join("models", f"{sym}_scalping_{tf}.pkl")
    mark = "✔ ready" if os.path.exists(model_path) else "❌ not trained"
    st.sidebar.write(f"{sym}: {mark}")

if mode == "testnet":
    for sym in multi_symbols:
        model_path = os.path.join("models", f"{sym}_scalping_{tf}.pkl")
        if not os.path.exists(model_path):
            st.sidebar.info(
                f"No ML model for {sym} yet. Sistem akan melatih otomatis dari histori."
            )

train_clicked = st.sidebar.button(
    "Train All Selected Symbols", disabled=len(multi_symbols) == 0
)

st.sidebar.write("Status: " + ("🟢 Bot aktif" if st.session_state.bot_running else "🔴 Bot nonaktif"))

# === UI Control Buttons ===
col1, col2 = st.columns(2)
with col1:
    start_clicked = st.button("🚀 START", disabled=st.session_state.bot_running)
with col2:
    stop_clicked = st.button("🛑 STOP", disabled=not st.session_state.bot_running)

# === START ===
if start_clicked and not st.session_state.bot_running:
    if not api_key or not api_secret:
        st.error("❌ API key kosong.")
    else:
        for sym in multi_symbols:
            strategy_params.setdefault(sym, {})
            strategy_params[sym]["score_threshold"] = score_threshold
            strategy_params[sym]["ml_conf_threshold"] = ml_conf_threshold
            strategy_params[sym]["hybrid_fallback"] = hybrid_fallback
            strategy_params[sym]["only_trend_15m"] = only_trend_15m
        cfg = build_cfg(
            api_key,
            api_secret,
            client,
            multi_symbols,
            strategy_params,
            auto_sync,
            leverage,
            risk_pct,
            max_pos,
            max_sym,
            max_slip,
            loss_limit,
            notif_entry,
            notif_exit,
            notif_error,
            notif_resume,
            resume_flag,
            tf,
        )
        st.session_state.stop_signal = False
        logging.info(
            f"Start bot with max_pos={max_pos}, max_sym={max_sym}, risk_pct={risk_pct}"
        )
        st.session_state.handles = start_bot(cfg)
        if bot_flags.IS_READY:
            st.session_state.bot_running = True
            st.success("✅ Bot berjalan.")
            st.info("Bot aktif & menunggu sinyal")
        else:
            st.error("❌ Gagal sync saldo Binance.")

# === STOP ===
if stop_clicked and st.session_state.bot_running:
    st.session_state.stop_signal = True
    stop_bot(st.session_state.handles)
    st.session_state.bot_running = False
    st.success("🛑 Bot dihentikan.")

# === TRAIN MODELS ===
def train_selected_symbols(symbols):
    """Latih semua simbol dan tampilkan hasil di UI."""
    results = {}
    with st.status("Melatih model...", expanded=True) as status:
        for sym in symbols:
            status.update(label=f"{sym} sedang diproses")
            csv_path = os.path.join("data", "training_data", f"{sym}_{tf}.csv")
            use_existing = False
            if os.path.exists(csv_path):
                try:
                    df = pd.read_csv(csv_path)
                except Exception as e:
                    df = pd.DataFrame()
                    logging.error(f"[ML] Gagal membaca {csv_path}: {e}")
                else:
                    if "label" in df.columns and len(df.dropna(subset=training.FEATURE_COLS + ["label"])) >= training.MIN_DATA:
                        use_existing = True

            if use_existing:
                acc = training.train_model(sym, tf)
            else:
                end = pd.Timestamp.utcnow().date().isoformat()
                start = (
                    pd.Timestamp.utcnow() - pd.Timedelta(days=MAX_DAYS.get(tf, 30))
                ).date().isoformat()
                res = historical_trainer.train_from_history(sym, tf, start, end)
                acc = res.get("train_accuracy", 0.0) if res else 0.0
            results[sym] = acc
            status.update(label=f"{sym} selesai: {acc:.2%}")

    st.success(
        "Training selesai untuk symbols: " + ", ".join(symbols) + ". Model disimpan di folder /models."
    )
    if results:
        st.table(
            pd.DataFrame([
                {"Symbol": k, "Akurasi": f"{v:.2%}"} for k, v in results.items()
            ])
        )


if train_clicked:
    train_selected_symbols(multi_symbols)
