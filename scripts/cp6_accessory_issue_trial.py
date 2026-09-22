"""Ordinary authenticated access to accessory draft/post/inverse public facades."""
from datetime import timedelta
from decimal import Decimal as D
import copy,json,uuid
import cp6_foundation_qualification as foundation

def call(a,cur,action,payload,key=None):
    a.ordinary(cur)
    result=cur.execute('select public.erp_save_accessory_issue_action_v1(%s,%s::jsonb,%s)',(action,json.dumps(payload,default=str),key or uuid.uuid4())).fetchone()[0]
    a.admin(cur);return result

def read(a,cur,filters):
    a.ordinary(cur);result=cur.execute('select public.erp_get_accessory_issue_workspace_v1(%s::jsonb)',(json.dumps(filters,default=str),)).fetchone()[0]
    a.admin(cur);return result

def fixture(a,cur,today,factor=12):
    a.admin(cur);cur.execute('grant usage on schema erp to authenticated')
    start=a.production.at(today-timedelta(days=2),0)
    model,contractor=cur.execute("select model_id,contractor_id from erp.production_orders where po_number='CP6-RACE-PO'").fetchone()
    foundation.OWNER=a.base.OPERATOR_AUTH
    foundation.MASTER=dict(model=model,contractor=contractor,start=start,supplier=cur.execute("select id from erp.suppliers where supplier_code='CP6-RACE-SUP'").fetchone()[0],pcs=cur.execute("select unit_code from erp.uom_definitions where upper(unit_code)='PCS' and dimension='COUNT'").fetchone()[0],t0=start+timedelta(hours=1),t3=start+timedelta(hours=4))
    a.production.prior.set_open_period(cur,today-timedelta(days=10));a.admin(cur)
    cat,uom=foundation.category(cur,factor);mat=foundation.material(cur,'ACCESSORY',cat);loc,other=foundation.locations(cur)
    purchase=foundation.purchase(cur,mat,loc,300,2,foundation.MASTER['t0']);a.admin(cur)
    price=cur.execute('insert into erp.contractor_accessory_price_versions(contractor_id,category_id,selling_price,selling_uom_code,effective_from) values(%s,%s,%s,%s,%s) returning id',(contractor,cat,D(factor)*3,uom,start)).fetchone()[0]
    cur.execute('revoke usage on schema erp from authenticated')
    p=dict(id=None,expected_version=None,number=foundation.tag(),contractor_id=str(contractor),location_id=str(loc),po_id=None,
        physical_at=str(today-timedelta(days=1))+'T10:15:00+07:00',notes='Synthetic connected retail',reason='Connected fixture',
        items=[dict(material_id=str(mat),qty='7',mode='MANUAL',manual_price='3.25')])
    w=read(a,cur,{k:p[k] for k in ('contractor_id','location_id','physical_at')})
    quote=next(m for m in w['materials'] if m['id']==str(mat));assert quote['stock']=='300.000000' and quote['factor']==str(factor)+'.000000'
    return dict(payload=p,quote=quote,material=mat,category=cat,price=price,location=loc,other=other,purchase=purchase)

