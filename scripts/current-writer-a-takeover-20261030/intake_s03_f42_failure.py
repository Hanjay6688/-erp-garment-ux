"""Read-only intake; a failed Browser4 is never promoted by partial successes."""
from pathlib import Path
from hashlib import sha256
import argparse,ast,gzip,json,re
from intake_common import GitBytes,exact,fields,pin,original_zip
from intake_sku27 import strict

HEAD='f42e76978852ba9efe34f75a4b622990c0331866'
TREE='489f35012ae17821afc9c138a7dc64cb024d5cd4'
ARCHIVE=dict(bytes=527507908,sha256='8c3c3f435d1ecf7de032e9bc42ec93de9056d8c36e0520c9756e9a683d9fe68c')
MAIN='CP7_S03_MOUNTED_FULL_APP_BROWSER4.json'

def intake(root,archive):
    with GitBytes(root,HEAD,TREE)as g,original_zip(archive,ARCHIVE,217)as z:
        raw=z.read(MAIN);main=strict(raw);browser=main['committed']['S03_MOUNTED_FULL_APP_AUTH_BROWSER4']['browser']
        fields(main,dict(status='INCOMPLETE',qualification_commit=HEAD,required_case_ids_pass=False,
            baseline_full22_all_rows_all_sequences_equal=True,restore_raw_public_equal=True,cp6_restored=True,
            baseline_advisors_equal=True,advisor_gate=True,production_go=False,independent_acceptance=False),'FAILED_ACTUAL_RESTORED')
        evidence=g.read('scripts/current-attendance-choice-browser4-lawful-successor/evidence.mjs').decode()
        ids=ast.literal_eval(re.search(r'export const IDS\s*=\s*(\[.*?\])',evidence,re.S).group(1))
        exact(browser['planned_case_ids'],ids,'EXACT_CURRENT_BROWSER4');exact(list(browser['cases']),ids,'ONE_CURRENT_ATTEMPT')
        exact([browser['cases'][key]['status']for key in ids],['PASS','PASS','PASS','INCOMPLETE'],'THREE_PASS_ONE_INCOMPLETE')
        fields(browser,dict(status='INCOMPLETE',counts={'PASS':3,'INCOMPLETE':1},host_exit=0,host_status='RUN_COMPLETE',
            database_remaining=0,console_errors=0,auth_cleanup_failures=[],session_leaks=[],
            auth_counts=dict(before=[0,0,0,0],after=[0,0,0,0],restored=True)),'ACTUAL_CLEANUP')
        package=strict(z.read('T3_PACKAGE_INSTALL.json'))
        exact(package['gate'],dict(installed=True,primary_unchanged=True,backup_restore_drill=True,
            security_advisors=True,writer_runtime=False),'NO_FIFTH_GATE')
        fields(package['run_identity'],dict(tool_head=HEAD,github_sha=HEAD,run_id='41168528689',run_attempt='1'),'ONE_EXACT_RUN')
        first_name=next(name for name in z.namelist()if '_ACCESS_'in name and name.endswith('_FIRST_FAILURE.json'))
        first_raw=z.read(first_name);first=strict(first_raw)
        assert 'TypeError: fetch failed'in first['error'] and 'cases.mjs:131:2'in first['error']
        transitions=first['progress']['current_rights_transitions'];exact(len(transitions),1,'FIRST_DEMOTION_ONLY')
        fields(transitions[0],dict(status='ACTUAL_PUBLIC_ROLE_TRANSITION_VERIFIED',role='ADMIN'),'FIRST_ADMIN_TRANSITION')
        boundary=[]
        for label in ('012_AFTER_SAME_JWT_ADMIN_DENIALS','013_AFTER_AUTHORIZED_ROLE_OWNER','014_AFTER_ACCESS_ROLE_REPLAY_OWNER'):
            name=next(name for name in z.namelist()if label in name)
            state=strict(gzip.decompress(z.read(name)));rows=state['all_rows']
            exact(len(state['all22']),22,'COMPLETE_RAW_CATALOG_GROUPS')
            subject=next(row for row in rows['erp.app_users']if row['auth_user_id']==first['fixture']['owner'])
            audit=[row for row in rows['erp.app_access_audit']if row['entity_id']==subject['id']]
            requests=[row for row in rows['erp.idempotency_requests']if row['operation_name']=='save_app_user_v2']
            boundary.append(dict(label=label,raw_archive_member=name,packed=pin(z.read(name)),
                member_utc=list(z.getinfo(name).date_time),subject_role=subject['role'],subject_version=subject['row_version'],
                audit=[{key:row[key]for key in('client_request_id','changed_at','action')}for row in audit],
                requests=[{key:row[key]for key in('client_request_id','created_at','status')}for row in requests]))
        exact([row['subject_role']for row in boundary],['ADMIN','OWNER','OWNER'],'LAWFUL_CLEANUP_RESTORED_OWNER')
        exact([row['subject_version']for row in boundary],[2,3,3],'ONE_CLEANUP_MUTATION')
        exact([len(row['audit'])for row in boundary],[1,2,2],'NO_DUPLICATE_ROLE_AUDIT')
        exact([len(row['requests'])for row in boundary],[1,2,2],'NO_DUPLICATE_ROLE_IDEMPOTENCY')
        return dict(status='ROOT_VERIFIED_CURRENT_S03_BROWSER4_INCOMPLETE',head=HEAD,tree=TREE,
            run_id=41168528689,job_id=124441234727,artifact_id=13032507966,archive=dict(ARCHIVE,members=217),
            main_original=pin(raw),case_statuses={key:browser['cases'][key]['status']for key in ids},
            first_failure=dict(name=first_name,raw=pin(first_raw),member_utc=list(z.getinfo(first_name).date_time),error=first['error']),
            actual_access_boundaries=boundary,package_gates=package['gate'],outer_restore_source_bound_receipts=True,
            real_Auth_cleanup_restored=True,complete_browser4_qualified=False,package_all_five=False,
            transport_error_cause_not_serialized=True,exact_transport_root_cause_confirmed=False,
            local_idle_socket_hypothesis_reproduced=False,prior_runs_aggregated=False,
            fresh_composite_case_credit=0,production_go=False,independent_acceptance=False)

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    for name in('source','archive','output'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();result=intake(args.source,args.archive);args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({key:result[key]for key in('status','complete_browser4_qualified','package_all_five','exact_transport_root_cause_confirmed')}))
