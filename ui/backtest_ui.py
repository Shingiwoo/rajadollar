import os
import time
import datetime as dt
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
import requests
import streamlit as st
import plotly.graph_objects as go
from utils.config_loader import load_global_config, save_global_config

from backtest.engine import run_backtest
from backtest.metrics import calculate_metrics
from ml import training
from ml.historical_trainer import label_and_save

st.set_page_config(page_title="Backtest Multi-Simbol")
st.title("🔁 Backtest Multi-Simbol")

SYMBOL_FILE = "config/symbols.txt"
if os.path.exists(SYMBOL_FILE):
    with open(SYMBOL_FILE) as f:
        SEMUA_SIMBOL = [s.strip() for s in f if s.strip()]
else:
    SEMUA_SIMBOL = ["XRPUSDT", "DOGEUSDT", "TURBOUSDT"]

cfg = load_global_config()
tf_options = ["1m", "5m", "15m"]
tf = st.selectbox("Pilih Timeframe", tf_options, index=tf_options.index(cfg.get("selected_timeframe", "5m")))
if tf != cfg.get("selected_timeframe"):
    save_global_config({"selected_timeframe": tf})

simbol_terpilih = st.multiselect("Pilih Simbol", SEMUA_SIMBOL, default=SEMUA_SIMBOL[:3])
kol1, kol2 = st.columns(2)
with kol1:
    tanggal_mulai = st.date_input("Tanggal Mulai", dt.date.today() - dt.timedelta(days=1))
with kol2:
    tanggal_akhir = st.date_input("Tanggal Akhir", dt.date.today())

if "backtest_running" not in st.session_state:
    st.session_state.backtest_running = False

jalankan = st.button("Run Backtest", disabled=st.session_state.backtest_running)
if st.session_state.backtest_running:
    st.warning("⚠️ Backtest sedang berjalan! Jangan refresh atau tutup halaman!")
    st.markdown("""
<script>
  window.onbeforeunload = function() { return "Backtest sedang berjalan! Jangan refresh!"; };
</script>
""", unsafe_allow_html=True)


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
                trades, equity, _ = run_backtest(
                    df,
                    symbol=simbol,
                    start=str(tanggal_mulai),
                    end=str(tanggal_akhir),
                    timeframe=tf,
                )
                metrik, kurva = calculate_metrics(trades, equity)

            st.subheader(simbol)
            if metrik:
                cols = st.columns(len(metrik))
                for (k, v), col in zip(metrik.items(), cols):
                  if isinstance(v, pd.Timedelta):
                    v = str(v)
                  col.metric(k, v)
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
