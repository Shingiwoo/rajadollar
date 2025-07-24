def is_liquidation_risk(entry_price, side, leverage, threshold=0.03):
    """
    Return True jika margin/leverage terlalu mepet (likuidasi <3% dari harga entry)
    """
    min_move = 1.0 / leverage if leverage > 0 else float('inf')
    return min_move <= threshold