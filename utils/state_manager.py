import os
import json
import tempfile
import shutil
import logging
from typing import Any, List, Dict

STATE_DIR = "./runtime_state"
STATE_FILE = os.path.join(STATE_DIR, "active_trades.json")
BACKUP_FILE = os.path.join(STATE_DIR, "active_trades.bak.json")

def save_state(data: List[Dict[str, Any]]) -> None:
    """
    Simpan state trading secara atomik dengan mekanisme:
    1. Tulis ke temporary file
    2. Atomic replace ke file utama
    3. Buat backup copy
    
    Args:
        data: Data state yang akan disimpan (list of dicts)
    """
    os.makedirs(STATE_DIR, exist_ok=True)
    if not (os.stat(STATE_DIR).st_mode & 0o200):
        raise RuntimeError("State directory tidak bisa ditulis")
    tmp_path = None
    
    try:
        # Stage 1: Tulis ke temp file
        with tempfile.NamedTemporaryFile(
            mode="w",
            dir=STATE_DIR,
            delete=False,
            prefix=".tmp_",
            suffix=".json"
        ) as tmp_file:
            json.dump(data, tmp_file, indent=2)
            tmp_path = tmp_file.name

        # Stage 2: Atomic replace
        os.replace(tmp_path, STATE_FILE)
        
        # Stage 3: Create backup
        shutil.copy2(STATE_FILE, BACKUP_FILE)
        
    except (OSError, IOError, TypeError, ValueError) as e:
        # Cleanup jika gagal
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
        raise RuntimeError(f"Failed to save state: {str(e)}")

def load_state() -> List[Dict[str, Any]]:
    """
    Muat state dari file dengan fallback ke backup.
    
    Returns:
        List of trade dictionaries atau empty list jika gagal
    """
    for filepath in [STATE_FILE, BACKUP_FILE]:
        if os.path.exists(filepath):
            try:
                with open(filepath, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError, IOError, ValueError):
                logging.error(f"Gagal load state dari {filepath}")
                continue
    return []

def delete_state() -> None:
    """Hapus semua file state dan backup."""
    for filepath in (STATE_FILE, BACKUP_FILE):
        try:
            if os.path.exists(filepath):
                os.unlink(filepath)
        except OSError:
            pass