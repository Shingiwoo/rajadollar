import numpy as np
import pandas as pd
from strategies.scalping_strategy import apply_indicators, generate_signals

def test_apply_indicators_and_signals():
    data = {
        'close': np.linspace(100, 130, 30),
        'high': np.linspace(101, 131, 30),
        'low':  np.linspace(99, 129, 30)
    }
    df = pd.DataFrame(data)
    df = apply_indicators(df)
    df = generate_signals(df)
    assert "long_signal" in df.columns
    print("Signals:", df[['long_signal', 'short_signal']].tail())

if __name__ == "__main__":
    test_apply_indicators_and_signals()
