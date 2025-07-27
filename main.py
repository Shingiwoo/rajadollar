import streamlit as st
import time
import threading
import pandas as pd
from binance.client import Client

# --- Import Modular ---
from config import BINANCE_KEYS
from notifications.notifier import kirim_notifikasi_telegram
from notifications.command_handler import get_updates, handle_command
from utils.state_manager import save_state, load_state, delete_state
from utils.safe_api import safe_api_call
from strategies.scalping_strategy import apply_indicators, generate_signals
from execution.order_router import safe_futures_create_order, adjust_quantity_to_min, safe_close_order_market, get_mark_price
from execution.slippage_handler import verify_price_before_order
from risk_management.position_manager import apply_trailing_sl, can_open_new_position, update_open_positions, check_exit_condition, is_position_open
from risk_management.risk_checker import is_liquidation_risk
from risk_management.risk_calculator import calculate_order_qty
from database.sqlite_logger import log_trade, init_db, get_all_trades
from models.trade import Trade
from utils.data_provider import fetch_latest_data, load_symbol_filters

# --- INIT ---
st.set_page_config(page_title="RajaDollar Trading", layout="wide")
init_db()
client = Client(BINANCE_KEYS["testnet"]["API_KEY"], BINANCE_KEYS["testnet"]["API_SECRET"], testnet=True)
client.API_URL = 'https://testnet.binancefuture.com/fapi'

# --- UI PARAMS ---
symbol = st.sidebar.selectbox("Symbol", ["DOGEUSDT", "XRPUSDT"])
leverage = st.sidebar.slider("Leverage", 1, 50, 20)
capital = st.sidebar.number_input("Initial Capital (USDT)", value=1000.0)
risk_per_trade = st.sidebar.number_input("Risk per Trade (%)", min_value=0.01, max_value=1.0, value=0.02)
max_positions = st.sidebar.slider("Max Positions", 1, 8, 4)
max_symbols = st.sidebar.slider("Max Symbols", 1, 4, 2)
max_slippage = st.sidebar.number_input("Max Slippage (%)", 0.1, 1.0, 0.5)
resume_flag = st.sidebar.checkbox("Resume Otomatis", value=True)
notif_entry = st.sidebar.checkbox("Notifikasi Entry", value=True)
notif_exit = st.sidebar.checkbox("Notifikasi Exit", value=True)
notif_error = st.sidebar.checkbox("Notifikasi Error", value=True)
notif_resume = st.sidebar.checkbox("Notifikasi Resume Start", value=True)

# --- State ---
active_positions = load_state() if resume_flag else []
symbol_filters = load_symbol_filters(client, [symbol])  # Akan diisi saat load_symbol_filters
trading_active = False
open_positions = []  # Untuk pengecekan max_positions/koin

