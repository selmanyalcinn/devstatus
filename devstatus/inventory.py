from __future__ import annotations
import platform
from pathlib import Path
from .scanners import scan_all_detailed
from .resolvers.classifier import classify
from .state.snapshots import load_latest


def os_info() -> dict:
    pretty=platform.platform(); os_id='linux'; version=''
    p=Path('/etc/os-release')
    if p.exists():
        vals={}
        for line in p.read_text(errors='ignore').splitlines():
            if '=' in line:
                k,v=line.split('=',1); vals[k]=v.strip('"')
        pretty=vals.get('PRETTY_NAME',pretty); os_id=vals.get('ID',os_id); version=vals.get('VERSION_ID','')
    return {'os':pretty,'os_id':os_id,'os_version':version,'kernel':platform.release(),'hostname':platform.node(),'arch':platform.machine()}

def build(show_all_unknown: bool=False, previous: dict|None=None) -> dict:
    if previous is None: previous=load_latest()
    artifacts,errors=scan_all_detailed()
    prev_ids={a['identity'] for a in previous.get('artifacts',[])} if previous else None
    tools,unmatched=classify(artifacts, prev_ids, show_all_unknown=show_all_unknown)
    return {
        'schema_version':1,
        'system': os_info(),
        'tools':[t.to_dict() for t in sorted(tools,key=lambda x:(x.category,x.name.lower()))],
        'artifacts':[a.to_dict() for a in sorted(artifacts,key=lambda x:(x.source,x.name.lower(),x.identity))],
        'unmatched':[a.to_dict() for a in unmatched],
        'scan_errors':errors,
    }
