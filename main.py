import streamlit as st
from models.trade import Trade
from utils.state_manager import save_state, load_state, delete_state
from notifications.notifier import kirim_notifikasi_telegram
from strategies.scalping_strategy import apply_indicators, generate_signals
from execution.order_router import safe_futures_create_order
from execution.order_monitor import check_exit_condition
from risk_management.position_manager import apply_trailing_sl
from database.sqlite_logger import log_trade, get_all_trades, init_db

resume_flag = st.sidebar.checkbox("Aktifkan Resume Otomatis", value=True)
notif_entry = st.sidebar.checkbox("Notifikasi Entry", value=True)
notif_exit = st.sidebar.checkbox("Notifikasi Exit", value=True)
notif_error = st.sidebar.checkbox("Notifikasi Error", value=True)
notif_resume = st.sidebar.checkbox("Notifikasi Resume Start", value=True)

init_db()
active_positions = []

if resume_flag:
    active_positions = load_state()
    if active_positions and notif_resume:
        symbols = ", ".join([pos['symbol'] for pos in active_positions])
        kirim_notifikasi_telegram(f"✅ *Bot Resumed*: Memulihkan posisi aktif {len(active_positions)} koin ({symbols})")
else:
    delete_state()

if st.sidebar.button("Lihat Trade History"):
    df = get_all_trades()
    if not df.empty:
        st.dataframe(df)
        st.line_chart(df['pnl'].cumsum())
    else:
        st.warning("Tidak ada histori trade.")