def lifecycle(a,cur,today,factor=12,price='3.25'):
    f=fixture(a,cur,today,factor);p=f['payload'];p['items'][0]['manual_price']=price
    before=a.production.ledger(cur);a.admin(cur)
    master=cur.execute('select to_jsonb(p) from erp.contractor_accessory_price_versions p where id=%s',(f['price'],)).fetchone()[0]
    p['items'][0]['qty']='5';saved=call(a,cur,'SAVE_DRAFT',p)
    assert saved['status']=='DRAFT' and a.production.ledger(cur)==before
    p.update(id=saved['id'],expected_version=saved['row_version']);p['items'][0]['qty']='7'
    key=uuid.uuid4();posted=call(a,cur,'POST',p,key);assert posted['status']=='POSTED'
    state=a.actors.boundary(cur);assert call(a,cur,'POST',p,key)==posted and a.actors.boundary(cur)==state
    assert cur.execute('select cached_stock_qty from erp.materials where id=%s',(f['material'],)).fetchone()[0]==293
    item=cur.execute('select qty,transaction_qty,base_qty_per_transaction_uom,unit_sale_price_snapshot,total_receivable from erp.contractor_material_issue_items where issue_id=%s',(posted['id'],)).fetchone()
    assert item==(7,7,1,D(price),7*D(price)),item
    w=read(a,cur,dict(id=posted['id']));d=w['document'];assert d['total']==str((7*D(price)).quantize(D('.01'))) and d['row_version']==posted['row_version']
    charge=cur.execute("select coalesce(sum(l.debit),0) from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id where j.source_id=%s and j.source_type='CONTRACTOR_MATERIAL_RECEIVABLE'",(posted['id'],)).fetchone()[0]
    assert charge==7*D(price),charge
    assert cur.execute('select to_jsonb(p) from erp.contractor_accessory_price_versions p where id=%s',(f['price'],)).fetchone()[0]==master
    reverse=dict(id=posted['id'],expected_version=posted['row_version'],reason='Undo connected issue');rkey=uuid.uuid4()
    result=call(a,cur,'REVERSE',reverse,rkey);state=a.actors.boundary(cur)
    assert call(a,cur,'REVERSE',reverse,rkey)==result and a.actors.boundary(cur)==state
    assert result['status']=='REVERSED' and a.production.ledger(cur)==before
    assert cur.execute('select cached_stock_qty from erp.materials where id=%s',(f['material'],)).fetchone()[0]==300
    assert cur.execute('select qty,transaction_qty,base_qty_per_transaction_uom,unit_sale_price_snapshot,total_receivable from erp.contractor_material_issue_items where issue_id=%s',(posted['id'],)).fetchone()==item
    return dict(status='PASS',master_basis=factor,physical_pcs=7,price=price,charge=str(charge),latest_draft_used=True,master_unchanged=True,source_immutable=True,replay_exact=True,inverse_restores_all_accounts=True)

def master_lifecycle(a,cur,today):
    f=fixture(a,cur,today);p=f['payload'];q=f['quote'];p['items']=[dict(material_id=str(f['material']),qty='12',mode='MASTER',price_version_id=q['price_version_id'],factor=q['factor'])]
    r=call(a,cur,'POST',p);assert read(a,cur,dict(id=r['id']))['document']['total']=='36.00'
    assert cur.execute('select qty,manual_retail_unit_price,accessory_price_version_id from erp.contractor_material_issue_items where issue_id=%s',(r['id'],)).fetchone()==(12,None,f['price'])
    return dict(status='PASS',master_price_preserved=True,pcs=12,charge='36.00')

def refused(a,cur,today,kind):
    f=fixture(a,cur,today);p=f['payload'];line=p['items'][0];action='POST';needle=''
    if kind=='FRACTIONAL':line['qty']='7.0000001';needle='PCS utuh'
    elif kind=='NUMBER':line['qty']=7;needle='PCS utuh'
    elif kind=='PRICE_PRECISION':line['manual_price']='3.251';needle='dua desimal'
    elif kind=='PRICE_COMMA':line['manual_price']='3,25';needle='dua desimal'
    elif kind=='PRICE_NEGATIVE':line['manual_price']='-1';needle='nonnegatif'
    elif kind=='OVER_STOCK':line['qty']='301'
    elif kind=='EMPTY_LOCATION':p['location_id']=str(f['other'])
    elif kind=='FUTURE':p['physical_at']=str(today+timedelta(days=1))+'T10:15:00+07:00';needle='masa depan'
    elif kind=='BAD_DATE':p['physical_at']='2026-02-30T10:15:00+07:00'
    elif kind=='UNKNOWN_FIELD':line['unit_sale_price_snapshot']='0';needle='unexpected'
    elif kind=='DUPLICATE':p['items'].append(copy.deepcopy(line));needle='dua baris'
    elif kind=='STALE_PRICE':line.update(mode='MASTER',price_version_id=str(uuid.uuid4()),factor='12.000000');line.pop('manual_price');needle='STALE_PRICE'
    elif kind=='MASTER_FRACTION':line.update(mode='MASTER',price_version_id=f['quote']['price_version_id'],factor=f['quote']['factor']);line.pop('manual_price');needle='eceran manual'
    elif kind=='STALE_VERSION':
        r=call(a,cur,'SAVE_DRAFT',p);p.update(id=r['id'],expected_version=str(int(r['row_version'])+1));needle='STALE_VERSION'
    elif kind=='POSTED_EDIT':
        r=call(a,cur,'POST',p);p.update(id=r['id'],expected_version=r['row_version']);action='SAVE_DRAFT';needle='tidak dapat diedit'
    before=a.actors.boundary(cur)
    result=a.inherited.refused(cur,lambda:call(a,cur,action,p))
    assert a.actors.boundary(cur)==before
    if needle:assert needle.lower() in result['message'].lower(),result
    assert result['sqlstate']!='42501','ACL denial does not prove business validation'
    return dict(status='PASS',refusal=kind,error=result,complete_boundary_unchanged=True)

