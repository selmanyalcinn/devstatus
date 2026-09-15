from __future__ import annotations

def _tool_view(t: dict) -> dict:
    return {'id':t['id'],'name':t.get('name',t['id']),'version':t.get('version'),'category':t.get('category',[]),
            'status':t.get('status'),'sources':t.get('sources',[])}

def compare(old: dict | None, new: dict) -> dict:
    empty={"added":[],"removed":[],"updated":[],"tool_added":[],"tool_removed":[],"tool_updated":[]}
    if not old: return empty
    oa={a["identity"]:a for a in old.get("artifacts",[])}; na={a["identity"]:a for a in new.get("artifacts",[])}
    added=[na[k] for k in sorted(na.keys()-oa.keys())]
    removed=[oa[k] for k in sorted(oa.keys()-na.keys())]
    ot={t["id"]:t for t in old.get("tools",[])}; nt={t["id"]:t for t in new.get("tools",[])}
    tool_added=[_tool_view(nt[k]) for k in sorted(nt.keys()-ot.keys())]
    tool_removed=[_tool_view(ot[k]) for k in sorted(ot.keys()-nt.keys())]
    updated=[]; tool_updated=[]
    for k in sorted(ot.keys() & nt.keys()):
        before,after=ot[k],nt[k]
        changes={}
        for field in ('version','status','category','name'):
            if before.get(field)!=after.get(field): changes[field]=(before.get(field),after.get(field))
        if changes:
            tool_updated.append({'id':k,'name':after.get('name',k),'changes':changes,
                                 'before':before.get('version'),'after':after.get('version')})
            if 'version' in changes:
                updated.append({'id':k,'name':after.get('name',k),'before':before.get('version'),'after':after.get('version')})
    return {"added":added,"removed":removed,"updated":updated,
            "tool_added":tool_added,"tool_removed":tool_removed,"tool_updated":tool_updated}
