import logging
import os

def setup_logger():
    os.makedirs("logs", exist_ok=True)
    logging.basicConfig(
        filename="logs/app.log",
        format="%(asctime)s [%(levelname)s] %(message)s",
        level=logging.INFO
    )
    
