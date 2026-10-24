"""Explicit bounded official-finance qualification; original legacy suite untouched.

Business fixtures post through retained Native writers. Operational public
calls retain their ordinary 8s limit. Private finance steps run as the capture
owner with the requesting actor's claims, never as a fabricated HTTP login.
"""
import json
import uuid

import cp7_p19_staged_cases as staged
from cp7_finance_capture import cases as finance

IDS=('OW12_BOUNDED_FINANCE_REQUEST_EXACT_ONCE',
     'OW12_BOUNDED_FINANCE_OPERATIONAL_FIRST_OFFICIAL_FINANCE',
     'OW12_BOUNDED_FINANCE_CHANGED_BOOK_REFUSED',
     'OW12_BOUNDED_FINANCE_DEFERRED_NO_CAPTURE',
     'OW12_BOUNDED_FINANCE_CURRENT_FINANCE_ACCESS')


def setup(cur,today):
    staged.analysis.setup(cur,today)
    return finance.given(cur,today)


def request(cur,today,key,mode='STAGED',subject=None):
    q=staged.query(today)
    rpc='erp_cp7_request_bounded_staged_analysis_v1'
    if mode is not None:
        q['finance_mode']=mode;rpc='erp_cp7_request_bounded_finance_analysis_v1'
    job=staged.checked(staged.limited(cur,rpc,(json.dumps(q),key),subject),key)
    row=staged.job_row(cur,key,subject)
    assert row['reference']['bounded_request_contract']=='cp7.bounded-analysis-request.v1'
    if 'finance_capture'in job:
        assert job['finance_capture']['job_id']==row['id']
        assert job['finance_capture']['query']==row['query']
        assert row['reference']['finance_sidecar_mode']=='STAGED'
    return job


def sidecar(job,key,state=None):
    value=job['finance_capture']
    assert value['contract_version']=='cp7.analysis-finance-sidecar.v1'
    assert value['request_id']==str(key)and str(uuid.UUID(value['job_id']))==value['job_id']
    assert value['reference']==job['reference']
    assert value['production_go']is False
    if state is not None:assert value['state']==state,value
    if value['state']!='READY':assert value['result']is None
    if value['capture']is not None:
        assert value['capture']['owner_kind']=='STAGED_ANALYSIS'
        assert value['capture']['owner_id']==value['job_id']
    return value


def stored_capture(cur,cid):
    staged.b.api.admin(cur)
    return cur.execute('select to_jsonb(c)from cp7_finance_capture.captures c where id=%s',(cid,)).fetchone()[0]


def run_capture(cur,cid,subject=None,once=False):
    prior=cur.execute('show statement_timeout').fetchone()[0]
    cur.execute("set local statement_timeout='8s'")
    try:return finance.step(cur,cid,subject)if once else finance.run(cur,cid,subject)
    finally:
        if cur.connection.info.transaction_status!=finance.TransactionStatus.INERROR:
            cur.execute('select set_config(\'statement_timeout\',%s,true)',(prior,))


