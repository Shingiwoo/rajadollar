import streamlit as st
from database.sqlite_logger import get_all_trades, init_db

st.set_page_config(page_title="📊 Trade Dashboard", layout="wide")
st.title("📈 Histori Trading & Analisis")

init_db()

if st.button("Tampilkan Trade History"):
    df = get_all_trades()
    if not df.empty:
        st.dataframe(df)
        st.line_chart(df['pnl'].cumsum(), use_container_width=True)
        st.metric("Total Trades", len(df))
        st.metric("Total PnL", f"${df['pnl'].sum():.2f}")
    else:
        st.info("Belum ada histori trade.")
