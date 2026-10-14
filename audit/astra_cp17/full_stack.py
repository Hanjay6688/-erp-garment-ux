"""Install and remove the candidate's declared FULL composition on its disposable clone.

The installer/verifier are reused intact from P21. This is harness reuse, not a
writer verdict; each audit case executes on the resulting candidate bodies.
"""
from pathlib import Path
from contextlib import contextmanager
import hashlib,json,os,subprocess,sys,traceback
import psycopg

PRODUCT=Path.cwd().parent/'auditor'
sys.path.insert(0,str(PRODUCT/'scripts'))
import cp7_p21_full_rehearsal_probe as composition
import cp7_restore_state as restore_state
import cp6_t3_package_run as package
from cp6_t3_aligned_install import advisors,advisor_delta

OUT=PRODUCT/'cp6-proof/t3'

def save(name,value):
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/(name+'.json')).write_text(json.dumps(value,indent=2,default=str)+'\n')

def identity():
    return dict(candidate_sha=subprocess.check_output(['git','-C',str(PRODUCT),'rev-parse','HEAD'],text=True).strip(),
                candidate_tree=subprocess.check_output(['git','-C',str(PRODUCT),'rev-parse','HEAD^{tree}'],text=True).strip(),
                workflow_sha=os.environ.get('GITHUB_SHA'),run_id=os.environ.get('GITHUB_RUN_ID'),
                run_attempt=os.environ.get('GITHUB_RUN_ATTEMPT'),round_id='cp17-20261014')

@contextmanager
def installed(report):
    originals=None;ready=False
    report.update(identity(),production_go=False,installation_origin='CANDIDATE_P21_FULL_UNCHANGED',
                  full_composition_sha256=hashlib.sha256(composition.top.bundle().encode()).hexdigest())
    assert report['candidate_sha']=='0b7049d9203bac52b47a4c89f3e0d75646067a8f'
    assert report['candidate_tree']=='ce6aed0a0af920e8aa80248f3cabcd293688df18'
    try:
        with psycopg.connect(package.boundary.ADMIN) as conn,conn.cursor() as cur:
            composition.p09.wip.policy.bf.verified(cur)
            before=restore_state.capture(cur,package.boundary.snapshot,composition.f05.public_state,composition.p09.functions)
            conn.rollback()
            originals,details=composition.install(cur)
            report['installation']=details
            conn.commit();ready=True
            report['full_runtime_before']=composition.verify(cur)
            conn.rollback()
        report['advisors_installed']=advisors(package.boundary.PG)
        yield composition.verify
    finally:
        if ready:
            try:
                with psycopg.connect(package.boundary.ADMIN) as conn,conn.cursor() as cur:
                    report['full_runtime_after']=composition.verify(cur)
                    conn.rollback()
                    composition.uninstall(cur,originals);conn.commit()
                    report['cp6_restored']=restore_state.prove(cur,before,package.boundary.snapshot,
                        composition.f05.public_state,composition.p09.functions,report)
                    conn.rollback();composition.p09.wip.policy.bf.verified(cur);conn.rollback()
                delta=advisor_delta(advisors(package.boundary.PG),report['advisors_installed'])
                report['advisor_delta']=delta
                # Same exact reviewed INFO class used by candidate FULL probes.
                report['advisor_gate']=delta['status']=='NO_NEW_FINDINGS' or (
                    delta['status']=='REVIEW_REQUIRED' and all(
                        f.get('name')=='rls_enabled_no_policy' and f.get('level')=='INFO'
                        and (f.get('metadata') or {}).get('schema') in (
                            'cp7_recost','cp7_period','cp7_sales','cp7_payroll','cp7_attendance',
                            'cp7_fg','cp7_private','cp7_identity','cp7_wip','cp7_procurement',
                            'cp7_material','cp7_supplier_return','cp7_invoice','cp7_receipt_fix')
                        for f in delta.get('added',[])))
            except Exception as exc:
                report.update(cp6_restored=False,restore_error=str(exc),restore_traceback=traceback.format_exc())

