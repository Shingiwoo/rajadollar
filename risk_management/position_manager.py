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