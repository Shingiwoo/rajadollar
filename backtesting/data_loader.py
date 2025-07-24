import pandas as pd

def load_csv(filepath):
    df = pd.read_csv(filepath)
    df.columns = [col.lower() for col in df.columns]
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df.set_index('timestamp', inplace=True)
    return df
