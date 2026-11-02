"""Typed future Native FREE3 and complete package gate; pending stays closed."""
from pathlib import Path
from decimal import Decimal
from datetime import date,datetime,time,timedelta
from zoneinfo import ZoneInfo
import importlib.util,json,subprocess

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
MAIN='CP7_CURRENT_COMPLETE_DE_FREE_DATE_NATIVE3.json'
RAW='CP7_CURRENT_COMPLETE_DE_FREE_DATE_NATIVE3_CASES.json'
CASE='CURRENT_COMPLETE_DE_FREE_DATE_NATIVE3'


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def money(value):
    if type(value)is not str:raise ValueError('FREE_DATE_RAW_DECIMAL_TEXT_REQUIRED')
    result=Decimal(value)
    if not result.is_finite():raise ValueError('FREE_DATE_RAW_FINITE_AMOUNT_REQUIRED')
    return result


def posted(p,snapshot,issue,at):
    if(type(snapshot)is not dict or not {'header','items','free_provenance'}<=set(snapshot)
       or type(snapshot['items'])is not list or type(snapshot['free_provenance'])is not list):
        raise ValueError('FREE_DATE_RAW_POSTED_SNAPSHOT_STRUCTURE_REQUIRED')
    p.fields(snapshot['header'],dict(id=issue,status='POSTED'),'FREE_DATE_RAW_POSTED_HEADER')
    actual=datetime.fromisoformat(snapshot['header']['physical_at'])
    expected=datetime.fromisoformat(at)
    if actual.utcoffset()is None or expected.utcoffset()is None or actual!=expected:
        raise ValueError('FREE_DATE_RAW_ORIGINAL_PHYSICAL_TIMESTAMP_REQUIRED')
    if len(snapshot['items'])!=1 or len(snapshot['free_provenance'])!=1:
        raise ValueError('FREE_DATE_RAW_ONE_FREE_LINE_AND_PROVENANCE_REQUIRED')
    item=snapshot['items'][0];provenance=snapshot['free_provenance'][0]
    p.fields(item,dict(issue_id=issue),'FREE_DATE_RAW_POSTED_ITEM_SOURCE')
    p.fields(provenance,dict(issue_id=issue,material_id=item['material_id']),
        'FREE_DATE_RAW_FREE_PROVENANCE_SOURCE')
    for key,expected in(('qty',Decimal(3)),('total_receivable',Decimal(0)),
                       ('manual_retail_unit_price',Decimal(0))):
        value=item[key]
        if type(value)not in(int,float,str)or money(str(value))!=expected:
            raise ValueError('FREE_DATE_RAW_SINGLE_FREE_ITEM_AMOUNT_OR_QUANTITY:'+key)
    if(type(provenance['category_id'])is not str or not provenance['category_id']
       or type(provenance['policy_version'])is not int or provenance['policy_version']<1):
        raise ValueError('FREE_DATE_RAW_EXPLICIT_CATEGORY_AND_POLICY_VERSION_REQUIRED')


def case_boundary(boundary):
    before=boundary['before'];after=boundary['after'];observed=boundary['after_operation']
    if(before['actual_all22']!=after['actual_all22']or len(before['actual_all22'])!=22):
        raise ValueError('FREE_DATE_CASE_ALL22_CATALOG_CHANGED')
    original=before['full_data_and_sequences'];restored=after['full_data_and_sequences']
    if({k:v for k,v in original.items()if not k.startswith('sequence:')}!=
       {k:v for k,v in restored.items()if not k.startswith('sequence:')}):
        raise ValueError('FREE_DATE_CASE_ALL_TABLE_ROWS_NOT_RESTORED')
    first={k:v for k,v in original.items()if k.startswith('sequence:')}
    last={k:v for k,v in restored.items()if k.startswith('sequence:')}
    audit='sequence:erp.audit_logs_id_seq'
    if(set(first)!=set(last)or set(first)!=set(observed['sequences'])or audit not in first):
        raise ValueError('FREE_DATE_CASE_ALL_SEQUENCE_MEMBERS_REQUIRED')
    if last!=observed['sequences']:
        raise ValueError('FREE_DATE_CASE_ROLLBACK_CHANGED_SEQUENCE_VALUES')
    if any(first[k]!=last[k]for k in first if k!=audit):
        raise ValueError('FREE_DATE_CASE_UNEXPECTED_NON_AUDIT_SEQUENCE_CHANGE')
    for value in(first[audit],last[audit]):
        if(type(value)is not list or len(value)!=2 or type(value[0])is not str
           or type(value[1])is not bool or not value[0].isdecimal()
           or str(int(value[0]))!=value[0]or int(value[0])<1):
            raise ValueError('FREE_DATE_CASE_TYPED_AUDIT_SEQUENCE_REQUIRED')
    ids=observed['audit_ids'];count=observed['audit_row_count']
    minimum=int(first[audit][0])+(1 if first[audit][1]else 0)
    if(type(ids)is not list or not ids or type(count)is not int
       or any(type(v)is not str for v in ids)
       or ids!=[str(minimum+i)for i in range(len(ids))]
       or last[audit]!=[ids[-1],True]
       or count!=original['erp.audit_logs'][0]+len(ids)):
        raise ValueError('FREE_DATE_CASE_AUDIT_ADVANCE_REQUIRES_EVERY_ACTUAL_INSERTED_ID')
    return dict(classification='AUDITED_NATIVE_SEQUENCE_CONSUMPTION_NOT_TRANSACTIONAL_RESTORE',
        audit_sequence_increments=len(ids),all_table_rows_restored=True,all22_catalog_exact=True,
        all_other_sequences_unchanged=True,rollback_sequence_values_unchanged=True,
        case_sequence_reset_performed=False,complete_outer_backup_sequence_restore_required=True)


