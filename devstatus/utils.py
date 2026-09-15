from __future__ import annotations
import os, re, shutil, subprocess
from pathlib import Path

VERSION_PATTERNS = [
    re.compile(r"(?i)(?:version|release|go|python|node|rustc|cargo|npm)?\s*[=:]?\s*v?(\d+\.\d+(?:\.\d+)?(?:\.\d+)?(?:[-+~][0-9A-Za-z._~+-]+)?)"),
    re.compile(r"\bv?(\d{1,4}(?:\.\d+){1,3}(?:[-+~][0-9A-Za-z._~+-]+)?)\b"),
]

def run(cmd: list[str] | str, timeout: float = 4.0, shell: bool = False, env: dict|None=None) -> tuple[int,str,str]:
    try:
        p = subprocess.run(cmd, shell=shell, text=True, capture_output=True, timeout=timeout,
                           env=(env or os.environ.copy()))
        return p.returncode, p.stdout.strip(), p.stderr.strip()
    except Exception as e:
        return 127, "", str(e)

def which(name: str) -> str | None:
    return shutil.which(name)

def first_line(s: str) -> str:
    return next((x.strip() for x in s.splitlines() if x.strip()), "")

def parse_version(text: str | None) -> str | None:
    if not text: return None
    for pat in VERSION_PATTERNS:
        m=pat.search(text)
        if m: return m.group(1)
    return None

def safe_version_command(cmd: list[str], timeout: float=3.0) -> tuple[str|None,str|None]:
    if not cmd: return None,None
    exe=cmd[0]
    if "/" not in exe and not which(exe): return None,None
    rc,out,err = run(cmd, timeout=timeout)
    text = first_line(out or err)
    return parse_version(text), text or None

def probe_binary(path: str, timeout: float=2.0) -> tuple[str|None,str|None,str|None]:
    """Best-effort version probe. Returns (version, source-command, raw-first-line)."""
    for suffix in (["--version"],["version"],["-V"]):
        cmd=[path,*suffix]
        rc,out,err=run(cmd, timeout=timeout)
        text=first_line(out or err)
        version=parse_version(text)
        if version:
            return version, " ".join([Path(path).name,*suffix]), text
    return None,None,None

def slugify(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r"[^a-z0-9._+-]+", "-", s)
    return s.strip("-")

def human_size(n: int|float) -> str:
    n=float(n)
    for unit in ("B","KiB","MiB","GiB","TiB"):
        if abs(n)<1024 or unit=="TiB": return f"{n:.1f} {unit}" if unit!="B" else f"{int(n)} B"
        n/=1024
    return f"{n:.1f} PiB"
