from binance.client import Client
from config import BINANCE_KEYS

def create_client(mode: str) -> Client | None:
    mode = mode.lower()
    if mode == "real":
        key = BINANCE_KEYS["real"]["API_KEY"]
        secret = BINANCE_KEYS["real"]["API_SECRET"]
        if not key or not secret:
            return None
        # Gunakan endpoint futures dengan TLD 'com'
        return Client(key, secret)
    
    elif mode in ["testnet", "testnet (simulasi)"]:
        key = BINANCE_KEYS["testnet"]["API_KEY"]
        secret = BINANCE_KEYS["testnet"]["API_SECRET"]
        if not key or not secret:
            return None
        client = Client(key, secret, testnet=True)
        return client