def gate(directory,head):
    load('free_date_actual_parent_before_report_read',HERE/'admission.py').parent_receipt()
    p=load('free_date_exact_original_typed_report_gate',
        ROOT/'scripts/current-s03-sku-s05-composite-qualification/parents.py')
    source=load('free_date_exact_three_source_ids',HERE/'native_free.py').source_controls()
    ids=source['case_ids']
    main=p.strict((directory/MAIN).read_bytes());raw=p.strict((directory/RAW).read_bytes())
    package=p.strict((directory/'T3_PACKAGE_INSTALL.json').read_bytes())
    supervised=load('free_date_own_process_supervision',HERE/'runtime_controls.py').receipt(p,
        p.strict((directory/'FREE_DATE_RUNTIME_SUPERVISION.json').read_bytes()),head,package['run_identity']['run_id'])
    backup=p.strict((directory/'T3_BACKUP_RESTORE_DRILL.json').read_bytes())
    value=validate(p,main,raw,package,backup,ids,head)
    value['runtime_supervision']=supervised
    return value


def validate(p,main,raw,package,backup,ids,head):
    p.fields(main,dict(status='PASS',qualification_commit=head,required_case_ids=[CASE],required_case_ids_pass=True,
        actual_Native_cases=3,actual_browser_cases=0,actual_business_cases=3,actual_Auth_HTTP_cases=0,
        actual_two_session_races=0,retained_DE30_fresh_case_credit=0,real_Auth_browser_claim=False,
        real_Auth_HTTP_qualified=False,baseline_full22_all_rows_all_sequences_equal=True,restore_raw_public_equal=True,
        cp6_restored=True,baseline_advisors_equal=True,advisor_gate=True,used_guard_refused_before_DDL=True,
        production_go=False,independent_acceptance=False),'FREE_DATE_NATIVE3_AND_FULL_RESTORE')
    p.exact(set(main['committed']),{CASE},'FREE_DATE_ONE_CURRENT_COMPONENT')
    part=main['committed'][CASE]
    p.fields(part,dict(status='PASS',business_counts={'PASS':3},actual_Native_cases=3,
        actual_browser_cases=0,actual_Auth_HTTP_cases=0,actual_two_session_races=0,real_Auth=False,
        reader_remains_installed=True,retained_DE30_fresh_case_credit=0,used_guard_refused_before_DDL=True,
        GOOD_eligibility_policy_decided=False,Afui_GOOD_nonpayable_path_complete=False,
        global_writer_or_permission_or_lock_closure=False,production_go=False,independent_acceptance=False),
        'FREE_DATE_NO_RETAINED_OR_GOOD_OR_GLOBAL_CREDIT')
    p.exact(raw,part['native'],'FREE_DATE_RAW_NATIVE3_EQUALS_EMBEDDED')
    p.fields(raw,dict(status='PASS',counts={'PASS':3},planned_case_ids=ids,missing=[],
        final={key:'PASS'for key in ids},complete_boundary_restored=True),'FREE_DATE_THREE_CURRENT_STRICT_CASES')
    p.exact(list(raw['cases']),ids,'FREE_DATE_EXACT_CASE_ORDER')
    if raw.get('business_day_retried')or raw.get('business_day_first_attempt'):
        raise ValueError('FREE_DATE_SINGLE_REAL_BUSINESS_DAY_ATTEMPT_REQUIRED')
    for name,row in raw['cases'].items():
        p.fields(row,dict(status='PASS',full_boundary_restored=True,public_schema_unchanged=True,
            session_leaks=dict(advisory_locks=0,advisory_lock_keys=[],other_sessions=[])),
            'FREE_DATE_ORIGINAL_STRICT_CASE:'+name)
        if row.get('business_day_rollover'):raise ValueError('FREE_DATE_CASE_ROLLED_OVER:'+name)
        boundary=row['actual_full22_case_boundary']
        p.exact(boundary['verification'],case_boundary(boundary),
            'FREE_DATE_EVERY_CASE_AUDITED_SEQUENCE_CONSUMPTION_AND_ALL_ROWS:'+name)
    lookup,replay,history=[raw['cases'][key]for key in ids]
    p.fields(lookup,dict(actual_public_final_day_quotes=4,null_and_absent_ids_ineligible=True,
        product_clock_changed=False,GOOD_eligibility_policy_decided=False),'FREE_DATE_ACTUAL_NORMAL_PUBLIC_QUOTE')
    observations=lookup['actual_lookup_observations']
    if(len(observations)!=20 or [r['session_timezone']for r in observations]!=
       [name for name in('UTC','Asia/Jakarta','America/New_York','Pacific/Kiritimati')for _ in range(5)]):
        raise ValueError('FREE_DATE_ACTUAL_TWENTY_BOUNDARIES_REQUIRED')
    start=date.fromisoformat(lookup['policy_from']);end=date.fromisoformat(lookup['policy_to'])
    first=datetime.combine(start,time.min,ZoneInfo('Asia/Jakarta'))
    following=datetime.combine(end+timedelta(days=1),time.min,ZoneInfo('Asia/Jakarta'))
    points=[(first-timedelta(microseconds=1)).isoformat(),first.isoformat(),
        datetime.combine(end,time.min,ZoneInfo('Asia/Jakarta')).isoformat(),
        (following-timedelta(microseconds=1)).isoformat(),following.isoformat()]
    p.exact([r['at']for r in observations],points*4,'FREE_DATE_RAW_ACTUAL_POLICY_BOUNDARY_TIMESTAMPS')
    p.exact([r['expected_eligible']for r in observations],[False,True,True,True,False]*4,
        'FREE_DATE_INDEPENDENT_INCLUSIVE_BOUNDARY_ORACLE')
    for row in observations:
        if type(row['expected_eligible'])is not bool or (row['actual']is not None)!=row['expected_eligible']:
            raise ValueError('FREE_DATE_ACTUAL_ELIGIBILITY_MUST_MATCH_BOUNDARY')
    expected_basis=observations[1]['actual']
    if(type(expected_basis)is not dict or set(expected_basis)!={'category_id','policy_version'}
       or any(type(v)is not str or not v for v in expected_basis.values())):
        raise ValueError('FREE_DATE_ACTUAL_EXPLICIT_CATEGORY_AND_POLICY_BASIS_REQUIRED')
    for row in observations:
        if row['expected_eligible']:p.exact(row['actual'],expected_basis,'FREE_DATE_SAME_ACTUAL_BASIS_ALL_TIMEZONES')
    p.fields(replay,dict(replay_stock_GL_and_history_unchanged=True,original_normal_post_route=True,
        source_lines=1,paid_companion_lines=0,mandatory_PO_or_FG_match=False,product_clock_changed=False),
        'FREE_DATE_ORIGINAL_SINGLE_FREE_POST_AND_REPLAY')
    p.exact(replay['actual_posted_snapshot'],replay['actual_posted_snapshot_after_replay'],
        'FREE_DATE_REPLAY_RAW_POSTED_HISTORY')
    posted(p,replay['actual_posted_snapshot'],replay['issue_id'],replay['physical_at'])
    p.fields(replay['actual_replay_response'],dict(id=replay['issue_id'],status='POSTED'),
        'FREE_DATE_EXACT_REPLAY_OF_ORIGINAL_POST')
    p.exact(replay['account_balances_after_post'],replay['account_balances_after_replay'],
        'FREE_DATE_REPLAY_RAW_GL_NO_EFFECT')
    p.exact(replay['stock_after_post'],replay['stock_after_replay'],'FREE_DATE_REPLAY_RAW_STOCK_NO_EFFECT')
    if money(replay['stock_before'])-money(replay['stock_after_post'])!=3:
        raise ValueError('FREE_DATE_RAW_STOCK_DECREMENT_EXACT_THREE')
    before={k:money(v)for k,v in replay['account_balances_before'].items()}
    after={k:money(v)for k,v in replay['account_balances_after_post'].items()}
    p.exact(set(before),set(after),'FREE_DATE_RAW_ACCOUNT_SET')
    delta={k:after[k]-before[k]for k in before if after[k]!=before[k]}
    if(delta.get('MATERIAL_INVENTORY')!=Decimal('-6.00')or sum(delta.values(),Decimal(0))!=0
       or any(delta.get(k,0)!=0 for k in('CONTRACTOR_RECEIVABLE','CASH','BANK','OTHER_INCOME'))):
        raise ValueError('FREE_DATE_RAW_GL_COST_AND_NO_RECEIVABLE_OR_CASH')
    p.fields(history,dict(later_eligibility=None,stock_GL_and_posted_history_unchanged=True,
        posted_row_updates=0,policy_history_rewrites=0,GOOD_eligibility_policy_decided=False,
        product_clock_changed=False),'FREE_DATE_HISTORY_REMAINS_POSTED_AFTER_ELIGIBILITY_END')
    p.exact(history['actual_original_snapshot'],history['actual_posted_snapshot_after_read'],
        'FREE_DATE_LATER_READ_RAW_HISTORY_NO_EFFECT')
    posted(p,history['actual_original_snapshot'],history['issue_id'],history['original_physical_at'])
    p.fields(history['actual_public_document'],dict(id=history['issue_id'],status='POSTED'),
        'FREE_DATE_LATER_PUBLIC_READ_SAME_POSTED_DOCUMENT')
    p.exact(history['account_balances_before_read'],history['account_balances_after_read'],
        'FREE_DATE_LATER_READ_RAW_GL_NO_EFFECT')
    p.exact(history['stock_before_read'],history['stock_after_read'],'FREE_DATE_LATER_READ_RAW_STOCK_NO_EFFECT')
    used=part['separate_committed_Native_use']
    p.fields(used,dict(status='NATIVE_FREE_NOTE_COMMITTED',Native_case_credit=0,
        actual_used_inverse_error='SPECIAL_FREE_DATE_AFTER_USE_REQUIRES_FULL_BACKUP_RESTORE',
        original_normal_post_route=True,source_lines=1,paid_companion_lines=0,
        mandatory_PO_or_FG_match=False,product_clock_changed=False),'FREE_DATE_ACTUAL_COMMITTED_USED_REFUSAL')
    p.exact(used['before'],used['after'],'FREE_DATE_USED_INVERSE_RAW_NO_EFFECT')
    if len(used['before']['actual_all22'])!=22:raise ValueError('FREE_DATE_USED_REFUSAL_COMPLETE_RAW22_REQUIRED')
    p.exact(package['gate'],p.GATES,'FREE_DATE_ALL_FIVE_ACTUAL_PACKAGE_GATES')
    p.fields(package['run_identity'],dict(tool_head=head,github_sha=head,run_attempt='1'),
        'FREE_DATE_EXACT_CURRENT_OWNING_PACKAGE')
    p.fields(backup,dict(status='RESTORED_IDENTICAL'),'FREE_DATE_ACTUAL_BACKUP_DRILL')
    if not backup['checks']or any(type(v)is not bool or not v for v in backup['checks'].values()):
        raise ValueError('FREE_DATE_ALL_TYPED_BACKUP_CHECKS_REQUIRED')
    p.exact(backup['data']['differ'],{},'FREE_DATE_BACKUP_NO_ROW_DIFFERENCE')
    return dict(status='CURRENT_COMPLETE_DE_FREE_DATE_NATIVE3_AND_ALL5_PASS',head=head,actual_fresh_cases=3,
        actual_browser_cases=0,actual_Auth_HTTP_cases=0,actual_two_session_races=0,
        retained_DE30_fresh_case_credit=0,GOOD_eligibility_policy_decided=False,
        Afui_GOOD_nonpayable_path_complete=False,global_writer_or_permission_or_lock_closure=False,
        production_go=False,independent_acceptance=False)


if __name__=='__main__':
    load('free_date_actual_parent_before_final_report_gate',HERE/'admission.py').parent_receipt()
    value=gate(ROOT/'cp6-proof/t3',subprocess.check_output(['/usr/bin/git','-C',str(ROOT),
        'rev-parse','HEAD'],text=True).strip())
    (ROOT/'cp6-proof/t3/FREE_DATE_FINAL_GATE.json').write_text(json.dumps(value,indent=2)+'\n')
    print(json.dumps(value))