def cases(cur,today):
    def exact_once():
        setup(cur,today);key=uuid.uuid4()
        job=request(cur,today,key);s=sidecar(job,key,'RUNNING');cid=s['capture']['capture_id']
        before=stored_capture(cur,cid)
        replay=request(cur,today,key);assert replay['finance_capture']['job_id']==s['job_id']
        assert sidecar(replay,key,'RUNNING')==s and stored_capture(cur,cid)==before
        count=cur.execute("select count(*)from cp7_finance_capture.captures where owner_kind='STAGED_ANALYSIS'and owner_id=%s",(s['job_id'],)).fetchone()[0]
        assert count==1
        refusal=staged.auth.refused(cur,lambda:request(cur,today,key,None),'CP7_ANALYSIS_REQUEST_CHANGED')
        assert stored_capture(cur,cid)==before
        return dict(status='PASS',one_job_one_capture=True,lost_response_UUID_replay_exact=True,
            changed_finance_mode_refused=refusal,capture_id=cid)

    def official_finance():
        posting=setup(cur,today);key=uuid.uuid4();job=request(cur,today,key)
        s=sidecar(job,key,'RUNNING');cid=s['capture']['capture_id']
        done,calls=staged.drive(cur,key)
        assert done['state']=='DONE',done
        pending=sidecar(done,key,'RUNNING');assert pending['capture']['units_done']==0
        original,pages,page_stats=staged.fetch(cur,done['run_id'])
        assert original['financial_source']is None
        ready,trail=run_capture(cur,cid);assert ready['state']=='READY',ready
        job=staged.status(cur,key);result=sidecar(job,key,'READY')['result']
        source=finance.call(cur,'select cp7_finance_capture.result(%s)',(cid,))
        signature,counts=finance.independent_signature(cur,source['dates']['as_of'])
        assert signature==source['book_signature']
        assert counts=={fam:source['capture']['plan'][fam]['rows']for fam in finance.FAMILIES}
        official=finance.official(cur,source['dates'])
        for part in('performance','financial_position','basis','data_confidence'):
            assert source['report']['snapshot'][part]==official['snapshot'][part],part
        wanted,readiness=finance.metrics(cur,source)
        observed={m['metric_id']:m['value']for m in result['metrics']}
        assert observed==wanted and result['readiness']==readiness
        assert result['capture_id']==cid and result['source_hash']==source['source_hash']
        assert result['dates']==source['dates']and result['report_read_at']==ready['report_read_at']
        assert wanted and all(source['source_hash']in json.dumps(v['refs'])for v in observed.values())
        unknown=[name for name,value in observed.items()if value['state']=='UNKNOWN']
        assert all('value'not in observed[name]for name in unknown)
        again,after,after_stats=staged.fetch(cur,done['run_id'])
        assert again==original and after['header']==pages['header']and after['pages']==pages['pages']
        assert after['identity_hash']==pages['identity_hash']and after_stats==page_stats
        return dict(status='PASS',operational_done_while_finance_running=True,
            official_sections_equal=True,official_metric_count=len(wanted),readiness=readiness,
            unknown_metric_ids=unknown,unknown_never_zero=True,independent_book_signature=True,
            sealed_operational_original_unchanged=True,finance_steps=len(trail),
            operational_steps=len(calls),page_stats=page_stats,kasbon_number=posting['kasbon']['number'])

    def changed_book():
        setup(cur,today);key=uuid.uuid4();job=request(cur,today,key)
        cid=sidecar(job,key,'RUNNING')['capture']['capture_id']
        first=run_capture(cur,cid,once=True);assert first['state']=='RUNNING'and first['units_done']==1
        later=finance.given(cur,today,'900.00')
        failed,trail=run_capture(cur,cid)
        assert failed['state']=='FAILED'and failed['failure_code']=='CP7_FINANCE_CAPTURE_SOURCE_CHANGED'
        current=sidecar(staged.status(cur,key),key,'FAILED')
        assert current['capture']['failure_code']=='CP7_FINANCE_CAPTURE_SOURCE_CHANGED'
        assert current['result']is None and stored_capture(cur,cid)['source_hash']is None
        refusal=staged.auth.refused(cur,lambda:finance.call(cur,'select cp7_finance_capture.result(%s)',(cid,)),
            'CP7_FINANCE_CAPTURE_NOT_READY')
        return dict(status='PASS',book_changed_by_real_posting=later['kasbon']['number'],
            failure_code=failed['failure_code'],result_refused=refusal,no_stale_financial_result=True)

    def deferred():
        setup(cur,today)
        before=cur.execute('select count(*)from cp7_finance_capture.captures').fetchone()[0]
        key=uuid.uuid4();job=request(cur,today,key,None)
        assert 'finance_capture'not in job
        original_job=staged.job_row(cur,key)['id']
        replay=request(cur,today,key,None)
        assert replay==job and staged.job_row(cur,key)['id']==original_job
        staged.auth.refused(cur,lambda:request(cur,today,key),'CP7_ANALYSIS_REQUEST_CHANGED')
        staged.auth.refused(cur,lambda:request(cur,today,uuid.uuid4(),'DEFERRED'),
            'CP7_BOUNDED_FINANCE_EXPLICIT_STAGED_REQUIRED')
        staged.auth.refused(cur,lambda:staged.limited(cur,'erp_cp7_request_bounded_finance_analysis_v1',
            (json.dumps(staged.query(today)),uuid.uuid4())),'CP7_BOUNDED_FINANCE_EXPLICIT_STAGED_REQUIRED')
        done,calls=staged.drive(cur,key);assert done['state']=='DONE'and 'finance_capture'not in done
        original,pages,stats=staged.fetch(cur,done['run_id'])
        assert original['financial_source']is None
        assert cur.execute('select count(*)from cp7_finance_capture.captures').fetchone()[0]==before
        return dict(status='PASS',old_three_field_route_stays_deferred=True,explicit_finance_mode_required=True,both_cross_mode_UUIDs_refused=True,no_capture_created=True,
            operational_original_readable=True,operational_steps=len(calls),page_stats=stats)

    def current_access():
        setup(cur,today);subject,role=finance.finance_cases.admin_actor(cur,staged.analysis)
        key=uuid.uuid4();job=request(cur,today,key,subject=subject)
        cid=sidecar(job,key,'RUNNING')['capture']['capture_id']
        ready,_=run_capture(cur,cid,subject);assert ready['state']=='READY',ready
        sidecar(staged.status(cur,key,subject),key,'READY')
        sealed=stored_capture(cur,cid)
        cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='finance.reports.view'",(role,))
        assert cur.rowcount==1
        hidden=sidecar(staged.status(cur,key,subject),key,'ACCESS_REVOKED')
        assert hidden['capture']is None and hidden['result']is None
        refusal=staged.auth.refused(cur,lambda:request(cur,today,uuid.uuid4(),subject=subject),
            'CP7_ANALYSIS_FINANCE_ACCESS_CHANGED')
        replay_refusal=staged.auth.refused(cur,lambda:request(cur,today,key,subject=subject),
            'CP7_ANALYSIS_FINANCE_ACCESS_CHANGED')
        assert stored_capture(cur,cid)==sealed
        return dict(status='PASS',current_permission_hides_progress_and_result=True,
            new_request_refused=refusal,old_UUID_replay_refused=replay_refusal,sealed_history_unchanged=True)

    return list(zip(IDS,(exact_once,official_finance,changed_book,deferred,current_access)))
