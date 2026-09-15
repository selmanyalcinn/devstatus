from __future__ import annotations
import psutil

def _guess_tool(process: str|None, snapshot: dict|None) -> str|None:
    if not process or not snapshot: return None
    p=process.lower()
    for t in snapshot.get('tools',[]):
        names=[t.get('name',''),t.get('id','')]
        names += [c.get('name','') for c in t.get('components',[])]
        if any(n and (n.lower() in p or p in n.lower()) for n in names): return t.get('name')
    return None

def listening_ports(snapshot: dict|None=None) -> list[dict]:
    rows=[]
    try: conns=psutil.net_connections(kind='inet')
    except Exception: return rows
    for c in conns:
        if not c.laddr: continue
        listening=(c.type==1 and c.status==psutil.CONN_LISTEN) or c.type==2
        if not listening: continue
        proc=None
        if c.pid:
            try: proc=psutil.Process(c.pid).name()
            except Exception: pass
        rows.append({'host':c.laddr.ip,'port':c.laddr.port,'pid':c.pid,'process':proc,'tool':_guess_tool(proc,snapshot),
                     'protocol':'tcp' if c.type==1 else 'udp'})
    return sorted(rows,key=lambda x:(x['port'],x['protocol'],x['host']))
