import pytest
from execution.order_router import adjust_quantity_to_min, wait_until_filled
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta

def test_adjust_quantity_to_min_basic():
    """Test penyesuaian quantity berdasarkan minQty"""
    symbol_filters = {
        "BTCUSDT": {
            "minQty": 0.001,
            "stepSize": 0.001,
            "minNotional": 5
        }
    }
    
    # Test quantity di bawah minimum
    qty = adjust_quantity_to_min("BTCUSDT", 0.0004, 30000, symbol_filters)
    assert qty == 0.001  # Harus naik ke minQty
    assert isinstance(qty, float)

    # Test quantity sudah valid
    qty = adjust_quantity_to_min("BTCUSDT", 0.002, 30000, symbol_filters)
    assert qty == 0.002

def test_adjust_quantity_to_min_notional():
    """Test penyesuaian untuk memenuhi minNotional"""
    symbol_filters = {
        "ETHUSDT": {
            "minQty": 0.001,
            "stepSize": 0.001,
            "minNotional": 5
        }
    }
    
    # Test quantity yang membutuhkan penyesuaian karena minNotional
    qty = adjust_quantity_to_min("ETHUSDT", 0.0025, 2000, symbol_filters)
    assert qty == 0.003  # 0.003 * 2000 = 6 (melebihi minNotional 5)
    assert qty * 2000 >= 5

def test_adjust_quantity_edge_cases():
    """Test kasus edge seperti stepSize kecil dan presisi tinggi"""
    symbol_filters = {
        "XRPUSDT": {
            "minQty": 10,
            "stepSize": 1,
            "minNotional": 10
        }
    }
    
    qty = adjust_quantity_to_min("XRPUSDT", 9.999, 1, symbol_filters)
    assert qty == 10

def test_wait_until_filled_success():
    """Test berhasil mendapatkan status FILLED"""
    mock_client = MagicMock()
    # Pastikan return value adalah dict, bukan None
    mock_client.futures_get_order.return_value = {
        "status": "FILLED",
        "orderId": "order123",
        "symbol": "BTCUSDT"
    }
    
    result = wait_until_filled(mock_client, "BTCUSDT", "order123", timeout=1)
    assert result is not None  # Pastikan tidak None
    assert result["status"] == "FILLED"  # Sekarang aman diakses
    mock_client.futures_get_order.assert_called_once_with(
        symbol="BTCUSDT",
        orderId="order123"
    )

def test_wait_until_filled_timeout():
    """Test timeout ketika order tidak terisi"""
    mock_client = MagicMock()
    mock_client.futures_get_order.return_value = {"status": "NEW"}
    
    with pytest.raises(TimeoutError):
        wait_until_filled(mock_client, "BTCUSDT", "order456", timeout=0.1)

def test_wait_until_filled_retry_logic():
    """Test logika retry sampai FILLED"""
    mock_client = MagicMock()
    mock_client.futures_get_order.side_effect = [
        {"status": "NEW", "orderId": "order789"},
        {"status": "PARTIALLY_FILLED", "orderId": "order789"},
        {"status": "FILLED", "orderId": "order789", "executedQty": "1.0"}
    ]
    
    start_time = datetime.now()
    result = wait_until_filled(mock_client, "BTCUSDT", "order789", timeout=2)  # Perbesar timeout
    duration = datetime.now() - start_time
    
    assert result is not None
    assert result["status"] == "FILLED"
    assert mock_client.futures_get_order.call_count == 3
    assert duration < timedelta(seconds=1.5)  # Adjust threshold

if __name__ == "__main__":
    pytest.main(["-v", "--tb=short"])