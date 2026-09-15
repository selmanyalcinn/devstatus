from __future__ import annotations
import os, shutil
from pathlib import Path
from ..utils import run, which

def diagnose(snapshot: dict) -> list[dict]:
    issues=[]; ids={t['id']:t for t in snapshot.get('tools',[])}
    for err in snapshot.get('scan_errors',[]):
        issues.append({'level':'info','name':'Scanner','message':f"{err.get('scanner')}: {err.get('error')}"})
    if 'docker' in ids:
        rc,_,_=run(['docker','info'],timeout=5)
        if rc: issues.append({'level':'warn','name':'Docker','message':'Docker CLI is installed but the daemon is not reachable by this user.'})
    ros_envs=[a for a in snapshot.get('artifacts',[]) if a.get('source')=='ros' and a.get('kind')=='environment']
    if ros_envs and not os.environ.get('ROS_DISTRO'):
        distros=', '.join(a['name'] for a in ros_envs)
        issues.append({'level':'info','name':'ROS','message':f'Installed ({distros}) but no ROS_DISTRO is active in this shell.'})
    if which('nvidia-smi'):
        rc,_,_=run(['nvidia-smi'],timeout=5)
        if rc: issues.append({'level':'warn','name':'NVIDIA','message':'nvidia-smi exists but failed to query the GPU.'})
    failed=[a['name'] for a in snapshot.get('artifacts',[]) if a.get('kind')=='service' and a.get('status')=='failed']
    for name in failed[:20]: issues.append({'level':'warn','name':name,'message':'systemd reports this service as failed.'})
    root=shutil.disk_usage('/')
    if root.free/root.total < .08:
        issues.append({'level':'warn','name':'Disk','message':f'Root filesystem has only {root.free/root.total:.1%} free space.'})
    for folder in (Path.home()/'.local/bin',Path.home()/'.cargo/bin'):
        if folder.is_dir():
            broken=[]
            for p in folder.iterdir():
                if p.is_symlink() and not p.exists(): broken.append(p.name)
            if broken: issues.append({'level':'info','name':'PATH','message':f"Broken symlinks in {folder}: {', '.join(broken[:8])}"})
    for t in snapshot.get('tools',[]):
        if not t.get('version') and t.get('id','').startswith(('unclassified:','generic:')):
            issues.append({'level':'info','name':t['name'],'message':f"Version is unknown. Override with: devstatus set '{t['id']}' version <value>"})
    return issues
