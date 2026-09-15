from __future__ import annotations
import json, re
from importlib import metadata
from pathlib import Path
from ..models import Artifact
from ..utils import run, which, parse_version

def scan() -> list[Artifact]:
    items=[]
    try:
        for d in metadata.distributions():
            name=d.metadata.get('Name') or d.name
            if name:
                items.append(Artifact(identity=f"python-pkg:{name.lower()}", name=name, kind='language-package', source='python',
                                      version=d.version, description=d.metadata.get('Summary') or ''))
    except Exception: pass
    if which('python3'):
        rc,out,_=run(['python3','-m','pip','list','--not-required','--format','json'],timeout=10)
        if rc==0 and out:
            try:
                for pkg in json.loads(out):
                    items.append(Artifact(identity=f"python-top:{pkg['name'].lower()}", name=pkg['name'], kind='language-package', source='python-top', version=pkg.get('version')))
            except Exception: pass
    if which('pipx'):
        rc,out,_=run(['pipx','list','--json'],timeout=8)
        if rc==0:
            try:
                data=json.loads(out)
                for name,meta in data.get('venvs',{}).items():
                    pkg=meta.get('metadata',{}).get('main_package',{})
                    items.append(Artifact(identity=f"pipx:{name}", name=name, kind='language-package', source='pipx', version=pkg.get('package_version')))
            except Exception: pass
    if which('npm'):
        rc,out,_=run(['npm','list','-g','--depth=0','--json'],timeout=10)
        if rc in (0,1) and out:
            try:
                data=json.loads(out)
                for name,meta in data.get('dependencies',{}).items():
                    items.append(Artifact(identity=f"npm:{name}", name=name, kind='language-package', source='npm', version=meta.get('version')))
            except Exception: pass
    if which('cargo'):
        rc,out,_=run(['cargo','install','--list'],timeout=10)
        if rc==0:
            for line in out.splitlines():
                if line and not line.startswith(' '):
                    m=re.match(r"([^ ]+) v([^:]+):",line)
                    if m: items.append(Artifact(identity=f"cargo:{m.group(1)}", name=m.group(1), kind='language-package', source='cargo', version=m.group(2)))
    if which('go'):
        gobin=Path.home()/'go/bin'
        if gobin.is_dir():
            for p in gobin.iterdir():
                if not p.is_file(): continue
                rc,out,_=run(['go','version','-m',str(p)],timeout=4)
                if rc==0:
                    version=None; module=None
                    for line in out.splitlines():
                        fields=line.strip().split()
                        if fields and fields[0]=='mod' and len(fields)>=3:
                            module=fields[1]; version=fields[2].lstrip('v'); break
                    items.append(Artifact(identity=f"go-tool:{p.name}",name=p.name,kind='language-package',source='go-tool',version=version,
                                          path=str(p),metadata={'module':module}))
    if which('flatpak'):
        rc,out,_=run(['flatpak','list','--columns=application,version'],timeout=8)
        if rc==0:
            for line in out.splitlines():
                p=line.split('\t')
                if p and p[0]: items.append(Artifact(identity=f"flatpak:{p[0]}", name=p[0], kind='package', source='flatpak', version=p[1] if len(p)>1 else None))
    return items
