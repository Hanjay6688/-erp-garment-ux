"""Exact current SKU27 success intake; no ERP/DB/browser/runtime imports."""
from pathlib import Path
from copy import deepcopy
from hashlib import sha256
import argparse,json
from intake_common import GitBytes,exact,fields,pin,require,original_zip,digest
from intake_sku27 import strict,literal,group,raw_evidence,declared_files,full_census,CASE,MAIN,NATIVE,COST,PACKAGE,FILES,RESTORE,NS

HEAD='090b85d3fcb738d3e694d4329d306f199a686eb8'
TREE='e04831b441bed987cd72ff738cf2a06a7c0ef0ae'
RUN=41167734749
JOB=124438845597
ARTIFACT=13031164777
ARCHIVE=dict(bytes=94781660,sha256='9ad923d20d0972b2a01df3ce3307bf03db537406ac89f99f700cf6d235bfc341')
GATES=dict(installed=True,primary_unchanged=True,backup_restore_drill=True,security_advisors=True,writer_runtime=True)
COUNTS=dict(actual_Native_cases=12,base_Native_cases=7,cost_Native_cases=5,actual_two_session_races=3,
    actual_Native_session_permission_waits=7,actual_Native_nonblocking_busy_cases=1,
    actual_Auth_HTTP_cases=0,actual_browser_cases=4,group_recovery_supported=False)


def source(g):
    own=strict(g.read(NS+'SOURCE.json'))
    fields(own,dict(base_head='f3d014648d12279dfa89ca8593f25585430a5efe',
        base_tree='b1c316d6e853805f933a6665a81edf9332d12a36',base_file_count=13759,
        frozen_original23_callbacks_edited=0,original_23_ids_retained=True,actual_successor_cases=0,
        group_recovery_supported=False,production_go=False,independent_acceptance=False),'CURRENT_SOURCE_SCOPE')
    exact(len(own['files']),131,'CURRENT_131_SOURCE_PINS')
    for name,expected in own['files'].items():g.verify_pin(name,expected)
    base=g.entries(own['base_head']);exact(len(base),13759,'EXACT_PARENT_FILE_COUNT')
    parent=strict(g.read(NS+'PARENT_SOURCE.json'));exact(set(parent['files']),set(base),'EXACT_PARENT_PINSET')
    for name,entry in base.items():
        exact(g.tree.get(name),entry,'UNCHANGED_PARENT_BLOB_MODE:'+name)
        exact({k:parent['files'][name][k]for k in('mode','blob')},entry,'PARENT_DECLARED_BLOB_MODE:'+name)
    delta=set(g.tree)-set(base)
    exact(delta,set(own['allowed_changes']),'EXACT_CURRENT_NAMESPACE_CLOSURE')
    exact(delta,set(own['files'])|{NS+'SOURCE.json'},'EXACT_CURRENT_132_PATHS')
    ids={
        'native':list(literal(g,'scripts/current-sku-pair-conversion-qualification/cases.py','IDS')),
        'cost':list(literal(g,'scripts/current-sku-group-cost-qualification/cases.py','IDS'))+list(literal(g,NS+'recovery_cases.py','IDS')),
        'races':list(literal(g,'scripts/current-sku-pair-conversion-qualification/races.py','IDS')),
        'waits':list(literal(g,'scripts/current-sku-pair-conversion-qualification/auth_waits.py','IDS'))+[literal(g,NS+'recovery_sessions.py','IDS')[0]],
        'busy':[literal(g,NS+'recovery_sessions.py','IDS')[1]],
        'browser':list(literal(g,'scripts/current-sku-combined-followup-qualification/plan.py','BROWSER_IDS')),
    }
    exact([len(v)for v in ids.values()],[7,5,3,7,1,4],'EXACT_CURRENT_CASE_GROUPS')
    exact(len(set(x for rows in ids.values()for x in rows)),27,'EXACT_27_UNIQUE_CASES')
    return ids,dict(manifest=pin(g.read(NS+'SOURCE.json')),source_pins=131,unchanged_parent_blobs_and_modes=13759,
        whole_parent_physical_bytes_reread=False,parent_git_blob_identity_reused=True,declared_current_paths=132)


