import time

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

def safe_api_call_with_retry(fn, *args, max_retry=3, delay=2, **kwargs):
    for attempt in range(max_retry):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            if "429" in str(e) or "Too Many Requests" in str(e):
                time.sleep(delay)
            else:
                raise
    raise Exception(f"API rate limit exceeded after {max_retry} attempts.")
