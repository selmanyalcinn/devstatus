from __future__ import annotations
import fnmatch, re
from importlib.resources import files
from pathlib import Path
import yaml
from ..models import Artifact, Tool
from ..utils import which, safe_version_command, slugify, parse_version
from ..config import load_overrides, config_dir


def _load_yaml_resource(name: str) -> dict:
    p = files("devstatus.rules").joinpath(name)
    return yaml.safe_load(p.read_text()) or {}

def _load_custom_products() -> list[dict]:
    out=[]
    for p in sorted((config_dir()/"rules.d").glob("*.y*ml")):
        try:
            data=yaml.safe_load(p.read_text()) or {}
            if isinstance(data,dict): out.extend(data.get('products',[]))
        except Exception:
            continue
    return out

BUILTIN_CATALOG = _load_yaml_resource("catalog.yaml").get("products", [])
GENERIC = _load_yaml_resource("generic.yaml").get("categories", [])


def catalog() -> list[dict]:
    custom=_load_custom_products()
    seen=set(); out=[]
    for rule in [*custom,*BUILTIN_CATALOG]:
        rid=rule.get('id')
        if not rid or rid in seen: continue
        seen.add(rid); out.append(rule)
    return out

def extract_version(text: str | None) -> str | None:
    return parse_version(text)

def _matches(patterns: list[str], value: str) -> bool:
    return any(fnmatch.fnmatch(value.lower(), p.lower()) for p in patterns or [])

def _rule_artifacts(rule: dict, artifacts: list[Artifact]) -> list[Artifact]:
    out=[]
    for a in artifacts:
        matched=False
        if a.source=="apt" and _matches(rule.get("packages",[]), a.name): matched=True
        elif a.source=="snap" and _matches(rule.get("snaps",[]), a.name): matched=True
        elif a.source=="flatpak" and _matches(rule.get("flatpaks",[]), a.name): matched=True
        elif a.source in {'npm'} and _matches(rule.get('npm',[]),a.name): matched=True
        elif a.source in {'python','python-top','pipx','uv-tool'} and _matches(rule.get('python_packages',[]),a.name): matched=True
        elif a.source in {'cargo'} and _matches(rule.get('cargo',[]),a.name): matched=True
        elif a.source in {'go-tool'} and _matches(rule.get('go_modules',[]),a.metadata.get('module') or a.name): matched=True
        if _matches(rule.get("artifact_names",[]), a.name): matched=True
        if a.kind=="binary" and _matches(rule.get("binaries",[]), a.name): matched=True
        if a.source in {'npm','cargo','pipx','uv-tool','go-tool'} and _matches(rule.get("binaries",[]), a.name): matched=True
        if a.kind=="service" and _matches(rule.get("services",[]), a.name): matched=True
        if a.kind=='manual-install' and _matches(rule.get('paths',[]), a.path or a.name): matched=True
        if matched: out.append(a)
    for b in rule.get("binaries",[]) or []:
        p=which(b)
        if p and not any(x.kind=="binary" and x.name==b for x in out):
            out.append(Artifact(identity=f"which:{b}", name=b, kind="binary", source="path", path=p))
    return out

def _keyword_in(keyword: str, text: str) -> bool:
    return re.search(r'(?<![A-Za-z0-9_])' + re.escape(keyword.lower()) + r'(?![A-Za-z0-9_])', text.lower()) is not None

def _generic_tool(a: Artifact, min_hits: int=1) -> Tool | None:
    hay=f"{a.name} {a.description} {a.metadata.get('module','')} {a.path or ''}".lower()
    for g in GENERIC:
        hits=sum(1 for k in g.get("keywords",[]) if _keyword_in(k, hay))
        if hits >= min_hits:
            return Tool(id=f"generic:{slugify(a.name)}", name=a.name, category=tuple(g["category"]), version=a.version,
                        version_source=a.metadata.get('version_source') or a.source,
                        tags=set(g.get("tags",[])), sources={a.source}, components=[a],
                        metadata={'classification':'generic','keyword_hits':hits})
    return None

def _canonical_unknown(name: str) -> str:
    n=name.lower()
    n=re.sub(r'\.service$','',n)
    n=re.sub(r'^(python3?-|node-|lib)','',n)
    n=re.sub(r'[-_.](server|daemon|client|cli|tools?|common|core|runtime|desktop|dev|devel)$','',n)
    return slugify(n) or slugify(name)

def _unknown_groups(artifacts: list[Artifact]) -> dict[str,list[Artifact]]:
    groups={}
    for a in artifacts:
        key=_canonical_unknown(a.name)
        groups.setdefault(key,[]).append(a)
    return groups

def _pick_version(rule: dict, comps: list[Artifact]) -> tuple[str|None,str|None]:
    for cmd in rule.get("version_commands",[]) or []:
        version,raw=safe_version_command([str(x) for x in cmd])
        if version: return version,' '.join(str(x) for x in cmd)
    preferred=[]
    sigs=((rule.get('artifact_names',[]) or []) + (rule.get('packages',[]) or []) +
          (rule.get('snaps',[]) or []) + (rule.get('python_packages',[]) or []) +
          (rule.get('npm',[]) or []) + (rule.get('cargo',[]) or []))
    for c in comps:
        if c.version and (not sigs or any(fnmatch.fnmatch(c.name.lower(), sig.lower()) for sig in sigs)):
            preferred.append(c)
    versions=preferred or [c for c in comps if c.version]
    if versions:
        c=versions[0]
        return c.version,c.metadata.get('version_source') or c.source
    return None,None

