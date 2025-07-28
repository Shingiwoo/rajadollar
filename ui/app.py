import streamlit as st
import time
import pandas as pd
from database.sqlite_logger import (
    get_all_trades,
    init_db,
    get_trades_filtered,
)
from utils.state_manager import load_state

def auto_refresh(interval: int = 10):
    if "_last_refresh" not in st.session_state:
        st.session_state["_last_refresh"] = time.time()
    if time.time() - st.session_state["_last_refresh"] > interval:
        st.session_state["_last_refresh"] = time.time()
        st.experimental_rerun()

st.set_page_config(page_title="📊 Trade Dashboard", layout="wide")
st.title("📈 Dashboard Trading")

init_db()

interval = st.sidebar.number_input("Refresh tiap (detik)", 5, 60, 10)
auto_refresh(interval)

df_all = get_all_trades()
open_pos = load_state()

st.subheader("📌 Posisi Terbuka")
if open_pos:
    st.dataframe(pd.DataFrame(open_pos))
else:
    st.info("Tidak ada posisi aktif.")

st.subheader("📊 Histori Trading")
if df_all.empty:
    st.info("Belum ada histori trade.")
else:
    col1, col2 = st.columns(2)
    with col1:
        symbol_sel = st.selectbox(
            "Symbol",
            ["Semua"] + sorted(df_all["symbol"].unique().tolist()),
        )
    with col2:
        start = st.date_input("Dari", value=None)
        end = st.date_input("Sampai", value=None)

    symbol = None if symbol_sel == "Semua" else symbol_sel
    df = get_trades_filtered(symbol, start.isoformat() if start else None, end.isoformat() if end else None)

    st.dataframe(df)
    st.line_chart(df["pnl"].cumsum(), use_container_width=True)

    daily = df.copy()
    daily["date"] = pd.to_datetime(daily["entry_time"]).dt.date
    daily_pnl = daily.groupby("date")["pnl"].sum()
    win_rate = 0.0
    profit_factor = 0.0
    last7 = daily[daily["date"] >= (pd.to_datetime("today").date() - pd.Timedelta(days=6))]
    if not last7.empty:
        win = (last7["pnl"] > 0).sum()
        win_rate = (win / len(last7)) * 100
        gain = last7[last7["pnl"] > 0]["pnl"].sum()
        loss = abs(last7[last7["pnl"] <= 0]["pnl"].sum())
        profit_factor = gain / loss if loss else float("inf")

    st.metric("Total Trades", len(df))
    st.metric("Total PnL", f"${df['pnl'].sum():.2f}")
    st.metric("Win Rate 7 Hari", f"{win_rate:.2f}%")
    st.metric("Profit Factor 7 Hari", f"{profit_factor:.2f}")

    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button("📥 Export CSV", csv, file_name="trade_history.csv")
