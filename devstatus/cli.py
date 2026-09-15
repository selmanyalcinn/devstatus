from __future__ import annotations
import json
from collections import Counter
from pathlib import Path
import typer, yaml
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt

from . import __version__
from .inventory import build
from .renderers.tree import render
from .state.snapshots import load_latest, save, history as history_files, resolve as resolve_snapshot, reset as reset_baseline
from .state.diff import compare as compare_state
from .config import load_overrides, save_overrides, load_settings, save_settings, config_dir
from .diagnostics.doctor import diagnose
from .diagnostics.ports import listening_ports
from .diagnostics.disk import usage as disk_usage
from .project.detector import detect as detect_project
from .resolvers.classifier import catalog, BUILTIN_CATALOG

app=typer.Typer(add_completion=True, no_args_is_help=False, help="Dynamic developer machine inventory and environment intelligence.")
rules_app=typer.Typer(help='Inspect and extend classification rules.')
config_app=typer.Typer(help='Read or change devstatus settings.')
app.add_typer(rules_app,name='rules'); app.add_typer(config_app,name='config')
console=Console()

def _version_cb(value: bool):
    if value:
        console.print(f'devstatus {__version__}'); raise typer.Exit()

def _current(show_all_unknown: bool=False):
    prev=load_latest(); cur=build(show_all_unknown=show_all_unknown, previous=prev)
    return prev,cur,compare_state(prev,cur)

@app.callback(invoke_without_command=True)
def main(ctx: typer.Context, version: bool=typer.Option(False,'--version',callback=_version_cb,is_eager=True,help='Show version and exit.')):
    """Run without a subcommand to scan, render, and save a snapshot."""
    if ctx.invoked_subcommand is None:
        prev,cur,changes=_current(False); render(cur,changes); save(cur)

@app.command()
def scan(all_unknown: bool=typer.Option(False,'--all-unknown',help='Include baseline unknown APT / system packages.'),
         no_save: bool=typer.Option(False,'--no-save',help='Do not update snapshot history.'),
         version_source: bool=typer.Option(False,'--version-source',help='Show where each detected version came from.')):
    """Scan the machine and render the dynamic tree."""
    prev,cur,changes=_current(all_unknown); render(cur,changes,version_source)
    if not no_save:
        p=save(cur); console.print(f"\n[dim]Snapshot saved: {p.name}[/dim]")

@app.command('all')
def all_inventory():
    """Render the tree including all unclassified packages."""
    _,cur,changes=_current(True); render(cur,changes,True)

@app.command('new')
def new_changes(raw: bool=typer.Option(False,'--raw',help='Also show package/artifact-level changes.')):
    """Show changes since the last saved snapshot without updating it."""
    prev,cur,changes=_current(False)
    if not prev:
        console.print('No baseline snapshot yet. Run [bold]devstatus scan[/bold] first.'); raise typer.Exit()
    if not any(changes.get(k) for k in ('tool_added','tool_removed','tool_updated','added','removed')):
        console.print('[green]No changes since the last snapshot.[/green]'); return
    t=Table('Change','Tool','Details')
    for x in changes['tool_added']: t.add_row('+',x['name'],x.get('version') or 'unknown')
    for x in changes['tool_removed']: t.add_row('-',x['name'],x.get('version') or 'unknown')
    for x in changes['tool_updated']:
        details=[]
        for field,(a,b) in x['changes'].items(): details.append(f"{field}: {a or 'unknown'} → {b or 'unknown'}")
        t.add_row('~',x['name'],'; '.join(details))
    console.print(t)
    if raw:
        a=Table('Artifact change','Source','Artifact','Version')
        for x in changes['added']: a.add_row('+',x['source'],x['name'],x.get('version') or '')
        for x in changes['removed']: a.add_row('-',x['source'],x['name'],x.get('version') or '')
        console.print(a)

