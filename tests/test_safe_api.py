import time
from utils.safe_api import safe_api_call

def fake_api(x):
    time.sleep(0.01)
    return x + 1

def test_safe_api_call():
    result = safe_api_call(fake_api, 10)
    assert result == 11
    print("Safe API OK:", result)

if __name__ == "__main__":
    test_safe_api_call()

