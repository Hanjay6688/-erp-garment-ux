"""Independent test of the real, pinned audit-control module, with synthetic case results.
The injected accounting/capacity failures are detector controls, not claims that the ERP makes them.
No database, wall clock, product file or writer expectation is modified.
"""
from copy import deepcopy
from datetime import date
from pathlib import Path
import contextlib, hashlib, importlib.util, io, json, sys

PRODUCT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd().parent / 'auditor'
SOURCE = PRODUCT / 'scripts/cp6_auditor_business_day.py'
spec = importlib.util.spec_from_file_location('candidate_business_day_control', SOURCE)
bd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bd)
D9, D10 = date(2026, 10, 9), date(2026, 10, 10)
ROWS = []

def record(case, ok, witness):
    row = dict(audit_case_id=case, status='PASS' if ok else 'COUNTEREXAMPLE',
               evidence_origin='INDEPENDENT_TOOL_RUNTIME', oracle_origin='ASTRA_CONTRACT',
               fixture_origin='ASTRA_SYNTHETIC_CASE_RESULTS', observations=witness)
    ROWS.append(row)
    print(json.dumps(row, sort_keys=True), flush=True)

def group(row):
    return dict(status=row['status'], cases={'CONTROL': deepcopy(row)}, counts={row['status']: 1},
                missing=[], error=None, database_remaining=0, cleanup_failures=[], complete_boundary_restored=True)

def drive(first, second):
    attempts, kept = [], []
    def run_once():
        attempts.append(len(attempts) + 1)
        return deepcopy(first if len(attempts) == 1 else second)
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        final = bd.with_retry('ASTRA_DATE_CONTROL', run_once, lambda r: r['cases'], lambda r: kept.append(deepcopy(r)))
    return dict(attempts=len(attempts), final=final, kept_first=kept, stdout=output.getvalue())

# Positive date control: a result that was otherwise PASS is correctly made INCOMPLETE.
rolled_pass = dict(status='PASS', observed_total='100', expected_total='100')
bd.guard(rolled_pass, D9, D10, D10)
control = drive(group(rolled_pass), group(dict(status='PASS', observed_total='100', expected_total='100')))
record('ASF-09-DATE-PASS-CONTROL', rolled_pass['status'] == 'INCOMPLETE'
       and control['attempts'] == 2 and control['final']['status'] == 'PASS'
       and control['kept_first'] == [group(rolled_pass)], dict(guarded=rolled_pass, **control))

# A missing cent is date-independent. The three dates do not explain this injected arithmetic failure.
for status, case in [('FAIL', 'ASF-10-DATE-UNRELATED-FAIL'), ('COUNTEREXAMPLE', 'ASF-11-DATE-UNRELATED-COUNTEREXAMPLE')]:
    row = dict(status=status, error='ASTRA_INJECTED_DATE_INDEPENDENT_RECONCILIATION',
               expected_total_cents=10000, observed_total_cents=10001,
               date_dependency=False, oracle='10001 != 10000 on either date')
    bd.guard(row, D9, D10, D10)
    outcome = drive(group(row), group(dict(status='PASS', expected_total_cents=10000, observed_total_cents=10000)))
    record(case, outcome['attempts'] == 1 and outcome['final']['status'] == status,
           dict(guard_preserved_failure=row['status'] == status, retry_allowed=bd.retry_allowed(group(row), {'CONTROL': row}),
                preserved_in_nested_evidence=bool(outcome['kept_first']), **outcome))

# Positive blocking controls: no date change, boundary failure, malformed result, absent case, failed cleanup.
controls = []
for kind in ('no_rollover', 'boundary', 'malformed', 'missing', 'cleanup'):
    row = dict(status='FAIL', error='ASTRA_INJECTED_ACCOUNTING_MISMATCH')
    bd.guard(row, D9, D9, D9 if kind == 'no_rollover' else D10)
    first = group(row)
    if kind == 'boundary': first['cases']['CONTROL']['harness_check_failed'] = True
    if kind == 'malformed': first['cases']['CONTROL']['error'] = 'AUDITOR_CASE_RESULT_NOT_A_DICT'
    if kind == 'missing': first['missing'] = ['UNRUN']
    if kind == 'cleanup': first['cleanup_failures'] = ['NOT_REMOVED']
    out = drive(first, group(dict(status='PASS')))
    controls.append(dict(kind=kind, **out))
record('ASF-12-DATE-BLOCKING-CONTROLS', all(x['attempts'] == 1 and x['final']['status'] == 'FAIL' for x in controls), controls)

report = dict(candidate_sha='d0b9e9c2e41a9f0f3a138346887434fd7d3c14f0',
              module_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(), cases=ROWS,
              counts={s: sum(r['status'] == s for r in ROWS) for s in ('PASS', 'COUNTEREXAMPLE')},
              scope='Synthetic failure injection into unchanged audit-control module; no ERP business bug claimed',
              production_go=False)
report['status'] = 'COUNTEREXAMPLE' if report['counts']['COUNTEREXAMPLE'] else 'PASS'
dest = Path(__file__).resolve().parent / 'evidence/ASF_BUSINESS_DAY.json'
dest.parent.mkdir(exist_ok=True)
dest.write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({k: report[k] for k in ('status', 'counts', 'module_sha256')}), flush=True)
sys.exit(1 if report['status'] != 'PASS' else 0)