@app.command()
def history(limit: int=typer.Option(20,'--limit','-n')):
    """List saved snapshots. Index 0 is the newest history entry."""
    rows=history_files()[:limit]
    if not rows: console.print('No snapshots yet.'); return
    t=Table('Index','Snapshot','Timestamp')
    for i,p in enumerate(rows):
        d=json.loads(p.read_text()); t.add_row(str(i),p.name,d.get('timestamp',''))
    console.print(t)

@app.command()
def diff(left: str='previous', right: str='latest'):
    """Diff two snapshot refs: latest, previous, history index, timestamp prefix, or JSON file."""
    lp,a=resolve_snapshot(left); rp,b=resolve_snapshot(right)
    if not a or not b: raise typer.BadParameter('Could not resolve one of the snapshot references.')
    ch=compare_state(a,b); t=Table('Change','Tool','Details')
    for x in ch['tool_added']: t.add_row('+',x['name'],x.get('version') or 'unknown')
    for x in ch['tool_removed']: t.add_row('-',x['name'],x.get('version') or 'unknown')
    for x in ch['tool_updated']:
        details='; '.join(f"{k}: {v[0] or 'unknown'} → {v[1] or 'unknown'}" for k,v in x['changes'].items())
        t.add_row('~',x['name'],details)
    console.print(f"[dim]{lp} → {rp}[/dim]"); console.print(t)

@app.command('baseline-reset')
def baseline_reset():
    """Remove latest baseline pointer. History files are kept."""
    reset_baseline(); console.print('[green]Latest baseline reset. History preserved.[/green]')

@app.command()
def env():
    """Show runtime and environment-manager environments."""
    _,cur,_=_current(False); rows=[a for a in cur['artifacts'] if a['kind']=='environment']
    t=Table('Source','Environment','Version','Status','Path')
    for a in rows: t.add_row(a['source'],a['name'],a.get('version') or '',a.get('status') or '',a.get('path') or '')
    console.print(t)

@app.command()
def services(all_services: bool=typer.Option(False,'--all',help='Show every systemd service, not just developer-related matches.')):
    """Show services and their runtime/enabled state."""
    _,cur,_=_current(False); arts=[a for a in cur['artifacts'] if a['kind']=='service']
    recognized=set()
    for tool in cur['tools']:
        recognized.update(c['identity'] for c in tool.get('components',[]) if c.get('kind')=='service')
    if not all_services: arts=[a for a in arts if a['identity'] in recognized or a.get('status')=='failed']
    t=Table('Service','Status','Enabled')
    for a in arts: t.add_row(a['name'],a.get('status') or 'unknown',str(a.get('metadata',{}).get('enabled','')))
    console.print(t)

@app.command()
def packages(source: str|None=typer.Option(None,'--source',help='Filter: apt, snap, npm, pipx, cargo, python, flatpak, uv-tool, go-tool…')):
    """Show package-manager inventory."""
    _,cur,_=_current(False); allowed={'package','language-package'}
    rows=[a for a in cur['artifacts'] if a['kind'] in allowed and (not source or a['source']==source)]
    t=Table('Source','Package','Version')
    for a in sorted(rows,key=lambda x:(x['source'],x['name'].lower())): t.add_row(a['source'],a['name'],a.get('version') or 'unknown')
    console.print(t)

@app.command()
def docker():
    """Show Docker engine, images, and containers."""
    _,cur,_=_current(False); arts=cur['artifacts']
    tools=[a for a in arts if a['source']=='docker' and a['kind']=='tool']
    if tools:
        t=Table('Docker component','Version')
        for a in tools: t.add_row(a['name'],a.get('version') or 'unknown')
        console.print(t)
    images=[a for a in arts if a['kind']=='docker-image']
    if images:
        t=Table('Image','Tag / Version','Size')
        for a in images: t.add_row(a['name'],a.get('metadata',{}).get('tag') or a.get('version') or '',a.get('metadata',{}).get('size') or '')
        console.print(t)
    containers=[a for a in arts if a['kind']=='docker-container']
    if containers:
        t=Table('Container','Image','Status','Ports')
        for a in containers: t.add_row(a['name'],a.get('metadata',{}).get('image') or '',a.get('status') or '',a.get('metadata',{}).get('ports') or '')
        console.print(t)
    if not tools and not images and not containers: console.print('Docker not detected or daemon not reachable.')

