import json
import os
import threading
_REGISTRY_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'sources_registry.json')
_lock = threading.Lock()

def _load():
    if not os.path.exists(_REGISTRY_PATH):
        return {}
    with open(_REGISTRY_PATH, 'r') as f:
        return json.load(f)

def _save(data):
    os.makedirs(os.path.dirname(_REGISTRY_PATH), exist_ok=True)
    with open(_REGISTRY_PATH, 'w') as f:
        json.dump(data, f, indent=2)

def upsert(source_name: str, config: dict):
    with _lock:
        data = _load()
        data[source_name] = config
        _save(data)

def get(source_name: str):
    with _lock:
        return _load().get(source_name)

def remove(source_name: str):
    with _lock:
        data = _load()
        data.pop(source_name, None)
        _save(data)

def all_entries():
    with _lock:
        return _load()