import os
import json
from typing import Any, Dict

RESUME_FILE = "./runtime_state/risk_state.json"

def save_resume_state(data: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(RESUME_FILE), exist_ok=True)
    with open(RESUME_FILE, "w") as f:
        json.dump(data, f)

def load_resume_state() -> Dict[str, Any]:
    if os.path.exists(RESUME_FILE):
        try:
            with open(RESUME_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {"daily_drawdown": 0.0, "consecutive_losses": 0, "paused": False}