@app.command()
def search(query: str):
    """Search tools, tags, categories, components, descriptions, and paths."""
    _,cur,_=_current(True); q=query.lower(); hits=[]
    for t in cur['tools']:
        hay=' '.join([t['id'],t['name'],' '.join(t.get('category',[])),' '.join(t.get('tags',[])),t.get('notes') or ''] +
                     [f"{c.get('name','')} {c.get('description','')} {c.get('path','')}" for c in t.get('components',[])])
        if q in hay.lower(): hits.append(t)
    if not hits: console.print('No matches.'); return
    t=Table('ID','Name','Version','Category','Status')
    for x in hits: t.add_row(x['id'],x['name'],x.get('version') or 'unknown',' > '.join(x.get('category',[])),x.get('status') or '')
    console.print(t)

@app.command()
def tag(tag_name: str):
    """Show tools with a given tag, such as robotics, backend, ai, security."""
    _,cur,_=_current(True); q=tag_name.lower(); rows=[t for t in cur['tools'] if q in [x.lower() for x in t.get('tags',[])]]
    t=Table('Tool','Version','Category')
    for x in rows: t.add_row(x['name'],x.get('version') or 'unknown',' > '.join(x.get('category',[])))
    console.print(t)

@app.command()
def explain(tool_id: str):
    """Explain how a tool was detected, classified, and versioned."""
    _,cur,_=_current(True); t=next((x for x in cur['tools'] if x['id']==tool_id),None)
    if not t: console.print('Tool not found. Use devstatus search <query>.'); raise typer.Exit(1)
    console.print(f"[bold]{t['name']}[/bold]  {t.get('version') or 'unknown'}")
    console.print(f"ID: {t['id']}\nCategory: {' > '.join(t.get('category',[]))}\nTags: {', '.join(t.get('tags',[]))}\nSources: {', '.join(t.get('sources',[]))}")
    console.print(f"Version source: {t.get('version_source') or 'unknown'}\nClassification: {t.get('metadata',{}).get('classification','unknown')}")
    if t.get('notes'): console.print(f"Notes: {t['notes']}")
    c=Table('Component','Kind','Source','Version','Status','Path')
    for a in t.get('components',[]): c.add_row(a['name'],a['kind'],a['source'],a.get('version') or '',a.get('status') or '',a.get('path') or '')
    console.print(c)

@app.command('set')
def set_override(tool_id: str, field: str, value: str):
    """Override name/version/category/tags/hidden/notes/status for a detected tool."""
    allowed={'name','version','category','hidden','notes','tags','status'}
    if field not in allowed: raise typer.BadParameter(f"field must be one of: {', '.join(sorted(allowed))}")
    data=load_overrides(); ov=data.setdefault(tool_id,{})
    if field=='hidden': ov[field]=value.lower() in {'1','true','yes','on'}
    elif field=='category': ov[field]=[x.strip() for x in value.split('>') if x.strip()]
    elif field=='tags': ov[field]=[x.strip() for x in value.split(',') if x.strip()]
    else: ov[field]=value
    save_overrides(data); console.print(f"[green]Saved override[/green] {tool_id}.{field}")

@app.command()
def unset(tool_id: str, field: str):
    """Remove one override and return that field to automatic detection."""
    data=load_overrides()
    if tool_id in data and field in data[tool_id]:
        del data[tool_id][field]
        if not data[tool_id]: del data[tool_id]
        save_overrides(data); console.print('[green]Override removed.[/green]')
    else: console.print('No such override.')

