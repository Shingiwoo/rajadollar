import json
from pathlib import Path

CONFIG_PATH = Path("config/global_config.json")
DEFAULT_CFG = {"selected_timeframe": "5m"}

def load_global_config() -> dict:
    if CONFIG_PATH.exists():
        try:
            with CONFIG_PATH.open() as f:
                return json.load(f)
        except Exception:
            pass
    return DEFAULT_CFG.copy()

def save_global_config(cfg: dict) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CONFIG_PATH.open("w") as f:
        json.dump(cfg, f)
