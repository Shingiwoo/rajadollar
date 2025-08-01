import os
import glob
from utils.logger import LOG_DIR
import requests
import logging
import re
import pandas as pd
from ml.training import train_model, MIN_DATA
from ml import historical_trainer
import matplotlib.pyplot as plt
from database.sqlite_logger import get_all_trades, export_trades_csv
from notifications.notifier import kirim_notifikasi_telegram
from telegram.ext import ApplicationBuilder, MessageHandler, filters

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
AUTHORIZED_CHAT_IDS = [os.getenv("TELEGRAM_CHAT_ID")]
API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

def get_updates(offset=None):
    url = f"{API_URL}/getUpdates"
    params = {"timeout": 100, "offset": offset}
    response = requests.get(url, params=params)
    return response.json()

def send_reply(chat_id, text):
    url = f"{API_URL}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    }
    requests.post(url, data=data)

def send_photo(chat_id, image_path):
    url = f"{API_URL}/sendPhoto"
    with open(image_path, 'rb') as img:
        requests.post(url, data={"chat_id": chat_id}, files={"photo": img})

def send_document(chat_id, file_path):
    url = f"{API_URL}/sendDocument"
    with open(file_path, 'rb') as f:
        requests.post(url, data={"chat_id": chat_id}, files={"document": f})


def _train_symbol(symbol: str) -> float:
    """Latih model untuk satu simbol dan kembalikan akurasinya."""
    path = os.path.join("data", "training_data", f"{symbol}.csv")
    if os.path.exists(path):
        try:
            df = pd.read_csv(path)
        except Exception:
            df = pd.DataFrame()
    else:
        df = pd.DataFrame()

    if len(df) >= MIN_DATA:
        return train_model(symbol)

    result = historical_trainer.train_from_history(symbol)
    return result.get("train_accuracy", 0.0) if result else 0.0


