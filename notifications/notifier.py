import os
import datetime
from utils.logger import LOG_DIR
try:
    import requests
except ModuleNotFoundError:
    from types import SimpleNamespace

    def _missing_post(*args, **kwargs):
        raise RuntimeError("requests library not available")

    requests = SimpleNamespace(post=_missing_post)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def kirim_notifikasi_telegram(pesan_markdown):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": pesan_markdown,
        "parse_mode": "Markdown"
    }
    try:
        requests.post(url, data=data)
    except Exception as e:
        print(f"[NOTIF] Gagal kirim Telegram: {e}")

def kirim_notifikasi_entry(symbol, price, sl, tp, qty, order_id):
    msg = f"📈 *LONG ENTRY* [id {order_id}]: {symbol} @ {price}, SL: {sl}, TP: {tp}, Size: {qty}"
    kirim_notifikasi_telegram(msg)

def kirim_notifikasi_exit(symbol, price, pnl, order_id):
    msg = f"🔒 EXIT: [id {order_id}] {symbol} closed @ {price}, PnL: {pnl:.2f}"
    kirim_notifikasi_telegram(msg)

def kirim_notifikasi_ml_training(msg: str):
    try:
        kirim_notifikasi_telegram(f"🤖 *ML Model Update*\n{msg}")
    except Exception as e:
        print(f"[ML Notify Error] {e}")

ERROR_LOG_FILE = os.path.join(LOG_DIR, "error.log")

def catat_error(pesan: str):
    ts = datetime.datetime.now().isoformat()
    with open(ERROR_LOG_FILE, "a") as f:
        f.write(f"{ts} {pesan}\n")

def laporkan_error(pesan: str):
    catat_error(pesan)
    try:
        kirim_notifikasi_telegram(f"❌ {pesan}")
    except Exception as e:
        print(f"[NOTIF] Gagal kirim error: {e}")

