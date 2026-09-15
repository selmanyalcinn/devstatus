from __future__ import annotations
from ..models import Artifact
from ..utils import run, which

def scan() -> list[Artifact]:
    if not which("systemctl"): return []
    rc,out,_=run(["systemctl","list-unit-files","--type=service","--no-legend","--no-pager"], timeout=12)
    if rc: return []
    enabled_map={}
    for line in out.splitlines():
        p=line.split()
        if p and p[0].endswith('.service'): enabled_map[p[0]]=p[1] if len(p)>1 else None
    active_map={}
    rc2,out2,_=run(["systemctl","list-units","--type=service","--all","--no-legend","--no-pager"], timeout=12)
    if rc2==0:
        for line in out2.splitlines():
            p=line.split()
            if len(p)>=4 and p[0].endswith('.service'):
                active_map[p[0]]=(p[2],p[3])
    failed=set()
    rc3,out3,_=run(["systemctl","--failed","--type=service","--no-legend","--no-pager"],timeout=8)
    if rc3==0:
        failed={line.split()[0] for line in out3.splitlines() if line.split()}
    items=[]
    for unit,enabled in enabled_map.items():
        active,sub=active_map.get(unit,('inactive','dead'))
        status='failed' if unit in failed else ('running' if active=='active' and sub in {'running','exited','listening'} else active)
        items.append(Artifact(identity=f"service:{unit}", name=unit, kind="service", source="systemd", status=status,
                              metadata={"enabled":enabled,"active":active,"sub":sub}))
    return items
