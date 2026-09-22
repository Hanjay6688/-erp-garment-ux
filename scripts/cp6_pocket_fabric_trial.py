"""Warehouse-only pocket fabric outflow: real stock, expense, recost, inverse."""
from datetime import timedelta
from decimal import Decimal as D
import json,uuid
import cp6_initial_import_receipt_trial as receipts
from cp6_initial_import_advance_trial import ledger


def call(a,cur,action,payload,key=None):
    a.ordinary(cur)
    r=cur.execute('select public.erp_save_pocket_fabric_action_v1(%s,%s::jsonb,%s)',(action,json.dumps(payload,default=str),key or uuid.uuid4())).fetchone()[0]
    a.admin(cur);return r


def read(a,cur,query=''):
    a.ordinary(cur);r=cur.execute('select public.erp_get_pocket_fabric_workspace_v1(%s)',(query,)).fetchone()[0];a.admin(cur);return r


def fixture(a,cur,today,register=True):
    f=receipts.fixture(a,cur,today,True);r=receipts.finalize(a,cur,f)
    if register:
        before=ledger(cur);call(a,cur,'REGISTER',dict(material_id=r['material_id'],reason='Universal pocket fabric'))
        assert ledger(cur)==before
    return {**r,'code':f['code']}


def payload(a,cur,r,today,mode='USED',quantity='5'):
    roll=next(x for x in read(a,cur,r['code'])['rolls'] if x['id']==str(r['roll_id']))
    return dict(roll_id=roll['id'],location_id=roll['location_id'],expected_revision=roll['revision'],mode=mode,
        quantity=quantity,date=str(today-timedelta(days=5)),reason='Shared pocket fabric; no mandor or product allocation')


def truth(cur):
    receipts.truth(cur)
    rows=cur.execute("select check_name,issue_count from erp.run_v267_financial_truth_checks() where check_name like 'AP_POCKET_%'").fetchall()
    assert len(rows)==3 and all(n==0 for _,n in rows),rows
    assert cur.execute('select count(*) from erp.pocket_fabric_execution_context').fetchone()==(0,)
    return dict(rows)


def effects(cur):
    book=ledger(cur)
    return {k:book.get(str(cur.execute('select erp.account_id(%s)',(k,)).fetchone()[0]),D(0))
      for k in ['MATERIAL_INVENTORY','OTHER_EXPENSE','WIP','FG_INVENTORY','COGS']}


def lifecycle(a,cur,today,mode,closed):
    cur.execute("set local timezone='Pacific/Kiritimati'" if closed else "set local timezone='UTC'")
    r=fixture(a,cur,today);before=ledger(cur);start=effects(cur)
    p=payload(a,cur,r,today,mode,'15' if mode=='REMAINING' else '5');key=uuid.uuid4()
    if closed:receipts.rpc(a,cur,'close_accounting_through',today-timedelta(days=2),'Close pocket economic date')
    result=call(a,cur,'POST',p,key);assert result['status']=='POSTED'
    boundary=a.actors.boundary(cur);assert call(a,cur,'POST',p,key)==result and a.actors.boundary(cur)==boundary
    w=read(a,cur,r['code']);assert w['rolls'][0]['qty']=='15.000000' and w['history'][0]['current_cost']=='11.25',w
    after=effects(cur);assert after['MATERIAL_INVENTORY']-start['MATERIAL_INVENTORY']==D('-11.25') and after['OTHER_EXPENSE']-start['OTHER_EXPENSE']==D('11.25')
    assert all(after[k]==start[k] for k in ['WIP','FG_INVENTORY','COGS']);truth(cur)
    date=cur.execute("select economic_date,transaction_date from erp.journal_entries where source_type='MATERIAL_ADJUSTMENT' and source_id=%s",(result['id'],)).fetchone()
    assert date==(today-timedelta(days=5),today if closed else today-timedelta(days=5)),date
    invoice=receipts.invoice(a,cur,today,r,20,'3');receipts.post_invoice(a,cur,invoice)
    after=effects(cur);assert read(a,cur,r['code'])['history'][0]['current_cost']=='15.00'
    assert after['OTHER_EXPENSE']-start['OTHER_EXPENSE']==15 and all(after[k]==start[k] for k in ['WIP','FG_INVENTORY','COGS']);truth(cur)
    h=read(a,cur,r['code'])['history'][0]
    call(a,cur,'REVERSE',dict(id=h['id'],expected_version=h['row_version'],reason='Restore the roll'))
    w=read(a,cur,r['code']);assert w['rolls'][0]['qty']=='20.000000' and w['history'][0]['current_cost']=='0.00';truth(cur)
    receipts.rpc(a,cur,'reverse_material_supplier_invoice',invoice['supplier_invoice_id'],'Restore original benchmark')
    assert ledger(cur)==before;truth(cur)
    return dict(status='PASS',mode=mode,closed=closed,initial_stock='20',issued='5',remaining='15',expense='11.25',recost_expense='15.00',product_hpp_unchanged=True,replay_exact=True,all_accounts_restored=True)


