import os
import time
import datetime as dt
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
import requests
import streamlit as st
import plotly.graph_objects as go
import json

from backtest.engine import run_backtest
from backtest.metrics import calculate_metrics
from backtest.optimizer import optimize_strategy
from ml import training
from ml.historical_trainer import label_and_save
from utils.historical_data import MAX_DAYS

st.set_page_config(page_title="Backtest Multi-Simbol")
st.title("Backtest Multi-Simbol")

# Hanya inisialisasi sekali, sebelum form!
for k, v in {
    "tf": "5m",
    "initial_capital": 1000,
    "risk_per_trade": 1.0,
    "leverage": 20,
}.items():
    if k not in st.session_state:
        st.session_state[k] = v

with st.form("param_backtest"):
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        tf = st.selectbox(
            "Pilih Timeframe", ["1m", "5m", "15m"],
            index=["1m", "5m", "15m"].index(st.session_state["tf"]),
            key="tf"
        )
    with col2:
        initial_capital = st.number_input(
            "Initial Capital ($)", min_value=10, value=st.session_state["initial_capital"], key="initial_capital"
        )
    with col3:
        risk_per_trade = st.number_input(
            "Risk per Trade (%)", min_value=0.1, max_value=10.0, value=st.session_state["risk_per_trade"], key="risk_per_trade"
        )
    with col4:
        leverage = st.number_input(
            "Leverage", min_value=1, max_value=125, value=st.session_state["leverage"], key="leverage"
        )
    submit_param = st.form_submit_button("Set Parameter")

# ❗❗❗ JANGAN set session_state["tf"] = tf, dsb. Streamlit sudah otomatis!

tf = st.session_state["tf"]
initial_capital = st.session_state["initial_capital"]
risk_per_trade = st.session_state["risk_per_trade"]
leverage = st.session_state["leverage"]

SYMBOL_FILE = "config/symbols.txt"
if os.path.exists(SYMBOL_FILE):
    with open(SYMBOL_FILE) as f:
        SEMUA_SIMBOL = [s.strip() for s in f if s.strip()]
else:
    SEMUA_SIMBOL = ["XRPUSDT", "DOGEUSDT", "TURBOUSDT"]

STRAT_PATH = "config/strategy_params.json"
if os.path.exists(STRAT_PATH):
    with open(STRAT_PATH) as f:
        STRATEGY_PARAMS = json.load(f)
else:
    STRATEGY_PARAMS = {}

simbol_terpilih = st.multiselect("Pilih Simbol", SEMUA_SIMBOL, default=SEMUA_SIMBOL[:3])
kol1, kol2 = st.columns(2)
with kol1:
    tanggal_mulai = st.date_input("Tanggal Mulai", dt.date.today() - dt.timedelta(days=1))
with kol2:
    tanggal_akhir = st.date_input("Tanggal Akhir", dt.date.today())

if (tanggal_akhir - tanggal_mulai).days > MAX_DAYS.get(tf, 30):
    st.error(
        f"Rentang tanggal terlalu panjang untuk TF {tf}. Maksimum {MAX_DAYS.get(tf, 30)} hari."
    )
    st.stop()

if "backtest_running" not in st.session_state:
    st.session_state.backtest_running = False

col_btn1, col_btn2 = st.columns(2)
with col_btn1:
    do_optimize = st.button("🔎 Optimasi Parameter", key="btn_optimize")
with col_btn2:
    jalankan = st.button(
        "🔁 Backtest Pakai Param Optimal",
        key="btn_backtest",
        disabled=st.session_state.backtest_running,
    )
if st.session_state.backtest_running:
    st.warning("⚠️ Backtest sedang berjalan! Jangan refresh atau tutup halaman!")
    st.markdown(
        """
<script>
  window.onbeforeunload = function() { return "Backtest sedang berjalan! Jangan refresh!"; };
</script>
""",
        unsafe_allow_html=True,
    )

