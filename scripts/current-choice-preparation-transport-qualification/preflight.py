"""Local source-only checks, explicitly neither Auth nor database execution."""
from pathlib import Path
from hashlib import sha256
import ast
import json
import subprocess
import yaml

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]


def check():
    cfg = json.loads((HERE / 'CONFIG.json').read_bytes())
    ids = cfg['case_ids']
    assert len(ids) == len(set(ids)) == cfg['count'] == 6
    assert ids == cfg['groups']['choice_http'] + cfg['groups']['choice_races']
    common = ast.parse((HERE / 'common.py').read_text())
    node = next(n for n in common.body if isinstance(n, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == 'IDS' for t in n.targets))
    declared = {kw.arg: ast.literal_eval(kw.value) for kw in node.value.keywords}
    assert cfg['groups'] == {'choice_' + kind: values for kind, values in declared.items()}
    for path in HERE.glob('*.py'):
        ast.parse(path.read_text(), filename=str(path))
    workflow = REPO / '.github/workflows/cp7-d17-18-choice-preparation-transport.yml'
    data = yaml.safe_load(workflow.read_text())
    assert data['on']['push']['branches'] == ['astra-a/d17-18-choice-preparation-transport-20261026']
    assert data['jobs']['p21']['timeout-minutes'] == 120
    shell_steps = 0
    for step in data['jobs']['p21']['steps']:
        if 'run' in step:
            subprocess.run(['bash', '-n'], input=step['run'], text=True, check=True)
            shell_steps += 1
    run_steps = [s['run'] for s in data['jobs']['p21']['steps'] if 'run' in s]
    assert sum("current-choice-preparation-transport-qualification/probe.py'" in s for s in run_steps) == 1
    assert not any("current-choice-preparation-native-qualification/probe.py'" in s for s in run_steps)
    # Evidence validator is byte-for-byte the independently prepared UI gate.
    assert sha256((HERE / 'evidence.py').read_bytes()).hexdigest() == '8cace2ba4dfe2ee8d84299affa38e3ce19e1fa14ed22ee6c61bf4c934f6e444a'
    return dict(status='SOURCE_PREFLIGHT_PASS', case_ids=ids, Python_AST_files=len(list(HERE.glob('*.py'))),
        shell_steps_parsed=shell_steps, actual_Auth_HTTP_credit=False, actual_race_credit=False,
        bound=(HERE / 'SOURCE.json').exists(), production_go=False)


if __name__ == '__main__':
    print(json.dumps(check(), indent=2))
