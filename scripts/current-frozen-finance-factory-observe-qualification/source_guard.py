"""Keep every business oracle and add only a bounded read-only terminal observation."""
from pathlib import Path
from hashlib import sha256
import ast,importlib.util,json
HERE=Path(__file__).resolve().parent;REPO=HERE.parents[1]
IMPORT_ADDITION="_diag_spec=importlib.util.spec_from_file_location('factory_terminal_diagnostics',Path(__file__).with_name('diagnostics.py'))\ndiagnostics=importlib.util.module_from_spec(_diag_spec);_diag_spec.loader.exec_module(diagnostics)\n"
CALL_ADDITION="            report['terminal_diagnostics']=diagnostics.capture(admin_url,[finance_key,bounded_key],capture)\n"
def source_binding():
    old=REPO/'scripts/current-frozen-finance-factory-date2-qualification'
    spec=importlib.util.spec_from_file_location('retained_factory_date2_guard',old/'source_guard.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    retained=m.source_binding();cfg=json.loads((HERE/'CONFIG.json').read_bytes())
    runner=(HERE/'runner.py').read_text()
    assert runner.count(IMPORT_ADDITION)==runner.count(CALL_ADDITION)==1
    assert "            report['schedules_removed_and_unrelated_jobs_unchanged']=True\n"+CALL_ADDITION in runner
    assert runner.replace(IMPORT_ADDITION,'').replace(CALL_ADDITION,'')==(old/'runner.py').read_text()
    for name in('fixture.py','probe.py'):assert(HERE/name).read_bytes()==(old/name).read_bytes(),name
    assert sha256((HERE/'diagnostics.py').read_bytes()).hexdigest()==cfg['diagnostics_sha256']
    assert sum(isinstance(n,ast.Assert)for n in ast.walk(ast.parse(runner)))==retained['retained_assertions']['runner.py']
    return dict(retained=retained,only_added_read_only_terminal_observation=True,
        full_job_and_capture_rows_preserved=True,unchanged65_business_assertions=True,
        no_product_SQL_or_guard_change=True,runtime_qualified=False,production_go=False)
