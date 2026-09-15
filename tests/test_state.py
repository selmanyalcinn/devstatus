from devstatus.state.diff import compare


def snap(version='1.0',status='running'):
    return {'artifacts':[], 'tools':[{'id':'foo','name':'Foo','version':version,'category':['Dev'],'status':status,'sources':['apt']}]}


def test_tool_version_diff():
    d=compare(snap('1.0'),snap('2.0'))
    assert d['tool_updated'][0]['changes']['version']==('1.0','2.0')


def test_tool_add_remove():
    a={'artifacts':[],'tools':[]}; b=snap()
    assert compare(a,b)['tool_added'][0]['id']=='foo'
    assert compare(b,a)['tool_removed'][0]['id']=='foo'
