import time
import logging
from binance.exceptions import BinanceAPIException, BinanceAPIException as ClientError

_last_api_call = 0

def safe_api_call(func, *args, **kwargs):
    """Panggilan API dengan throttle sederhana."""
    global _last_api_call
    now = time.time()
    if now - _last_api_call < 0.1:
        time.sleep(0.1 - (now - _last_api_call))
    _last_api_call = time.time()
    return func(*args, **kwargs)

def safe_api_call_with_retry(func, *args, retries=3, delay=2, **kwargs):
    """Eksekusi API dengan retry dan logging saat gagal atau terkena limit."""
    for attempt in range(retries):
        try:
            return safe_api_call(func, *args, **kwargs)
        except BinanceAPIException as e:
            if "429" in str(e):
                logging.warning(
                    f"[RateLimit] percobaan {attempt+1}/{retries} terkena 429: {e}"
                )
            else:
                logging.error(f"[ClientError] {e}")
        except Exception as e:
            logging.error(f"[API Error] {e}")

        if attempt < retries - 1:
            logging.info(
                f"[Retry] {func.__name__} percobaan {attempt+2}/{retries}"
            )
            time.sleep(delay)

    logging.error(f"[FAILED] Setelah {retries} percobaan: {func.__name__}")
    return None
