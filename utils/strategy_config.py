import json
import os
from typing import Dict, Any

STRATEGY_CFG_PATH = os.path.join("config", "strategy.json")

DEFAULT_MANUAL_PARAMS = {
    "ema_period": 5,
    "sma_period": 22,
    "macd_fast": 12,
    "macd_slow": 26,
    "macd_signal": 9,
    "rsi_period": 14,
    "bb_window": 20,
    "atr_window": 14,
    "score_threshold": 1.8,
}


def load_strategy_config(path: str | None = None) -> Dict[str, Any]:
    cfg_path = path or STRATEGY_CFG_PATH
    if os.path.exists(cfg_path):
        with open(cfg_path) as f:
            cfg = json.load(f)
    else:
        cfg = {
            "enable_optimizer": True,
            "manual_parameters": {"DEFAULT": DEFAULT_MANUAL_PARAMS.copy()},
        }

    manual = cfg.get("manual_parameters", {})
    # Jika format lama (single-object), bungkus jadi DEFAULT
    if manual and all(not isinstance(v, dict) for v in manual.values()):
        manual = {"DEFAULT": manual}
    elif not manual:
        manual = {"DEFAULT": DEFAULT_MANUAL_PARAMS.copy()}
    cfg["manual_parameters"] = manual
    return cfg


def save_strategy_config(cfg: Dict[str, Any], path: str | None = None) -> None:
    cfg_path = path or STRATEGY_CFG_PATH
    os.makedirs(os.path.dirname(cfg_path), exist_ok=True)
    try:
        with open(cfg_path, "w") as f:
            json.dump(cfg, f, indent=2)
    except PermissionError as e:  # pragma: no cover
        raise PermissionError(f"Gagal menyimpan ke {cfg_path}: {e}")


def validate_manual_params(params: Dict[str, Any]) -> bool:
    for k, v in params.items():
        if isinstance(v, (int, float)) and v <= 0:
            raise ValueError(f"{k} harus > 0")
    return True
