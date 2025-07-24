import os, json

STATE_PATH = "./runtime_state"
STATE_FILE = os.path.join(STATE_PATH, "active_orders.json")

def save_state(data):
    os.makedirs(STATE_PATH, exist_ok=True)
    with open(STATE_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return []
    return []

def delete_state():
    if os.path.exists(STATE_FILE):
        os.remove(STATE_FILE)