def summary(docs,ids):
    main,package,restore=(docs[name]for name in(MAIN,PACKAGE,RESTORE));part=main['committed'][CASE]
    fields(main,dict(status='PASS',qualification_commit=HEAD,required_case_ids=[CASE],required_case_ids_pass=True,
        real_Auth_browser_claim=True,actual_business_cases=27,baseline_full22_all_rows_all_sequences_equal=True,
        restore_raw_public_equal=True,cp6_restored=True,baseline_advisors_equal=True,advisor_gate=True,
        used_guard_refused_before_DDL=True,scheduler_quiet_before_baseline_restore=True,
        production_go=False,independent_acceptance=False,**COUNTS),'EXACT_CURRENT_PASS_OUTER')
    exact(set(main['committed']),{CASE},'ONE_CURRENT_COMPOSITE')
    fields(part,dict(status='PASS',business_counts={'PASS':27},used_guard_refused_before_DDL=True,**COUNTS),'ALL_27_SAME_RUN')
    all_ids=[name for rows in ids.values()for name in rows]
    exact(part['business_cases'],{name:{'status':'PASS'}for name in all_ids},'EVERY_27_BUSINESS_CASE_PRESENT')
    exact(main.get('error'),None,'NO_HIDDEN_OUTER_ERROR');exact(main.get('restore_error'),None,'NO_HIDDEN_RESTORE_ERROR')
    browser=part['fresh_real_Auth_browser4']['browser']
    fields(part['fresh_real_Auth_browser4'],dict(status='PASS'),'BROWSER_COMPONENT_PASS')
    fields(browser,dict(status='RUN_COMPLETE',counts={'PASS':4},planned_case_ids=ids['browser'],real_auth=True,
        jwt_signed_by_runtime=False,host_exit=0,host_status='RUN_COMPLETE',console_errors=0,users_created=4,
        auth_cleanup_failures=[],host_error=None,session_leaks=[],cleanup_failures=False,database_remaining=0,
        auth_counts=dict(before=[0,0,0,0],after=[0,0,0,0],restored=True),
        cleanup=dict(users_created=0,cleanup_failures=[],rest_remaining=False)),'EXACT_FOUR_REAL_AUTH_BROWSER_AND_CLEANUP')
    exact(list(browser['cases']),ids['browser'],'FOUR_EXACT_BROWSER_CASES')
    for row in browser['cases'].values():fields(row,dict(status='PASS'),'EVERY_BROWSER_PASS')
    for value in(browser,part['fresh_callbacks11']['concurrency']):
        require(not value.get('business_day_retried')and not value.get('business_day_first_attempt'),'ONE_FIRST_ATTEMPT_ONLY')
    exact(package['gate'],GATES,'ALL_FIVE_PACKAGE_GATES')
    fields(package,dict(status='ALL_STAGES_INSTALLED',primary_unchanged=True,auth_users_before=0,auth_users_after=0,
        backup_restore_drill='RESTORED_IDENTICAL',production_go=False),'PRIMARY_AUTH_AND_BACKUP')
    fields(package['run_identity'],dict(tool_head=HEAD,github_sha=HEAD,run_id=str(RUN),run_attempt='1',mode='install'),'EXACT_SINGLE_CURRENT_RUN')
    fields(restore,dict(status='RESTORED_IDENTICAL'),'COMPLETE_BACKUP_DRILL')
    require(all(type(v)is bool and v for v in restore['checks'].values()),'ALL_TYPED_BACKUP_CHECKS')
    exact(restore['data']['differ'],{},'NO_RESTORE_ROW_DIFFERENCE')
    fields(main['baseline_restore'],dict(unexplained=[],only_pg_cron_errors=True,database_owner_acl_and_settings_preserved=True),'COMPLETE_OUTER_RESTORE')
    fields(main['baseline_role_cleanup'],dict(baseline_roles_exact=True),'COMPLETE_ROLE_RESTORE')
    return part,browser


