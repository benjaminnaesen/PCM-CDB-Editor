import json
import os

CONFIG_FILE = "session_config.json"

DEFAULT_CONFIG = {
    "favorites": [],
    "last_path": "",
    "window_size": "1200x800",
    "theme": "light"
}

def load_config():
    if not os.path.exists(CONFIG_FILE):
        return DEFAULT_CONFIG
    try:
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    except:
        return DEFAULT_CONFIG

def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)