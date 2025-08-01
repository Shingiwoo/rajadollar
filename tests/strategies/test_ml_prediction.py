import pickle
import pandas as pd
import strategies.scalping_strategy as strat

class DummyModel:
    def predict(self, X):
        return [0] * len(X)

def test_ml_prediction(tmp_path, monkeypatch):
    model_path = tmp_path / 'model.pkl'
    with open(model_path, 'wb') as f:
        pickle.dump(DummyModel(), f)

    monkeypatch.setattr(strat, 'MODEL_PATH', str(model_path))
    strat._ml_models = {}
    strat.load_ml_model("")

    length = 20
    df = pd.DataFrame({
        'open': [1 + i for i in range(length)],
        'high': [1 + i for i in range(length)],
        'low': [1 + i for i in range(length)],
        'close': [1 + i for i in range(length)],
        'volume': [100]*length
    })

    config = {'ema_period':2,'sma_period':2,'rsi_period':2,'macd_fast':1,'macd_slow':3,'macd_signal':1}
    df = strat.apply_indicators(df, config)
    df = strat.generate_signals(df, 1.0, "")
    assert 'ml_signal' in df.columns
    assert df['ml_signal'].iloc[-1] == 0
    assert 'short_signal' in df.columns
