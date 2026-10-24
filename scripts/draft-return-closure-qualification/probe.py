"""Sibling DRAFT return isolation on the exact current A/B installation.

The latest full A source admission and all declared B/correction hashes are
checked before DB. 32 regression controls before and after one declared private-function delta, strict rollback and full22 inverse;
no hosted effects, real-Auth claim, factory-scale claim or audit acceptance.
"""
from pathlib import Path
from hashlib import sha256
from contextlib import contextmanager
import json,os,subprocess,sys,traceback
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
sys.path.insert(0,str(REPO/'scripts'))
import cp7_p21_current_chain_rehearsal_probe as chain
from cp7_ab_bounded_chain import composition as product
import cp7_ab_ui_admission as current_admission
import cp7_current_installation as installation
import cp7_draft_return_isolation as delta
import importlib.util
_spec=importlib.util.spec_from_file_location("draft_return_regression_cases",REPO/"scripts/draft-return-regression-qualification/cases.py")
business=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(business)
import psycopg
from cp6_t3_aligned_install import advisors,advisor_delta
from cp7_catalog_state import exact_public_catalog
control=chain.helper.control
previous,native,package,core,p09=chain.previous,control.native,chain.package,chain.core,chain.p09
IDS=business.IDS
LABEL='CP7_DRAFT_RETURN_CLOSURE_NATIVE32'
OUT=REPO/'cp6-proof/t3'/f'{LABEL}.json'
STATE=None
PATCH_STATE=None
database,drill,dump=chain.database,chain.drill,chain.dump
PRE_DUMP='/tmp/draft_return_closure_pre.dump'


def admitted():
    previous,_=current_admission.admitted()
    guard_path=REPO/'scripts/cp7_customer_credit/integration/source_triggers/trigger_guard.py'
    spec=importlib.util.spec_from_file_location('current_owner_trigger_guard',guard_path)
    guard=importlib.util.module_from_spec(spec);spec.loader.exec_module(guard);guard.declarations(REPO)
    pins=json.loads((HERE/'SOURCE.json').read_bytes())
    for path,digest in pins['files'].items():
        assert sha256((REPO/path).read_bytes()).hexdigest()==digest,('DRAFT_RETURN_ISOLATION_SOURCE_CHANGED',path)
    assert pins['case_ids']==list(IDS)and len(IDS)==32
    # Frozen builders can import from the immutable writer sibling. Admit the
    # bytes actually loaded as well as their canonical repository paths.
    imported=[]
    for entry in pins['local_loaded_CP6_imports_verified']:
        module=sys.modules.get(entry['module'])
        assert module is not None and getattr(module,'__file__',None),('CP6_DECLARED_IMPORT_MISSING',entry['module'])
        actual=sha256(Path(module.__file__).read_bytes()).hexdigest()
        assert actual==entry['sha256']==pins['files'][entry['path']],('CP6_LOADED_IMPORT_SOURCE_CHANGED',entry['module'])
        imported.append(entry['module'])
    expected=json.loads((HERE/'EXPECTED.json').read_text())
    assert expected['count']==32 and expected['case_ids']==list(IDS)
    assert expected['unfixed_counterexamples']==list(business.COUNTEREXAMPLES)
    assert expected['fixed_counts']=={'PASS':32}and expected['unfixed_counts']=={'INCOMPLETE':2,'PASS':30}
    assert expected['retained_unchanged_case_ids']==list(business.RETAINED_IDS)
    assert expected['historical_unchanged_failures_with_explicit_successors']==business.SUCCESSOR_MAP
    original_raw=Path(os.environ['DRAFT_RETURN_COUNTEREXAMPLE_ORIGINAL_REPORT']).read_bytes()
    proof=pins['actual_counterexample_observation']
    assert len(original_raw)==proof['bytes']and sha256(original_raw).hexdigest()==proof['sha256']
    original=json.loads(original_raw)
    assert original['status']=='INCOMPLETE'and original['baseline']['counts']=={'PASS':6}
    assert original['native']['counts']=={'PASS':5,'INCOMPLETE':1}
    assert original['cp6_restored']and original['advisor_gate']
    assert original['source_declaration']['current_installation']==installation.sources()
    assert not subprocess.check_output(['git','-C',str(REPO),'status','--porcelain','--',str(HERE)],text=True).strip()
    return dict(loaded_CP6_imports_verified=imported,qualified_A_predecessor=previous,complete_AB_product=product.sources(),current_installation=installation.sources(),qualification=pins)


