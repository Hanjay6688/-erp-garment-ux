"""Reversible private source adapters; financial callback assertions are retained."""
from hashlib import sha256
from pathlib import Path
import ast
import importlib.util

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
NS = 'scripts/current-sku-all-member-native23-qualification'
OLD_NS = 'scripts/current-sku-combined-fixture-followup'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


legacy = load('sku23_retained_seventeen_derivations', ROOT / OLD_NS / 'derive.py')
SOURCES = dict(legacy.SOURCES)
SOURCES.update(
    native_admission=('scripts/current-sku-pair-native-adapter/admission.py', 'ba3406ae26b660d350136c3d75d305abfeedcb9b69b46c30a758b94d4d7c35b7'),
    cost_guard=('scripts/current-sku-group-cost-qualification/source_guard.py', '147f8cae3795a171615bb9c536c4354dac655d235acff50bcd6595c37f51a883'),
    browser_guard=('scripts/current-sku-pair-browser-qualification/source_guard.py', '9ed13bb9db34d55451acf7602fa0fbd72751d6981d7e064cc5d4e8a753a01832'),
)
IMPORT = "\n_sku23_path = Path(__file__).resolve().parents[2] / '" + NS + "/transition.py'\n_sku23_spec = importlib.util.spec_from_file_location('sku23_explicit_source_transition', _sku23_path)\n_sku23 = importlib.util.module_from_spec(_sku23_spec)\n_sku23_spec.loader.exec_module(_sku23)\n"
# Source-predicate changes below are deliberately listed apart from case/oracle
# assertions. No retained manifest, product.sources(), or catalog is replaced.
EXTRA = {
 'cost_cases': (
  ("n=load('sku_group_cost_Native_fixture',", "_sku23=load('sku23_cost_transition',HERE.parents[1]/'" + NS + "/transition.py')\nn=load('sku_group_cost_Native_fixture',"),
  ("guard=load('sku_group_cost_source_guard',HERE/'source_guard.py')", "guard=load('sku_group_cost_source_guard',HERE.parents[1]/'" + NS + "/cost_guard.py')"),
  ("assert backend_commit=='21c69cf25defcee854beb08e998062d7e883d968'", "assert backend_commit==_sku23.PRODUCT_HEAD"),
  ('n.at(fixture,20)', '_sku23.bc_at(fixture,20)'),
  ('n.at(fixture,30)', '_sku23.bc_at(fixture,30)'),
  ('n.at(fixture,40)', '_sku23.bc_at(fixture,40)'),
  ("    # The actual immutable member order proves the unblocked second part is\n    # attempted first, then the first part's active usage refuses the command.",
   "    # The immutable reverse order still starts with part2. The reviewed\n    # all-member preflight must now refuse before either Native child writes."),
  ("coverage='NATIVE_GROUP_INVERSE_WITH_SECOND_PART_DML_BEFORE_FIRST_PART_COST_REFUSAL'", "coverage='NATIVE_GROUP_ALL_MEMBER_PREFLIGHT_BEFORE_ANY_NATIVE_INVERSE'"),
  ("Native_inverse_order=[row[0]for row in order],active_cost_part=1,unblocked_inverse_attempt_part=2,\n      earlier_second_part_DML_path_inferred_from_exact_Native_source_order_and_later_first_part_error=True,",
   "Native_inverse_order=[row[0]for row in order],active_cost_part=1,unblocked_inverse_attempt_part=None,\n      retained_first_inverse_member=2,all_member_preflight_before_any_child_write=True,"),
 ),
 'runner': (
  ("ROOT / '" + OLD_NS + "/cost_cases.py'", "ROOT / '" + NS + "/cost_cases.py'"),
  ("gate = load('sku_combined_group_gate', HERE / 'gate.py')", "gate = load('sku_combined_group_gate', HERE / 'gate.py')\n_sku23 = load('sku23_runner_transition', ROOT / '" + NS + "/transition.py')"),
  ("original_report_sha256=retained['original_sha256'], backend_commit=gate.BASE", "original_report_sha256=_sku23.fresh_native7_sha(first), backend_commit=_sku23.PRODUCT_HEAD"),
  ("HERE / 'admission.py'", "ROOT / '" + NS + "/admission.py'"),
 ),
 'probe': (
  ("ROOT / '" + OLD_NS + "/runner.py'", "ROOT / '" + NS + "/runner.py'"),
  ("ROOT / '" + OLD_NS + "/admission.py'", "ROOT / '" + NS + "/admission.py'"),
  ("engine.LABEL = 'CP7_SKU_COMBINED_FOLLOWUP23'", "engine.LABEL = 'CP7_SKU_ALL_MEMBER_NATIVE23'"),
 ),
 'historical_admission': (
  ("gate = load('sku_combined_retained_gate', HERE / 'gate.py')", "gate = load('sku_combined_retained_gate', HERE / 'gate.py')\n" + IMPORT),
  ("product.sources(),\n                         load('sku_combined_ids'", "_sku23.historical_sources(product),\n                         load('sku_combined_ids'"),
  ("assert len(raw) == expected['bytes'] and sha256(raw).hexdigest() == expected['sha256'], path", "assert _sku23.verify_pin(ROOT, path, expected), path"),
  ("assert (ROOT / path).read_bytes() == subprocess.check_output(['git', '-C', str(ROOT), 'show', gate.BASE + ':' + path]), path", "assert _sku23.historical_path(ROOT, path, gate.BASE), path"),
  ("text, scope = historical_native_admission(original.read_bytes())", "text, scope = _sku23.native_admission(original.read_bytes())"),
 ),
 'native_admission': (
  ("def admitted(repo, here, product, derivation):", IMPORT + "\ndef admitted(repo, here, product, derivation):"),
  ("assert sha256((repo / path).read_bytes()).hexdigest() == digest, path", "assert _sku23.verify_pin(repo, path, digest), path"),
  ("changed = git('diff', '--name-only', cfg['base_head'], 'HEAD').decode().splitlines()", "changed = git('diff', '--name-only', cfg['base_head'], '21c69cf25defcee854beb08e998062d7e883d968').decode().splitlines()"),
  ("assert current['files'] == cfg['runtime_files']", "assert current['files'] == _sku23.runtime_files(cfg['runtime_files'])"),
 ),
 'cost_guard': (
  ('import json', 'import json\nimport importlib.util' + IMPORT),
  ("assert sha256((root/path).read_bytes()).hexdigest()==expected,('SKU_COST_SOURCE_CHANGED',path)", "assert _sku23.verify_pin(root,path,expected),('SKU_COST_SOURCE_CHANGED',path)"),
  ("actual_Native_execution=False,actual_Auth_browser=False", "current_source_transition=_sku23.source_receipt(),actual_Native_execution=False,actual_Auth_browser=False"),
 ),
 'browser_guard': (
  ('import json', 'import json\nimport importlib.util' + IMPORT),
  ("assert sha256((root/path).read_bytes()).hexdigest()==digest,('SKU29_BROWSER_SOURCE_CHANGED',path)", "assert _sku23.verify_pin(root,path,digest),('SKU29_BROWSER_SOURCE_CHANGED',path)"),
  ('actual_runtime_execution=False,production_go=False', 'current_source_transition=_sku23.source_receipt(),actual_runtime_execution=False,production_go=False'),
 ),
}


