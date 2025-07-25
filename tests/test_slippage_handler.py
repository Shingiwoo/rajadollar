from execution.slippage_handler import verify_price_before_order
from binance.client import Client
from config import BINANCE_KEYS

def test_verify_price_before_order():
    # Ambil API KEY dari config.py
    client = Client(
        BINANCE_KEYS["testnet"]["API_KEY"],
        BINANCE_KEYS["testnet"]["API_SECRET"],
        testnet=True
    )
    symbol = "BTCUSDT"
    expected_price = 30000.0
    allowed = verify_price_before_order(client, symbol, "BUY", expected_price, max_slippage=0.01)
    assert isinstance(allowed, bool)
    print("Slippage check:", allowed)

if __name__ == "__main__":
    test_verify_price_before_order()