def used_guard(cur):
    held=delta.catalog._data(cur);catalog=delta.catalog._catalog_rows(cur)
    try:
        with control.product_catalog(cur):delta.rollback_preuse(cur,PATCH_STATE)
    except ValueError as error:assert str(error)==delta.USED_ERROR,str(error)
    else:raise AssertionError('USED_DELTA_REMOVED')
    assert delta.catalog._data(cur)==held and delta.catalog._catalog_rows(cur)==catalog
    return dict(refused=True,all_rows_sequences_catalog_unchanged=True)


def cases(cur,today):
    business.PATCHED=PATCH_STATE is not None
    business.USED_GUARD=used_guard
    result=business.cases(cur,today)
    assert tuple(key for key,_ in result)==IDS
    return result


def verify(cur):
    if STATE is None:raise ValueError('DRAFT_RETURN_ISOLATION_INSTALLATION_REQUIRED')
    # The retained SQL harness alone may grant ERP USAGE; it is removed only
    # while the product catalog is compared, never projected into the product.
    with control.product_catalog(cur):
        return delta.verify(cur,PATCH_STATE)if PATCH_STATE is not None else installation.verify(cur,STATE)


@contextmanager
def keep_group_originals():
    old=native.r1.OUT
    native.r1.OUT=OUT.parent/'strict-groups'
    try:yield
    finally:native.r1.OUT=old


