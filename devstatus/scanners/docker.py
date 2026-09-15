from __future__ import annotations
from ..models import Artifact
from ..utils import run, which

def scan() -> list[Artifact]:
    if not which("docker"): return []
    items=[]
    rc,out,_=run(["docker","version","--format","{{.Client.Version}}"], timeout=4)
    if rc==0 and out:
        items.append(Artifact(identity="tool:docker", name="docker", kind="tool", source="docker", version=out,
                              metadata={'version_source':'docker version'}))
    rc,out,_=run(["docker","compose","version","--short"], timeout=4)
    if rc==0 and out:
        items.append(Artifact(identity="tool:docker-compose", name="docker-compose", kind="tool", source="docker", version=out,
                              metadata={'version_source':'docker compose version'}))
    rc,out,_=run(["docker","images","--format","{{.Repository}}\t{{.Tag}}\t{{.ID}}\t{{.Size}}"], timeout=8)
    if rc==0:
        for line in out.splitlines():
            p=line.split("\t")
            if len(p)>=2:
                repo,tag=p[0],p[1]
                items.append(Artifact(identity=f"image:{repo}:{tag}", name=repo, kind="docker-image", source="docker",
                                      version=None if tag in {'latest','<none>'} else tag,
                                      metadata={"tag":tag,"image_id": p[2] if len(p)>2 else None, "size": p[3] if len(p)>3 else None}))
    rc,out,_=run(["docker","ps","-a","--format","{{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}"], timeout=8)
    if rc==0:
        for line in out.splitlines():
            p=line.split("\t")
            if p:
                status=p[2] if len(p)>2 else None
                normalized='running' if status and status.lower().startswith('up ') else ('stopped' if status else None)
                items.append(Artifact(identity=f"container:{p[0]}", name=p[0], kind="docker-container", source="docker",
                                      status=normalized, metadata={"image": p[1] if len(p)>1 else None,
                                                                  "raw_status":status,"ports":p[3] if len(p)>3 else None}))
    return items
