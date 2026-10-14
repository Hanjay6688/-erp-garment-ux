"""First CP7 FULL executions of inherited browser/Auth/race coverage.

The verified FULL parent is cloned by the candidate mode runner. Tests and
expectations are unchanged. No automatic business-day retry is allowed.
"""
from pathlib import Path
import importlib, json, sys, traceback
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import full_stack
import cp6_auditor_modes as modes
import cp6_auditor_runner as native
from cp7_catalog_state import exact_public_catalog

TAG = sys.argv[1]
assert TAG in ('bb','bc','bd','bd-revision','bd-range','be','be-revision','bf')
MODULE = 'cp6_bf_combined_modes' if TAG == 'bf' else 'cp6_' + TAG.replace('-','_') + '_modes'
native.r1.OUT = full_stack.OUT

def run():
    module = importlib.import_module(MODULE)
    label = 'ASTRA_CP17_COVERAGE_MODES_' + TAG.upper().replace('-','_')
    report = dict(label=label, status='INCOMPLETE', production_go=False, groups={},
                  evidence_origin='ASTRA_FIRST_EXECUTION_ON_CP7_FULL',
                  oracle_origin='INHERITED_UNMODIFIED', retry=False)
    try:
        with full_stack.installed(report) as verify:
            with exact_public_catalog(native, retain_raw=True, retain_locations=True) as catalog:
                if TAG == 'bf':
                    report['groups']['native'] = native._strict_group_once(label+'_NATIVE', module.cases, verify)
                    full_stack.save(label, report)
                if hasattr(module, 'races'):
                    report['groups']['races'] = modes._run_races_once(module, verify, 'coverage-'+TAG)
                    full_stack.save(label, report)
                if hasattr(module, 'http_cases'):
                    report['groups']['http'] = modes._run_http_once(module, verify, 'coverage-'+TAG)
                    full_stack.save(label, report)
                if TAG in ('bb','bc','bd','be','bf'):
                    script = 'cp6_bf_vendor_browser.mjs' if TAG == 'bf' else 'cp6_'+TAG+'_browser.mjs'
                    report['groups']['browser'] = modes._run_browser_once(full_stack.PRODUCT/'scripts'/script, verify, 'coverage-'+TAG)
                    full_stack.save(label, report)
                report['catalog_adapter'] = catalog
    except Exception as exc:
        report.update(error=str(exc), traceback=traceback.format_exc())
    good = bool(report['groups']) and not report.get('error') and all(
        g.get('status') in ('PASS','RUN_COMPLETE') and set(g.get('counts',{})) == {'PASS'}
        and g['counts']['PASS'] > 0 and g.get('database_remaining',0) == 0
        for g in report['groups'].values())
    report['status'] = 'PASS' if good and report.get('cp6_restored') and report.get('advisor_gate') else 'INCOMPLETE'
    full_stack.save(label, report)
    print(json.dumps({k:report.get(k) for k in ('label','status','error','cp6_restored','advisor_gate')},default=str),flush=True)
    return dict(status=report['status'], production_go=False)

if __name__ == '__main__':
    full_stack.package._writer_runtime = lambda browser_mode=False:run()
    full_stack.package.run('install')
