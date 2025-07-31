from typing import List, Dict, Set, Tuple, Optional
from datetime import datetime
from utils.state_manager import load_state, save_state
from utils.safe_api import safe_api_call_with_retry
from notifications.notifier import kirim_notifikasi_telegram
import json
import os

STRAT_PATH = os.path.join("config", "strategy_params.json")

def handle_resume(resume_flag: bool, notif_resume: bool) -> list:
    if not resume_flag:
        return []

    active = load_state()
    if not active:
        return []

    try:
        with open(STRAT_PATH, "r") as f:
            strategy_params = json.load(f)
    except Exception:
        strategy_params = {}

    valid = []
    ignored = []
    for t in active:
        sym = t.get("symbol")
        if sym in strategy_params:
            valid.append(t)
        else:
            ignored.append(sym)

    if notif_resume and valid:
        positions = [f"{t.get('symbol', '?')} {t.get('side', '?')}" for t in valid]
        kirim_notifikasi_telegram(
            f"🔄 Resumed {len(valid)} positions: " + ", ".join(positions)
        )
    if ignored:
        kirim_notifikasi_telegram(
            "⚠️ Orphan positions ignored: " + ", ".join(ignored)
        )
    return valid

def sync_with_binance(client) -> List[Dict]:
    """Sync between Binance and local state with auto-recovery."""
    try:
        remote_positions = safe_api_call_with_retry(
            client.futures_position_information
        )
        if remote_positions is None:
            kirim_notifikasi_telegram("🔴 Sync failed: No data from Binance API")
            return load_state()
    except Exception as e:
        kirim_notifikasi_telegram(f"🔴 Sync failed: {str(e)}")
        print(f"[SYNC ERROR] {str(e)}")
        return load_state()

    # Process active positions
    real_positions: Set[Tuple[str, str]] = {
        (p["symbol"], "long" if float(p["positionAmt"]) > 0 else "short")
        for p in remote_positions
        if abs(float(p["positionAmt"])) > 0
    }

    local_state = load_state()
    if local_state is None:
        local_state = []

    local_set = {(t["symbol"], t["side"]) for t in local_state}    

    # Case 1: Positions match
    if real_positions == local_set:
        return local_state

    # Case 2: Missing positions
    missing = real_positions - local_set
    if missing:
        new_trades = []
        for symbol, side in missing:
            pos = next(p for p in remote_positions if p["symbol"] == symbol)
            new_trades.append({
                "symbol": symbol,
                "side": side,
                "entry_time": datetime.now().isoformat(),
                "entry_price": float(pos["entryPrice"]),
                "size": abs(float(pos["positionAmt"])),
                "sl": 0.0,
                "tp": 0.0,
                "trailing_sl": 0.0,
                "order_id": f"SYNC-{datetime.now().timestamp()}"
            })
        local_state = local_state + new_trades
        save_state(local_state)
        kirim_notifikasi_telegram(
            f"⚠️ Added {len(missing)} positions: " + ", ".join(f"{s} {side}" for s, side in missing)
        )
    
    # Case 3: Extra positions (shouldn't happen)
    extra = local_set - real_positions
    if extra:
        kirim_notifikasi_telegram(
            f"🔴 Orphan positions: " + ", ".join(f"{s} {side}" for s, side in extra)
        )
        local_state = [t for t in local_state if (t["symbol"], t["side"]) not in extra]
        save_state(local_state)
    return local_state