import pandas as pd
import streamlit as st
from backtesting.data_loader import load_csv
from backtesting.backtest_engine import run_backtest
from backtesting.metrics import calculate_metrics

st.title("🔁 Backtest Scalping Strategy")
file = st.file_uploader("Upload Data CSV", type=["csv"])
if file:
    df = load_csv(file)
    trades, capital = run_backtest(df)
    st.success(f"Backtest selesai. Ending capital: ${capital:.2f}")

    metrics = calculate_metrics(trades)
    for k, v in metrics.items():
        st.metric(k, v)

    if trades:
        df_result = pd.DataFrame([t.to_dict() for t in trades])
        st.dataframe(df_result)
        st.line_chart(df_result['pnl'].cumsum())