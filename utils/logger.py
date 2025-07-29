import logging
import os

LOG_DIR = os.getenv("LOG_DIR", "/app/logs")

def setup_logger():
    os.makedirs(LOG_DIR, exist_ok=True)
    logging.basicConfig(
        filename=os.path.join(LOG_DIR, "app.log"),
        format="%(asctime)s [%(levelname)s] %(message)s",
        level=logging.INFO
    )
    
