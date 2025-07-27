import streamlit as st
import time
import threading
import pandas as pd
import os
import json
from datetime import datetime, date
from typing import cast, Tuple

from binance.client import Client
from binance.exceptions import BinanceAPIException

# --- Import Modular ---
from config import BINANCE_KEYS
from notifications.notifier import (
    kirim_notifikasi_telegram,
    kirim_notifikasi_entry,
    kirim_notifikasi_exit,
)
from utils.state_manager import save_state, load_state, delete_state
from utils.safe_api import safe_api_call_with_retry
from strategies.scalping_strategy import apply_indicators, generate_signals
from execution.order_router import (
    safe_futures_create_order,
    adjust_quantity_to_min,
    get_mark_price,
)
from execution.slippage_handler import verify_price_before_order
from risk_management.position_manager import (
    apply_trailing_sl,
    can_open_new_position,
    update_open_positions,
    check_exit_condition,
    is_position_open,
)
from risk_management.risk_checker import is_liquidation_risk
from risk_management.risk_calculator import calculate_order_qty
from database.sqlite_logger import log_trade, init_db, get_all_trades
from models.trade import Trade
from utils.data_provider import fetch_latest_data, load_symbol_filters, get_futures_balance

# --- Pilihan Mode Trading ---
mode = st.sidebar.selectbox(
    "MODE Trading",
    ["Testnet (Simulasi)", "Real Trading"],
    index=0
)

# --- Inisialisasi DB & UI ---
st.set_page_config(page_title="RajaDollar Trading", layout="wide")
init_db()

# --- Setup Binance Client ---
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

# --- Load / Init Strategy Params JSON ---
STRAT_PATH = "config/strategy_params.json"
if not os.path.exists(STRAT_PATH):
    default_cfg = {
      "DOGEUSDT": {
        "ema_period": 15, "sma_period": 14, "rsi_period": 15,
        "macd_fast": 12, "macd_slow": 26, "macd_signal": 9,
        "score_threshold": 2.0,
        "trailing_offset": 0.25, "trigger_threshold": 0.5
      },
      "XRPUSDT": {
        "ema_period": 22, "sma_period": 18, "rsi_period": 14,
        "macd_fast": 12, "macd_slow": 26, "macd_signal": 9,
        "score_threshold": 2.5,
        "trailing_offset": 0.30, "trigger_threshold": 0.7
      }
    }
    with open(STRAT_PATH,"w") as f:
        json.dump(default_cfg, f, indent=2)

with open(STRAT_PATH,"r") as f:
    strategy_params = json.load(f)

st.sidebar.subheader("Strategi per Symbol")
if st.sidebar.checkbox("Edit strategy_params.json (Expert)"):
    txt = st.sidebar.text_area("JSON", json.dumps(strategy_params, indent=2), height=250)
    if st.sidebar.button("Save"):
        with open(STRAT_PATH,"w") as f: f.write(txt)
        st.sidebar.success("Tersimpan, reload app!")
        st.stop()

# --- UI: Pengaturan Multi-Symbol & Risk ---
multi_symbols = st.sidebar.multiselect("Pilih Symbols", list(strategy_params.keys()), default=list(strategy_params.keys()))
auto_sync = st.sidebar.checkbox("Sync Modal dari Binance", True)
leverage = st.sidebar.slider("Leverage",1,50,20)
risk_pct = st.sidebar.number_input("Risk per Trade (%)",0.01,1.0,0.02)
max_pos = st.sidebar.slider("Max Posisi",1,8,4)
max_sym = st.sidebar.slider("Max Symbols Concurrent",1,4,2)
max_slip = st.sidebar.number_input("Max Slippage (%)",0.1,1.0,0.5)
resume_flag = st.sidebar.checkbox("Resume Otomatis", True)
notif_entry = st.sidebar.checkbox("Notifikasi Entry", True)
notif_exit  = st.sidebar.checkbox("Notifikasi Exit", True)
notif_error = st.sidebar.checkbox("Notifikasi Error", True)
notif_resume= st.sidebar.checkbox("Notifikasi Resume", True)

status_pl = st.empty()
st.markdown(f"**Mode:** {mode}")

# --- Capital ---
if auto_sync and client:
    try: bal = get_futures_balance(client)
    except: bal = 1000.0
else:
    bal = 1000.0
capital = st.sidebar.number_input("Initial Capital (USDT)",value=bal)

# --- Global State ---
threads = {}
status = {sym:"🔴" for sym in strategy_params}
trading_on = False

