import json
from pathlib import Path
from devstatus.project.detector import detect


def test_project_detection(tmp_path: Path):
    (tmp_path/'pyproject.toml').write_text('[project]\nrequires-python=">=3.11"\n')
    (tmp_path/'package.json').write_text(json.dumps({'engines':{'node':'>=20'}}))
    (tmp_path/'.nvmrc').write_text('22\n')
    kinds={x['kind'] for x in detect(str(tmp_path))}
    assert 'Python' in kinds
    assert 'Node.js' in kinds
    assert 'Python requirement' in kinds
    assert 'Node engines' in kinds
    assert 'Node pin' in kinds
