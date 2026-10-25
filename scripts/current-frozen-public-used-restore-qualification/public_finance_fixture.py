"""Committed official finance from the existing real Native opening/sale/return.

No direct financial fixture, synthetic report, manual cron or new policy.
Private capture steps are explicit Native SQL qualification, not actual cron.
"""
import importlib.util
import json
import uuid
from pathlib import Path
import cp7_ow11_analog_choice_cases as analog

path=Path(__file__).resolve().parents[1]/'current-frozen-public-native-qualification/public_finance_cases.py'
spec=importlib.util.spec_from_file_location('bounded_finance_restore_cases',path)
native=importlib.util.module_from_spec(spec);spec.loader.exec_module(native)
staged,finance=native.staged,native.finance


def request(cur,key,query):
    return staged.checked(staged.limited(cur,'erp_cp7_request_bounded_finance_analysis_v1',
        (json.dumps(dict(query,finance_mode='STAGED')),key)),key)


def prepare(cur,query,report):
    before=analog.plan.monetary_state(cur);key=str(uuid.uuid4())
    initial=request(cur,key,query)
    pending=native.sidecar(initial,key,'RUNNING');cid=pending['capture']['capture_id']
    row=staged.job_row(cur,key)
    assert row['query']==query and row['reference']['finance_sidecar_mode']=='STAGED'
    assert row['reference']['bounded_request_contract']=='cp7.bounded-analysis-request.v2'
    done,calls=staged.drive(cur,key)
    assert done['state']=='DONE',done
    native.sidecar(done,key,'RUNNING')
    operational,pages,meta=staged.fetch(cur,done['run_id'])
    assert operational['financial_source']is None
    ready,trail=native.run_capture(cur,cid)
    assert ready['state']=='READY'and ready['failure_code']is None
    source=finance.call(cur,'select cp7_finance_capture.result(%s)',(cid,))
    signature,counts=finance.independent_signature(cur,source['dates']['as_of'])
    assert signature==source['book_signature']
    assert counts=={family:source['capture']['plan'][family]['rows']for family in finance.FAMILIES}
    official=finance.official(cur,source['dates'])
    for part in('performance','financial_position','basis','data_confidence'):
        assert source['report']['snapshot'][part]==official['snapshot'][part],part
    status=staged.status(cur,key);sidecar=native.sidecar(status,key,'READY')
    wanted,readiness=finance.metrics(cur,source)
    observed={m['metric_id']:m['value']for m in sidecar['result']['metrics']}
    assert wanted==observed and sidecar['result']['readiness']==readiness
    assert all('value'not in value for value in observed.values()if value['state']=='UNKNOWN')
    assert analog.plan.monetary_state(cur)==before
    capture=native.stored_capture(cur,cid)
    assert capture['actor']==row['actor']and capture['owner_id']==row['id']and capture['query']==query
    assert source['dates']['as_of']==cur.execute("select(%s::timestamptz at time zone 'Asia/Jakarta')::date::text",
        (row['reference']['captured_at'],)).fetchone()[0]
    assert request(cur,key,query)==status and native.stored_capture(cur,cid)==capture
    report['public_frozen_finance_before_full_used_backup']=dict(request_id=key,job_id=row['id'],capture_id=cid,
        exact_actor_job_query_capture_date=True,official_sections_equal=True,official_metric_count=len(wanted),
        independent_book_signature=True,unknown_without_zero=True,operational_steps=len(calls),
        finance_steps=len(trail),private_capture_steps_not_actual_cron=True,physical_stock_money_HPP_unchanged=True)
    return dict(key=key,query=query,run_id=done['run_id'],capture_id=cid,capture=capture,
        source=source,status=status,operational=operational,pages=pages,page_meta=meta)


def assert_restored(cur,held,report,label):
    before=analog.plan.monetary_state(cur)
    old=native.stored_capture(cur,held['capture_id'])
    assert old==held['capture'],'RESTORED_FINANCE_CAPTURE_CHANGED'
    status=staged.status(cur,held['key']);native.sidecar(status,held['key'],'READY')
    assert status==held['status'],'RESTORED_FINANCE_STATUS_CHANGED'
    assert request(cur,held['key'],held['query'])==held['status'],'RESTORED_FINANCE_REPLAY_CHANGED'
    source=finance.call(cur,'select cp7_finance_capture.result(%s)',(held['capture_id'],))
    assert source==held['source'],'RESTORED_FINANCE_REPORT_OR_PROVENANCE_CHANGED'
    original,pages,meta=staged.fetch(cur,held['run_id'])
    assert(original,pages,meta)==(held['operational'],held['pages'],held['page_meta'])
    assert native.stored_capture(cur,held['capture_id'])==old
    assert cur.execute("select count(*)from cp7_finance_capture.captures where owner_kind='STAGED_ANALYSIS'and owner_id=%s",
        (held['status']['job_id']if'job_id'in held['status']else old['owner_id'],)).fetchone()[0]==1
    assert analog.plan.monetary_state(cur)==before
    report.setdefault('public_frozen_finance_full_restore_checks',[]).append(dict(label=label,
        exact_capture_report_provenance_and_operational_pages=True,READY_read_and_same_UUID_replay=True,
        captures_for_job=1,physical_stock_money_HPP_unchanged=True))
