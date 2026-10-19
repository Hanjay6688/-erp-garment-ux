"""Static and pure-gate validation only; no product module import or DB call."""
import ast
from copy import deepcopy
from decimal import Decimal
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import yaml

A = Path(__file__).resolve().parent
R = A.parents[1]

def main():
    m = json.loads((A / 'DERIVED_DETECTOR_PREEXECUTION_MANIFEST.json').read_text())
    for path, expected in m['pinned_product_sources'].items():
        assert hashlib.sha256((R / path).read_bytes()).hexdigest() == expected
    for path, expected in m['audit_tools'].items():
        text = (A / path).read_text()
        assert hashlib.sha256(text.encode()).hexdigest() == expected
        ast.parse(text)
    ddl = gzip.decompress((R / 'supabase/tests/fixtures/erp_enteng_cp45a_catalog_bootstrap.sql.gz').read_bytes()).decode()
    for table, pin in m['table_field_source_pins'].items():
        assert pin['ddl'] in ddl and hashlib.sha256(pin['ddl'].encode()).hexdigest() == pin['ddl_sha256']
        assert ddl.splitlines()[pin['line'] - 1].lower().startswith('create table "erp"."' + table + '"')
    ids = [c['id'] for c in m['cases']]
    assert len(ids) == len(set(ids)) == 9
    assert sum(c['negative_detector_sensitivity_claim'] for c in m['cases']) == 7
    target = {key for c in m['cases'] for phase in c['expected_phases'].values() for key in phase}
    assert len(target) == 10 and len(target - {'run_v268_financial_report_checks:V2620C_PO_HPP_TARGET_STATE_MISMATCH'}) == 9
    assert set(m['predicate_source_pins']) == target
    for pin in m['predicate_source_pins'].values():
        assert hashlib.sha256(pin['predicate_sql'].encode()).hexdigest() == pin['predicate_sha256']
    tree = ast.parse((A / 'detector_derived_controls.py').read_text())
    parent = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'cases')
    returned = next(n for n in parent.body if isinstance(n, ast.Return))
    assert [n.args[0].value for n in returned.value.elts] == ids
    strings = [n.value.lower() for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)]
    assert not any(any(bad in s for bad in ['disable trigger', 'drop trigger', 'create trigger', 'alter function', 'create function', 'set session_replication_role', 'grant ', 'revoke ']) for s in strings)
    for statement in strings:
        if statement.startswith(('update erp.', 'delete from erp.')):
            assert not any(('erp.' + t + ' ') in statement for t in m['protected_fact_tables'])
    # The existing all167/immutable-fact actual metadata gates are reused unchanged.
    base_tree = ast.parse((A / 'detector_mutable_controls.py').read_text())
    functions = {n.name: n for n in base_tree.body if isinstance(n, ast.FunctionDef)}
    count_fn = next(n for n in ast.parse((A / 'detector_case.py').read_text()).body if isinstance(n, ast.FunctionDef) and n.name == 'counts')
    env = {}
    exec(compile(ast.fix_missing_locations(ast.Module(body=[count_fn, functions['baseline'], functions['phase'], functions['restored']], type_ignores=[])), '<actual metadata gates>', 'exec'), env)
    all_names = [r['identity'] for r in json.loads((A / 'DETECTOR_DISPOSITIONS.json').read_text())['rows']]
    zero = dict.fromkeys(all_names, 0)
    rows = lambda values: [dict(function=k.split(':', 1)[0], check_name=k.split(':', 1)[1], issue_count=v) for k, v in values.items()]
    env['fingerprints'] = lambda cur: dict(immutable_facts='constant', guard_definitions='constant')
    env['detector_rows'] = lambda cur: rows(zero)
    observed = {}; assert env['baseline'](None, observed) == zero
    positives = 0
    for case in m['cases']:
        for name, delta in case['expected_phases'].items():
            values = dict(zero); values.update(delta)
            env['detector_rows'] = lambda cur, v=values: rows(v)
            env['phase'](None, observed, name, delta, zero); positives += 1
    negatives = 0
    key = next(iter(target)); one = dict(zero); one[key] = 1
    mutations = [dict(one, **{'EXTRA:IDENTITY': 1}), {k: v for k, v in one.items() if k != next(x for x in zero if x != key)},
                 dict(one, **{key: 2}), dict(one, **{key: -1}), dict(one, **{next(x for x in zero if x != key): 1})]
    for values in mutations:
        env['detector_rows'] = lambda cur, v=values: rows(v)
        try: env['phase'](None, observed, 'NEGATIVE', {key: 1}, zero)
        except AssertionError: negatives += 1
        else: raise AssertionError('INVALID_PHASE_ACCEPTED')
    for bad in [dict(immutable_facts='changed', guard_definitions='constant'), dict(immutable_facts='constant', guard_definitions='changed')]:
        env['detector_rows'] = lambda cur: rows(one)
        env['fingerprints'] = lambda cur, v=bad: v
        try: env['phase'](None, observed, 'NEGATIVE_PROTECTED', {key: 1}, zero)
        except AssertionError: negatives += 1
        else: raise AssertionError('PROTECTED_CHANGE_ACCEPTED')
    env['fingerprints'] = lambda cur: dict(immutable_facts='constant', guard_definitions='constant')
    env['detector_rows'] = lambda cur: rows(zero); env['restored'](None, observed, zero)
    qt = ast.parse((A / 'detector_derived_qualification.py').read_text())
    assign = next(n for n in ast.walk(qt) if isinstance(n, ast.Assign) and isinstance(n.value, ast.IfExp) and isinstance(n.targets[0], ast.Subscript) and isinstance(n.targets[0].slice, ast.Constant) and n.targets[0].slice.value == 'status')
    gate = compile(ast.Expression(assign.value.test), '<actual outer gate>', 'eval')
    report = dict(cp6_restored=True, observed_case_ids=ids, expected_case_ids=ids, counts={'PASS': 9}, phase_manifest_binding=True)
    native = dict(status='PASS', complete_boundary_restored=True, missing=[])
    assert eval(gate, {'report': report, 'n': native}) is True
    changes = [('report', 'phase_manifest_binding', False), ('report', 'error', 'x'), ('report', 'cp6_restored', False), ('report', 'observed_case_ids', ids[:-1]), ('report', 'counts', {'PASS': 8, 'INCOMPLETE': 1}), ('n', 'status', 'INCOMPLETE'), ('n', 'complete_boundary_restored', False), ('n', 'missing', [ids[0]]), ('n', 'error', 'x')]
    for target_name, key, value in changes:
        ctx = dict(report=deepcopy(report), n=deepcopy(native)); ctx[target_name][key] = value
        assert eval(gate, ctx) is False
    old = yaml.safe_load((R / '.github/workflows/audit-sol-r4-mutable-detectors.yml').read_text())
    new = yaml.safe_load((R / '.github/workflows/audit-sol-r4-derived-detectors.yml').read_text())
    expected = deepcopy(old)
    for k in ('name', 'run-name'): expected[k] = new[k]
    expected['on']['push']['paths'] = new['on']['push']['paths']; expected['concurrency']['group'] = new['concurrency']['group']; expected['jobs']['phase']['name'] = new['jobs']['phase']['name']
    for i, step in enumerate(expected['jobs']['phase']['steps']):
        if step.get('run') == "python '../sol/audit/sol_cp17_r4/detector_mutable_qualification.py'":
            step['run'] = "python '../sol/audit/sol_cp17_r4/detector_derived_qualification.py'"; step['name'] = new['jobs']['phase']['steps'][i]['name']
        if step.get('uses', '').startswith('actions/upload-artifact@'): step['with']['name'] = new['jobs']['phase']['steps'][i]['with']['name']
    assert expected == new and new['permissions'] == {'contents': 'read', 'actions': 'read'}
    assert 'for attempt in 1 2;' in next(s['run'] for s in new['jobs']['phase']['steps'] if s.get('name') == 'Start disposable database')
    assert Decimal('120.000001') != Decimal('120.00') and Decimal('.000001') < Decimal('.005')
    assert not subprocess.check_output(['git', 'diff', '--name-only', m['candidate_sha'], '--', 'src', 'supabase', 'scripts', 'package.json', 'package-lock.json', 'index.html', 'vite.config.ts'], cwd=R, text=True)
    result = dict(state='STATIC_AND_PURE_METADATA_ONLY_NO_PRODUCT_CASES_RUN', exact_case_ids=9, new_sensitivity_cases=7, prevention_only_cases=2, new_target_identities=9, declared_existing_collateral=1,
                  actual_phase_positive=positives, actual_phase_negative=negatives, actual_outer_gate_positive=1, actual_outer_gate_negative=len(changes),
                  source_tool_DDL_hashes_verified=True, parsed_workflow_names_entrypoint_artifact_only=True, permissions_setup_budget_unchanged=True,
                  all167_keysets_enforced=True, protected_facts_and_guards_unchanged_enforced=True, product_diff_empty=True, held_probes_resumed=False)
    (A / 'DERIVED_DETECTOR_PREEXECUTION_VALIDATION.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))

if __name__ == '__main__': main()