def intake(root,archive):
    with GitBytes(root,HEAD,TREE)as g,original_zip(archive,ARCHIVE,170)as z:
        ids,src=source(g);names=(MAIN,NATIVE,COST,PACKAGE,FILES,RESTORE)
        docs={name:strict(z.read(name))for name in names};part,browser=summary(docs,ids)
        exact(browser['script_sha256'],sha256(g.read(NS+'cases.mjs')).hexdigest(),'EXACT_EXECUTED_CURRENT_BROWSER_SCRIPT')
        for key,name in(('fresh_base_native7',NATIVE),('fresh_cost_native5',COST)):
            exact(part[key]['native'],docs[name],'SAME_RUN_RAW_NATIVE_ORIGINAL')
        group(docs[NATIVE],ids['native']);group(docs[COST],ids['cost'])
        fields(part['fresh_base_native7'],dict(status='PASS',actual_Native_cases=7,used_guard_refused_before_DDL=True),'FRESH_NATIVE7')
        fields(part['fresh_cost_native5'],dict(status='PASS',actual_cost_Native_cases=5),'FRESH_COST5')
        callbacks=part['fresh_callbacks11']['concurrency'];callback_ids=ids['races']+ids['waits']+ids['busy']
        fields(callbacks,dict(status='RUN_COMPLETE',counts={'PASS':11},planned_race_ids=callback_ids,
            database_remaining=0,copy_per_race=True),'EXACT_ELEVEN_CURRENT_CALLBACKS')
        exact(list(callbacks['races']),callback_ids,'EXACT_CALLBACK_ORDER')
        for row in callbacks['races'].values():
            fields(row,dict(status='PASS',session_leaks=[]),'EVERY_CALLBACK_PASS')
            fields(row['installed_baseline_restoration'],dict(complete_database_dump_restored=True,
                all22_all_rows_all_sequences_roles_exact=True,cp6_restored=True,advisors_equal=True,
                selected_table_cleanup=False),'EVERY_FULL_COPY_RESTORED')
        for index,name in enumerate(ids['races']):
            row=callbacks['races'][name]
            fields(row,dict(same_uuid=index==0,first_commit=index!=2,one_group_exactly_two_Native_parts=True,
                source=dict(physical=6,reserved=1,available=5),target=dict(physical=8,reserved=0,available=8)),'RACE_EXACT_POSTCONDITIONS')
            contention=row['contention']
            if index==0:
                fields(contention,dict(kind='BLOCKED',holder_blocks_worker=True),'SAME_UUID_REAL_WAIT')
                exact(row['outcome']['result'],row['holder'],'EXACT_COMPLETE_UUID_REPLAY')
            else:
                fields(contention,dict(kind='FAIL_FAST',holder_blocks_worker=False,distinct_actual_backend_pids=True,
                    holder_in_transaction_at_refusal=True,retry_only_after_holder_release=True,
                    same_request_and_payload_retried=True,holder_committed=index==1),'EXACT_POCKET_CONTENTION')
                a,b=contention['holder_backend_pid'],contention['worker_backend_pid']
                require(type(a)is type(b)is int and a>0 and b>0 and a!=b,'TWO_REAL_BACKENDS')
                fields(contention['first_attempt'],dict(ok=False,sqlstate='P0001'),'POCKET_BUSY_REFUSAL')
                require(contention['first_attempt']['message'].startswith('POCKET_PERIOD_BUSY:'),'EXACT_POCKET_BUSY_ERROR')
        busy=callbacks['races'][ids['busy'][0]]
        fields(busy,dict(declared_cases=1,distinct_busy_attempts=2,complete_noeffect_each_attempt=True),'ONE_BUSY_CASE_BOTH_DOMAINS')
        exact([r['busy_holder']for r in busy['attempts']],['FG','MATERIAL_NONE'],'BOTH_BUSY_LOCK_DOMAINS')
        for row in busy['attempts']:fields(row,dict(two_actual_backends=True,nonblocking_busy_refused_while_holder_still_held=True),'ACTUAL_NONBLOCKING_REFUSAL')
        cache=callbacks['races'][ids['waits'][-1]]
        fields(cache,dict(two_actual_backends=True,completed_UUID_replay=True,actual_request_row_blocking_observed=True),'CURRENT_PERMISSION_AFTER_WAIT')
        fields(cache['answer'],dict(ok=False,sqlstate='42501'),'WITHDRAWN_PERMISSION_REFUSED')
        handoff=part['Native_to_copy_handoff'];fields(handoff,dict(all22_exact=True,committed_Native_business_rows_and_sequences_unchanged=True,
            source_all_rows_sequences_unchanged_after_callbacks=True),'ACTUAL_NATIVE_TO_COPY_HANDOFF')
        exact(handoff['full_data_and_sequences_before_handoff'],handoff['full_data_and_sequences_after_callbacks'],'FULL_HANDOFF_ROWS_SEQUENCES')
        census=full_census(handoff['raw_current_catalog'],handoff['full_data_and_sequences_before_handoff'])
        actual_digest=sha256(json.dumps(handoff['raw_current_catalog'],sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
        exact(actual_digest,handoff['raw_current_catalog_sha256'],'RAW_HANDOFF_CATALOG_DIGEST')
        exact(handoff['every_race_copy_exact_admission_sha256'],[actual_digest]*11,'ALL11_COPY_HANDOFF_CHAIN')
        follow=part['fresh_callbacks11'];ui=part['fresh_real_Auth_browser4']
        exact(len(follow['copy_catalog_admissions']),11,'EXACT_ELEVEN_COPY_ADMISSIONS');exact(len(ui['copy_catalog_admissions']),1,'ONE_BROWSER_COPY')
        for row in follow['copy_catalog_admissions']+ui['copy_catalog_admissions']:
            fields(row,dict(full22_after_must_equal_original_install=True,product_state_modified=False,
                Native_or_schema_or_RPC_permissions_changed=False,all22_groups_equal_original_install=True,
                exact_catalog_sha256=actual_digest),'EXACT_ACTUAL_COPY_CATALOG')
            exact(row['actual_copy_after_authority'],row['source_database_authority'],'COPY_AUTHORITY_RESTORED')
        raw=raw_evidence(z,part)
        declaration=docs[MAIN]['source_declaration'];source_maps=declared_files(g,declaration['current_installation'])
        fields(declaration['full_source_closure'],dict(unchanged_parent_files=13759,parent_sql_exceptions=0,
            current_physical_sources=True,financial_quantity_fullcensus_oracles_changed=False),'ACTUAL_FULL_SOURCE_CLOSURE')
        fields(docs[FILES],dict(status='ALL_FILES_INSTALLED'),'ALL_PACKAGE_FILES')
        require(all(row==dict(key=row['key'],status='PASS')for row in docs[FILES]['files']),'EACH_PACKAGE_FILE_PASS')
        controls=[]
        for label,change in(
            ('failed_outer',lambda d:d[MAIN].__setitem__('status','INCOMPLETE')),
            ('missing_fifth_gate',lambda d:d[PACKAGE]['gate'].__setitem__('writer_runtime',False)),
            ('missing_Auth_restore',lambda d:d[MAIN]['committed'][CASE]['fresh_real_Auth_browser4']['browser']['auth_counts'].__setitem__('restored',False)),
            ('float_not_exact_count',lambda d:d[MAIN]['committed'][CASE]['business_counts'].__setitem__('PASS',27.0)),
        ):
            changed=deepcopy(docs);change(changed)
            try:summary(changed,ids)
            except(ValueError,KeyError,TypeError)as error:controls.append(dict(name=label,refusal=str(error)))
            else:raise ValueError('NEGATIVE_ROOT_CONTROL_ACCEPTED:'+label)
        return dict(status='ROOT_VERIFIED_CURRENT_SKU27_ALL5',head=HEAD,tree=TREE,run_id=RUN,job_id=JOB,
            artifact_id=ARTIFACT,archive=dict(ARCHIVE,members=170),originals={name:pin(z.read(name))for name in names},
            source=src,actual_product_source_maps=source_maps,case_ids=ids,observed_counts=dict(PASS=27),
            browser_counts=browser['counts'],package_gates=docs[PACKAGE]['gate'],handoff_census=census,
            raw_evidence=raw,negative_controls=controls,complete27_qualified=True,package_all_five=True,
            prior_runs_aggregated=False,outer_restore_source_bound_receipts=True,outer_raw_before_after_not_serialized=True,
            actual_Auth_HTTP_case_credit=0,combined_S03_SKU_S05_runtime_qualified=False,
            production_go=False,independent_acceptance=False)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    for name in('source','archive','output'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();result=intake(args.source,args.archive)
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({key:result[key]for key in('status','observed_counts','complete27_qualified','package_all_five')}))