if do_optimize:
    if not simbol_terpilih:
        st.warning("Silakan pilih minimal satu simbol.")
    else:
        for simbol in simbol_terpilih:
            with st.spinner(f"Optimasi {simbol}..."):
                try:
                    best_param, best_metrik = optimize_strategy(
                        simbol, tf, str(tanggal_mulai), str(tanggal_akhir)
                    )
                    STRATEGY_PARAMS[simbol] = best_param or {}
                    with open(STRAT_PATH, "w") as f:
                        json.dump(STRATEGY_PARAMS, f, indent=2)
                    winrate = best_metrik.get("Persentase Menang", 0) if best_metrik else 0
                    pf = best_metrik.get("Profit Factor", 0) if best_metrik else 0
                    pesan = f"Optimasi {simbol} selesai. Winrate: {winrate:.2f}% PF: {pf:.2f}"
                    if winrate < 70 or pf <= 3:
                        st.warning(pesan)
                    else:
                        st.success(pesan)
                    if best_param:
                        st.json(best_param)
                except Exception as e:
                    st.error(f"Optimasi {simbol} gagal: {e}")


def unduh_klines(simbol: str, mulai_ms: int, akhir_ms: int, timeframe: str) -> pd.DataFrame:
    url = "https://api.binance.com/api/v3/klines"
    batas = 1000
    data = []
    awal = mulai_ms
    step = int(timeframe.rstrip("m")) * 60 * 1000
    while awal < akhir_ms:
        params = {
            "symbol": simbol,
            "interval": timeframe,
            "startTime": awal,
            "endTime": min(awal + batas * step, akhir_ms),
            "limit": batas,
        }
        r = requests.get(url, params=params, timeout=10)
        if r.status_code != 200:
            raise RuntimeError(r.text)
        klines = r.json()
        if not klines:
            break
        data.extend(klines)
        awal = klines[-1][0] + step
        time.sleep(0.2)  # antisipasi limit
    kolom = [
        "timestamp",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "close_time",
        "quote_asset_volume",
        "number_of_trades",
        "taker_buy_base_asset_volume",
        "taker_buy_quote_asset_volume",
        "ignore",
    ]
    df = pd.DataFrame(data, columns=kolom)
    df = df[["timestamp", "open", "high", "low", "close", "volume"]]
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df.set_index("timestamp", inplace=True)
    return df.astype(float)


