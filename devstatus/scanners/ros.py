from __future__ import annotations
from ..models import Artifact
from ..utils import run, which

def scan() -> list[Artifact]:
    if not which("ros2"): return []
    items=[]
    rc,out,_=run(["ros2","pkg","list"], timeout=12)
    if rc==0:
        for pkg in out.splitlines():
            if pkg.strip(): items.append(Artifact(identity=f"ros-pkg:{pkg.strip()}", name=pkg.strip(), kind="ros-package", source="ros"))
    return items