def handle_command(command_text, chat_id, bot_state):
    """Proses perintah Telegram dengan validasi chat id."""
    logging.info(f"Telegram command from {chat_id}: {command_text}")
    if str(chat_id) not in AUTHORIZED_CHAT_IDS:
        logging.warning(f"Unauthorized chat {chat_id}")
        send_reply(chat_id, "❌ Akses ditolak.")
        return

    if command_text == "/status":
        df = get_all_trades()
        last = df.iloc[0] if not df.empty else None
        equity = df['pnl'].sum() if not df.empty else 0
        msg = (
            f"✅ Bot Aktif\nPosisi terbuka: {len(bot_state.get('positions', []))}\n"
            f"Equity: {equity:.2f}"
        )
        if last is not None:
            msg += (
                f"\nTrade terakhir {last['symbol']} {last['side']} PnL {last['pnl']:.2f}"
            )
        send_reply(chat_id, msg)

    elif command_text.startswith("/entry"):
        parts = command_text.split()
        if len(parts) < 2:
            send_reply(chat_id, "Format perintah salah. Gunakan /entry SYMBOL")
            return
        _, symbol = parts
        flag = bot_state.setdefault("manual_entry_flag", {})
        flag[symbol.upper()] = True
        bot_state["manual_entry"] = symbol.upper()
        send_reply(chat_id, f"📩 Manual ENTRY dikirimkan: {symbol.upper()}")

    elif command_text == "/stop":
        bot_state["force_exit"] = True
        send_reply(chat_id, "🛑 Perintah STOP diterima. Semua posisi akan ditutup.")

    elif command_text == "/restart":
        bot_state["force_restart"] = True
        send_reply(chat_id, "🔄 Perintah RESTART diterima. Bot akan di-reset.")
    
    elif command_text == "/pnl":
        df = get_all_trades()
        total_pnl = df['pnl'].sum() if not df.empty else 0
        win = (df['pnl'] > 0).sum() if not df.empty else 0
        wr = (win / len(df)) * 100 if not df.empty else 0
        send_reply(chat_id, f"💰 PnL: *${total_pnl:.2f}* | Win Rate: {wr:.2f}%")

    elif command_text == "/export":
        df = get_all_trades()
        if df.empty:
            send_reply(chat_id, "📭 Tidak ada data untuk diexport.")
        else:
            path = export_trades_csv("runtime_state/export.csv")
            send_document(chat_id, path)
            send_reply(chat_id, "📤 File CSV dikirim.")
    
    elif command_text.startswith("/mltrain"):
        parts = command_text.split()
        if len(parts) < 2:
            send_reply(chat_id, "⚠ Format: /mltrain SYMBOL atau /mltrain all")
            return
        target = parts[1].upper()
        if target == "ALL":
            send_reply(chat_id, "⏳ Training ML models untuk semua simbol...")
            files = glob.glob(os.path.join("data", "training_data", "*.csv"))
            symbols = [os.path.splitext(os.path.basename(p))[0].upper() for p in files]
            results = []
            for sym in symbols:
                acc = _train_symbol(sym)
                results.append((sym, acc))
            lines = [f"- **{s}**: {a*100:.1f}%" for s, a in results]
            summary = " Semua model selesai dilatih:\n" + "\n".join(lines) + "\n(models tersimpan di folder /models)"
            send_reply(chat_id, summary)
        else:
            if not re.fullmatch(r"[A-Z0-9]{6,12}", target):
                send_reply(chat_id, "⚠ Symbol tidak valid.")
                return
            send_reply(chat_id, f"⏳ Training ML model untuk **{target}**...")
            acc = _train_symbol(target)
            if acc > 0:
                path = f"models/{target}_scalping.pkl"
                send_reply(chat_id, f"Model **{target}** selesai dilatih. Akurasi: {acc*100:.1f}% . Disimpan di: {path}")
            else:
                send_reply(chat_id, f"⚠ Gagal melatih model **{target}** (data tidak mencukupi).")

    elif command_text == "/log":
        df = get_all_trades()
        if df.empty:
            send_reply(chat_id, "📭 Belum ada trade yang tercatat.")
        else:
            last = df.head(5)
            log_msg = "\n".join(
                f"{row['symbol']} {row['side'].upper()} | Entry: {row['entry']:.2f} → Exit: {row['exit']:.2f} | PnL: {row['pnl']:.2f}"
                for _, row in last.iterrows()
            )
            send_reply(chat_id, f"📜 *5 Trade Terakhir:*\n{log_msg}")

    elif command_text == "/summary":
        df = get_all_trades()
        if df.empty:
            send_reply(chat_id, "📊 Tidak ada data untuk summary.")
        else:
            total = len(df)
            win = len(df[df['pnl'] > 0])
            loss = total - win
            wr = (win / total) * 100
            pf = df[df['pnl'] > 0]['pnl'].sum() / abs(df[df['pnl'] <= 0]['pnl'].sum()) if not df[df['pnl'] <= 0].empty else '∞'
            avg = df['pnl'].mean()
            send_reply(chat_id, f"""📈 *Ringkasan Trading*
    Total: {total}
    Win Rate: {wr:.2f}%
    Profit Factor: {pf}
    Avg PnL: {avg:.2f}""")

    elif command_text == "/ml":
        df = get_all_trades()
        if len(df) < 10:
            send_reply(chat_id, "📉 Tidak cukup data untuk training.")
        else:
            train_model("all")
            send_reply(chat_id, "✅ *Model berhasil dilatih ulang!*")

    elif command_text == "/chart":
        df = get_all_trades()
        if df.empty:
            send_reply(chat_id, "📉 Tidak ada data untuk ditampilkan.")
        else:
            plt.figure(figsize=(10, 4))
            df['pnl'].cumsum().plot()
            plt.title("Equity Curve")
            plt.xlabel("Trades")
            plt.ylabel("Cumulative PnL")
            chart_path = "runtime_state/equity_chart.png"
            plt.tight_layout()
            plt.savefig(chart_path)
            plt.close()
            send_photo(chat_id, chart_path)   

    else:
        send_reply(chat_id, "🤖 Perintah tidak dikenali.")



def start_polling(bot_state: dict) -> None:
    """Jalankan Telegram polling secara asynchronous."""
    if not TELEGRAM_TOKEN:
        logging.warning("TELEGRAM_TOKEN kosong, polling tidak dimulai")
        return
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    async def _all_cmd(update, context):
        text = update.message.text
        chat_id = str(update.effective_chat.id)
        handle_command(text, chat_id, bot_state)

    app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^/"), _all_cmd))
    app.run_polling()
