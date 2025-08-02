import pandas as pd


def load_csv(filepath: str, start: str | None = None, end: str | None = None) -> pd.DataFrame:
    """Muat data CSV dan filter sesuai rentang waktu."""

    df = pd.read_csv(filepath)
    df.columns = [col.lower() for col in df.columns]
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df.sort_values("timestamp", inplace=True)
    if start:
        df = df[df["timestamp"] >= pd.to_datetime(start)]
    if end:
        df = df[df["timestamp"] <= pd.to_datetime(end)]
    df.set_index("timestamp", inplace=True)
    return df
