from __future__ import annotations
import json, re
from pathlib import Path
from ..models import Artifact
from ..utils import parse_version

ROOTS=[Path('/opt')]
VERSION_FILES=('VERSION','VERSION.txt','version.txt','RELEASE','release.txt')

def _manifest_version(root: Path) -> tuple[str|None,str|None]:
    for name in VERSION_FILES:
        p=root/name
        if p.is_file():
            try:
                text=p.read_text(errors='ignore')[:4096]
                v=parse_version(text)
                if v: return v,str(p)
            except Exception: pass
    pj=root/'package.json'
    if pj.is_file():
        try:
            data=json.loads(pj.read_text(errors='ignore'))
            if data.get('version'): return str(data['version']),str(pj)
        except Exception: pass
    v=parse_version(root.name)
    if v: return v,'directory-name'
    return None,None

def scan() -> list[Artifact]:
    items=[]
    for base in ROOTS:
        if not base.exists(): continue
        try:
            children=list(base.iterdir())[:500]
        except PermissionError:
            continue
        for p in children:
            if not p.is_dir(): continue
            v,src=_manifest_version(p)
            items.append(Artifact(identity=f"manual:{p}",name=p.name,kind='manual-install',source='manual',
                                  version=v,path=str(p),metadata={'version_source':src}))
    return items
