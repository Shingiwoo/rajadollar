from binance import ThreadedWebsocketManager

shared_price = {}

def start_price_stream(api_key, api_secret, symbols):
    twm = ThreadedWebsocketManager()
    twm.start()

    def handle_message(msg):
        try:
            symbol = msg['s']
            price = float(msg['c'])
            shared_price[symbol] = price
        except Exception as e:
            print(f"WebSocket error: {e}")

    for symbol in symbols:
        twm.start_symbol_ticker_socket(callback=handle_message, symbol=symbol.lower())

    return twm
