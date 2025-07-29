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
        return Client(key, secret)
    elif mode in ["testnet", "testnet (simulasi)"]:
        key = BINANCE_KEYS["testnet"]["API_KEY"]
        secret = BINANCE_KEYS["testnet"]["API_SECRET"]
        if not key or not secret:
            return None
        c = Client(key, secret, testnet=True)
        c.API_URL = "https://testnet.binancefuture.com/fapi"
        return c
    return None
