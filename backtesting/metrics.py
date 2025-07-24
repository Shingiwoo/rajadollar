import pandas as pd

def calculate_metrics(trades):
    if not trades:
        return {}
    df = pd.DataFrame([t.to_dict() for t in trades])
    wins = df[df['pnl'] > 0]
    losses = df[df['pnl'] <= 0]
    return {
        "Total Trades": len(df),
        "Win Rate": f"{(len(wins) / len(df) * 100):.2f}%",
        "Total PnL": f"{df['pnl'].sum():.2f}",
        "Profit Factor": f"{wins['pnl'].sum() / abs(losses['pnl'].sum()) if not losses.empty else '∞'}",
        "Avg PnL": f"{df['pnl'].mean():.2f}"
    }