from backtest.engine import run_backtest
from backtest.data_loader import load_csv


def test_run_backtest():
    df = load_csv("data/historical_data/1h/BTCUSDT_1h.csv")
    trades, equity, final_capital = run_backtest(df, symbol="BTCUSDT")
    assert isinstance(trades, list)
    assert not equity.empty
    print(f"Backtest {len(trades)} trades, modal akhir: {final_capital}")


if __name__ == "__main__":
    test_run_backtest()
