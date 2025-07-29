from unittest.mock import MagicMock, patch
from utils.binance_helper import create_client
from binance.streams import BinanceSocketManager


def test_client_creation_testnet():
    with patch.dict('utils.binance_helper.BINANCE_KEYS', {
        'testnet': {'API_KEY': 'a', 'API_SECRET': 'b'},
        'real': {'API_KEY': 'c', 'API_SECRET': 'd'}
    }), patch('utils.binance_helper.Client', return_value=MagicMock(testnet=True)):
        client = create_client('testnet')
        assert client.testnet is True
        with patch('tests.test_binance_client.BinanceSocketManager') as bsm:
            BinanceSocketManager(client=client)
            bsm.assert_called_with(client=client)


def test_client_creation_real():
    with patch.dict('utils.binance_helper.BINANCE_KEYS', {
        'testnet': {'API_KEY': 'a', 'API_SECRET': 'b'},
        'real': {'API_KEY': 'c', 'API_SECRET': 'd'}
    }), patch('utils.binance_helper.Client', return_value=MagicMock(testnet=False)):
        client = create_client('real')
        assert client.testnet is False
        with patch('tests.test_binance_client.BinanceSocketManager') as bsm:
            BinanceSocketManager(client=client)
            bsm.assert_called_with(client=client)


