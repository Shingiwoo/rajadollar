def check_exit_condition(price, trailing_sl, tp, hold, max_hold=100, direction='long'):
    if direction == 'long':
        return price <= trailing_sl or price >= tp or hold > max_hold
    else:
        return price >= trailing_sl or price <= tp or hold > max_hold
