import pandas as pd
import numpy as np
import pandas as pd
import pytest
from strategies.scalping_strategy import apply_indicators, generate_signals
import strategies.scalping_strategy as strat

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


def test_filter_trend_15m(monkeypatch, dummy_df, config):
    config['only_trend_15m'] = True
    df = apply_indicators(dummy_df.copy(), config)

    def fake_confirm(df, config=None):
        return False, True

    monkeypatch.setattr(strat, 'confirm_by_higher_tf', fake_confirm)
    df = generate_signals(df, 0.0, config=config)
    assert not df['long_signal'].iloc[-1]
    assert df['short_signal'].iloc[-1]

    config['only_trend_15m'] = False
    df = apply_indicators(dummy_df.copy(), config)
    monkeypatch.setattr(strat, 'confirm_by_higher_tf', fake_confirm)
    df = generate_signals(df, 0.0, config=config)
    assert df['long_signal'].iloc[-1]


def test_bb_width_filter(dummy_df, config):
    df = apply_indicators(dummy_df.copy(), config)
    df.loc[df.index[-1], 'bb_width'] = 0.0
    config['min_bb_width'] = 0.5
    df = generate_signals(df, config['score_threshold'], config=config)
    assert not df['long_signal'].iloc[-1]
    assert not df['short_signal'].iloc[-1]
    assert df['skip_reason'].iloc[-1] == "Volatilitas rendah"


def test_crossover_filter(dummy_df, config):
    config['use_crossover_filter'] = True
    config['score_threshold'] = 2.0
    config['hybrid_fallback'] = False
    df = apply_indicators(dummy_df.copy(), config)
    df.loc[df.index[-2], 'ema'] = df['sma'].iloc[-2] - 1
    df.loc[df.index[-1], 'ema'] = df['sma'].iloc[-1] + 1
    df.loc[df.index[-1], 'macd'] = df['macd_signal'].iloc[-1] + 0.1
    df.loc[df.index[-1], 'rsi'] = 50
    df = generate_signals(df, config['score_threshold'], config=config)
    assert df['long_signal'].iloc[-1]
