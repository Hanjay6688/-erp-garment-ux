"""Committed OW05 use, exact read/replay and named inverses after fresh restore."""
from decimal import Decimal as D
import json
import uuid

from cp7_contractor_correction import native_cases as n
import cp7_nota_cases as nota
import cp7_settlement_cases as payroll

def sewing(cur,p,request,expected):
    n.auth.actor(cur)
    r=n.one(cur,'select public.erp_cp7_save_sewing_completion_v1(%s,%s,%s)',(json.dumps(p),str(request),expected))
    n.auth.b.api.admin(cur);return r

def record(cur,g,choice):
    w=n.old.sewing_workspace(cur,g);key=str(uuid.uuid4())
    p=dict(action='RECORD',group_id=g['group'],qty_pcs='4',physical_at=g['at'](10).isoformat(),
        review_token=w['review_token'],change_reason='OW05 committed restore journey')
    if choice is not None:p['rate_choice']=choice
    result=sewing(cur,p,key,w['group_version'])
    return dict(payload=p,request=key,expected=w['group_version'],result=result)

def prepare(cur,today):
    g=n.fixture(cur,today,True);w=n.workspace(cur,g['po']);p=n.payload(w,g['target']);key=str(uuid.uuid4())
    correction=n.command(cur,p,key);posted=record(cur,g,'NEW')
    assert D(str(posted['result']['result']['wage_amount']))==D('24.00')
    note_payload=nota.payload(cur,dict(contractor=g['target']),today)
    note_payload.update(period_start=str(g['day']),period_end=str(today))
    save_key=str(uuid.uuid4());saved=nota.command(cur,'SAVE',note_payload,key=save_key)
    post_payload=dict(id=saved['note_id'],change_reason='OW05 committed restore nota24');post_key=str(uuid.uuid4())
    note=nota.command(cur,'POST',post_payload,saved['row_version'],post_key)
    assert D(payroll.doc(cur,note['payroll_id'])['net_payable'])==D('24.00')
    item=dict(g=g,correction_payload=p,correction_request=key,correction=correction,sewing=posted,
        nota_save_payload=note_payload,nota_save_request=save_key,nota_saved=saved,
        nota_post_payload=post_payload,nota_post_request=post_key,nota_posted=note,today=today)
    return item

def read(cur,item):
    g=item['g'];n.auth.b.api.admin(cur)
    result=dict(workspace=n.workspace(cur,g['po']),
        history=cur.execute('select to_jsonb(h)from cp7_contractor_correction.history_v1 h where po_id=%s order by generation_no',(g['po'],)).fetchall(),
        requests=cur.execute("select to_jsonb(r)from cp7_contractor_correction.requests_v1 r where payload->>'po_id'=%s order by request_id",(g['po'],)).fetchall(),
        works=cur.execute('select to_jsonb(w)from erp.work_completion_events w where po_id=%s order by id',(g['po'],)).fetchall(),
        work_lines=cur.execute('select to_jsonb(l)from erp.work_completion_lines l join erp.work_completion_events w on w.id=l.completion_id where w.po_id=%s order by l.id',(g['po'],)).fetchall(),
        payroll=n.one(cur,'select to_jsonb(p)from erp.payroll_settlements p where id=%s',(item['nota_posted']['payroll_id'],)),
        old_payable=str(-n.balance(cur,g['po'],'CONTRACTOR_PAYABLE',g['mandor'])),
        new_payable=str(-n.balance(cur,g['po'],'CONTRACTOR_PAYABLE',g['target'])),
        WIP_increment=str(n.balance(cur,g['po'],'WIP')-g['base_wip']),
        old_work=n.one(cur,'select to_jsonb(w)from erp.work_completion_events w where id=%s',(g['completion'],)),
        context_count=n.one(cur,'select count(*)from cp7_contractor_correction.context_v1'))
    assert result['old_payable']=='0.00'and result['new_payable']=='24.00'and result['WIP_increment']=='24.00'
    assert len(result['history'])==len(result['requests'])==1 and result['context_count']==0
    return result

def replay(cur,item):
    assert n.command(cur,item['correction_payload'],item['correction_request'])==item['correction']
    s=item['sewing'];assert sewing(cur,s['payload'],s['request'],s['expected'])==s['result']
    assert nota.command(cur,'SAVE',item['nota_save_payload'],key=item['nota_save_request'])==item['nota_saved']
    assert nota.command(cur,'POST',item['nota_post_payload'],item['nota_saved']['row_version'],item['nota_post_request'])==item['nota_posted']

def inverses(cur,item):
    g=item['g'];old_read=read(cur,item)
    payroll.act(cur,'CANCEL',payroll.doc(cur,item['nota_posted']['payroll_id']))
    terminal=n.one(cur,"select id::text from erp.sewing_terminal_events e where po_id=%s and event_kind='SELESAI_DIJAHIT'and not exists(select 1 from erp.sewing_terminal_events r where r.reversal_of_id=e.id)",(g['po'],))
    n.old.sewing_command(cur,n.old.sewing_workspace(cur,g),event=terminal)
    target=g['target'];original=g['mandor'];w=n.workspace(cur,g['po']);assert w['eligible']
    before=n.one(cur,'select cp7_contractor_correction.financial_fingerprint_v1(%s)',(g['po'],))
    response=n.command(cur,n.payload(w,original))
    assert n.one(cur,'select cp7_contractor_correction.financial_fingerprint_v1(%s)',(g['po'],))==before
    assert response['status']=='PICKUPS_REPLACED';again=record(cur,g,None)
    assert D(str(again['result']['result']['wage_amount']))==D('16.00')
    assert n.balance(cur,g['po'],'CONTRACTOR_PAYABLE',target)==0
    assert n.balance(cur,g['po'],'CONTRACTOR_PAYABLE',original)==D('-16.00')
    assert n.one(cur,'select to_jsonb(w)from erp.work_completion_events w where id=%s',(g['completion'],))==old_read['old_work']
    generations=cur.execute('select generation_no from cp7_contractor_correction.history_v1 where po_id=%s order by generation_no',(g['po'],)).fetchall()
    assert len(generations)==2 and generations[0][0]<generations[1][0]
    assert n.one(cur,'select count(*)from cp7_contractor_correction.context_v1')==0
    return dict(status='PASS',restored_nota24_cancelled_through_Native=True,restored_wage24_undone=True,
        next_generation_after_restore=True,current_original_mandor_payable='16.00',previous_mandor_payable='0.00',
        original_history_unchanged=True,history_generations=2,private_contexts=0)
