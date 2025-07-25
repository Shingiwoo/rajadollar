from backtesting.backtest_engine import run_backtest
from backtesting.data_loader import load_csv

def test_run_backtest():
    # File CSV harus ada di data/historical_data//1h/BTCUSDT_1h.csv
    df = load_csv("data/historical_data/1h/BTCUSDT_1h.csv")
    trades, capital = run_backtest(df)
    assert isinstance(trades, list)
    print(f"Backtest {len(trades)} trades, capital: {capital}")

if __name__ == "__main__":
    test_run_backtest()
