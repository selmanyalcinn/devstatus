from __future__ import annotations
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Tree, Static
from .inventory import build

class DevStatusApp(App):
    TITLE='devstatus'
    SUB_TITLE='Developer machine inventory'
    BINDINGS=[('q','quit','Quit'),('r','refresh_scan','Refresh')]

    def __init__(self):
        super().__init__(); self.snapshot=None

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static('Scanning…',id='summary')
        yield Tree('Developer environment',id='inventory')
        yield Static('Select a tool to inspect it.',id='details')
        yield Footer()

    def on_mount(self) -> None:
        self._refresh()

    def _refresh(self):
        self.snapshot=build(False)
        s=self.snapshot['system']; self.query_one('#summary',Static).update(f"{s['os']} · {s['hostname']} · {s['kernel']} · {len(self.snapshot['tools'])} tools")
        tree=self.query_one('#inventory',Tree); tree.root.remove_children()
        nodes={}
        for tool in self.snapshot['tools']:
            cur=tree.root; acc=[]
            for part in tool.get('category') or ['Other']:
                acc.append(part); key=tuple(acc)
                if key not in nodes: nodes[key]=cur.add(part,expand=True)
                cur=nodes[key]
            ver=tool.get('version') or 'unknown'; status=f" [{tool['status']}]" if tool.get('status') else ''
            cur.add_leaf(f"{tool['name']} {ver}{status}",data=tool)
        tree.root.expand()

    def action_refresh_scan(self) -> None:
        self._refresh()

    def on_tree_node_selected(self,event: Tree.NodeSelected) -> None:
        t=event.node.data
        if not isinstance(t,dict): return
        lines=[f"{t['name']} ({t['id']})",f"Version: {t.get('version') or 'unknown'}",f"Category: {' > '.join(t.get('category',[]))}",
               f"Sources: {', '.join(t.get('sources',[]))}",f"Tags: {', '.join(t.get('tags',[]))}"]
        if t.get('version_source'): lines.append(f"Version source: {t['version_source']}")
        if t.get('notes'): lines.append(f"Notes: {t['notes']}")
        self.query_one('#details',Static).update('\n'.join(lines))

def run_tui():
    DevStatusApp().run()