def derive(key, raw=None):
    path, digest = SOURCES[key]
    raw = (ROOT / path).read_bytes() if raw is None else raw
    if sha256(raw).hexdigest() != digest:
        raise ValueError('SKU23_FROZEN_SOURCE_CHANGED:' + path)
    base, prior = legacy.derive(key, raw) if key in legacy.SOURCES else (raw.decode(), None)
    text = base
    for before, after in EXTRA.get(key, ()):
        if text.count(before) != 1 or after in text:
            raise ValueError('SKU23_EXACT_ONE_ADAPTER_ANCHOR:' + key + ':' + before)
        text = text.replace(before, after, 1)
    inverse = text
    for before, after in reversed(EXTRA.get(key, ())):
        assert inverse.count(after) == 1
        inverse = inverse.replace(after, before, 1)
    assert inverse == base, 'SKU23_PRIVATE_DERIVATION_NOT_REVERSIBLE'
    if path.endswith('.py'):
        a, b = ast.parse(raw), ast.parse(text)
        original = sum(isinstance(n, ast.Assert) for n in ast.walk(a))
        derived = sum(isinstance(n, ast.Assert) for n in ast.walk(b))
        assert original == derived, 'SKU23_RETAINED_ASSERTION_COUNT_CHANGED'
        compile(text, path, 'exec')
    else:
        original = derived = 0
    return text, dict(source=path, original_sha256=digest, derived_sha256=sha256(text.encode()).hexdigest(),
        retained17_derivation=prior, new_counted_changes=len(EXTRA.get(key, ())),
        byte_exact_reversible_to_retained_derivation=True, original_asserts=original, derived_asserts=derived,
        assertions_removed=0, original_files_modified=False)


def inventory():
    result = {key: derive(key)[1] for key in SOURCES}
    assert sum(result[key]['original_asserts'] for key in legacy.SOURCES) == 134
    assert sum(result[key]['derived_asserts'] for key in legacy.SOURCES) == 134
    return result


def execute(key, namespace):
    text, proof = derive(key)
    namespace['__file__'] = str(ROOT / SOURCES[key][0])
    exec(compile(text, namespace['__file__'], 'exec'), namespace)
    namespace['SKU23_PRIVATE_DERIVATION'] = proof
