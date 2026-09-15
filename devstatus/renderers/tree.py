from __future__ import annotations
from rich.console import Console
from rich.tree import Tree
from ..config import load_settings

console=Console()

def _insert_category(root: Tree, cache: dict, path: list[str]) -> Tree:
    cur=root; acc=[]
    for part in path:
        acc.append(part); key=tuple(acc)
        if key not in cache: cache[key]=cur.add(f"[bold]{part}[/bold]")
        cur=cache[key]
    return cur

def _status_markup(status: str|None) -> str:
    if not status: return ''
    if status in {'running','active'}: return f" [green][{status}][/green]"
    if status=='failed': return f" [red][{status}][/red]"
    return f" [yellow][{status}][/yellow]"

def render(snapshot: dict, changes: dict|None=None, show_version_source: bool=False) -> None:
    s=snapshot['system']
    console.print(f"[bold cyan]{s['os']}[/bold cyan]  [dim]{s['hostname']} · {s['kernel']} · {s['arch']}[/dim]")
    if changes and (changes.get('tool_added') or changes.get('tool_removed') or changes.get('tool_updated')):
        console.print(); console.print('[bold yellow]Changes since last snapshot[/bold yellow]')
        for x in changes.get('tool_added',[])[:12]: console.print(f"  [green]+[/green] {x['name']} [dim]{x.get('version') or 'unknown'}[/dim]")
        for x in changes.get('tool_removed',[])[:12]: console.print(f"  [red]-[/red] {x['name']}")
        for x in changes.get('tool_updated',[])[:12]:
            parts=[]
            for field,(before,after) in x.get('changes',{}).items():
                if field=='category': before=' > '.join(before or []); after=' > '.join(after or [])
                parts.append(f"{field}: {before or 'unknown'} → {after or 'unknown'}")
            console.print(f"  [yellow]~[/yellow] {x['name']} [dim]{'; '.join(parts)}[/dim]")
    console.print()
    root=Tree('[bold]Developer environment[/bold]'); cache={}; settings=load_settings()
    for t in snapshot['tools']:
        parent=_insert_category(root,cache,t.get('category') or ['Other'])
        ver=t.get('version') or 'unknown'; status=_status_markup(t.get('status'))
        label=f"{t['name']} [cyan]{ver}[/cyan]{status}"
        if t.get('id','').startswith('unclassified:'): label+=' [yellow][unclassified][/yellow]'
        if settings.get('show_sources',True) and t.get('sources'): label+=f" [dim]· {', '.join(t['sources'])}[/dim]"
        if show_version_source and t.get('version_source'): label+=f" [dim]· version: {t['version_source']}[/dim]"
        parent.add(label)
    console.print(root)
    if snapshot.get('scan_errors'):
        console.print(f"\n[yellow]{len(snapshot['scan_errors'])} scanner warning(s). Run devstatus doctor for details.[/yellow]")
