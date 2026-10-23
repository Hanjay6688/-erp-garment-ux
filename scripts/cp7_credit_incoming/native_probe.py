"""OW-04b slice C Native qualification on a disposable aligned CP6 copy (7 savepoint cases + 1 two-session race).

The stage is installed over slice B (admitted by slice B's probe and pins, which admit slice A and its original, and by
the exact qualified slice B Native6+Race1 original report). No hosted or production effect. The race runs on a fresh
committed copy (cp6_auditor_modes).
"""
from pathlib import Path
from hashlib import sha256
import json,os,subprocess,sys,time,traceback
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
sys.path.insert(0,str(REPO/'scripts'))
from cp7_credit_multi import native_probe as lower
setup=lower.setup
for extra in('cp7_customer_credit/consumer','cp7_customer_credit/reconciliation/native',
             'cp7_customer_credit/native','cp7_customer_credit/initial-settlement'):
    if str(REPO/'scripts'/extra)not in sys.path:sys.path.append(str(REPO/'scripts'/extra))
from cp7_credit_incoming import composition as product,cases as business
import psycopg
import cp6_auditor_modes as modes
from cp6_t3_aligned_install import advisors,advisor_delta
from cp7_catalog_state import exact_public_catalog
control=setup.control
previous,native,package,core,p09=setup.previous,setup.native,setup.package,setup.core,setup.p09
IDS=business.IDS
RACE_IDS=business.RACE_IDS
LABEL='CP7_OW04BC_INCOMING_CREDIT_RETURN_NATIVE7_RACE1'
OUT=REPO/'cp6-proof/t3'/f'{LABEL}.json'
STATE=None


def admitted():
    old=lower.admitted()
    pins=json.loads((HERE/'SOURCE.json').read_bytes())
    for path,digest in pins['files'].items():assert sha256((REPO/path).read_bytes()).hexdigest()==digest,('OW04BC_SOURCE_CHANGED',path)
    assert pins['predecessor_stage']=='cp7_credit_multi'
    assert pins['case_ids']==list(IDS)and len(IDS)==7
    assert pins['race_ids']==list(RACE_IDS)and len(RACE_IDS)==1
    raw=Path(os.environ['OW04BB_NATIVE6_ORIGINAL_REPORT']).read_bytes();proof=pins['native_original']
    assert len(raw)==proof['bytes']and sha256(raw).hexdigest()==proof['sha256']
    actual=json.loads(raw)
    assert actual['label']=='CP7_OW04BB_MULTI_RETURN_NATIVE6_RACE1'and actual['status']=='PASS'
    assert actual['native']['counts']=={'PASS':6}and actual['races']['counts']=={'PASS':1}
    assert actual['cp6_restored']and actual['advisor_gate']and actual['required_case_ids_pass']and actual['required_race_ids_pass']
    assert actual['source_declaration']['OW04BB_declared_source']==old['OW04BB_declared_source']
    assert not subprocess.check_output(['git','-C',str(REPO),'status','--porcelain','--',str(HERE)],text=True).strip()
    return dict(qualified_slice_b=proof,slice_b_admission=old,OW04BC_declared_source=pins)


def bind():
    business.ORIGINALS=STATE['originals'];business.AS_OWNER=product.as_owner


def cases(cur,today):
    bind()
    result=business.cases(cur,today)
    assert tuple(key for key,_ in result)==IDS
    return result


def verify(cur):
    if STATE is None:raise ValueError('OW04BC_INSTALLATION_REQUIRED')
    # The retained SQL harness alone may grant ERP USAGE; it is removed only
    # while the product catalog is compared, never projected into the product.
    with control.product_catalog(cur):
        return product.verify(cur,STATE)


def race_verify(cur):
    """A fresh copy of the installed database: exact patched definitions and private reader authority.

    The complete 22-group catalog equality (which includes the database's own name-level authority) is proven on the
    installed database itself by verify(); a copy is a different database object, so only the stage's objects are
    compared there.
    """
    if STATE is None:raise ValueError('OW04BC_INSTALLATION_REQUIRED')
    return product.verify_objects(cur,STATE)


def quiesce(limit=90):
    """Before removal: wait (bounded) until no OTHER backend holds a lock on a relation of a cp7 schema, and record who
    did. The retained removal still takes its ACCESS EXCLUSIVE NOWAIT locks unchanged; this only avoids racing a
    transient holder (run 39893191153 could not lock cp7_sales.requests; the holder was not recorded)."""
    seen=[];deadline=time.monotonic()+limit
    with psycopg.connect(package.boundary.ADMIN,autocommit=True)as conn,conn.cursor()as cur:
        while True:
            rows=cur.execute("""select a.pid,a.backend_type,coalesce(a.state,''),l.mode,c.relname,n.nspname,left(coalesce(a.query,''),160)
             from pg_locks l join pg_class c on c.oid=l.relation join pg_namespace n on n.oid=c.relnamespace
             left join pg_stat_activity a on a.pid=l.pid
             where l.pid<>pg_backend_pid()and l.database=(select oid from pg_database where datname=current_database())
              and n.nspname like 'cp7%'order by 1,5""").fetchall()
            if rows and len(seen)<30:seen.append([list(map(str,r))for r in rows[:10]])
            if not rows:return dict(clear=True,waited_polls=len(seen),holders_seen=seen)
            if time.monotonic()>deadline:return dict(clear=False,waited_polls=len(seen),holders_seen=seen)
            time.sleep(1)


