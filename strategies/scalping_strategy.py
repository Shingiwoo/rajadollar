import pandas as pd
from ta.trend import EMAIndicator, SMAIndicator, MACD
from ta.momentum import RSIIndicator
from ta.volatility import BollingerBands, AverageTrueRange

def apply_indicators(df, ema_period=10, sma_period=20, rsi_period=14, bb_std=2):
    df['ema'] = EMAIndicator(df['close'], ema_period).ema_indicator()
    df['ma'] = SMAIndicator(df['close'], sma_period).sma_indicator()
    df['macd'] = MACD(df['close']).macd()
    df['macd_signal'] = MACD(df['close']).macd_signal()
    df['rsi'] = RSIIndicator(df['close'], rsi_period).rsi()
    bb = BollingerBands(df['close'], window=20, window_dev=bb_std)
    df['bb_upper'] = bb.bollinger_hband()
    df['bb_lower'] = bb.bollinger_lband()
    df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['close']
    df['atr'] = AverageTrueRange(df['high'], df['low'], df['close']).average_true_range()
    return df

def generate_signals(df, score_threshold=1.4):
    c1 = (df['ema'] > df['ma']) & (df['macd'] > df['macd_signal'])
    c2 = (df['rsi'] > 40) & (df['rsi'] < 70)
    c3 = df.get('ml_signal', 1) == 1
    df['long_signal'] = (c1.astype(int) + 0.5 * c2.astype(int) + c3.astype(int)) >= score_threshold

    c1s = (df['ema'] < df['ma']) & (df['macd'] < df['macd_signal'])
    c2s = (df['rsi'] > 30) & (df['rsi'] < 60)
    c3s = df.get('ml_signal', 0) == 0
    df['short_signal'] = (c1s.astype(int) + 0.5 * c2s.astype(int) + c3s.astype(int)) >= score_threshold
    return df
