"""Root readback: retained four plus fresh three catalog primitives, never ERP."""
from pathlib import Path
from hashlib import sha256
import argparse,json,zipfile
from intake_common import GitBytes,exact,fields,pin,require,safe_path
from intake_sku27 import strict

HEAD='82f7894b1bb80e0fcff3813d32f96a851e4433c6'
TREE='525d3f2845265b6fdfe63774e015f9d4b322a89c'
NS='scripts/current-global-catalog-lock-controls/'
OLD_ZIP=dict(bytes=1801,sha256='dfb4a2236ca78c1330ce99b28d3f2082d62113cff8f7d91bede777d117ccdab1')
NEW_ZIP=dict(bytes=2987,sha256='8df3aa06abf667f8111ec7773ba2b8e0c7c0e7a9c301a8f6633321e811582c83')
OLD_IDS=('PG_PROC_SHARE_BLOCKS_CREATE_OR_REPLACE_FUNCTION','PG_PROC_SHARE_BLOCKS_FUNCTION_EXECUTE_GRANT',
    'PG_AUTHID_SHARE_BLOCKS_ROLE_CAPABILITY_CHANGE','PG_AUTH_MEMBERS_SHARE_BLOCKS_ROLE_MEMBERSHIP_GRANT')
NEW_IDS=('PREEXISTING_CATALOG_WRITER_REFUSED_BY_FRESH_XID_QUIESCENCE_BEFORE_EFFECT',
    'ALL_CATALOG_SHARE_LOCKS_ALLOW_EXISTING_FUNCTION_AND_ORDINARY_DML',
    'ACTUAL_EMPTY_IDENTIFIER_AND_EMPTY_SEARCH_PATH_SETTINGS_DIFFER')
NO_CREDIT=dict(actual_ERP_cases=0,actual_Native_cases=0,global_writer_closure=False,
    production_go=False,independent_acceptance=False)


def archive(path,expected,report):
    raw=Path(path).read_bytes();exact(pin(raw),expected,'CATALOG_ROOT_CANONICAL_FULL_BYTES')
    with zipfile.ZipFile(path)as z:
        names=z.namelist();exact(len(names),3,'CATALOG_ROOT_THREE_CANONICAL_MEMBERS')
        exact(len(set(names)),3,'CATALOG_ROOT_NO_DUPLICATE_MEMBERS')
        for name in names:safe_path(name)
        require(z.testzip()is None,'CATALOG_ROOT_CRC')
        exact(set(names),{report,'MODEL_POSTGRES_IMAGE.json','MODEL_SOURCE_IDENTITY.json'},'CATALOG_ROOT_EXACT_ORIGINAL_NAMES')
        docs={name:strict(z.read(name))for name in names};pins={name:pin(z.read(name))for name in names}
    exact(docs['MODEL_POSTGRES_IMAGE.json'],['postgres@sha256:00bc86618629af00d2937fdc5a5d63db3ff8450acf52f0636ec813c7f4902929'],'CATALOG_ROOT_ACTUAL_IMAGE')
    return docs[report],pins


def checked_api(value,head,tree,run,job,conclusion):
    fields(value['run'],dict(id=run,head_sha=head,run_attempt=1,event='push',status='completed',conclusion=conclusion),'CATALOG_ROOT_ACTUAL_TERMINAL')
    exact(value['run']['head_commit']['tree_id'],tree,'CATALOG_ROOT_ACTUAL_COMMIT_TREE')
    exact(value['jobs']['total_count'],1,'CATALOG_ROOT_ONE_OWNING_JOB')
    fields(value['jobs']['jobs'][0],dict(id=job,run_id=run,head_sha=head,status='completed',conclusion=conclusion),'CATALOG_ROOT_ACTUAL_JOB')


