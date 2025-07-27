import time
import logging
from binance.error import ClientError

_last_api_call = 0

def safe_api_call(func, *args, **kwargs):
    global _last_api_call
    now = time.time()
    if now - _last_api_call < 0.1:
        time.sleep(0.1 - (now - _last_api_call))
    _last_api_call = time.time()
    try:
        return func(*args, **kwargs)
    except Exception as e:
        print(f"API call error: {e}")
        return None

def safe_api_call_with_retry(func, *args, retries=3, delay=2, **kwargs):
    for attempt in range(retries):
        try:
            return func(*args, **kwargs)
        except ClientError as e:
            if '429' in str(e):
                logging.warning(f"[RateLimit] Retry {attempt+1}/{retries} after 429 error")
                time.sleep(delay)
            else:
                raise e
        except Exception as e:
            logging.error(f"[API Error] {str(e)}")
            time.sleep(delay)
    logging.error(f"[FAILED] After {retries} attempts: {func.__name__}")
    return None