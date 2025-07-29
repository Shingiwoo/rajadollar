from binance import ThreadedWebsocketManager
import threading
from typing import Dict, Optional

# Variabel global dengan type hint dan penamaan jelas
price_data: Dict[str, float] = {}
price_lock = threading.Lock()

def get_price(symbol: str) -> Optional[float]:
    """Ambil harga terakhir untuk symbol tertentu.
    
    Args:
        symbol: Pair trading (contoh: 'BTCUSDT')
    
    Returns:
        Harga terakhir (float) atau None jika symbol tidak ditemukan
    """
    with price_lock:
        return price_data.get(symbol)

def update_price(symbol: str, price: float) -> None:
    """Perbarui harga untuk symbol tertentu.
    
    Args:
        symbol: Pair trading 
        price: Harga terbaru
    """
    with price_lock:
        price_data[symbol] = price

def clear_prices() -> None:
    """Reset semua data harga yang tersimpan."""
    with price_lock:
        price_data.clear()

def start_price_stream(api_key: str, api_secret: str, symbols: list) -> ThreadedWebsocketManager:
    """Mulai WebSocket stream untuk update harga real-time.
    
    Args:
        api_key: Binance API key
        api_secret: Binance API secret
        symbols: List pair trading yang akan dimonitor
    
    Returns:
        Instance ThreadedWebsocketManager yang sedang berjalan
    """
    twm = ThreadedWebsocketManager(api_key, api_secret)
    try:
        twm.start()
    except Exception as e:
        print(f"WebSocket start error: {e}")
        return twm

    def handle_message(msg):
        try:
            symbol = msg['s']
            price = float(msg['c'])
            update_price(symbol, price)
        except KeyError as e:
            print(f"Format message tidak valid: {e}")
        except ValueError as e:
            print(f"Error konversi harga: {e}")
        except Exception as e:
            print(f"Error tidak terduga: {e}")

    for symbol in symbols:
        twm.start_symbol_ticker_socket(
            callback=handle_message,
            symbol=symbol.lower()
        )

    return twm


def stop_price_stream(twm: ThreadedWebsocketManager | None) -> None:
    """Hentikan stream harga jika aktif."""
    if twm:
        try:
            twm.stop()
        except Exception as e:
            print(f"WS stop error: {e}")