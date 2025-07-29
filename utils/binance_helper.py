from binance.client import Client
from binance.enums import FuturesType
from config import BINANCE_KEYS


def create_client(mode: str, futures: bool = True) -> Client | None:
    """
    Buat client Binance dengan konfigurasi eksplisit.
    
    Args:
        mode: 'real' atau 'testnet'
        futures: True untuk Futures API, False untuk Spot API
    """
    mode = mode.lower()
    
    if mode == "real":
        key = BINANCE_KEYS["real"]["API_KEY"]
        secret = BINANCE_KEYS["real"]["API_SECRET"]
        if not key or not secret:
            return None
            
        if futures:
            client = Client(key, secret)
            client.FUTURES_URL = "https://fapi.binance.com"  # Pastikan Futures URL
            return client
        else:
            return Client(key, secret)  # Spot API default
            
    elif mode in ["testnet", "testnet (simulasi)"]:
        key = BINANCE_KEYS["testnet"]["API_KEY"]
        secret = BINANCE_KEYS["testnet"]["API_SECRET"]
        if not key or not secret:
            return None
            
        if futures:
            return Client(key, secret, testnet=True)
        else:
            return Client(key, secret, testnet=True, tld='com')
    
    return None
