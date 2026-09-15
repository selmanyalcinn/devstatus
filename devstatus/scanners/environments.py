from __future__ import annotations
import json, os, re
from pathlib import Path
from ..models import Artifact
from ..utils import run, which, parse_version

def _conda_python_version(path: Path) -> str|None:
    meta=path/'conda-meta'
    if not meta.is_dir(): return None
    candidates=sorted(meta.glob('python-*.json'), reverse=True)
    for p in candidates:
        try:
            d=json.loads(p.read_text())
            if d.get('version'): return str(d['version'])
        except Exception: pass
    return None

def scan() -> list[Artifact]:
    items=[]
    if which("python3"):
        rc,out,_=run(["python3","--version"])
        items.append(Artifact(identity="runtime:python3", name="python", kind="runtime", source="system",
                              version=out.replace("Python ","") if rc==0 else None,
                              metadata={'version_source':'python3 --version'}))
    if which("uv"):
        rc,out,_=run(["uv","--version"])
        items.append(Artifact(identity="tool:uv", name="uv", kind="tool", source="uv",
                              version=out.split()[-1] if rc==0 and out else None))
        rc,out,_=run(["uv","python","list","--only-installed"], timeout=8)
        if rc==0:
            for line in out.splitlines():
                text=line.strip()
                if not text: continue
                v=parse_version(text)
                items.append(Artifact(identity=f"uvpy:{text}", name=text.split()[0], kind="environment", source="uv",
                                      version=v, metadata={'raw':text}))
        rc,out,_=run(["uv","tool","list"],timeout=8)
        if rc==0:
            current=None
            for line in out.splitlines():
                if line and not line.startswith((' ','-')):
                    m=re.match(r'([^ ]+) v?([^ ]+)',line.strip())
                    if m:
                        current=m.group(1)
                        items.append(Artifact(identity=f"uvtool:{current}",name=current,kind='language-package',source='uv-tool',version=parse_version(m.group(2)) or m.group(2)))
    if which("conda"):
        rc,out,_=run(["conda","--version"])
        items.append(Artifact(identity="tool:conda", name="conda", kind="tool", source="conda",
                              version=out.split()[-1] if rc==0 and out else None))
        rc,out,_=run(["conda","env","list","--json"], timeout=8)
        if rc==0:
            try:
                data=json.loads(out); active=os.environ.get("CONDA_PREFIX")
                for p in data.get("envs",[]):
                    path=Path(p); name='base' if path.name in {'miniconda3','anaconda3','miniforge3'} else (path.name or 'base')
                    items.append(Artifact(identity=f"conda:{p}", name=name, kind="environment", source="conda",
                                          version=_conda_python_version(path), path=p,
                                          status="active" if active==p else None,
                                          metadata={'runtime':'python'}))
            except Exception: pass
    if which("node"):
        rc,out,_=run(["node","--version"])
        items.append(Artifact(identity="runtime:node", name="node", kind="runtime", source="node",
                              version=out.lstrip("v") if rc==0 else None, status="active",
                              metadata={'version_source':'node --version'}))
    nvm_root=Path(os.environ.get("NVM_DIR", Path.home()/".nvm"))
    nvm_dir=nvm_root/"versions/node"
    if nvm_root.exists():
        nvm_version=None
        pkg=nvm_root/'package.json'
        if pkg.exists():
            try: nvm_version=str(json.loads(pkg.read_text()).get('version') or '') or None
            except Exception: pass
        if not nvm_version and (nvm_root/'.git').exists() and which('git'):
            rc,v,_=run(['git','-C',str(nvm_root),'describe','--tags','--abbrev=0'],timeout=3)
            if rc==0: nvm_version=v.lstrip('v')
        items.append(Artifact(identity='tool:nvm',name='nvm',kind='tool',source='nvm',version=nvm_version,path=str(nvm_root)))
    active_node=None
    if which('node'):
        try: active_node=str(Path(which('node')).resolve())
        except Exception: active_node=None
    if nvm_dir.exists():
        for p in sorted(nvm_dir.iterdir()):
            if p.is_dir():
                node_path=str((p/'bin/node').resolve()) if (p/'bin/node').exists() else ''
                items.append(Artifact(identity=f"nvm:{p.name}", name=p.name, kind="environment", source="nvm",
                                      version=p.name.lstrip("v"), path=str(p), status='active' if active_node and node_path==active_node else None,
                                      metadata={'runtime':'node'}))
    if which("rustup"):
        rc,out,_=run(["rustup","toolchain","list"])
        if rc==0:
            for line in out.splitlines():
                status="active" if "(active" in line or "(default" in line else None
                name=line.split()[0]
                items.append(Artifact(identity=f"rustup:{name}", name=name, kind="environment", source="rustup", status=status,
                                      metadata={'runtime':'rust'}))
    rosroot=Path("/opt/ros")
    if rosroot.exists():
        active=os.environ.get("ROS_DISTRO")
        for p in sorted(rosroot.iterdir()):
            if p.is_dir():
                items.append(Artifact(identity=f"ros:{p.name}", name=p.name, kind="environment", source="ros", path=str(p),
                                      status="active" if active==p.name else None, metadata={'runtime':'ros'}))
    return items
