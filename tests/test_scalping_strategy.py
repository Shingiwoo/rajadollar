import pandas as pd
import numpy as np
import pytest
from strategies.scalping_strategy import apply_indicators, generate_signals

@pytest.fixture
def dummy_df():
    return pd.DataFrame({
        'open':   [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15],
        'high':   [1.5, 2.5, 3.5, 4.5, 5.5, 6.5, 7.5, 8.5, 9.5, 10.5, 11.5, 12.5, 13.5, 14.5, 15.5],
        'low':    [0.5, 1.5, 2.5, 3.5, 4.5, 5.5, 6.5, 7.5, 8.5, 9.5, 10.5, 11.5, 12.5, 13.5, 14.5],
        'close':  [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15],
        'volume': [1000]*15
    })

@pytest.fixture
def config():
    return {
        'ema_period': 5,
        'sma_period': 5,
        'rsi_period': 5,
        'macd_fast': 3,
        'macd_slow': 6,
        'macd_signal': 2,
        'score_threshold': 1.0,
        'hybrid_fallback': False
    }

def test_apply_indicators(dummy_df, config):
    df = apply_indicators(dummy_df.copy(), config)
    assert all(col in df.columns for col in [
        'ema', 'sma', 'macd', 'macd_signal',
        'rsi', 'bb_upper', 'bb_lower', 'bb_width', 'atr'
    ])
    assert not df[['ema', 'sma', 'macd', 'rsi', 'atr']].isnull().all().any()

def test_generate_signals(dummy_df, config):
    df = apply_indicators(dummy_df.copy(), config)
    df = generate_signals(df, config['score_threshold'], config=config)
    assert 'long_signal' in df.columns
    assert 'short_signal' in df.columns
    assert 'score_long' in df.columns
    assert 'score_short' in df.columns
    assert 'ml_confidence' in df.columns
    assert df['long_signal'].iloc[-1] == (df['score_long'].iloc[-1] >= config['score_threshold'])
    assert df['short_signal'].iloc[-1] == (df['score_short'].iloc[-1] >= config['score_threshold'])


def test_no_entry_logs(dummy_df, config, caplog):
    config['score_threshold'] = 2.0
    df = apply_indicators(dummy_df.copy(), config)
    with caplog.at_level('INFO'):
        df = generate_signals(df, config['score_threshold'], config=config)
    assert any('Skor long' in r.message for r in caplog.records)
