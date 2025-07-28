import logging
from notifications.notifier import (
    kirim_notifikasi_exit as _notif_exit,
    kirim_notifikasi_telegram as _notif_telegram,
)


def kirim_notifikasi_exit(symbol: str, price: float, pnl: float, order_id: str | None):
    """Kirim notifikasi exit dengan logging."""
    try:
        _notif_exit(symbol, price, pnl, order_id)
    except Exception as e:
        logging.error(f"Gagal kirim notifikasi exit: {e}")


def kirim_notifikasi_telegram(msg: str):
    try:
        _notif_telegram(msg)
    except Exception as e:
        logging.error(f"Gagal kirim Telegram: {e}")
