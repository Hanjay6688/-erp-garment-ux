"""Static/source and actual outer-result metadata validation; no product run."""
import ast
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import yaml

A = Path(__file__).resolve().parent
R = A.parents[1]

def main():
    m = json.loads((A / 'PAYROLL_DETECTOR_DISPUTE_PREEXECUTION_MANIFEST.json').read_text())
    for p, h in m['pinned_product_sources'].items(): assert hashlib.sha256((R / p).read_bytes()).hexdigest() == h
    for p, h in m['audit_tools'].items():
        assert hashlib.sha256((A / p).read_bytes()).hexdigest() == h
        ast.parse((A / p).read_text())
    ids = [r['id'] for r in m['cases']]
    assert ids == ['SOL_R4_INV_D02_VALID_FG_REPAIR_NOTA_ZERO_ALARM', 'SOL_R4_D01_OPENING_DERIVED_STATUS']
    assert m['cases'][0]['expected_phases']['AFTER_VALID_NOTA_POST'] == {'all167': 0}
    assert len(m['cases'][1]['expected_phases']['OPENING_DERIVED_STATUS_ONLY']) == 2
    src = (A / 'payroll_detector_dispute_cases.py').read_text()
    tree = ast.parse(src)
    assert 'contractor_id::text,w.contractor_id::text' in src and "row[6] == row[7] == header[1]" in src
    assert "o.update(status='COUNTEREXAMPLE', false_alarm_reproduced=True, contract_satisfied=False" in src
    assert "o.setdefault('status', 'PASS')" in src
    strings = [n.value.lower() for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)]
    assert [s for s in strings if s.lstrip().startswith(('update erp.', 'delete from erp.', 'insert into erp.'))] == ["update erp.opening_subledger_balances set status='settled' where id=%s returning status"]
    assert not any(any(t in s for t in ['disable trigger', 'alter function', 'set session_replication_role']) for s in strings)
    qt = ast.parse((A / 'payroll_detector_dispute_qualification.py').read_text())
    gate_node = next(n for n in ast.walk(qt) if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'evidence_complete' for t in n.targets))
    status_node = next(n for n in ast.walk(qt) if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Subscript) and isinstance(n.targets[0].slice, ast.Constant) and n.targets[0].slice.value == 'status')
    gate = compile(ast.Expression(gate_node.value), '<actual evidence gate>', 'eval')
    status = compile(ast.Expression(status_node.value), '<actual status>', 'eval')
    report = dict(cp6_restored=True, expected_case_ids=ids, observed_case_ids=ids, counts={'PASS': 1, 'COUNTEREXAMPLE': 1}, opening_phase_manifest_binding=True)
    native = dict(status='COUNTEREXAMPLE', complete_boundary_restored=True, missing=[])
    def evaluate(r, n):
        complete = eval(gate, {'report': r, 'n': n})
        return complete, eval(status, {'report': r, 'evidence_complete': complete})
    assert evaluate(report, native) == (True, 'COUNTEREXAMPLE')
    healthy = deepcopy(report); healthy['counts'] = {'PASS': 2}; nhealthy = deepcopy(native); nhealthy['status'] = 'PASS'
    assert evaluate(healthy, nhealthy) == (True, 'PASS')
    changes = [('report', 'error', 'x'), ('report', 'cp6_restored', False), ('report', 'observed_case_ids', ids[:-1]),
               ('report', 'opening_phase_manifest_binding', False), ('report', 'counts', {'PASS': 1, 'INCOMPLETE': 1}),
               ('n', 'status', 'INCOMPLETE'), ('n', 'complete_boundary_restored', False), ('n', 'missing', [ids[1]]), ('n', 'error', 'x')]
    for who, key, value in changes:
        ctx = dict(report=deepcopy(report), n=deepcopy(native)); ctx[who][key] = value
        assert evaluate(ctx['report'], ctx['n']) == (False, 'INCOMPLETE')
    old = yaml.safe_load((R / '.github/workflows/audit-sol-r4-derived-detectors.yml').read_text())
    new = yaml.safe_load((R / '.github/workflows/audit-sol-r4-payroll-detector-dispute.yml').read_text())
    expected = deepcopy(old)
    for k in ('name', 'run-name'): expected[k] = new[k]
    expected['on']['push']['paths'] = new['on']['push']['paths']; expected['concurrency']['group'] = new['concurrency']['group']; expected['jobs']['phase']['name'] = new['jobs']['phase']['name']
    for i, step in enumerate(expected['jobs']['phase']['steps']):
        if step.get('run') == "python '../sol/audit/sol_cp17_r4/detector_derived_qualification.py'":
            step['run'] = "python '../sol/audit/sol_cp17_r4/payroll_detector_dispute_qualification.py'"; step['name'] = new['jobs']['phase']['steps'][i]['name']
        if step.get('uses', '').startswith('actions/upload-artifact@'): step['with']['name'] = new['jobs']['phase']['steps'][i]['with']['name']
    assert expected == new and new['permissions'] == {'contents': 'read', 'actions': 'read'}
    assert not subprocess.check_output(['git', 'diff', '--name-only', m['candidate_sha'], '--', 'src', 'supabase', 'scripts', 'package.json', 'package-lock.json', 'index.html', 'vite.config.ts'], cwd=R, text=True)
    result = dict(state='STATIC_AND_PURE_METADATA_ONLY_NO_PRODUCT_RUN', case_ids=2, new_business_contract_ids=1, isolated_existing_opening_id=1,
                  actual_counterexample_gate_positive=1, actual_healthy_gate_positive=1, actual_outer_gate_negative=len(changes),
                  healthy_expected_zero_not_lowered=True, observed_contrary_never_PASS=True, source_and_tool_hashes_verified=True,
                  readonly_lineage_query_binds_source_header_contractor_component_qty_rate_amount=True,
                  parsed_workflow_names_entrypoint_artifact_only=True, setup_permissions_budget_unchanged=True, product_diff_empty=True)
    (A / 'PAYROLL_DETECTOR_DISPUTE_PREEXECUTION_VALIDATION.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))

if __name__ == '__main__': main()