def trading_loop(symbol):
    try:
        status[symbol] = "🟢"
        params = strategy_params[symbol]
        filters = load_symbol_filters(client,[symbol])
        # Resume state
        active = load_state() if resume_flag else []
        # Notify resume
        if notif_resume:
            for p in active:
                if p['symbol']==symbol:
                    kirim_notifikasi_telegram(
                        f"🔄 *Resume*: {symbol} ({p['side']}) @ {p['entry_price']}, SL:{p['sl']}, TP:{p['tp']}, size:{p['size']}"
                    )
        open_pos=[]
        while trading_on and status[symbol]=="🟢":
            # sync capital
            cap = get_futures_balance(client) if auto_sync else capital
            # fetch & indicators
            df = fetch_latest_data(symbol, client,'5m',100)
            df = apply_indicators(df, params)
            df = generate_signals(df, params['score_threshold'])
            row = df.iloc[-1]
            price = row['close']
            # ENTRY logic (long/short)
            for side in ['long','short']:
                sig = row['long_signal'] if side=='long' else row['short_signal']
                if sig and can_open_new_position(symbol,max_pos,max_sym,open_pos) and not is_position_open(active,symbol,side):
                    # risk checks
                    if is_liquidation_risk(price, side, leverage): break
                    qty = calculate_order_qty(symbol, price,
                        price*(0.99 if side=='long' else 1.01),
                        cap, risk_pct, leverage)
                    qty = adjust_quantity_to_min(symbol,qty,price,filters)
                    if not verify_price_before_order(client,symbol, ("BUY" if side=='long' else "SELL"), price, max_slip/100): break
                    ord = safe_api_call_with_retry(
                        safe_futures_create_order,
                        client,symbol,("BUY" if side=='long' else "SELL"),
                        'MARKET',qty,filters
                    )
                    if ord:
                        oid = ord.get('orderId',str(int(time.time())))
                        now= datetime.utcnow().isoformat()
                        sl=price*(0.99 if side=='long' else 1.01)
                        tp=price*(1.02 if side=='long' else 0.98)
                        tr_off = params.get('trailing_offset',0.25)
                        trg_thr= params.get('trigger_threshold',0.5)
                        trade = Trade(
                            symbol,
                            side,
                            now,
                            price,
                            qty,
                            sl,
                            tp,
                            sl,
                            order_id=oid,
                            trailing_offset=tr_off,
                            trigger_threshold=trg_thr,
                        )
                        active.append(trade.to_dict()); save_state(active)
                        update_open_positions(symbol,side,qty,price,'open',open_pos)
                        if notif_entry: kirim_notifikasi_entry(symbol,price,sl,tp,qty,oid)
            # EXIT + Trailing
            for p in active[:]:
                if p['symbol']!=symbol: continue
                tr_sl = apply_trailing_sl(price,p['entry_price'],p['side'],p['trailing_sl'],p['trailing_offset'],p['trigger_threshold'])
                if check_exit_condition(price,tr_sl,p['tp'],p['sl'],p['side']):
                    ord2 = safe_api_call_with_retry(
                        safe_futures_create_order,
                        client,symbol,('SELL' if p['side']=='long' else 'BUY'),
                        'MARKET',p['size'],filters
                    )
                    mprice = get_mark_price(client,symbol)
                    pnl = (mprice-p['entry_price'])*p['size'] if p['side']=='long' else (p['entry_price']-mprice)*p['size']
                    now2= datetime.utcnow().isoformat()
                    trade=Trade(**p)
                    trade.exit_time=now2; trade.exit_price=mprice; trade.pnl=pnl
                    log_trade(trade)
                    active.remove(p); save_state(active)
                    update_open_positions(symbol,p['side'],p['size'],mprice,'close',open_pos)
                    if notif_exit: kirim_notifikasi_exit(symbol,mprice,pnl,p.get('order_id',''))
            # update UI status
            status_pl.markdown(" ".join([f"{s}:{status[s]}" for s in status]))
            time.sleep(60)
    except Exception as e:
        status[symbol]="🔴"
        if notif_error: kirim_notifikasi_telegram(f"⚠ [{symbol}] CRASH: {e}")

# --- UI Controls ---
col1,col2,col3 = st.columns(3)
with col1:
    if st.button("Start Trading") and not trading_on:
        trading_on=True
        for sym in multi_symbols:
            t=threading.Thread(target=trading_loop,args=(sym,),daemon=True)
            t.start(); threads[sym]=t
        st.success("🚀 Dimulai: "+",".join(multi_symbols))
with col2:
    if st.button("Stop Trading") and trading_on:
        trading_on=False
        for sym in status: status[sym]="🔴"
        st.warning("🛑 Trading dihentikan")
        kirim_notifikasi_telegram("⏹ STOP: Semua trading dihentikan")
with col3:
    if st.button("Close All Positions"):
        active=load_state()
        for p in active[:]:
            sym, side, sz = p['symbol'], p['side'], p['size']
            opp = 'SELL' if side=='long' else 'BUY'
            safe_api_call_with_retry(
                safe_futures_create_order, client, sym, opp, 'MARKET', sz, load_symbol_filters(client,[sym])
            )
            active.remove(p); save_state(active)
            kirim_notifikasi_telegram(f"🛑 FORCE CLOSE: {sym} {side} size:{sz}")
        st.info("Semua posisi paksa ditutup")

# --- Trade History & PNL Viewer ---
st.header("📊 Trade History & PnL Summary")
df = get_all_trades()
if not df.empty:
    # Filter controls
    syms = st.multiselect("Filter Symbol", options=sorted(df['symbol'].unique()), default=sorted(df['symbol'].unique()))
    dates = cast(
        Tuple[date, date],
        st.date_input(
            "Filter Date Range",
            [df['entry_time'].min().date(), df['entry_time'].max().date()],
        ),
    )
    df['entry_date'] = pd.to_datetime(df['entry_time']).dt.date
    mask = df['symbol'].isin(syms) & df['entry_date'].between(dates[0], dates[1])
    dff = df[mask]
    # PnL summary per symbol
    summary = dff.groupby('symbol').agg(
        total_trades=('pnl','size'),
        total_pnl=('pnl','sum'),
        win_rate=('pnl',lambda x: (x>0).sum()/len(x)*100 if len(x)>0 else 0)
    ).reset_index()
    st.subheader("📈 PnL & Win Rate per Symbol")
    st.table(summary)
    # Log
    st.subheader("📋 Detail Trades")
    st.dataframe(dff[['entry_time','symbol','side','entry_price','exit_price','pnl']])
    st.subheader("📈 Equity Curve")
    st.line_chart(dff.groupby('entry_date')['pnl'].sum().cumsum())
else:
    st.info("Belum ada trade tercatat.")

# --- DOWNLOAD LOG HISTORI ---
if not df.empty:
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Download CSV Histori",
        data=csv,
        file_name='trade_history.csv',
        mime='text/csv'
    )