def refusal(a,cur,today,kind):
    r=fixture(a,cur,today);p=payload(a,cur,r,today)
    if kind=='STALE':call(a,cur,'POST',p)
    elif kind=='OVER':p['quantity']='20.000001'
    elif kind=='NEGATIVE':p['quantity']='-1'
    elif kind=='PRECISION':p['quantity']='0.0000001'
    elif kind=='NUMBER':p['quantity']=5
    elif kind=='FUTURE':p['date']=str(today+timedelta(days=1))
    elif kind=='BEFORE_RECEIPT':p['date']=str(today-timedelta(days=40))
    elif kind=='COUNT_BEFORE_MOVEMENT':p['mode']='REMAINING';p['quantity']='15';p['date']=str(today-timedelta(days=9))
    elif kind=='WRONG_LOCATION':p['location_id']=str(uuid.uuid4())
    elif kind=='NOT_POCKET':
        other=fixture(a,cur,today,False);p['roll_id']=other['roll_id'];p['location_id']=other['location_id']
    elif kind=='ZERO':p['quantity']='0'
    else:raise AssertionError(kind)
    before=ledger(cur);boundary=a.actors.boundary(cur)
    a.inherited.refused(cur,lambda:call(a,cur,'POST',p))
    assert ledger(cur)==before and a.actors.boundary(cur)==boundary;truth(cur)
    return dict(status='PASS',refusal=kind,atomic=True)


def protections(a,cur,today):
    r=fixture(a,cur,today);p=payload(a,cur,r,today,mode='REMAINING',quantity='0')
    saved=call(a,cur,'POST',p);assert read(a,cur,r['code'])['rolls']==[]
    original=cur.execute('select to_jsonb(u) from erp.pocket_fabric_usage u where adjustment_id=%s',(saved['id'],)).fetchone()[0]
    j=cur.execute("select id from erp.journal_entries where source_type='MATERIAL_ADJUSTMENT' and source_id=%s",(saved['id'],)).fetchone()[0]
    m=cur.execute("select m.id from erp.material_stock_movements m join erp.material_adjustment_items i on i.id=m.source_id where m.source_type='MATERIAL_ADJUSTMENT_ITEM' and i.adjustment_id=%s",(saved['id'],)).fetchone()[0]
    before=ledger(cur)
    a.inherited.refused(cur,lambda:receipts.rpc(a,cur,'reverse_journal',j,'Unlinked reverse'))
    a.inherited.refused(cur,lambda:receipts.rpc(a,cur,'reverse_material_movement',m,'Unlinked reverse'))
    a.inherited.refused(cur,lambda:cur.execute('update erp.pocket_fabric_usage set input_quantity=1 where adjustment_id=%s',(saved['id'],)))
    h=read(a,cur,r['code'])['history'][0]
    a.inherited.refused(cur,lambda:call(a,cur,'REVERSE',dict(id=h['id'],expected_version='0',reason='Stale inverse')))
    assert ledger(cur)==before
    call(a,cur,'REVERSE',dict(id=h['id'],expected_version=h['row_version'],reason='Linked inverse'))
    assert cur.execute('select to_jsonb(u) from erp.pocket_fabric_usage u where adjustment_id=%s',(saved['id'],)).fetchone()[0]==original
    assert read(a,cur,r['code'])['rolls'][0]['qty']=='20.000000';truth(cur)
    return dict(status='PASS',empty_roll_supported=True,generic_journal_and_stock_inverse_refused=True,source_immutable=True)


def authorization(a,cur,today):
    r=fixture(a,cur,today);p=payload(a,cur,r,today);key=uuid.uuid4();call(a,cur,'POST',p,key)
    backup=uuid.uuid4()
    cur.execute("insert into auth.users(id,aud,role,email) values(%s,'authenticated','authenticated',%s)",(backup,'pocket-backup-'+backup.hex+'@example.test'))
    cur.execute("insert into erp.app_users(id,auth_user_id,full_name,role,role_id,is_active) select gen_random_uuid(),%s,'Pocket backup owner','OWNER',id,true from erp.app_roles where role_code='OWNER'",(backup,))
    cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(a.base.OPERATOR_AUTH,))
    before=ledger(cur)
    a.inherited.refused(cur,lambda:read(a,cur))
    a.inherited.refused(cur,lambda:call(a,cur,'POST',p,key))
    assert ledger(cur)==before
    return dict(status='PASS',revoked_actor_cannot_read_or_replay=True)


def cases(a,cur,today):
    return [('POCKET_LIFECYCLE:'+m+':'+str(c),lambda m=m,c=c:lifecycle(a,cur,today,m,c)) for m in ['USED','REMAINING'] for c in [False,True]]+[
      ('POCKET_REFUSAL:'+k,lambda k=k:refusal(a,cur,today,k)) for k in ['STALE','OVER','NEGATIVE','PRECISION','NUMBER','FUTURE','BEFORE_RECEIPT','COUNT_BEFORE_MOVEMENT','WRONG_LOCATION','NOT_POCKET','ZERO']]+[
      ('POCKET_PROTECTIONS',lambda:protections(a,cur,today)),('POCKET_AUTHORIZATION',lambda:authorization(a,cur,today))]
