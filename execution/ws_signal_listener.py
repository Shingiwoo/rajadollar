import threading, json
from binance import ThreadedWebsocketManager
from utils.data_provider import fetch_latest_data
from strategies.scalping_strategy import apply_indicators, generate_signals

signal_callbacks = {}
ws_manager = None

def register_signal_handler(symbol: str, callback):
    signal_callbacks[symbol.upper()] = callback

def start_signal_stream(api_key, api_secret, symbols: list[str], strategy_params):
    global ws_manager
    ws_manager = ThreadedWebsocketManager(api_key=api_key, api_secret=api_secret)
    ws_manager.start()

    def handle_kline(msg):
        symbol = msg['s']
        if msg['k']['x']:  # kline closed
            df = fetch_latest_data(symbol, ws_manager._client, interval='5m', limit=100)
            df = apply_indicators(df, strategy_params[symbol])
            df = generate_signals(df, strategy_params[symbol]['score_threshold'])
            last = df.iloc[-1]
            if symbol in signal_callbacks:
                signal_callbacks[symbol](symbol, last)

    for sym in symbols:
        ws_manager.start_kline_socket(callback=handle_kline, symbol=sym.lower(), interval='5m')
