from typing import List, Dict, Set, Tuple
from datetime import datetime
from utils.state_manager import load_state, save_state
from utils.safe_api import safe_api_call_with_retry
from notifications.notifier import kirim_notifikasi_telegram

def handle_resume(resume_flag: bool, notif_resume: bool) -> list:
    if not resume_flag:
        return []

    active = load_state()
    if active and notif_resume:
        # Handle case where 'side' might be missing
        positions = []
        for t in active:
            pos = f"{t.get('symbol', '?')} {t.get('side', '?')}"
            positions.append(pos)
        
        kirim_notifikasi_telegram(f"🔄 Resumed {len(active)} positions: " + ", ".join(positions))
    return active

def sync_with_binance(client) -> List[Dict]:
    """Sync between Binance and local state with auto-recovery."""
    try:
        remote_positions = safe_api_call_with_retry(
            client.futures_position_information
        )
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
        updated = local_state + new_trades
        save_state(updated)
        kirim_notifikasi_telegram(
            f"⚠️ Added {len(missing)} positions: " +
            ", ".join(f"{s} {side}" for s, side in missing)
        )
        return updated
    
    # Case 3: Extra positions (shouldn't happen)
    extra = local_set - real_positions
    if extra:
        kirim_notifikasi_telegram(
            f"🔴 Orphan positions: " +
            ", ".join(f"{s} {side}" for s, side in extra)
        )
    return local_state

    
    