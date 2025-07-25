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
    # Long signals
    conditions_long = [
        (df['ema'] > df['ma']) & (df['macd'] > df['macd_signal']),
        (df['rsi'] > 40) & (df['rsi'] < 70),
        df['ml_signal'] == 1 if 'ml_signal' in df.columns else pd.Series([1]*len(df), index=df.index)
    ]
    df['long_signal'] = (conditions_long[0].astype(int) + 
                         0.5 * conditions_long[1].astype(int) + 
                         conditions_long[2].astype(int)) >= score_threshold
    
    # Short signals
    conditions_short = [
        (df['ema'] < df['ma']) & (df['macd'] < df['macd_signal']),
        (df['rsi'] > 30) & (df['rsi'] < 60),
        df['ml_signal'] == 0 if 'ml_signal' in df.columns else pd.Series([0]*len(df), index=df.index)
    ]
    df['short_signal'] = (conditions_short[0].astype(int) + 
                          0.5 * conditions_short[1].astype(int) + 
                          conditions_short[2].astype(int)) >= score_threshold
    
    return df
