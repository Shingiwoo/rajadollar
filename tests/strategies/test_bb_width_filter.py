import pandas as pd

from strategies.scalping_strategy import apply_indicators, generate_signals


def test_skip_when_bb_width_low():
    df = pd.DataFrame({
        'open': [100] * 30,
        'high': [100] * 30,
        'low': [100] * 30,
        'close': [100] * 30,
        'volume': [1] * 30,
    })
    df = apply_indicators(df)
    # Set ambang tinggi agar pasti ter-skip
    df = generate_signals(df, config={'min_bb_width': 1.0})
    assert not df['long_signal'].iloc[-1]
    assert not df['short_signal'].iloc[-1]
    assert df['skip_reason'].iloc[-1] == 'BB width rendah'
