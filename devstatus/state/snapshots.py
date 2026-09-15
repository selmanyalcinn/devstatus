from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
from ..config import state_dir, load_settings


def latest_path() -> Path:
    return state_dir()/"latest.json"

def load_path(p: Path) -> dict|None:
    try: return json.loads(p.read_text())
    except Exception: return None

def load_latest() -> dict | None:
    p=latest_path()
    return load_path(p) if p.exists() else None

def history() -> list[Path]:
    return sorted((state_dir()/"history").glob("*.json"), reverse=True)

def save(snapshot: dict) -> Path:
    snapshot=dict(snapshot)
    now=datetime.now(timezone.utc)
    snapshot["timestamp"]=now.isoformat()
    text=json.dumps(snapshot, indent=2, sort_keys=True)
    latest_path().write_text(text+"\n")
    hp=state_dir()/"history"/(now.strftime("%Y%m%dT%H%M%S.%fZ")+".json")
    hp.write_text(text+"\n")
    limit=int(load_settings().get('history_limit',100) or 100)
    if limit>0:
        for old in history()[limit:]:
            try: old.unlink()
            except OSError: pass
    return hp

def resolve(ref: str|None) -> tuple[Path|None,dict|None]:
    if not ref or ref=='latest':
        p=latest_path(); return (p,load_path(p)) if p.exists() else (None,None)
    hist=history()
    if ref in {'previous','prev'}:
        p=hist[1] if len(hist)>1 else None
        return (p,load_path(p)) if p else (None,None)
    if ref.isdigit():
        i=int(ref)
        p=hist[i] if 0<=i<len(hist) else None
        return (p,load_path(p)) if p else (None,None)
    p=Path(ref).expanduser()
    if p.exists(): return p,load_path(p)
    matches=[x for x in hist if x.name.startswith(ref)]
    if matches: return matches[0],load_path(matches[0])
    return None,None

def reset() -> None:
    lp=latest_path()
    if lp.exists(): lp.unlink()
