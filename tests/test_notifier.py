import os
from dotenv import load_dotenv
load_dotenv()
from notifications.notifier import kirim_notifikasi_telegram
assert os.getenv("TELEGRAM_TOKEN"), "TELEGRAM_TOKEN belum ter-set"
assert os.getenv("TELEGRAM_CHAT_ID"), "TELEGRAM_CHAT_ID belum ter-set"


def test_notifier():
    msg = "📈 *UNIT TEST* Notifikasi bot RajaDollar!"
    kirim_notifikasi_telegram(msg)
    print("Cek Telegram, notifikasi harus terkirim!")

if __name__ == "__main__":
    test_notifier()