if jalankan:
    if not simbol_terpilih:
        st.warning("Silakan pilih minimal satu simbol.")
    else:
        st.session_state.backtest_running = True
        os.makedirs("data/training_data", exist_ok=True)
        mulai_dt = dt.datetime.combine(tanggal_mulai, dt.time())
        akhir_dt = dt.datetime.combine(tanggal_akhir, dt.time()) + dt.timedelta(days=1)
        mulai_ms = int(mulai_dt.timestamp() * 1000)
        akhir_ms = int(akhir_dt.timestamp() * 1000)

        progress = st.progress(0.0)
        hasil_data: dict[str, pd.DataFrame] = {}

        def pekerja(simbol: str):
            df = unduh_klines(simbol, mulai_ms, akhir_ms, tf)
            path = f"data/training_data/{simbol}_{tf}.csv"
            df.to_csv(path)
            return simbol, df

        futures = []
        with ThreadPoolExecutor(max_workers=min(4, len(simbol_terpilih))) as ex:
            for s in simbol_terpilih:
                futures.append(ex.submit(pekerja, s))
            for i, fut in enumerate(as_completed(futures), 1):
                try:
                    simbol, df = fut.result()
                    hasil_data[simbol] = df
                except Exception as e:
                    st.error(f"Gagal mengunduh {s}: {e}")
                progress.progress(i / len(simbol_terpilih))
        progress.empty()
        for simbol, df in hasil_data.items():
            params = STRATEGY_PARAMS.get(simbol)
            if not params:
                with st.spinner(f"Otomatis optimasi param {simbol}..."):
                    try:
                        params, met_opt = optimize_strategy(
                            simbol, tf, str(tanggal_mulai), str(tanggal_akhir)
                        )
                        STRATEGY_PARAMS[simbol] = params or {}
                        with open(STRAT_PATH, "w") as f:
                            json.dump(STRATEGY_PARAMS, f, indent=2)
                        winrate = met_opt.get("Persentase Menang", 0) if met_opt else 0
                        pf = met_opt.get("Profit Factor", 0) if met_opt else 0
                        pesan = f"Winrate: {winrate:.2f}% PF: {pf:.2f}"
                        if winrate < 70 or pf <= 3:
                            st.warning(pesan)
                        else:
                            st.success(pesan)
                        if params:
                            st.json(params)
                    except Exception as e:
                        st.error(f"Optimasi {simbol} gagal: {e}")
                        continue
            path = f"data/training_data/{simbol}_{tf}.csv"
            try:
                df_check = pd.read_csv(path, nrows=1)
                need_label = "label" not in df_check.columns
            except Exception:
                need_label = True
            if need_label:
                with st.spinner(f"Labeling {simbol}..."):
                    try:
                        label_and_save(simbol, tf)
                    except Exception as e:
                        st.error(f"Labeling {simbol} gagal: {e}")
                        continue
            try:
                df_check = pd.read_csv(path, nrows=1)
            except Exception as e:
                st.error(f"Data {simbol} tidak bisa dibaca: {e}")
                continue
            if "label" not in df_check.columns:
                st.warning(f"{simbol} masih tanpa label, training dilewati")
                continue
            with st.spinner(f"Training {simbol}"):
                try:
                    training.train_model(simbol, tf)
                except Exception as e:
                    st.error(f"Training {simbol} gagal: {e}")
                    continue
            with st.spinner(f"Menjalankan backtest {simbol}"):
                cfg_sym = STRATEGY_PARAMS.get(simbol, {})
                trades, equity, _ = run_backtest(
                    df,
                    symbol=simbol,
                    start=str(tanggal_mulai),
                    end=str(tanggal_akhir),
                    timeframe=tf,
                    initial_capital=initial_capital,
                    config=cfg_sym,
                    score_threshold=cfg_sym.get("score_threshold", 1.4),
                    risk_per_trade=risk_per_trade,
                    leverage=leverage,
                )
                metrik, kurva = calculate_metrics(trades, equity)

            st.subheader(simbol)
            if metrik:
                winrate = metrik.get("Persentase Menang", 0)
                pf = metrik.get("Profit Factor", 0)
                pesan_bt = f"Winrate: {winrate:.2f}% PF: {pf:.2f}"
                if winrate < 70 or pf <= 3:
                    st.warning(pesan_bt)
                else:
                    st.success(pesan_bt)
                cols = st.columns(len(metrik))
                for (k, v), col in zip(metrik.items(), cols):
                    if isinstance(v, pd.Timedelta):
                        v = str(v)
                    col.metric(k, v)
            params = STRATEGY_PARAMS.get(simbol, {})
            st.json(params)
            if kurva is not None:
                fig = go.Figure()
                fig.add_trace(
                    go.Scatter(x=kurva.index, y=kurva["equity"], name="Ekuitas")
                )
                fig.add_trace(
                    go.Scatter(
                        x=kurva.index,
                        y=kurva["drawdown"],
                        name="Drawdown",
                        yaxis="y2",
                    )
                )
                fig.update_layout(
                    yaxis2=dict(overlaying="y", side="right"), legend=dict(orientation="h")
                )
                st.plotly_chart(fig, use_container_width=True)
            if trades:
                df_trades = pd.DataFrame([t.to_dict() for t in trades])
                st.dataframe(df_trades)
        st.session_state.backtest_running = False
