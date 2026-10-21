"""Six actual SQL races and uncommitted recovery cases, disposable only."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,traceback
REPO=Path(os.environ.get('ERP_REPO',Path(__file__).resolve().parents[2])).resolve()
sys.path[:0]=[str(REPO/'scripts/ow04-qualification'),str(REPO/'scripts')]
if len(sys.argv)>1:raise SystemExit('OW04 race entry accepts no arguments')
import transport_probe as transport_backend
core=transport_backend.core
import cp7_ow04_race_cases as race_cases
import cp6_auditor_modes as modes
import psycopg
from cp6_t3_aligned_install import advisors,advisor_delta
p09,package,credit=core.p09,core.package,core.credit
OUT=p09.bundle.ROOT/'cp6-proof/t3/CP7_OW04_RACES.json'
DECLARATION_BYTES=Path(__file__).with_name('RACE_EXPECTED.json').read_bytes()
DECLARATION=json.loads(DECLARATION_BYTES)
assert tuple(x['id']for x in DECLARATION['cases'])==race_cases.IDS and len(race_cases.IDS)==6


def git(*args):
    return subprocess.run(['git','-C',str(REPO),*args],check=True,capture_output=True,text=True).stdout.strip()


def run():
    # Fail before opening a connection if any previously qualified product or
    # installer dependency differs. Only this explicit qualification may differ.
    reused=transport_backend.qualified_core()
    report=dict(label='CP7_OW04_RACES',status='INCOMPLETE',expected_case_count=6,required_case_ids=list(race_cases.IDS),
        candidate_commit=git('rev-parse','HEAD'),core_directory_tree=git('rev-parse','HEAD:scripts/cp7_customer_credit'),
        native_probe_blob=git('rev-parse','HEAD:scripts/cp7_ow04_probe.py'),source_sha256=credit.source_files(native_empty=True),
        qualification_only=True,independent_acceptance=False,production_go=False,feature_complete=False,
        predeclared_case_sha256=hashlib.sha256(DECLARATION_BYTES).hexdigest(),
        race_cases_sha256=hashlib.sha256(Path(race_cases.__file__).read_bytes()).hexdigest(),
        race_probe_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        transport_entry_sha256=hashlib.sha256(Path(transport_backend.__file__).read_bytes()).hexdigest(),
        reused_native_binding=reused,
        scope='ACTUAL_PUBLIC_SQL_CONCURRENCY_AND_UNCOMMITTED_BACKEND_LOSS_RECOVERY',
        limits=['Native qualification is separate evidence; no inference from this SQL race group','Authenticated SQL fixtures, not real Auth or browser','Backend-loss case aborts an uncommitted transaction, not a committed lost HTTP reply or whole-server crash','No default installation or production deployment'])
    installed=False;originals={}
    try:
        with psycopg.connect(package.boundary.ADMIN)as conn,conn.cursor()as cur:
            p09.wip.policy.bf.verified(cur)
            before=core.restore_state.capture(cur,package.boundary.snapshot,core.predecessor.public_state,p09.functions);conn.rollback()
            originals=core.install_predecessor(cur,report)
            report['verified_predecessor_info_manifest']=core.predecessor_info_manifest(cur)
            core.STATE=credit.install(cur,core.predecessor.verify,p09.functions,native_empty=True)
            p09.INSTALLED_FUNCTIONS=p09.functions(cur)
            report['integrated_source_verification']=core.verify(cur)
            conn.commit();installed=True;conn.rollback()
        report['advisors_with_cp7']=advisors(package.boundary.PG)
        report['races']=modes.run_races(race_cases,core.verify,'cp7_ow04_settlement')
    except Exception as error:report.update(error=str(error),traceback=traceback.format_exc())
    finally:
        if installed:
            try:
                with psycopg.connect(package.boundary.ADMIN)as conn,conn.cursor()as cur:
                    credit.uninstall(cur,core.STATE)
                    for definition in originals.values():cur.execute(definition,prepare=False)
                    for role in core.predecessor.bundle.ROLES:cur.execute('drop owned by '+role+' cascade;drop role '+role,prepare=False)
                    conn.commit()
                    report['cp6_restored']=core.restore_state.prove(cur,before,package.boundary.snapshot,core.predecessor.public_state,p09.functions,report)
                    conn.rollback();p09.wip.policy.bf.verified(cur);conn.rollback()
                report['advisor_delta']=advisor_delta(advisors(package.boundary.PG),report['advisors_with_cp7'])
                report['advisor_disposition']=core.advisor_disposition(report['advisor_delta'],report['verified_predecessor_info_manifest'])
                report['advisor_gate']=report['advisor_disposition']['gate']
            except Exception as error:report.update(restore_error=str(error),restore_traceback=traceback.format_exc(),cp6_restored=False,advisor_gate=False)
        group=report.get('races',{});report['observed_case_count']=sum(group.get('counts',{}).values())
        report['required_case_ids_pass']=set(group.get('races',{}))==set(race_cases.IDS)
        if not report.get('error')and report.get('cp6_restored')and report.get('advisor_gate') \
            and group.get('status')in('PASS','RUN_COMPLETE')and group.get('counts')=={'PASS':6} \
            and report['required_case_ids_pass']and group.get('database_remaining',1)==0:
            report['status']='PASS'
        OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(report,indent=2,default=str)+'\n')
        print(json.dumps({k:report.get(k)for k in ('label','status','candidate_commit','core_directory_tree','expected_case_count','observed_case_count','cp6_restored','advisor_gate','error','traceback','restore_error')},default=str),flush=True)
    return dict(status=report['status'],production_go=False,independent_acceptance=False,feature_complete=False)


if __name__=='__main__':
    package._writer_runtime=lambda browser_mode=False:run()
    package.run('install')
