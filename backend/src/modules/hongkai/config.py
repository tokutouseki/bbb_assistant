import json
import os

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

def load_config(key=None, default=False):
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
            if key is not None:
                if '.' in key:
                    keys = key.split('.')
                    current = config
                    for k in keys:
                        if isinstance(current, dict) and k in current:
                            current = current[k]
                        else:
                            return default
                    return current
                else:
                    return config.get(key, default)
            return config
    if key is not None:
        return default
    return {"other_config": {}}

def save_config(config):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=4)

def update_config(key, value):
    config = load_config()
    if '.' in key:
        keys = key.split('.')
        current = config
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]
        current[keys[-1]] = value
    else:
        config[key] = value
    save_config(config)
