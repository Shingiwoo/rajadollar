import pandas as pd
from strategies.scalping_strategy import apply_indicators, generate_signals

def test_generate_signals_long_short():
    # Minimal 20 baris untuk MACD/ATR
    length = 50
    data = {
        'open': [1 + i * 0.1 for i in range(length)],
        'high': [1.2 + i * 0.1 for i in range(length)],
        'low':  [0.8 + i * 0.1 for i in range(length)],
        'close': [1 + i * 0.1 for i in range(length)],
        'volume': [1000]*length
    }
    df = pd.DataFrame(data)
    
    config = {
        'ema_period': 10,
        'sma_period': 10,
        'rsi_period': 10,
        'macd_fast': 12,
        'macd_slow': 26,
        'macd_signal': 9,
        'score_threshold': 2.0,
        'hybrid_fallback': False
    }
    
    df = apply_indicators(df, config)
    df['ml_signal'] = [1] * len(df)
    df = generate_signals(df, config['score_threshold'], config=config)

    assert 'long_signal' in df.columns
    assert 'short_signal' in df.columns
    assert df['long_signal'].dtype == bool
    assert df['short_signal'].dtype == bool
    # Pastikan setidaknya ada True di salah satu kolom
    assert df['long_signal'].any() or df['short_signal'].any()
