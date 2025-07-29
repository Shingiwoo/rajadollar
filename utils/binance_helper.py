from binance.client import Client
from config import BINANCE_KEYS


def create_client(mode: str) -> Client | None:
    """Buat instance Binance Client sesuai mode."""
    mode = mode.lower()
    if mode == "real":
        key = BINANCE_KEYS["real"]["API_KEY"]
        secret = BINANCE_KEYS["real"]["API_SECRET"]
        if not key or not secret:
            return None
        c = Client(key, secret)
        c.API_URL = "https://fapi.binance.com"
        print(c.API_URL)
        return c
    elif mode in ["testnet", "testnet (simulasi)"]:
        key = BINANCE_KEYS["testnet"]["API_KEY"]
        secret = BINANCE_KEYS["testnet"]["API_SECRET"]
        if not key or not secret:
            return None
        c = Client(key, secret, testnet=True)
        c.API_URL = "https://testnet.binancefuture.com"
        print(c.API_URL)
        return c
    return None