@app.command()
def edit(tool_id: str):
    """Interactively edit a detected tool's user override."""
    _,cur,_=_current(True); t=next((x for x in cur['tools'] if x['id']==tool_id),None)
    if not t: console.print('Tool not found. Use devstatus search <name>.'); raise typer.Exit(1)
    name=Prompt.ask('Name',default=t['name']); version=Prompt.ask('Version',default=t.get('version') or 'unknown')
    category=Prompt.ask('Category (use > between levels)',default=' > '.join(t.get('category',[])))
    tags=Prompt.ask('Tags (comma-separated)',default=', '.join(t.get('tags',[])))
    notes=Prompt.ask('Notes',default=t.get('notes') or '')
    data=load_overrides(); data[t['id']]={'name':name,'version':None if version=='unknown' else version,
        'category':[x.strip() for x in category.split('>') if x.strip()], 'tags':[x.strip() for x in tags.split(',') if x.strip()], 'notes':notes}
    save_overrides(data); console.print('[green]Saved.[/green]')

@app.command()
def hide(tool_id: str):
    """Hide a tool from the normal tree."""
    set_override(tool_id,'hidden','true')

@app.command()
def unhide(tool_id: str):
    """Remove a hidden override."""
    unset(tool_id,'hidden')

@app.command()
def doctor():
    """Check common developer-environment problems without changing the system."""
    _,cur,_=_current(False); issues=diagnose(cur)
    if not issues: console.print('[green]No obvious problems detected.[/green]'); return
    t=Table('Level','Area','Finding')
    for x in issues: t.add_row(x['level'].upper(),x['name'],x['message'])
    console.print(t)

@app.command()
def ports():
    """Show listening TCP/UDP ports and correlate them to detected tools when possible."""
    _,cur,_=_current(False); t=Table('Proto','Address','Port','PID','Process','Likely tool')
    for p in listening_ports(cur): t.add_row(p['protocol'],p['host'],str(p['port']),str(p['pid'] or ''),p['process'] or '',p['tool'] or '')
    console.print(t)

@app.command()
def disk():
    """Show disk usage of common developer stores."""
    for x in disk_usage():
        console.print(f"[bold]{x['name']}[/bold]  {x['size']}  [dim]{x['path']}[/dim]")
        if x.get('details'): console.print(x['details'],markup=False)

@app.command()
def project(path: str=typer.Argument('.',help='Project directory to inspect')):
    """Detect the current project's stack and runtime pins."""
    hits=detect_project(path)
    if not hits: console.print('No recognized project signatures found.'); return
    t=Table('Detected stack','Evidence','Details')
    for x in hits: t.add_row(x['kind'],', '.join(x['files']),json.dumps(x.get('details',{}),ensure_ascii=False) if x.get('details') else '')
    console.print(t)

@app.command('export')
def export_cmd(format: str=typer.Option('json','--format','-f',help='json or yaml'), output: Path|None=typer.Option(None,'--output','-o')):
    """Export the current inventory in machine-readable form."""
    _,cur,_=_current(True); fmt=format.lower()
    if fmt not in {'json','yaml','yml'}: raise typer.BadParameter('format must be json or yaml')
    text=json.dumps(cur,indent=2) if fmt=='json' else yaml.safe_dump(cur,sort_keys=False)
    if output: output.write_text(text+'\n'); console.print(f'Wrote {output}')
    else: console.print(text,markup=False)

@app.command()
def compare(left: Path, right: Path):
    """Compare two exported devstatus JSON/YAML snapshots, such as two machines."""
    def load(p: Path):
        text=p.read_text(); return yaml.safe_load(text) if p.suffix.lower() in {'.yaml','.yml'} else json.loads(text)
    a,b=load(left),load(right); ch=compare_state(a,b); table=Table('Change','Tool','Left','Right')
    for x in ch['tool_added']: table.add_row('+',x['name'],'—',x.get('version') or 'unknown')
    for x in ch['tool_removed']: table.add_row('-',x['name'],x.get('version') or 'unknown','—')
    for x in ch['tool_updated']:
        av=x.get('before'); bv=x.get('after'); table.add_row('~',x['name'],av or 'changed',bv or 'changed')
    console.print(table)

