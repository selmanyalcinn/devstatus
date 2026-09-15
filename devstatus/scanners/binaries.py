from __future__ import annotations
from pathlib import Path
from ..models import Artifact
from ..config import load_settings
from ..utils import probe_binary

USER_DIRS = [Path("/usr/local/bin"), Path.home()/".local/bin", Path.home()/".cargo/bin", Path.home()/"go/bin"]

def scan() -> list[Artifact]:
    items=[]; seen=set(); settings=load_settings(); probe=settings.get("probe_unknown_binaries", True)
    for root in USER_DIRS:
        if not root.exists(): continue
        try:
            for p in root.iterdir():
                try:
                    is_exec = (p.is_file() or p.is_symlink()) and p.exists() and p.stat().st_mode & 0o111
                except OSError:
                    is_exec=False
                if not is_exec: continue
                try: resolved=str(p.resolve())
                except Exception: resolved=str(p)
                key=(p.name,resolved)
                if key in seen: continue
                seen.add(key)
                version=None; version_source=None; raw=None
                if probe:
                    version,version_source,raw=probe_binary(str(p))
                items.append(Artifact(identity=f"bin:{p}", name=p.name, kind="binary", source="binary",
                                      path=str(p), version=version,
                                      description=raw or "",
                                      metadata={"resolved_path":resolved,"version_source":version_source}))
        except PermissionError:
            pass
    return items
