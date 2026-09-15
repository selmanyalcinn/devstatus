from __future__ import annotations
from importlib import metadata
from . import apt, snap, binaries, manual, systemd, docker, environments, gpu, ros, ecosystems

BUILTIN_SCANNERS = [apt.scan, snap.scan, binaries.scan, manual.scan, systemd.scan, docker.scan, environments.scan, gpu.scan, ros.scan, ecosystems.scan]

def _plugin_scanners():
    scanners=[]
    try:
        eps=metadata.entry_points()
        group=eps.select(group='devstatus.scanners') if hasattr(eps,'select') else eps.get('devstatus.scanners',[])
        for ep in group:
            try: scanners.append(ep.load())
            except Exception: pass
    except Exception: pass
    return scanners

def scan_all_detailed():
    out=[]; errors=[]
    for scanner in [*BUILTIN_SCANNERS,*_plugin_scanners()]:
        try:
            result=scanner() or []
            out.extend(result)
        except Exception as e:
            errors.append({'scanner':getattr(scanner,'__module__',repr(scanner)),'error':str(e)})
    seen={}
    for a in out: seen[a.identity]=a
    return list(seen.values()),errors

def scan_all():
    return scan_all_detailed()[0]