@app.command()
def outdated():
    """Ask supported package managers for available updates without changing the system."""
    from .utils import run, which
    tables=[]
    rc,out,_=run(['apt','list','--upgradable'],timeout=20)
    if rc==0:
        rows=[x for x in out.splitlines()[1:] if x.strip()]
        if rows:
            t=Table('APT upgradable'); [t.add_row(row) for row in rows]; tables.append(t)
    if which('snap'):
        rc,out,_=run(['snap','refresh','--list'],timeout=20)
        if rc==0 and out and 'All snaps up to date' not in out:
            t=Table('Snap updates'); [t.add_row(row) for row in out.splitlines()]; tables.append(t)
    if which('npm'):
        rc,out,_=run(['npm','outdated','-g','--json'],timeout=20)
        if rc in (0,1) and out:
            try:
                data=json.loads(out)
                if data:
                    t=Table('npm package','Current','Wanted','Latest')
                    for name,v in data.items(): t.add_row(name,str(v.get('current','')),str(v.get('wanted','')),str(v.get('latest','')))
                    tables.append(t)
            except Exception: pass
    if which('rustup'):
        rc,out,_=run(['rustup','check'],timeout=20)
        if rc==0 and out:
            pending=[x for x in out.splitlines() if 'Update available' in x or 'update available' in x]
            if pending:
                t=Table('Rustup updates'); [t.add_row(x) for x in pending]; tables.append(t)
    if not tables: console.print('[green]No updates reported by the checked package managers.[/green]')
    for t in tables: console.print(t)

@app.command()
def tui():
    """Open the interactive terminal UI."""
    from .tui import run_tui; run_tui()

@rules_app.command('stats')
def rules_stats():
    """Show built-in/custom classification knowledge-base statistics."""
    rules=catalog(); cats=Counter(' > '.join(r.get('category',[])) for r in rules)
    console.print(f"Built-in rules: [bold]{len(BUILTIN_CATALOG)}[/bold]\nTotal active rules: [bold]{len(rules)}[/bold]\nCustom rules directory: {config_dir()/'rules.d'}")
    t=Table('Top category','Rules')
    for cat,count in cats.most_common(25): t.add_row(cat,str(count))
    console.print(t)

@rules_app.command('path')
def rules_path():
    console.print(str(config_dir()/'rules.d'))

@rules_app.command('init')
def rules_init(filename: str='custom.yaml'):
    """Create a starter custom rule file."""
    p=config_dir()/'rules.d'/filename
    if p.exists(): console.print(f'{p} already exists.'); raise typer.Exit(1)
    p.write_text("""products:\n  - id: my-tool\n    name: My Tool\n    category: [My Domain, My Category]\n    tags: [custom]\n    packages: [my-tool]\n    binaries: [my-tool]\n    version_commands:\n      - [my-tool, --version]\n""")
    console.print(f'Created {p}')

@rules_app.command('validate')
def rules_validate():
    """Validate rule IDs and required fields."""
    seen=set(); errors=[]
    for r in catalog():
        rid=r.get('id')
        if not rid: errors.append('Rule missing id'); continue
        if rid in seen: errors.append(f'Duplicate id: {rid}')
        seen.add(rid)
        if not r.get('name'): errors.append(f'{rid}: missing name')
        if not r.get('category'): errors.append(f'{rid}: missing category')
    if errors:
        for e in errors: console.print(f'[red]ERROR[/red] {e}')
        raise typer.Exit(1)
    console.print(f'[green]Valid.[/green] {len(seen)} active rules.')

@config_app.command('show')
def config_show():
    console.print(json.dumps(load_settings(),indent=2),markup=False)

@config_app.command('set')
def config_set(key: str,value: str):
    """Set a devstatus setting. Booleans accept true/false."""
    settings=load_settings()
    if key not in settings: raise typer.BadParameter(f"Unknown setting. Valid: {', '.join(settings)}")
    old=settings[key]
    if isinstance(old,bool): new=value.lower() in {'true','1','yes','on'}
    elif isinstance(old,int): new=int(value)
    else: new=value
    settings[key]=new; save_settings(settings); console.print(f'[green]Saved[/green] {key}={new}')

if __name__=='__main__': app()