def intake(root,old_path,new_path,old_api,new_api):
    checked_api(old_api,'8e41633f7f4a6dc4406c0000e90afde7f703f8f8','ac968a55dd726f2676495a1515aa41b8341b33bf',41371274977,125042063644,'failure')
    checked_api(new_api,HEAD,TREE,41372699346,125046367770,'success')
    old,oldpins=archive(old_path,OLD_ZIP,'CATALOG_LOCK_BARRIER_NEW7.json')
    fresh,newpins=archive(new_path,NEW_ZIP,'CATALOG_QUIESCENCE_FOCUSED3.json')
    fields(old,dict(status='FAIL',error='CATALOG_MODEL_ACTUAL_PRIOR_PG_PROC_WRITER',cleanup_errors=[],all_opened_connections_closed=True,**NO_CREDIT),'CATALOG_ROOT_FAILED_FIRST_RUN_PRESERVED')
    exact(tuple(x['id']for x in old['cases']),OLD_IDS,'CATALOG_ROOT_EXACT_RETAINED_FOUR')
    for row,catalog in zip(old['cases'],('pg_proc','pg_proc','pg_authid','pg_auth_members')):
        fields(row,dict(status='PASS',actual_held_locks=[[catalog,'ShareLock',True]],
            lock_timeout_sqlstate='55P03',same_statement_succeeded_after_commit=True,
            worker_probe_rolled_back=True,model_rows_sequence_function_ACL_role_membership_equal=True),'CATALOG_ROOT_RETAINED_BLOCKING_MECHANICS')
        block=row['blocked'];require(block['holder_pid']!=block['worker_pid']and block['holder_pid']in block['blockers'],'CATALOG_ROOT_DISTINCT_ACTUAL_BLOCKING_PIDS')
    fields(fresh,dict(status='PASS',actual_new_primitive_cases=3,retained_original_run=41371274977,
        retained_original_completed_cases=4,original_run_relabelled_PASS=False,retained_catalog4_NOT_rerun=True,
        retained_relation_primitive9_NOT_rerun=True,cleanup_errors=[],all_opened_connections_closed=True,
        global_barrier_requires_no_other_permanent_transaction_ID_locks_in_addition_to_catalog_locks=True,
        catalog_SHARE_alone_does_NOT_close_preexisting_catalog_writer=True,**NO_CREDIT),'CATALOG_ROOT_FRESH_THREE_ONLY')
    exact(tuple(x['id']for x in fresh['cases']),NEW_IDS,'CATALOG_ROOT_EXACT_FRESH_THREE_IDS')
    require(all(x['status']=='PASS'for x in fresh['cases']),'CATALOG_ROOT_ALL_FRESH_CASES_PASS')
    baseline=fresh['model_baseline'];exact(fresh['model_final'],baseline,'CATALOG_ROOT_FULL_FINAL_MODEL_EQUALITY')
    first,second,third=fresh['cases'];observation=fresh['preexisting_writer_observation']
    require(first['writer_pid']!=first['guarded_pid']and first['writer_pid']==observation['writer_pid'],'CATALOG_ROOT_FRESH_DISTINCT_WRITER')
    fields(first,dict(catalog_SHARE_alone_admitted=True,uncommitted_function_result_not_visible=1,
        quiescence_refusal=dict(sqlstate='55P03',message='CATALOG_PREEXISTING_TRANSACTION_REVIEW_AGAIN')),'CATALOG_ROOT_PREEXISTING_WRITER_ACTUALLY_REFUSED')
    exact(first['actual_other_granted_transaction_ID_locks'],observation['actual_other_granted_transaction_ID_locks'],'CATALOG_ROOT_RETAINED_RAW_LOCK_OBSERVATION')
    require(any(row==[first['writer_pid'],str(int(first['writer_xid'])%4294967296),'ExclusiveLock',True,False]
        for row in first['actual_other_granted_transaction_ID_locks']),'CATALOG_ROOT_ACTUAL_PERMANENT_XID_LOCK')
    exact(first['actual_model_before_refusal'],baseline,'CATALOG_ROOT_BEFORE_EFFECT_BASELINE')
    exact(first['actual_model_after_rollback'],baseline,'CATALOG_ROOT_FIRST_ROLLBACK')
    exact(second['catalog_tables'],second['actual_held_catalog_tables'],'CATALOG_ROOT_EVERY_DECLARED_CATALOG_ACTUALLY_HELD')
    exact(len(set(second['catalog_tables'])),64,'CATALOG_ROOT_ACTUAL_ALL64_PG_CATALOG_TABLES')
    require({'pg_proc','pg_authid','pg_auth_members','pg_cast','pg_operator','pg_type','pg_policy','pg_event_trigger'}<=set(second['catalog_tables']),'CATALOG_ROOT_AUTHORITY_AND_DISPATCH_CATALOGS')
    fields(second,dict(actual_preexisting_transaction_ID_locks=[],existing_function_result=1,
        actual_uncommitted_worker_rows=[[1,'allowed ordinary model DML']],actual_model_after_rollback=baseline),'CATALOG_ROOT_ORDINARY_DML_AND_FULL_RESTORATION')
    require(second['holder_pid']!=second['worker_pid'],'CATALOG_ROOT_SECOND_REAL_TWO_BACKENDS')
    fields(third,dict(actual_SET_empty_identifier='""',actual_set_config_empty_path='',
        original_metadata_error_cause_not_claimed_proven=True),'CATALOG_ROOT_ACTUAL_EMPTY_PATH_DISTINCTION')
    with GitBytes(root,HEAD,TREE)as g:
        declaration=strict(g.read(NS+'SOURCE.json'));exact(len(declaration['files']),5,'CATALOG_ROOT_FIVE_SOURCE_PINS')
        for name,expected in declaration['files'].items():g.verify_pin(name,expected)
        exact(fresh['source']['head'],HEAD,'CATALOG_ROOT_REPORT_ACTUAL_PUBLIC_HEAD')
        exact(fresh['source']['tree'],TREE,'CATALOG_ROOT_REPORT_ACTUAL_PUBLIC_TREE')
        exact(fresh['source']['manifest'],pin(g.read(NS+'SOURCE.json')),'CATALOG_ROOT_EXACT_MANIFEST')
        origin=strict(g.read(NS+'FOCUSED3_TXLOCK_REPAIR_ORIGIN.json'));text=g.read(NS+'focused3.py').decode()
        exact(len(origin['routes']),8,'CATALOG_ROOT_EXACT_EIGHT_REPAIR_ROUTES')
        for route in reversed(origin['routes']):
            exact(text.count(route['after']),route['count'],'CATALOG_ROOT_EXACT_REPAIR_REVERSE')
            text=text.replace(route['after'],route['before'],route['count'])
        exact(pin(text.encode()),origin['before'],'CATALOG_ROOT_COMPLETE_ORIGINAL_209_FOCUSED_SOURCE_RECOVERED')
        exact(pin(g.read(NS+'probe.py')),declaration['retained_original_probe'],'CATALOG_ROOT_ORIGINAL_PROBE_UNCHANGED')
    return dict(status='ROOT_VERIFIED_REAL_PG17_CATALOG_PRIMITIVES_RETAINED4_FRESH3_NOT_ERP_CLOSURE',
        retained_run_id=41371274977,failed_first_focused_run_id=41372155092,focused_actual_success_run_id=41372699346,
        focused_head=HEAD,focused_tree=TREE,fresh_cases=3,retained_cases=4,logical_primitive_coverage=7,
        fresh7_one_attempt=False,prior_runs_aggregated=True,failed_runs_relabelled_PASS=False,
        retained_relation_primitive9_NOT_rerun=True,retained_catalog4_NOT_rerun=True,
        first4_raw_model_snapshots_not_retained_and_not_independently_recomputed=True,
        fresh3_raw_baseline_rows_sequence_function_OID_definition_ACL_equality_recomputed=True,
        exact_all64_catalog_ShareLocks_observed=True,preexisting_writer_XID_ExclusiveLock_and_refusal_observed=True,
        snapshot_xip_empty_is_NOT_quiescence=True,original_probe_unchanged=True,
        source_actual_public_head_and_tree_verified=True,reader_source=pin(Path(__file__).read_bytes()),
        old_archive=OLD_ZIP,new_archive=NEW_ZIP,
        old_originals=oldpins,new_originals=newpins,actual_global_adapter_installed=False,**NO_CREDIT)


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in('source','old-archive','new-archive','old-api','new-api','output'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();require(not a.output.exists(),'CATALOG_ROOT_NEW_RECEIPT')
    value=intake(a.source,a.old_archive,a.new_archive,strict(a.old_api.read_bytes()),strict(a.new_api.read_bytes()))
    a.output.write_text(json.dumps(value,indent=2)+'\n')
    print(json.dumps({k:value[k]for k in('status','fresh_cases','retained_cases','logical_primitive_coverage','fresh7_one_attempt')}))
