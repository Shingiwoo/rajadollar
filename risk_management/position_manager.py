def apply_trailing_sl(price, entry, direction, trailing_sl, trigger_pct, step_pct):
    profit_pct = (price - entry) / entry * 100 if direction == 'long' else (entry - price) / entry * 100
    if profit_pct >= trigger_pct:
        if direction == 'long':
            return max(trailing_sl, price - (step_pct / 100) * price)
        else:
            return min(trailing_sl, price + (step_pct / 100) * price)
    return trailing_sl

def check_exit_condition(price, trailing_sl, tp, hold, max_hold=100, direction='long'):
    if direction == 'long':
        return price <= trailing_sl or price >= tp or hold > max_hold
    else:
        return price >= trailing_sl or price <= tp or hold > max_hold
    
open_positions = []

def can_open_new_position(symbol, max_positions, max_symbols, open_positions):
    if len(open_positions) >= max_positions:
        return False
    symbols_open = {pos['symbol'] for pos in open_positions}
    if symbol not in symbols_open and len(symbols_open) >= max_symbols:
        return False
    return True

def update_open_positions(symbol, side, qty, price, status, open_positions):
    if status == 'open':
        open_positions.append({'symbol': symbol, 'side': side, 'qty': qty, 'entry_price': price})
    elif status == 'close':
        open_positions[:] = [pos for pos in open_positions if not (pos['symbol'] == symbol and pos['side'] == side)]

def is_position_open(active_positions, symbol, side):
    for pos in active_positions:
        if pos['symbol'] == symbol and pos['side'] == side:
            return True
    return False


