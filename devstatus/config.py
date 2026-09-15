from __future__ import annotations
import json, os
from pathlib import Path

APP = "devstatus"
DEFAULT_SETTINGS = {
    "probe_unknown_binaries": True,
    "show_sources": True,
    "history_limit": 100,
    "scan_timeout_seconds": 8,
}

def config_dir() -> Path:
    p = Path(os.environ.get("XDG_CONFIG_HOME", Path.home()/".config")) / APP
    p.mkdir(parents=True, exist_ok=True)
    (p/"rules.d").mkdir(exist_ok=True)
    return p

def state_dir() -> Path:
    p = Path(os.environ.get("XDG_STATE_HOME", Path.home()/".local/state")) / APP
    p.mkdir(parents=True, exist_ok=True)
    (p/"history").mkdir(exist_ok=True)
    return p

def cache_dir() -> Path:
    p = Path(os.environ.get("XDG_CACHE_HOME", Path.home()/".cache")) / APP
    p.mkdir(parents=True, exist_ok=True)
    return p

def _load_json(path: Path, default):
    if not path.exists(): return default
    try: return json.loads(path.read_text())
    except Exception: return default

def load_overrides() -> dict:
    return _load_json(config_dir()/"overrides.json", {})

def save_overrides(data: dict) -> None:
    (config_dir()/"overrides.json").write_text(json.dumps(data, indent=2, sort_keys=True)+"\n")

def load_settings() -> dict:
    data=dict(DEFAULT_SETTINGS)
    data.update(_load_json(config_dir()/"settings.json", {}))
    return data

def save_settings(data: dict) -> None:
    merged=dict(DEFAULT_SETTINGS); merged.update(data)
    (config_dir()/"settings.json").write_text(json.dumps(merged, indent=2, sort_keys=True)+"\n")
