from ..models import Artifact
from ..utils import run, which

def scan() -> list[Artifact]:
    if not which("snap"): return []
    rc,out,_=run(["snap","list"], timeout=8)
    if rc: return []
    items=[]
    for i,line in enumerate(out.splitlines()):
        if i==0: continue
        p=line.split()
        if len(p)>=2:
            items.append(Artifact(identity=f"snap:{p[0]}", name=p[0], kind="package", source="snap", version=p[1]))
    return items
