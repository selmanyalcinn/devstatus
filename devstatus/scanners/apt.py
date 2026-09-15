from __future__ import annotations
import gzip, re
from pathlib import Path
from ..models import Artifact
from ..utils import run

LOG_DIR=Path('/var/log/apt')

def _history_explicit_installs() -> set[str]:
    explicit=set()
    files=[]
    if LOG_DIR.exists():
        files.extend(sorted(LOG_DIR.glob('history.log*')))
    for p in files:
        try:
            text=(gzip.open(p,'rt',errors='ignore').read() if p.suffix=='.gz' else p.read_text(errors='ignore'))
        except Exception:
            continue
        for block in re.split(r'\n\s*\n',text):
            cmd=re.search(r'^Commandline:\s*(.+)$',block,re.M)
            if not cmd: continue
            cl=cmd.group(1)
            if not re.search(r'\b(apt|apt-get)\b.*\binstall\b',cl) or 'unattended-upgrade' in cl: continue
            inst=re.search(r'^Install:\s*(.+)$',block,re.M)
            if inst:
                for item in inst.group(1).split(', '):
                    m=re.match(r'([^ :(),]+)(?::[^ (),]+)?\s*\(',item)
                    if m and ', automatic)' not in item: explicit.add(m.group(1))
            parts=cl.split(); seen_install=False
            for token in parts:
                if token=='install': seen_install=True; continue
                if not seen_install or token.startswith('-') or token.startswith('./') or '/' in token: continue
                token=token.split('=',1)[0].split(':',1)[0]
                if re.match(r'^[A-Za-z0-9][A-Za-z0-9+.-]+$',token): explicit.add(token)
    return explicit

def scan() -> list[Artifact]:
    rc,manual,_ = run(["apt-mark","showmanual"], timeout=12)
    if rc != 0: return []
    names = {x.strip() for x in manual.splitlines() if x.strip()}
    if not names: return []
    history_explicit=_history_explicit_installs()
    rc,out,_ = run(["dpkg-query","-W","-f=${binary:Package}\t${Version}\t${binary:Summary}\\n"], timeout=15)
    if rc != 0: return []
    items=[]
    for line in out.splitlines():
        parts=line.split("\t",2)
        if len(parts)<2: continue
        pkg=parts[0].split(":",1)[0]
        if pkg not in names: continue
        items.append(Artifact(identity=f"apt:{pkg}", name=pkg, kind="package", source="apt", version=parts[1],
                              description=parts[2] if len(parts)>2 else "",
                              metadata={"manual": True,"history_explicit":pkg in history_explicit,"version_source":"dpkg"}))
    return items
