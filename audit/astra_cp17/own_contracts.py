"""Execute frozen Astra contract oracles on the pinned candidate FULL runtime.

No original case is filtered or rewritten. The native one-attempt runner is
called directly; its planned IDs are also saved before the first operation.
"""
from pathlib import Path
import importlib,json,sys,traceback

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE/'prior_astra'))
sys.path.insert(0,str(HERE))
import full_stack
import cp6_auditor_runner as native
from cp7_catalog_state import exact_public_catalog

SUITES={
 'money':['cases_business','cases_money_edges','cases_payroll','cases_cont_money','cases_cont_extra'],
 'planning':['cases_edges','cases_planning'],
 'staged':['cases_stage','cases_cont_state'],
}
SUITE=sys.argv[1]
assert SUITE in SUITES
native.r1.OUT=full_stack.OUT

def run():
    report=dict(label='ASTRA_CP17_OWN_'+SUITE.upper(),status='INCOMPLETE',groups={},
        evidence_origin='INDEPENDENT_NATIVE_CASE',oracle_origin='ASTRA_FROZEN_CONTRACT_E800E016',
        fixture_origin='ASTRA_INPUTS_WITH_CANDIDATE_TRANSPORT',production_go=False)
    try:
        with full_stack.installed(report) as verify:
            with exact_public_catalog(native,retain_raw=True,retain_locations=True) as catalog:
                for name in SUITES[SUITE]:
                    module=importlib.import_module(name)
                    group='CP17_OWN_'+name.upper()
                    def factory(cur,today,module=module,group=group):
                        cases=module.cases(cur,today)
                        full_stack.save(group+'_PREEXECUTION_PLAN',dict(
                            case_ids=[key for key,_ in cases],source=module.__file__,
                            business_day=str(today),**full_stack.identity()))
                        return cases
                    report['groups'][name]=native._strict_group_once(group,factory,verify)
                    full_stack.save(report['label'],report)
                report['catalog_adapter']=catalog
    except Exception as exc:
        report.update(error=str(exc),traceback=traceback.format_exc())
    good=not report.get('error') and len(report['groups'])==len(SUITES[SUITE]) and all(
        g['status']=='PASS' for g in report['groups'].values())
    report['status']='PASS' if good and report.get('cp6_restored') and report.get('advisor_gate') else 'INCOMPLETE'
    full_stack.save(report['label'],report)
    print(json.dumps({k:report.get(k) for k in ('label','status','error','cp6_restored','advisor_gate')},default=str),flush=True)
    return dict(status=report['status'],production_go=False)

if __name__=='__main__':
    full_stack.package._writer_runtime=lambda browser_mode=False:run()
    full_stack.package.run('install')
