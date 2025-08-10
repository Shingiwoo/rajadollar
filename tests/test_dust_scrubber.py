from unittest.mock import MagicMock
from execution import order_router as orouter


def setup_client(position_side_effect):
    client = MagicMock()
    client.futures_position_information.side_effect = position_side_effect
    client.futures_create_order = MagicMock()
    return client


def test_flatten_residual_min_qty(monkeypatch):
    client = setup_client([
        [{'positionAmt': '0.0004'}],
        [{'positionAmt': '0'}],
    ])
    monkeypatch.setattr(orouter, 'safe_api_call_with_retry', lambda func, **kw: func(**kw))
    monkeypatch.setattr(orouter, 'get_mark_price', lambda c, s: 10000.0)
    filters = {'BTCUSDT': {'minQty': 0.001, 'stepSize': 0.001, 'minNotional': 5}}
    orouter.flatten_residual_position(client, 'BTCUSDT', filters)
    client.futures_create_order.assert_called_once_with(
        symbol='BTCUSDT', side='SELL', type='MARKET', quantity=0.001, reduceOnly=True
    )


def test_flatten_residual_retry(monkeypatch):
    client = setup_client([
        [{'positionAmt': '0.0025'}],
        [{'positionAmt': '0.0012'}],
    ])
    monkeypatch.setattr(orouter, 'safe_api_call_with_retry', lambda func, **kw: func(**kw))
    monkeypatch.setattr(orouter, 'get_mark_price', lambda c, s: 10000.0)
    filters = {'BTCUSDT': {'minQty': 0.001, 'stepSize': 0.001, 'minNotional': 5}}
    orouter.flatten_residual_position(client, 'BTCUSDT', filters)
    assert client.futures_create_order.call_count == 2

