import pandas as pd

def fetch_latest_data(symbol, client, interval='5m', limit=100):
    klines = client.futures_klines(symbol=symbol, interval=interval, limit=limit)
    df = pd.DataFrame(klines, columns=[
        'timestamp', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_asset_volume', 'trades', 'taker_buy_base', 'taker_buy_quote', 'ignored'
    ])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = df[col].astype(float)
    df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']].set_index('timestamp')
    return df

def load_symbol_filters(client, coins):
    symbol_filters = {}
    info = client.futures_exchange_info()
    for s in info['symbols']:
        if s['symbol'] in coins:
            lot = next(f for f in s['filters'] if f['filterType'] == 'LOT_SIZE')
            min_qty = float(lot['minQty'])
            step_size = float(lot['stepSize'])
            notional_filter = next((f for f in s['filters'] if f['filterType'] in ['MIN_NOTIONAL','NOTIONAL']), None)
            min_notional = float(notional_filter.get('minNotional', notional_filter.get('notional', 0.0))) if notional_filter else 0.0
            symbol_filters[s['symbol']] = {'minQty': min_qty, 'stepSize': step_size, 'minNotional': min_notional}
    return symbol_filters
