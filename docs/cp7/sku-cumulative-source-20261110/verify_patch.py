"""Test the staged Mandor input against the real retained SKU admission."""
import importlib.util
import json
from pathlib import Path
import sys
from unittest.mock import patch

checkout, staged = (Path(arg).resolve() for arg in sys.argv[1:])
scripts = checkout / 'scripts'
area = scripts / 'current-sku-automatic-composite-preparation'
money_area = scripts / 'current-sku-money-composite-preparation'

def load(path):
    spec = importlib.util.spec_from_file_location('review_' + path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def refuses(call, reason):
    try:
        call()
    except ValueError as error:
        assert reason in str(error), str(error)
    else:
        raise AssertionError('Accepted input that should fail: ' + reason)

binding = load(area / 'money_binding.py')
parent = binding.cumulative_parent
old = load(money_area / 'admission.py')
old_code = old.admitted.__code__
raw = staged.read_bytes()
root = parent.verify(raw)
money_raw = (money_area / 'SKU_MONEY_PREPARED_SOURCE_INTAKE.json').read_bytes()
money = json.loads(money_raw)
assert parent.pin(money_raw) == dict(bytes=368964, sha256='55c13119aef4a9307b1638864b8eec3199e574a8876c26aa3254aa0920b1a8cb')
money_source = money['complete_candidate_source_admission']
case_ids = money_source['case_ids']
bindings = dict(PARENT_HEAD=root['head'], PARENT_TREE=root['tree'], PARENT_ROOT_PIN=parent.pin(raw),
                PARENT_SOURCE_PIN=parent.pin(parent.canonical(root['qualified_current_Mandor_sources'])),
                PARENT_MODULE_PIN=root['assembly_source'], SKU_HEAD=money['declared_candidate_head'],
                SKU_TREE=money['candidate_tree'], SKU_SOURCE_PREFLIGHT_PIN=parent.pin(money_raw),
                SKU_SOURCE_PIN=parent.pin(parent.canonical(money_source['current_installation'])),
                RUNTIME_ENTRY=binding.ENTRY)

def gates(candidate=raw, *, cumulative=True, **overrides):
    return binding._private_admission(old, bindings | overrides, candidate, cumulative_source_only=cumulative)

receipt = gates().admitted(raw, money_raw, case_ids)
assert receipt['actual_composite_cases'] == 0 and receipt['independent_acceptance'] is False
assert receipt['parent_root'] == parent.pin(raw)
assert root['cumulative_evidence']['original_run']['conclusion'] == 'failure'
assert root['cumulative_evidence']['paired_browser_run']['conclusion'] == 'success'
assert len(root['cumulative_evidence']['cases']) == 17
assert all(key not in root for key in ('run_id', 'job_id', 'artifact_id'))
assert all(root[k] is False for k in ('runtime_admission', 'production_go', 'independent_acceptance'))
refuses(lambda: gates(cumulative=False).admitted(raw, money_raw, case_ids), 'REQUIRED:status')
# Exercise the unchanged legacy path with a control root using its original schema.
legacy = {name: root[name] for name in parent.expected_parent(root) if name not in ('runtime_admission',)}
legacy.update(status='ROOT_VERIFIED_CURRENT_MANDOR17_ALL5', prior_runs_aggregated=False,
              qualified_current_Mandor_sources=root['qualified_current_Mandor_sources'])
legacy_raw = parent.canonical(legacy)
assert gates(cumulative=False, PARENT_ROOT_PIN=parent.pin(legacy_raw)).admitted(
    legacy_raw, money_raw, case_ids)['actual_composite_cases'] == 0

for key, value in (('prior_runs_aggregated', False), ('actual_business_cases', 16),
                   ('production_go', True), ('runtime_admission', True),
                   ('independent_acceptance', True), ('run_id', 42752853455),
                   ('head', root['cumulative_evidence']['tested_browser_app']['head'])):
    mutated = parent.canonical(root | {key: value})
    refuses(lambda: gates(mutated, PARENT_ROOT_PIN=parent.pin(mutated)), 'SKU_EXACT_CUMULATIVE_MANDOR_ROOT')
tampered = json.loads(raw)
tampered['cumulative_evidence']['original_run']['conclusion'] = 'success'
forged = parent.canonical(tampered)
refuses(lambda: gates(forged, PARENT_ROOT_PIN=parent.pin(forged)), 'SKU_EXACT_CUMULATIVE_MANDOR_REVIEW')
forged_money = parent.canonical(money | {'network_database_guard': money['network_database_guard'] | {'attempts': ['connect']}})
refuses(lambda: gates(SKU_SOURCE_PREFLIGHT_PIN=parent.pin(forged_money)).admitted(raw, forged_money, case_ids),
        'SKU_MONEY_COMPOSITE_EXACT_SOURCE_DATABASE_NETWORK_FENCE_REQUIRED')
refuses(lambda: gates(PARENT_SOURCE_PIN={'bytes': 1, 'sha256': '0' * 64}).admitted(raw, money_raw, case_ids),
        'SKU_MONEY_COMPOSITE_COMPLETE_PARENT_OR_CANDIDATE_SOURCE_GRAPH_REQUIRED')
refuses(lambda: gates().admitted(raw, money_raw, case_ids[:-1]), 'SKU_MONEY_COMPOSITE_EXACT_NINETEEN_CASES_REQUIRED')
with patch.object(old, '__file__', str(area / 'cumulative_parent.py')):
    refuses(gates, 'SKU_AUTOMATIC_EXACT_RETAINED_ADMISSION_FOR_CUMULATIVE_SOURCE_REQUIRED')
assert old.admitted.__code__ is old_code
assert all(getattr(old, k) is None for k in old.GATES)
assert all(getattr(binding.admission, k) is None for k in binding.admission.GATES)
refuses(lambda: binding.bind(raw, money_raw, b''), 'FULL_NATIVE_LIFECYCLE_PENDING')
print('PASS: actual Mandor 15+2 and exact money intake accepted by private source gate')
print('PASS: legacy contract, 12 tamper controls, and closed runtime verified')
