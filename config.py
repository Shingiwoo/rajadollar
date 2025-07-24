import os
from dotenv import load_dotenv
load_dotenv()

BINANCE_KEYS = {
    "testnet": {
        "API_KEY": os.getenv("testnet_api_key"),
        "API_SECRET": os.getenv("testnet_secret"),
    },
    "real": {
        "API_KEY": os.getenv("real_api_key"),
        "API_SECRET": os.getenv("real_api_secret"),
    }
}

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
