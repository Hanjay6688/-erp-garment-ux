"""Writer-only source binder. Qualification never regenerates its expected pins."""
from pathlib import Path
from hashlib import sha256
import ast
import json
import os
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def literal_assignment(path, name):
    tree = ast.parse(path.read_text())
    return next(ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == name for t in n.targets))


def bind():
    if os.environ.get('CI'):
        raise ValueError('SKU_EXPECTED_SOURCE_CANNOT_BE_REGENERATED_IN_CI')
    cfg = json.loads((HERE / 'CONFIG.json').read_bytes())
    tree = ast.parse((ROOT / 'scripts/cp7_sku_pair_conversion/composition.py').read_text())
    function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'sources')
    tuples = [g.iter for n in ast.walk(function) if isinstance(n, ast.DictComp)
              for g in n.generators if isinstance(g.target, ast.Name) and g.target.id == 'f']
    assert len(tuples) == 1
    leaves = ast.literal_eval(tuples[0])
    cfg['runtime_files'] = {'scripts/cp7_sku_pair_conversion/' + p:
                           sha256((ROOT / 'scripts/cp7_sku_pair_conversion' / p).read_bytes()).hexdigest() for p in leaves}
    cfg['native_case_ids'] = list(literal_assignment(ROOT / 'scripts/current-sku-pair-conversion-qualification/cases.py', 'IDS'))
    cfg['targeted_client_tests'] = 72
    cfg['client_proof_scope'] = 'JSDOM_AND_PARSER_NOT_AUTH_BROWSER'
    (HERE / 'CONFIG.json').write_text(json.dumps(cfg, indent=2) + '\n')
    paths = subprocess.check_output(['git', '-C', str(ROOT), 'diff', '--name-only', cfg['base_head']], text=True).splitlines()
    exact = {
        'src/ConnectedProductConversionPage.tsx', 'src/productConversion.ts', 'src/ConnectedSkuMasterPage.tsx', 'src/skuMaster.ts',
        'src/productionRecovery.ts', 'src/productionRecovery.test.ts', 'src/skuPairConversion.test.ts', 'src/ConnectedSkuConversion.dom.test.tsx',
        'src/NativeStagedAiPanel.tsx', 'src/NativeStagedAiPanel.fallback.dom.test.tsx',
        'tests/cp7/families/sku-pair-conversion.test.ts', '.github/workflows/cp7-sku-pair-native.yml'}
    prefixes = ('scripts/cp7_sku_pair_conversion/', 'scripts/current-sku-pair-conversion-qualification/',
                'scripts/current-sku-pair-native-adapter/', 'docs/cp7/d17-14/ow15/ai-fallback-local-20261029')
    assert all(p in exact or p.startswith(prefixes) for p in paths), 'UNDECLARED_CHILD_PATH'
    source = dict(contract='cp7.sku-pair-native-declared-child.v1',
                  status='EXACT_SOURCE_PREPARED_NOT_ACTUAL_NATIVE_PASS', browser_case_ids=[], Native_case_ids=cfg['native_case_ids'],
                  allowed_changes=paths,
                  files={p: sha256((ROOT / p).read_bytes()).hexdigest() for p in paths
                         if p != 'scripts/current-sku-pair-native-adapter/SOURCE.json'},
                  product_scope=dict(SKU='PAIR_AND_MANUAL_FIFO_CONVERSION',
                                     AI='ONE_DECLARED_RESPONSE_CONTEXT_HARDENING_LEAF_NOT_BROWSER_CREDIT'),
                  old_frozen_sources_rewritten=False, production_go=False, independent_acceptance=False)
    (HERE / 'SOURCE.json').write_text(json.dumps(source, indent=2) + '\n')
    return dict(files=len(source['files']), runtime_leaves=len(leaves), native_cases=len(cfg['native_case_ids']), browser_cases=0)


if __name__ == '__main__':
    print(json.dumps(bind()))
