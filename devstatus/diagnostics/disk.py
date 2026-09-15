from __future__ import annotations
from pathlib import Path
from ..utils import run, which

def _du(path: Path) -> str|None:
    if not path.exists(): return None
    rc,out,_=run(['du','-sh',str(path)],timeout=20)
    return out.split()[0] if rc==0 and out else None

def usage() -> list[dict]:
    home=Path.home()
    paths=[
        ('Miniconda',home/'miniconda3'),('Anaconda',home/'anaconda3'),('Miniforge',home/'miniforge3'),
        ('NVM',home/'.nvm'),('Cargo',home/'.cargo'),('Go',home/'go'),('uv cache',home/'.cache/uv'),
        ('pip cache',home/'.cache/pip'),('ROS',Path('/opt/ros')),('Local share',home/'.local/share'),
    ]
    items=[]; seen=set()
    for name,p in paths:
        if str(p) in seen: continue
        seen.add(str(p)); size=_du(p)
        if size: items.append({'name':name,'path':str(p),'size':size})
    if which('docker'):
        rc,out,_=run(['docker','system','df'],timeout=10)
        if rc==0 and out: items.append({'name':'Docker','path':'docker system df','size':'details','details':out})
    return items