def run():
    global STATE
    report=dict(label=LABEL,status='INCOMPLETE',source_declaration=admitted(),
        qualification_commit=subprocess.check_output(['git','-C',str(REPO),'rev-parse','HEAD'],text=True).strip(),
        expected_case_count=len(IDS),required_case_ids=list(IDS),expected_race_count=len(RACE_IDS),required_race_ids=list(RACE_IDS),
        formal_CP7C_started=False,OW04b_complete=False,production_go=False,independent_acceptance=False)
    installed=False
    try:
        with psycopg.connect(package.boundary.ADMIN)as conn,conn.cursor()as cur:
            p09.wip.policy.bf.verified(cur)
            before=previous.restore_state.capture(cur,package.boundary.snapshot,core.predecessor.public_state,p09.functions)
            conn.rollback()
            try:
                STATE=product.install(cur)
            except Exception:
                # Keep the exact predecessor definitions for diagnosis of a changed anchor.
                report['predecessor_definitions_on_install_failure']=dict(product.CAPTURED)
                raise
            control.STATE=dict(installed_catalog=STATE['after'])
            report['complete_installed_verification']=product.verify(cur,STATE)
            report['verified_predecessor_info_manifest']=core.predecessor_info_manifest(cur)
            conn.commit();installed=True
        report['advisors_with_cp7']=advisors(package.boundary.PG)
        with exact_public_catalog(native,retain_raw=True)as catalog:
            report['native']=native.strict_group(LABEL,cases,verify)
        report['native_public_catalog_comparison']=catalog
        bind()
        report['races']=modes.run_races(business,race_verify,'ow04b')
    except Exception as error:
        report.update(error=str(error),traceback=traceback.format_exc())
    finally:
        if installed:
            try:
                try:
                    report['pre_removal_lock_wait']=quiesce()
                except Exception as error:  # diagnostics only; removal below still runs with its own guards
                    report['pre_removal_lock_wait']=dict(clear=None,error=str(error))
                with psycopg.connect(package.boundary.ADMIN)as conn,conn.cursor()as cur:
                    report['complete_preuse_removal']=product.rollback_preuse(cur,STATE)
                    conn.commit()
                    report['cp6_restored']=previous.restore_state.prove(cur,before,package.boundary.snapshot,
                        core.predecessor.public_state,p09.functions,report)
                    conn.rollback();p09.wip.policy.bf.verified(cur);conn.rollback()
                report['advisor_delta']=advisor_delta(advisors(package.boundary.PG),report['advisors_with_cp7'])
                report['advisor_disposition']=core.advisor_disposition(report['advisor_delta'],report['verified_predecessor_info_manifest'])
                report['advisor_gate']=report['advisor_disposition']['gate']
            except Exception as error:
                report.update(restore_error=str(error),restore_traceback=traceback.format_exc(),cp6_restored=False,advisor_gate=False)
        group=report.get('native',{})
        races=report.get('races',{})
        report['observed_case_count']=sum(group.get('counts',{}).values())
        report['observed_race_count']=sum(races.get('counts',{}).values())
        report['required_case_ids_pass']=set(group.get('cases',{}))==set(IDS)and all(c['status']=='PASS'for c in group.get('cases',{}).values())
        report['required_race_ids_pass']=set(races.get('races',{}))==set(RACE_IDS)and all(c['status']=='PASS'for c in races.get('races',{}).values())
        if not report.get('error')and report.get('cp6_restored')and report.get('advisor_gate')and report['required_case_ids_pass']\
            and group.get('counts')=={'PASS':len(IDS)}and report['required_race_ids_pass']and races.get('counts')=={'PASS':len(RACE_IDS)}\
            and races.get('status')in('PASS','RUN_COMPLETE')and races.get('database_remaining',1)==0:
            report['status']='PASS'
        OUT.parent.mkdir(parents=True,exist_ok=True)
        OUT.write_text(json.dumps(report,indent=2,default=str)+'\n')
        print(json.dumps({key:report.get(key)for key in('label','status','observed_case_count','observed_race_count','cp6_restored',
            'advisor_gate','error','restore_error')},default=str),flush=True)
        for name,case in list(group.get('cases',{}).items())+list(races.get('races',{}).items()):
            print(json.dumps(dict(case=name,status=case.get('status'),error=case.get('error')),default=str)[:3000],flush=True)
    return dict(status=report['status'],OW04b_complete=False,production_go=False,independent_acceptance=False)


if __name__=='__main__':
    admitted();package._writer_runtime=lambda browser_mode=False:run();package.run('install')
