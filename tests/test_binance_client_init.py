import os
from utils.binance_helper import create_client
from config import BINANCE_KEYS
from unittest.mock import patch, MagicMock


def env_keys():
    return {
        "testnet_api_key": "a",
        "testnet_secret": "b",
        "real_api_key": "c",
        "real_api_secret": "d",
    }


def test_create_client_testnet():
    with patch.dict("utils.binance_helper.BINANCE_KEYS", {
        "testnet": {"API_KEY": "a", "API_SECRET": "b"},
        "real": {"API_KEY": "c", "API_SECRET": "d"},
    }), patch(
        "utils.binance_helper.Client",
        return_value=MagicMock(testnet=True, API_URL="https://testnet.binancefuture.com", API_KEY="a", API_SECRET="b")
    ):
        client = create_client("testnet")
        assert client.testnet is True
        assert client.API_KEY == "a"
        assert "testnet" in client.API_URL


def test_create_client_real():
    with patch.dict("utils.binance_helper.BINANCE_KEYS", {
        "testnet": {"API_KEY": "a", "API_SECRET": "b"},
        "real": {"API_KEY": "c", "API_SECRET": "d"},
    }), patch(
        "utils.binance_helper.Client",
        return_value=MagicMock(testnet=False, API_URL="https://fapi.binance.com", API_KEY="c", API_SECRET="d")
    ):
        client = create_client("real")
        assert client.testnet is False
        assert client.API_KEY == "c"
        assert "binance" in client.API_URL
