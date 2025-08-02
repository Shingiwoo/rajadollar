import logging
import os
from pathlib import Path

LOG_DIR = os.getenv("LOG_DIR", "logs")


def setup_logger():
    log_dir = Path(LOG_DIR)
    log_dir.mkdir(parents=True, exist_ok=True)
    if not os.access(log_dir, os.W_OK):
        print(f"[LOGGER] Folder {log_dir} tidak bisa ditulis")
        return
    logging.basicConfig(
        filename=str(log_dir / "app.log"),
        format="%(asctime)s [%(levelname)s] %(message)s",
        level=logging.INFO,
    )
    
