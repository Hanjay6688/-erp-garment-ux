"""Writer-only exact declaration; expected sources are never regenerated in CI."""
from pathlib import Path
from hashlib import sha256
import ast
import json
import os
import subprocess
from derive import derive

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def literal(path, name):
    nodes = ast.parse(path.read_text()).body
    return next(ast.literal_eval(n.value) for n in nodes if isinstance(n, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == name for t in n.targets))


def bind():
    if os.environ.get('CI'):
        raise ValueError('D1_EXPECTED_SOURCE_CANNOT_BE_REGENERATED_IN_CI')
    cfg = json.loads((HERE / 'CONFIG.json').read_bytes())
    stage = ROOT / 'scripts/cp7_credit_correction_de'
    leaves = literal(stage / 'composition.py', 'SQL') + ('native_delta.py', 'composition.py')
    cfg['runtime_files'] = {p: sha256((stage / p).read_bytes()).hexdigest() for p in leaves}
    cfg['native_case_ids'] = list(literal(stage / 'cases.py', 'IDS'))
    cfg['signed_dependencies'] = json.loads((stage / 'DEPENDENCIES.json').read_bytes())['signed_source_dependencies']
    _, cfg['runner_derivation'] = derive((ROOT / 'scripts/current-vendor-receivable-qualification/probe.py').read_bytes())
    (HERE / 'CONFIG.json').write_text(json.dumps(cfg, indent=2) + '\n')
    paths = subprocess.check_output(['git', '-C', str(ROOT), 'diff', '--name-only', cfg['base_head']], text=True).splitlines()
    allowed = {'src/SalesReturnCorrectionPanel.tsx', 'src/SalesReturnCorrectionPanel.dom.test.tsx',
               'src/salesReturnCorrectionContract.ts', '.github/workflows/cp7-credit-de-native.yml'}
    prefixes = ('scripts/cp7_credit_correction_de/', 'scripts/current-credit-de-native-qualification/')
    assert all(p in allowed or p.startswith(prefixes) for p in paths), 'D1_UNDECLARED_CHANGED_PATH'
    source = dict(contract='cp7.credit-de-native-source.v1',
                  status='PREPARED_NOT_ACTUAL_NATIVE_PASS', allowed_changes=paths,
                  files={p: sha256((ROOT / p).read_bytes()).hexdigest() for p in paths
                         if p != 'scripts/current-credit-de-native-qualification/SOURCE.json'},
                  native_case_ids=cfg['native_case_ids'], actual_Auth_HTTP_cases=0, actual_browser_cases=0,
                  D_complete=False, E_complete=False, production_go=False, independent_acceptance=False)
    (HERE / 'SOURCE.json').write_text(json.dumps(source, indent=2) + '\n')
    return dict(source_files=len(source['files']), runtime_leaves=len(leaves), native_cases=len(cfg['native_case_ids']))


if __name__ == '__main__':
    print(json.dumps(bind()))