def run():
    global STATE,PATCH_STATE
    report=dict(label=LABEL,status='INCOMPLETE',source_declaration=admitted(),
        qualification_commit=subprocess.check_output(['git','-C',str(REPO),'rev-parse','HEAD'],text=True).strip(),
        expected_case_count=len(IDS),required_case_ids=list(IDS),formal_CP7C_started=False,real_Auth_browser_claim=False,factory3600_claim=False,
        draft_customer_isolation_candidate=True,production_go=False,independent_acceptance=False)
    installed=False;before=None;pre_dumped=False;before_roles=set();new_roles=set()
    try:
        with psycopg.connect(package.boundary.ADMIN)as conn,conn.cursor()as cur:
            assert cur.connection.info.host in('127.0.0.1','localhost')and cur.execute('select current_database()').fetchone()==(database.SOURCE,)
            p09.wip.policy.bf.verified(cur)
            before_roles=database._roles(cur)
            before_catalog=delta.catalog._catalog_rows(cur);before_data=delta.catalog._data(cur)
            report['baseline_advisors']=advisors(package.boundary.PG)
            before=previous.restore_state.capture(cur,package.boundary.snapshot,core.predecessor.public_state,p09.functions)
            conn.rollback()
            pre_data=drill.data_hashes(database.SOURCE);pre_profile=database._database_profile(database.SOURCE)
            dump.dump(database.SOURCE,PRE_DUMP);pre_dumped=True
            try:
                STATE=installation.install(cur)
            except Exception:
                # Keep the exact predecessor definitions for diagnosis of a changed anchor.
                report['installation_failed_before_commit']=True
                raise
            control.STATE=dict(installed_catalog=STATE['after'])
            report['complete_installed_verification']=installation.verify(cur,STATE)
            report['verified_predecessor_info_manifest']=core.predecessor_info_manifest(cur)
            new_roles=database._roles(cur)-before_roles
            conn.commit();installed=True
        with keep_group_originals(),exact_public_catalog(native,retain_raw=True)as baseline_catalog:
            report['baseline']=native.strict_group(LABEL+'_UNFIXED',cases,verify)
        report['baseline_public_catalog_comparison']=baseline_catalog
        assert report['baseline']['complete_boundary_restored'],'UNFIXED_BOUNDARY_NOT_RESTORED'
        with psycopg.connect(package.boundary.ADMIN)as conn,conn.cursor()as cur:
            report['predecessor_verified_before_delta']=installation.verify(cur,STATE)
            PATCH_STATE=delta.install_delta(cur)
            report['delta_initial_preuse_inverse']=delta.rollback_preuse(cur,PATCH_STATE)
            report['predecessor_verified_after_initial_inverse']=installation.verify(cur,STATE)
            PATCH_STATE=delta.install_delta(cur)
            report['delta_verification']=delta.verify(cur,PATCH_STATE)
            control.STATE=dict(installed_catalog=PATCH_STATE['after'])
            conn.commit()
        report['advisors_with_cp7']=advisors(package.boundary.PG)
        with keep_group_originals(),exact_public_catalog(native,retain_raw=True)as catalog:
            report['native']=native.strict_group(LABEL,cases,verify)
        report['native_public_catalog_comparison']=catalog
    except Exception as error:
        report.update(error=str(error),traceback=traceback.format_exc())
    finally:
        if installed and PATCH_STATE is not None:
            # SQL savepoint rollback does not rewind PostgreSQL sequences.
            # Preserve and classify every observed difference. Never reset it
            # to evade the product's stricter all-row/all-sequence used guard.
            try:
                with psycopg.connect(package.boundary.ADMIN)as conn,conn.cursor()as cur:
                    report['quiesce_before_full_restore']=chain.quiesce(cur)
                    assert report['quiesce_before_full_restore']['clear']
                    delta.verify(cur,PATCH_STATE)
                    held=delta.catalog._data(cur);held_catalog=delta.catalog._catalog_rows(cur)
                    original=PATCH_STATE['preuse_data_and_sequences']
                    changes={k:dict(before=original.get(k),after=held.get(k))for k in set(original)|set(held)if original.get(k)!=held.get(k)}
                    report['post_test_data_or_sequence_changes']=changes
                    if changes:
                        try:delta.rollback_preuse(cur,PATCH_STATE)
                        except ValueError as error:assert str(error)==delta.USED_ERROR,str(error)
                        else:raise AssertionError('USED_DELTA_REMOVED_AFTER_CASES')
                        assert delta.catalog._data(cur)==held and delta.catalog._catalog_rows(cur)==held_catalog
                        report['post_test_used_guard']=dict(refused=True,all_data_sequences_catalog_unchanged=True)
                    assert all(k.startswith('sequence:')for k in changes),('UNEXPECTED_PERSISTENT_ROW_CHANGE',changes)
                    conn.rollback()
            except Exception as error:
                report.update(error=str(error),post_test_guard_traceback=traceback.format_exc())
        # Full source backup restores every original sequence value as well as
        # all business data and metadata. This runs even if diagnosis fails.
        if before is not None and pre_dumped:
            try:
                if installed:
                    restored=database._restore(PRE_DUMP,database.SOURCE,pre_profile)
                    assert restored['only_pg_cron_errors']
                    report['baseline_full_restore']=restored
                assert drill.data_hashes(database.SOURCE)==pre_data
                with psycopg.connect(package.boundary.ADMIN)as conn,conn.cursor()as cur:
                    for role in sorted(new_roles):cur.execute(chain.sql.SQL('drop role {}').format(chain.sql.Identifier(role)))
                    conn.commit();assert database._roles(cur)==before_roles
                    assert delta.catalog._data(cur)==before_data,'FULL_RESTORE_ROWS_OR_SEQUENCES_CHANGED'
                    assert delta.catalog._portable(delta.catalog._catalog_rows(cur))==delta.catalog._portable(before_catalog),'FULL_RESTORE_CATALOG_CHANGED'
                    report['baseline_all22_rows_sequences_exact']=True
                    report['cp6_restored']=previous.restore_state.prove(cur,before,package.boundary.snapshot,
                        core.predecessor.public_state,p09.functions,report)
                    conn.rollback();p09.wip.policy.bf.verified(cur);conn.rollback()
                report['baseline_advisors_equal']=advisors(package.boundary.PG)==report['baseline_advisors']
                report['advisor_delta']=advisor_delta(advisors(package.boundary.PG),report['advisors_with_cp7'])
                report['advisor_disposition']=core.advisor_disposition(report['advisor_delta'],report['verified_predecessor_info_manifest'])
                report['advisor_gate']=report['advisor_disposition']['gate']and report['baseline_advisors_equal']
            except Exception as error:
                report.update(restore_error=str(error),restore_traceback=traceback.format_exc(),cp6_restored=False,advisor_gate=False)
        drill.docker('rm','-f',PRE_DUMP,check=False)

        report['strict_group_originals']=[dict(path=str(p.relative_to(OUT.parent)),bytes=p.stat().st_size,sha256=sha256(p.read_bytes()).hexdigest())for p in sorted((OUT.parent/'strict-groups').glob('*.json'))]
        report['seed_prerequisite_preparation']=business.FIXTURES
        group=report.get('native',{})
        baseline=report.get('baseline',{})
        report['baseline_observed_case_count']=sum(baseline.get('counts',{}).values())
        report['case_status_comparison']={name:dict(baseline=baseline.get('cases',{}).get(name,{}).get('status'),current=group.get('cases',{}).get(name,{}).get('status'))for name in IDS}
        report['changed_case_statuses']={name:row for name,row in report['case_status_comparison'].items()if row['baseline']!=row['current']}
        report['regression_control_count']=len(IDS)
        report['legacy_results_relabelled']=False
        report['execution_count']=report['baseline_observed_case_count']+sum(group.get('counts',{}).values())
        report['new_business_case_credit']=0
        report['observed_case_count']=sum(group.get('counts',{}).values())
        report['required_case_ids_pass']=set(group.get('cases',{}))==set(IDS)and all(c['status']=='PASS'for c in group.get('cases',{}).values())
        bad=business.COUNTEREXAMPLES
        report['unfixed_counterexamples_reproduced']=baseline.get('counts')=={'INCOMPLETE':2,'PASS':30}and all(
            baseline.get('cases',{}).get(k,{}).get('status')=='INCOMPLETE'and
            'OW04_SOURCE_CUSTOMER_MISMATCH'in baseline.get('cases',{}).get(k,{}).get('error','')for k in bad)
        if not report.get('error')and report.get('cp6_restored')and report.get('advisor_gate')and report['required_case_ids_pass']and group.get('counts')=={'PASS':len(IDS)}and report['unfixed_counterexamples_reproduced']and report.get('delta_initial_preuse_inverse',{}).get('full22_restored')and report.get('baseline_all22_rows_sequences_exact'):
            report['status']='PASS'
        OUT.parent.mkdir(parents=True,exist_ok=True)
        OUT.write_text(json.dumps(report,indent=2,default=str)+'\n')
        print(json.dumps({key:report.get(key)for key in('label','status','observed_case_count','cp6_restored','advisor_gate','error','restore_error')},default=str),flush=True)
        for name,case in group.get('cases',{}).items():
            print(json.dumps(dict(case=name,status=case.get('status'),error=case.get('error')),default=str)[:3000],flush=True)
    return dict(status=report['status'],draft_customer_isolation_candidate=True,production_go=False,independent_acceptance=False)


if __name__=='__main__':
    admitted();package._writer_runtime=lambda browser_mode=False:run();package.run('install')