def trading_loop():
    global trading_active, active_positions, open_positions
    try:
        # 1. Kirim notifikasi resume
        if notif_resume and active_positions:
            symbols = ', '.join([pos['symbol'] for pos in active_positions])
            jum = len(active_positions)
            kirim_notifikasi_telegram(f"*Bot Resumed*: Memulihkan posisi aktif {jum} koin ({symbols})")
        kirim_notifikasi_telegram("🤖 *Bot trading aktif!*")

        while trading_active:
            # 2. Ambil data OHLCV terbaru
            df = fetch_latest_data(symbol, client, interval='5m', limit=100)
            df = apply_indicators(df)
            # 3. Integrasi ML
            df = generate_signals(df)  # long_signal/short_signal sudah include ML+indikator

            latest_row = df.iloc[-1]
            latest_price = latest_row['close']

            # 4. Handle Telegram command di setiap loop
            bot_state = {"positions": active_positions}
            updates = get_updates()
            for update in updates.get("result", []):
                message = update.get("message", {})
                text = message.get("text", "")
                chat_id = message.get("chat", {}).get("id")
                handle_command(text, chat_id, bot_state)
            if bot_state.get("force_exit"):
                active_positions.clear()
                open_positions.clear()
                delete_state()
                trading_active = False
                kirim_notifikasi_telegram("⛔ Semua posisi ditutup berdasarkan perintah Telegram.")
                continue

            # Check open positions
            if bool(latest_row['long_signal'] and
                can_open_new_position(symbol, max_positions, max_symbols, open_positions)):
                sl = latest_price * 0.99
                tp = latest_price * 1.02
                qty = calculate_order_qty(symbol, latest_price, sl, capital, risk_per_trade, leverage)
                qty = adjust_quantity_to_min(symbol, qty, latest_price, symbol_filters)
                if is_position_open(active_positions, symbol, 'long'):
                    continue  # SKIP ENTRY! Sudah ada posisi open di symbol ini!
                if is_liquidation_risk(latest_price, 'long', leverage):
                    st.warning(f"Risiko likuidasi tinggi untuk {symbol}!")
                    continue
                if not verify_price_before_order(client, symbol, 'BUY', latest_price, max_slippage / 100):
                    st.warning(f"Slippage terlalu besar pada {symbol}. Sinyal diabaikan.")
                    continue
                # Order eksekusi
                order = safe_api_call(
                    safe_futures_create_order, client, symbol, 'BUY', 'MARKET', qty, symbol_filters
                )
                if order:
                    trade = Trade(symbol, 'long', time.strftime("%Y-%m-%dT%H:%M:%S"), latest_price, qty, sl, tp, sl)
                    active_positions.append(trade.to_dict())
                    open_positions.append({'symbol': symbol, 'side': 'long', 'qty': qty, 'entry_price': latest_price})
                    save_state(active_positions)
                    if notif_entry:
                        kirim_notifikasi_telegram(f"📈 *LONG ENTRY*: {symbol} @ {latest_price}, SL: {sl}, TP: {tp}, Size: {qty}")

            elif bool(latest_row['short_signal'] and can_open_new_position(symbol, max_positions, max_symbols,      
                                                                           open_positions)):
                sl = latest_price * 1.01
                tp = latest_price * 0.98
                qty = calculate_order_qty(symbol, latest_price, sl, capital, risk_per_trade, leverage)
                qty = adjust_quantity_to_min(symbol, qty, latest_price, symbol_filters)
                if is_position_open(active_positions, symbol, 'short'):
                    continue
                if is_liquidation_risk(latest_price, 'short', leverage):
                    st.warning(f"Risiko likuidasi tinggi untuk {symbol} short!")
                    continue
                if not verify_price_before_order(client, symbol, 'SELL', latest_price, max_slippage / 100):
                    st.warning(f"Slippage terlalu besar pada {symbol}. Sinyal short diabaikan.")
                    continue
                order = safe_api_call(
                    safe_futures_create_order, client, symbol, 'SELL', 'MARKET', qty, symbol_filters
                )
                if order:
                    trade = Trade(symbol, 'short', time.strftime("%Y-%m-%dT%H:%M:%S"), latest_price, qty, sl, tp, sl)
                    active_positions.append(trade.to_dict())
                    open_positions.append({'symbol': symbol, 'side': 'short', 'qty': qty, 'entry_price': latest_price})
                    save_state(active_positions)
                    if notif_entry:
                        kirim_notifikasi_telegram(f"📉 *SHORT ENTRY*: {symbol} @ {latest_price}, SL: {sl}, TP: {tp}, Size: {qty}")

            # 6. Exit logic (TP/SL/Trailing)
            for pos in active_positions[:]:
                current_side = pos['side']
                trailing_sl = apply_trailing_sl(latest_price, pos['entry_price'], current_side, pos['trailing_sl'], 0.5, 0.25)
                exit_cond = check_exit_condition(latest_price, trailing_sl, pos['tp'], 0, direction=current_side)
                if exit_cond:
                    # Eksekusi close order
                    order_exit = safe_api_call(
                        safe_futures_create_order,
                        client, symbol, 'SELL' if current_side == 'long' else 'BUY', 'MARKET',
                        pos['size'], symbol_filters
                    )
                    pnl = (latest_price - pos['entry_price']) * pos['size']
                    trade = Trade(**pos)
                    trade.exit_time = time.strftime("%Y-%m-%dT%H:%M:%S")
                    trade.exit_price = latest_price
                    trade.pnl = pnl
                    log_trade(trade)
                    active_positions.remove(pos)
                    update_open_positions(symbol, current_side, pos['size'], latest_price, 'close', open_positions)
                    save_state(active_positions)
                    if notif_exit:
                        kirim_notifikasi_telegram(f"🔒 *EXIT*: {symbol} closed @ {latest_price}, PnL: {pnl:.2f}")

            time.sleep(60)  # Sesuaikan interval loop
    except Exception as e:
        kirim_notifikasi_telegram(f"⚠ *CRASH*: {str(e)}")
        trading_active = False

def stop_all_positions(client, active_positions, symbol_steps):
    # Loop semua posisi yang masih aktif
    for pos in active_positions[:]:
        symbol = pos['symbol']
        qty = pos['size']
        side = pos['side']
        order_id = pos.get('order_id', str(int(time.time())))
        mark_price = get_mark_price(client, symbol)
        if mark_price:
            order = safe_futures_create_order(
                client, symbol, 'SELL' if side == 'long' else 'BUY', 'MARKET', qty, symbol_steps
            )
            # Notifikasi dan logging
            pnl = (mark_price - pos['entry_price']) * qty if side == 'long' else (pos['entry_price'] - mark_price) * qty
            kirim_notifikasi_telegram(
                f"🔒 *STOP TRADE EXIT* [id {order_id}] {symbol} closed @ {mark_price}, PnL: {pnl:.2f}"
            )
            # Remove posisi dari state
            active_positions.remove(pos)
            save_state(active_positions)


# --- UI BUTTONS ---
if st.button("Start Trading") and not trading_active:
    trading_active = True
    threading.Thread(target=trading_loop, daemon=True).start()
    st.success("🚀 Bot trading dimulai!")

if st.button("Stop Trading") and trading_active:
    stop_all_positions(client, active_positions, symbol_filters)
    trading_active = False
    st.warning("🛑 Bot trading dihentikan")
    kirim_notifikasi_telegram("⏹ *STOP TRADE*: Semua trading dihentikan user/manual.")

# --- VIEW LOG HISTORI ---
if st.button("Lihat Trade History"):
    df = get_all_trades()
    if not df.empty:
        st.dataframe(df)
        st.line_chart(df['pnl'].cumsum())
    else:
        st.warning("Tidak ada histori trade.")
