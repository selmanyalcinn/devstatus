from __future__ import annotations
import json, re
from pathlib import Path

def _read(path: Path, limit=200000) -> str:
    try: return path.read_text(errors='ignore')[:limit]
    except Exception: return ''

def detect(path: str='.') -> list[dict]:
    root=Path(path).resolve(); found=[]
    signatures={
        'Python':['pyproject.toml','requirements.txt','Pipfile','uv.lock','poetry.lock'],
        'Node.js':['package.json','package-lock.json','pnpm-lock.yaml','yarn.lock','bun.lockb'],
        'Rust':['Cargo.toml','Cargo.lock'],'Go':['go.mod','go.sum'],'CMake':['CMakeLists.txt'],
        'Meson':['meson.build'],'Docker':['Dockerfile','compose.yaml','compose.yml','docker-compose.yml'],
        'ROS':['package.xml'],'Java / Maven':['pom.xml'],'Java / Gradle':['build.gradle','build.gradle.kts'],
        'Terraform':['main.tf','.terraform.lock.hcl'],'Kubernetes':['Chart.yaml','kustomization.yaml'],
        'Flutter':['pubspec.yaml'],'PlatformIO':['platformio.ini'],
    }
    for kind,names in signatures.items():
        hits=[n for n in names if (root/n).exists()]
        if hits: found.append({'kind':kind,'files':hits,'details':{}})
    if (root/'.venv').exists(): found.append({'kind':'Python venv','files':['.venv'],'details':{}})
    if (root/'src').is_dir() and any((root/'src').rglob('package.xml')): found.append({'kind':'ROS workspace','files':['src/**/package.xml'],'details':{}})
    pyproject=root/'pyproject.toml'
    if pyproject.exists():
        text=_read(pyproject)
        m=re.search(r'requires-python\s*=\s*["\']([^"\']+)',text)
        if m: found.append({'kind':'Python requirement','files':['pyproject.toml'],'details':{'version':m.group(1)}})
    pkg=root/'package.json'
    if pkg.exists():
        try:
            data=json.loads(_read(pkg)); engines=data.get('engines',{})
            if engines: found.append({'kind':'Node engines','files':['package.json'],'details':engines})
        except Exception: pass
    for fn,kind in [('.python-version','Python pin'),('.nvmrc','Node pin'),('.node-version','Node pin'),('rust-toolchain.toml','Rust pin')]:
        p=root/fn
        if p.exists(): found.append({'kind':kind,'files':[fn],'details':{'value':_read(p,4096).strip()}})
    return found
