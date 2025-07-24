import time

_last_api_call = 0

def safe_api_call(func, *args, **kwargs):
    global _last_api_call
    now = time.time()
    # rate limit: minimal 100ms antar-call
    if now - _last_api_call < 0.1:
        time.sleep(0.1 - (now - _last_api_call))
    _last_api_call = time.time()
    try:
        return func(*args, **kwargs)
    except Exception as e:
        print(f"API call error: {e}")
        return None
