"""Three explicit payroll-completed successors retaining every original financial oracle.

The latest full A source admission and all declared B/correction hashes are
checked before DB. 3 explicit successor cases at each installation boundary, strict rollback and full22 inverse;
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
import cp7_current_return_installation as installation
import importlib.util
_spec=importlib.util.spec_from_file_location("current_opening_replay_cases",HERE/"cases.py")
business=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(business)
import psycopg
from cp6_t3_aligned_install import advisors,advisor_delta
from cp7_catalog_state import exact_public_catalog
control=chain.helper.control
previous,native,package,core,p09=chain.previous,control.native,chain.package,chain.core,chain.p09
IDS=business.IDS
LABEL='CP7_CURRENT_CASH_LINKED_NATIVE3'
OUT=REPO/'cp6-proof/t3'/f'{LABEL}.json'
STATE=None
FIXTURES={}
database,drill,dump=chain.database,chain.drill,chain.dump
PRE_DUMP='/tmp/current_cash_linked_native3_pre.dump'


def admitted():
    spec=importlib.util.spec_from_file_location('qualified_current_return_installation',REPO/'scripts/current-return-installation-qualification/probe.py')
    predecessor=importlib.util.module_from_spec(spec);spec.loader.exec_module(predecessor)
    previous=predecessor.admitted()
    business.declared_cases()
    inherited=json.loads((REPO/'scripts/current-cash-ready-qualification/SOURCE.json').read_bytes())
    for path,digest in inherited['files'].items():
        assert sha256((REPO/path).read_bytes()).hexdigest()==digest,('CASH_READY_ANCESTOR_SOURCE_CHANGED',path)
    pins=json.loads((HERE/'SOURCE.json').read_bytes())
    for path,digest in pins['files'].items():
        assert sha256((REPO/path).read_bytes()).hexdigest()==digest,('CASH_READY_SOURCE_CHANGED',path)
    assert pins['case_ids']==list(IDS)and len(IDS)==3
    assert not subprocess.check_output(['git','-C',str(REPO),'status','--porcelain','--',str(HERE)],text=True).strip()
    return dict(qualified_composed_predecessor=previous,current_installation=installation.sources(),qualification=pins,inherited_qualification=inherited)


def acquire_qualification_boundary(cur):
    """Wait at most45s for the exact product table set before its unchanged NOWAIT guard.

    Only this disposable qualifier owns the connection/transaction. No backend
    is cancelled, catalog normalized, data reset or application grant changed.
    Locks remain held until the caller's transaction completes.
    """
    assert cur.connection.info.host in('127.0.0.1','localhost')
    assert cur.execute('select current_database()').fetchone()==(database.SOURCE,)
    catalog=installation.catalog
    names=cur.execute("select n.nspname,c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace where c.relkind in('r','p')and "+catalog.NAMESPACE+" order by n.nspname collate \"C\",c.relname collate \"C\"").fetchall()
    assert names
    observed=cur.execute("select a.pid,a.backend_type,coalesce(a.state,''),l.mode,n.nspname,c.relname,l.granted from pg_locks l join pg_class c on c.oid=l.relation join pg_namespace n on n.oid=c.relnamespace left join pg_stat_activity a on a.pid=l.pid where l.database=(select oid from pg_database where datname=current_database())and l.pid<>pg_backend_pid()and "+catalog.NAMESPACE+" order by a.pid,n.nspname,c.relname,l.mode").fetchall()
    previous_timeout=cur.execute('show lock_timeout').fetchone()[0]
    cur.execute("set local lock_timeout='45s'")
    cur.execute(chain.sql.SQL('lock table {} in share mode').format(chain.sql.SQL(',').join(chain.sql.Identifier(*n)for n in names)))
    cur.execute("select set_config('lock_timeout',%s,true)",(previous_timeout,))
    held=cur.execute("select count(distinct l.relation)from pg_locks l join pg_class c on c.oid=l.relation join pg_namespace n on n.oid=c.relnamespace where l.pid=pg_backend_pid()and l.granted and l.mode in('ShareLock','ShareRowExclusiveLock','ExclusiveLock','AccessExclusiveLock')and c.relkind in('r','p')and "+catalog.NAMESPACE).fetchone()[0]
    assert held>=len(names),(held,len(names))
    return dict(status='EXACT_TABLE_SET_SHARE_LOCKS_HELD',table_count=len(names),held_count=held,
        other_holders_before_wait=observed,bounded_lock_wait_seconds=45,product_NOWAIT_unchanged=True,
        cancelled_backends=0,data_or_catalog_changes=False)


def cases(cur,today):
    stage='current'if STATE is not None else 'baseline'
    evidence=FIXTURES.setdefault(stage,{})
    result=business.cases(cur,today,current=STATE is not None,evidence=evidence)
    assert tuple(key for key,_ in result)==IDS
    return result


def verify(cur):
    if STATE is None:raise ValueError('CURRENT_CP6_CROSSFLOW_INSTALLATION_REQUIRED')
    # The retained SQL harness alone may grant ERP USAGE; it is removed only
    # while the product catalog is compared, never projected into the product.
    with control.product_catalog(cur):
        return installation.verify(cur,STATE)


@contextmanager
def keep_group_originals():
    old=native.r1.OUT
    native.r1.OUT=OUT.parent/'strict-groups'
    try:yield
    finally:native.r1.OUT=old


def run():
    global STATE
    report=dict(label=LABEL,status='INCOMPLETE',source_declaration=admitted(),
        qualification_commit=subprocess.check_output(['git','-C',str(REPO),'rev-parse','HEAD'],text=True).strip(),
        expected_case_count=len(IDS),required_case_ids=list(IDS),formal_CP7C_started=False,real_Auth_browser_claim=False,factory3600_claim=False,
        CP6_retained_crossflow_only=True,production_go=False,independent_acceptance=False)
    installed=False;before=None;pre_dumped=False;before_roles=set();new_roles=set()
    try:
        with psycopg.connect(package.boundary.ADMIN)as conn,conn.cursor()as cur:
            assert conn.info.host in('127.0.0.1','localhost')and cur.execute('select current_database()').fetchone()==(database.SOURCE,)
            p09.wip.policy.bf.verified(cur)
            before_roles=database._roles(cur)
            before_catalog=installation.catalog._catalog_rows(cur);before_data=installation.catalog._data(cur)
            report['baseline_advisors']=advisors(package.boundary.PG)
            before=previous.restore_state.capture(cur,package.boundary.snapshot,core.predecessor.public_state,p09.functions)
            conn.rollback()
        pre_data=drill.data_hashes(database.SOURCE);pre_profile=database._database_profile(database.SOURCE)
        dump.dump(database.SOURCE,PRE_DUMP);pre_dumped=True
        # Observe the identical retained cases before CP7 without granting any new
        # table/function rights or changing their original expectations.
        with keep_group_originals(),exact_public_catalog(native,retain_raw=True)as baseline_catalog:
            report['baseline']=native.strict_group(LABEL+'_BASELINE',cases,p09.wip.policy.bf.verified)
        report['baseline_public_catalog_comparison']=baseline_catalog
        assert report['baseline']['complete_boundary_restored'],'CP6_CROSSFLOW_BASELINE_NOT_RESTORED'
        with psycopg.connect(package.boundary.ADMIN)as conn,conn.cursor()as cur:
            p09.wip.policy.bf.verified(cur)
            conn.rollback()
            try:
                report['initial_boundary_lock']=acquire_qualification_boundary(cur)
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
        report['advisors_with_cp7']=advisors(package.boundary.PG)
        with keep_group_originals(),exact_public_catalog(native,retain_raw=True)as catalog:
            report['native']=native.strict_group(LABEL,cases,verify)
        report['native_public_catalog_comparison']=catalog
    except Exception as error:
        report.update(error=str(error),traceback=traceback.format_exc())
    finally:
        if installed:
            # SQL savepoint rollback does not rewind PostgreSQL sequences.
            # Preserve and classify every observed difference. Never reset it
            # to evade the product's stricter all-row/all-sequence used guard.
            try:
                with psycopg.connect(package.boundary.ADMIN)as conn,conn.cursor()as cur:
                    report['complete_boundary_lock_before_used_guard']=acquire_qualification_boundary(cur)
                    report['quiesce_before_full_restore']=chain.quiesce(cur)
                    assert report['quiesce_before_full_restore']['clear']
                    installation.verify(cur,STATE)
                    held=installation.catalog._data(cur);held_catalog=installation.catalog._catalog_rows(cur)
                    original=STATE['delta']['preuse_data_and_sequences']
                    changes={k:dict(before=original.get(k),after=held.get(k))for k in set(original)|set(held)if original.get(k)!=held.get(k)}
                    report['post_test_data_or_sequence_changes']=changes
                    if changes:
                        try:installation.rollback_preuse(cur,STATE)
                        except ValueError as error:assert str(error)==installation.USED_ERROR,str(error)
                        else:raise AssertionError('USED_DELTA_REMOVED_AFTER_CASES')
                        assert installation.catalog._data(cur)==held and installation.catalog._catalog_rows(cur)==held_catalog
                        report['post_test_used_guard']=dict(refused=True,all_data_sequences_catalog_unchanged=True)
                    assert all(k.startswith('sequence:')for k in changes),('UNEXPECTED_PERSISTENT_ROW_CHANGE',changes)
                    conn.rollback()
            except Exception as error:
                report.update(error=str(error),post_test_guard_traceback=traceback.format_exc())
        # Full source backup restores every original sequence value as well as
        # all business data and metadata. This runs even if diagnosis fails.
        if before is not None and pre_dumped:
            try:
                if pre_dumped:
                    restored=database._restore(PRE_DUMP,database.SOURCE,pre_profile)
                    assert restored['only_pg_cron_errors']
                    report['baseline_full_restore']=restored
                assert drill.data_hashes(database.SOURCE)==pre_data
                with psycopg.connect(package.boundary.ADMIN)as conn,conn.cursor()as cur:
                    for role in sorted(new_roles):cur.execute(chain.sql.SQL('drop role {}').format(chain.sql.Identifier(role)))
                    conn.commit();assert database._roles(cur)==before_roles
                    assert installation.catalog._data(cur)==before_data,'FULL_RESTORE_ROWS_OR_SEQUENCES_CHANGED'
                    assert installation.catalog._portable(installation.catalog._catalog_rows(cur))==installation.catalog._portable(before_catalog),'FULL_RESTORE_CATALOG_CHANGED'
                    report['baseline_all22_rows_sequences_exact']=True
                    report['cp6_restored']=previous.restore_state.prove(cur,before,package.boundary.snapshot,
                        core.predecessor.public_state,p09.functions,report)
                    conn.rollback();p09.wip.policy.bf.verified(cur);conn.rollback()
                report['baseline_advisors_equal']=advisors(package.boundary.PG)==report['baseline_advisors']
                if 'advisors_with_cp7'in report:
                    report['advisor_delta']=advisor_delta(advisors(package.boundary.PG),report['advisors_with_cp7'])
                    report['advisor_disposition']=core.advisor_disposition(report['advisor_delta'],report['verified_predecessor_info_manifest'])
                    report['advisor_gate']=report['advisor_disposition']['gate']and report['baseline_advisors_equal']
                else:
                    report['advisor_gate']=report['baseline_advisors_equal']
                    report['installed_advisor_comparison_not_reached']=True
            except Exception as error:
                report.update(restore_error=str(error),restore_traceback=traceback.format_exc(),cp6_restored=False,advisor_gate=False)
        drill.docker('rm','-f',PRE_DUMP,check=False)

        report['explicit_fixture_prerequisite_receipts']=business.prerequisites.EVIDENCE
        report['diagnostic_only']=False
        report['strict_group_originals']=[dict(path=str(p.relative_to(OUT.parent)),bytes=p.stat().st_size,sha256=sha256(p.read_bytes()).hexdigest())for p in sorted((OUT.parent/'strict-groups').glob('*.json'))]
        report['seed_prerequisite_preparation']=FIXTURES
        group=report.get('native',{})
        baseline=report.get('baseline',{})
        report['baseline_observed_case_count']=sum(baseline.get('counts',{}).values())
        report['case_status_comparison']={name:dict(baseline=baseline.get('cases',{}).get(name,{}).get('status'),current=group.get('cases',{}).get(name,{}).get('status'))for name in IDS}
        report['changed_case_statuses']={name:row for name,row in report['case_status_comparison'].items()if row['baseline']!=row['current']}
        report['retained_case_credit']=0
        report['explicit_successor_case_count']=len(IDS)
        report['unchanged_original_diagnostic_case_count']=0
        report['legacy_results_relabelled']=False
        report['execution_count']=report['baseline_observed_case_count']+sum(group.get('counts',{}).values())
        report['new_business_case_credit']=0
        report['observed_case_count']=sum(group.get('counts',{}).values())
        report['required_case_ids_pass']=set(group.get('cases',{}))==set(IDS)and all(c['status']=='PASS'for c in group.get('cases',{}).values())
        if not report.get('error')and report.get('cp6_restored')and report.get('advisor_gate')and report['required_case_ids_pass']and group.get('counts')=={'PASS':len(IDS)}and baseline.get('counts')=={'PASS':len(IDS)}and report.get('baseline_all22_rows_sequences_exact'):
            report['status']='PASS'
        OUT.parent.mkdir(parents=True,exist_ok=True)
        OUT.write_text(json.dumps(report,indent=2,default=str)+'\n')
        print(json.dumps({key:report.get(key)for key in('label','status','observed_case_count','cp6_restored','advisor_gate','error','restore_error')},default=str),flush=True)
        for name,case in group.get('cases',{}).items():
            print(json.dumps(dict(case=name,status=case.get('status'),error=case.get('error')),default=str)[:3000],flush=True)
    return dict(status=report['status'],CP6_retained_crossflow_only=True,production_go=False,independent_acceptance=False)


if __name__=='__main__':
    admitted();package._writer_runtime=lambda browser_mode=False:run();package.run('install')