def _status(comps: list[Artifact]) -> str|None:
    statuses=[c.status for c in comps if c.status]
    if 'failed' in statuses: return 'failed'
    if any(x in {'running','active'} for x in statuses): return 'running'
    if 'stopped' in statuses: return 'stopped'
    return statuses[0] if statuses else None

def _apply_overrides(tools: list[Tool]) -> list[Tool]:
    overrides=load_overrides()
    for t in tools:
        ov=overrides.get(t.id,{})
        if "name" in ov: t.name=ov["name"]
        if "version" in ov:
            t.version=ov["version"] or None; t.version_source='override'
        if "category" in ov:
            cat=ov["category"]; t.category=tuple(cat if isinstance(cat,list) else [str(cat)])
        if "hidden" in ov: t.hidden=bool(ov["hidden"])
        if "notes" in ov: t.notes=ov["notes"]
        if "tags" in ov:
            vals=ov["tags"] if isinstance(ov["tags"],list) else [str(ov["tags"])]
            t.tags.update(vals)
        if "status" in ov: t.status=ov['status'] or None
    return [t for t in tools if not t.hidden]

def classify(artifacts: list[Artifact], previous_artifact_ids: set[str] | None = None,
             show_all_unknown: bool=False) -> tuple[list[Tool], list[Artifact]]:
    tools=[]; matched_ids=set(); known_ids=set()
    for rule in catalog():
        comps=_rule_artifacts(rule, artifacts)
        if not comps:
            kws=[x.lower() for x in rule.get("keywords",[]) or []]
            if kws:
                comps=[a for a in artifacts if a.source in {'apt','snap','flatpak','pipx','npm','cargo','uv-tool','go-tool','manual','binary'}
                       and any(_keyword_in(k, f"{a.name} {a.description}") for k in kws)]
        if not comps: continue
        rid=rule['id']
        if rid in known_ids: continue
        matched_ids.update(c.identity for c in comps)
        version,version_source=_pick_version(rule,comps)
        if rid=="ros2":
            envs=[c for c in comps if c.source=="ros" and c.kind=="environment"]
            if envs:
                active=next((c for c in envs if c.status=="active"), envs[0])
                version=active.name.capitalize(); version_source='/opt/ros'
        tools.append(Tool(id=rid, name=rule["name"], category=tuple(rule.get("category",["Other"])),
                          version=version, version_source=version_source,
                          tags=set(rule.get("tags",[])), sources={c.source for c in comps},
                          components=comps, status=_status(comps), metadata={'classification':'rule'}))
        known_ids.add(rid)

    for a in artifacts:
        if a.identity in matched_ids: continue
        if a.kind=='gpu' and a.source=='nvidia':
            tid=f"hardware:{slugify(a.name)}"
            if tid not in known_ids:
                drv=a.metadata.get('driver') or a.version
                tools.append(Tool(id=tid,name=a.name,category=('GPU Compute','Hardware'),
                                  version=(f"driver {drv}" if drv else None), version_source='nvidia-smi',
                                  tags={'gpu','nvidia','hardware'},sources={'nvidia'},components=[a],
                                  metadata={'classification':'structured'}))
                known_ids.add(tid); matched_ids.add(a.identity)
        elif a.identity=='nvidia:cuda-capability':
            tid='nvidia-cuda-driver-capability'
            if tid not in known_ids:
                tools.append(Tool(id=tid,name='NVIDIA CUDA driver capability',category=('GPU Compute','Driver Capability'),
                                  version=a.version,version_source='nvidia-smi',tags={'gpu','nvidia','cuda'},
                                  sources={'nvidia'},components=[a],metadata={'classification':'structured'}))
                known_ids.add(tid); matched_ids.add(a.identity)

    unmatched=[a for a in artifacts if a.identity not in matched_ids]
    prev=previous_artifact_ids or set()
    user_sources={'binary','manual','pipx','npm','cargo','uv-tool','go-tool','flatpak','snap'}
    noisy_sources={'apt','python','python-top','ros','systemd'}

    for a in list(unmatched):
        new_since_baseline=previous_artifact_ids is not None and a.identity not in prev
        eligible=(a.source in user_sources) or a.source=='apt' or (new_since_baseline and a.source in noisy_sources)
        if not eligible: continue
        min_hits=2 if (a.source=='apt' and previous_artifact_ids is None and not a.metadata.get('history_explicit')) else 1
        t=_generic_tool(a,min_hits=min_hits)
        if t and t.id not in known_ids:
            tools.append(t); known_ids.add(t.id); matched_ids.add(a.identity)
    unmatched=[a for a in artifacts if a.identity not in matched_ids]

    groups=_unknown_groups(unmatched)
    consumed=set()
    for key,comps in groups.items():
        include=False
        for a in comps:
            new_since_baseline=previous_artifact_ids is not None and a.identity not in prev
            if (show_all_unknown or a.source in user_sources or
                (a.source=='apt' and a.metadata.get('history_explicit')) or
                (new_since_baseline and a.source in noisy_sources)):
                include=True; break
        if not include: continue
        tid=f"unclassified:{key}"
        if tid in known_ids: continue
        version_comp=next((a for a in comps if a.version),None)
        display=next((a.name for a in comps if a.kind not in {'service'}),comps[0].name)
        tools.append(Tool(id=tid,name=display,category=("Other / Unclassified",),
                          version=version_comp.version if version_comp else None,
                          version_source=(version_comp.metadata.get('version_source') or version_comp.source) if version_comp else None,
                          tags={'unclassified'},sources={a.source for a in comps},components=comps,status=_status(comps),
                          metadata={'classification':'unclassified'}))
        known_ids.add(tid); consumed.update(a.identity for a in comps)

    return _apply_overrides(tools), [a for a in artifacts if a.identity not in matched_ids and a.identity not in consumed]