def delete_draft(a,cur,today):
    f=fixture(a,cur,today);before=a.production.ledger(cur);r=call(a,cur,'SAVE_DRAFT',f['payload']);p=dict(id=r['id'],expected_version=r['row_version'],reason='Discard unposted draft')
    key=uuid.uuid4();deleted=call(a,cur,'DELETE',p,key);state=a.actors.boundary(cur)
    assert deleted['status']=='DELETED' and call(a,cur,'DELETE',p,key)==deleted and a.actors.boundary(cur)==state
    assert a.production.ledger(cur)==before and not cur.execute('select 1 from erp.contractor_material_issues where id=%s',(r['id'],)).fetchone()
    return dict(status='PASS',draft_delete_inert=True,replay_exact=True)

def authorization(a,cur,today):
    for function in ['public.erp_get_accessory_issue_workspace_v1(jsonb)','public.erp_save_accessory_issue_action_v1(text,jsonb,uuid)']:
        assert cur.execute("select has_function_privilege('anon',%s,'EXECUTE'),has_function_privilege('authenticated',%s,'EXECUTE')",(function,function)).fetchone()==(False,True)
    for function in ['erp.accessory_issue_quote_v1(uuid,uuid,timestamp with time zone)','erp.get_accessory_issue_workspace_v1(jsonb)','erp.save_accessory_issue_action_v1(text,jsonb,uuid)']:
        assert cur.execute("select has_function_privilege('authenticated',%s,'EXECUTE')",(function,)).fetchone()[0] is False
    f=fixture(a,cur,today);key=uuid.uuid4();r=call(a,cur,'SAVE_DRAFT',f['payload'],key)
    backup=uuid.uuid4();cur.execute("insert into auth.users(id,aud,role,email) values(%s,'authenticated','authenticated',%s)",(backup,'accessory-backup-'+backup.hex+'@example.test'))
    cur.execute("insert into erp.app_users(auth_user_id,full_name,role,role_id,is_active) select %s,'Accessory backup owner','OWNER',id,true from erp.app_roles where role_code='OWNER'",(backup,))
    # The legacy STAFF catalog role is deliberately inactive. Use an active
    # read-only role, then narrow its fixture permissions to this one reader.
    role=cur.execute("select id from erp.app_roles where role_code='AUDITOR_VIEW_ONLY' and is_active").fetchone()[0]
    cur.execute('delete from erp.app_role_permissions where role_id=%s',(role,));cur.execute("insert into erp.app_role_permissions(role_id,permission_key) values(%s,'finance.contractor_accessory.view')",(role,))
    cur.execute("update erp.app_users set role='STAFF',role_id=%s where auth_user_id=%s",(role,a.base.OPERATOR_AUTH))
    assert read(a,cur,dict(id=r['id']))['document']['id']==r['id']
    rejected=a.inherited.refused(cur,lambda:call(a,cur,'SAVE_DRAFT',f['payload'],key));assert rejected['sqlstate']=='42501',rejected
    cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(a.base.OPERATOR_AUTH,))
    assert a.inherited.refused(cur,lambda:read(a,cur,dict(id=r['id'])))['sqlstate']=='42501'
    return dict(status='PASS',view_does_not_grant_write=True,revoked_replay_refused=True,inactive_reader_refused=True)

def cases(a,cur,today):
    return [('ACCESSORY_CONNECTED:'+str(f),lambda f=f:lifecycle(a,cur,today,f)) for f in (12,144)] + [
      ('ACCESSORY_CONNECTED_ZERO',lambda:lifecycle(a,cur,today,12,'0.00')),
      ('ACCESSORY_CONNECTED_MASTER',lambda:master_lifecycle(a,cur,today)),
      ('ACCESSORY_CONNECTED_DELETE',lambda:delete_draft(a,cur,today)),
      ('ACCESSORY_CONNECTED_AUTHORIZATION',lambda:authorization(a,cur,today)),
    ]+ [('ACCESSORY_CONNECTED_REFUSAL:'+k,lambda k=k:refused(a,cur,today,k)) for k in
       ('FRACTIONAL','NUMBER','PRICE_PRECISION','PRICE_COMMA','PRICE_NEGATIVE','OVER_STOCK','EMPTY_LOCATION','FUTURE','BAD_DATE','UNKNOWN_FIELD','DUPLICATE','STALE_PRICE','MASTER_FRACTION','STALE_VERSION','POSTED_EDIT')]
