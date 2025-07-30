from utils.binance_helper import create_client

def test_invalid_mode():
    assert create_client("unknown") is None
