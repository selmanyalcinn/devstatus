from __future__ import annotations
import re
from ..models import Artifact
from ..utils import run, which

def scan() -> list[Artifact]:
    if not which("nvidia-smi"): return []
    items=[]
    rc,out,_=run(["nvidia-smi","--query-gpu=name,driver_version","--format=csv,noheader"], timeout=5)
    if rc==0:
        for i,line in enumerate(out.splitlines()):
            p=[x.strip() for x in line.split(",",1)]
            items.append(Artifact(identity=f"gpu:nvidia:{i}", name=p[0], kind="gpu", source="nvidia",
                                  version=p[1] if len(p)>1 else None,
                                  metadata={"driver": p[1] if len(p)>1 else None,"version_source":"nvidia-smi"}))
    rc2,out2,_=run(["nvidia-smi"],timeout=5)
    if rc2==0:
        m=re.search(r"CUDA Version:\s*([0-9.]+)",out2)
        if m:
            items.append(Artifact(identity='nvidia:cuda-capability',name='NVIDIA CUDA driver capability',kind='capability',
                                  source='nvidia',version=m.group(1),description='Maximum CUDA API level reported by the NVIDIA driver'))
    return items
