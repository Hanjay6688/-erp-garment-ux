"""Predeclared source navigation controls on actual Native writers.

No stock or journal outcome is seeded. Read-only resolver checks are counted
separately from the two retained combined-stack write/revoke schedules.
"""
import json,uuid
import cp7_material_cases as material
import cp7_material_count_cases as count
import cp7_fg_adjustment_cases as fg
import cp7_invoice_cases as invoice
import cp7_sales_payment_cases as payment
import cp7_sales_return_cases as returned
import cp7_note_correction_cases as note
import cp7_misc_cases as misc
import cp7_f03_cases as combined
import cp7_transaction_source_bundle as bundle
b,auth=material.b,material.auth
REQUIRED=dict(native=12,races=2,http=2,browser=2)
EXPECTED=sum(REQUIRED.values())
RPC='erp_cp7_resolve_transaction_source_v1'

def read(cur,kind,ident,subject=None):
 auth.actor(cur,subject)
 out=cur.execute('select public.erp_cp7_resolve_transaction_source_v1(%s)',(json.dumps(dict(source_type=kind,source_id=str(ident))),)).fetchone()[0]
 b.api.admin(cur);return out

def exact(cur,kind,ident,domain,parent,focus=None,subject=None):
 before=b.boundary.snapshot(cur);r=read(cur,kind,ident,subject)
 assert r['contract_version']=='cp7.transaction-source.v1'and r['source']==dict(source_type=kind,source_id=str(ident))and r['status']=='AVAILABLE'and r['business_DML']is False
 assert set(r)=={'contract_version','actor_scope_id','source','status','document','read_at','business_DML'}
 d=r['document'];assert set(d)=={'domain','route','id','number','status','revision','focus'}
 assert d['domain']==domain and d['id']==str(parent)and d['number']
 if focus:assert d['focus']['kind']==focus[0]and d['focus']['id']==str(focus[1])
 else:assert d['focus']is None
 assert b.boundary.snapshot(cur)==before,'SOURCE_NAVIGATION_BUSINESS_DML'
 return d

def cases(cur,today):
 def receipts():
  f=material.fixture(cur,today);parent=f['receipt']['purchase_id'];item=cur.execute('select purchase_item_id from erp.material_rolls where id=%s',(f['roll'],)).fetchone()[0]
  for kind,ident in [('MATERIAL_PURCHASE',parent),('MATERIAL_PURCHASE_ITEM',item),('MATERIAL_PURCHASE_ROLL',f['roll'])]:exact(cur,kind,ident,'RECEIPT',parent)
  return dict(status='PASS',actual_receipt_item_roll_same_owning_header_read_only=True)
 def invoices():
  f=invoice.fixture(cur,today);r=invoice.finalize(cur,f);ident=r['invoice_id'];line=cur.execute('select id from erp.material_supplier_invoice_lines where invoice_id=%s',(ident,)).fetchone()[0]
  for kind,i in [('MATERIAL_SUPPLIER_INVOICE',ident),('MATERIAL_SUPPLIER_INVOICE_LINE',line)]:
   d=exact(cur,kind,i,'RECEIPT',f['receipt']['purchase_id'],('PURCHASE_INVOICE',ident));assert d['focus']['page_offset']==0
  return dict(status='PASS',actual_invoice_line_FK_not_assumed_header_purchase_id=True)
 def transfers():
  f=material.fixture(cur,today);draft,_=material.draft(cur,f);post=material.post(cur,draft);ident=post['transfer_id'];item=cur.execute('select id from erp.material_transfer_items where transfer_id=%s',(ident,)).fetchone()[0]
  for kind,i in [('MATERIAL_TRANSFER',ident),('MATERIAL_TRANSFER_ITEM',item)]:exact(cur,kind,i,'MATERIAL_TRANSFER',ident)
  material.reverse(cur,post);assert exact(cur,'MATERIAL_TRANSFER',ident,'MATERIAL_TRANSFER',ident)['status']=='REVERSED'
  return dict(status='PASS',actual_transfer_parent_and_inverse_history_exact=True)
 def counts():
  f=material.fixture(cur,today);draft,_=count.draft(cur,f);post=count.action(cur,'POST',draft);ident=post['adjustment_id'];item=cur.execute('select id from erp.material_adjustment_items where adjustment_id=%s',(ident,)).fetchone()[0]
  exact(cur,'MATERIAL_ADJUSTMENT_ITEM',item,'MATERIAL_COUNT',ident);count.action(cur,'REVERSE',post);exact(cur,'MATERIAL_ADJUSTMENT',ident,'MATERIAL_COUNT',ident)
  return dict(status='PASS',actual_material_count_owner_not_ledger_inverse=True)
 def finished():
  f=fg.fg.fixture(cur,today);draft,_=fg.draft(cur,f);post=fg.action(cur,'POST',draft);ident=post['adjustment_id'];item=cur.execute('select id from erp.fg_adjustment_items where adjustment_id=%s',(ident,)).fetchone()[0]
  exact(cur,'FG_ADJUSTMENT_ITEM',item,'FG_ADJUSTMENT',ident);fg.action(cur,'REVERSE',post);exact(cur,'FG_ADJUSTMENT',ident,'FG_ADJUSTMENT',ident)
  return dict(status='PASS',actual_finished_adjustment_item_parent_and_inverse=True)
 def sales():
  f=note.stock(cur,today,120);note.posted(cur,f,'36');old=f['sale'];item=cur.execute('select id from erp.sales_items where sale_id=%s',(old,)).fetchone()[0]
  exact(cur,'SALE_ITEM',item,'SALE',old);p,v=note.edit(cur,f,'24');replacement=note.correct(cur,p,v)
  assert exact(cur,'SALE_ITEM',item,'SALE',old)['status']=='REVERSED'
  exact(cur,'SALE',replacement['sale_id'],'SALE',replacement['sale_id'])
  return dict(status='PASS',owning_atomic_note_correction_preserves_original_navigation_and_replacement=True)
 def payments():
  f=payment.fixture(cur,today);old=payment.pay(cur,f,'1')
  for _ in range(25):payment.pay(cur,f,'1')
  d=exact(cur,'SALES_PAYMENT',old['payment_id'],'SALE',f['sale'],('SALES_PAYMENT',old['payment_id']));assert d['focus']['page_offset']==25
  page=payment.cash(cur,f,payment_offset=25,payment_limit=25);assert any(x['id']==old['payment_id']for x in page['payments']['rows'])
  return dict(status='PASS',actual26_payments_old_exact_source_on_second_owning_page=True)
 def returns():
  f=returned.fixture(cur,today);r=returned.returned(cur,f);ident=r['return_id'];item=cur.execute('select id from erp.sales_return_items where return_id=%s',(ident,)).fetchone()[0]
  for kind,i in [('SALES_RETURN',ident),('SALES_RETURN_ITEM',item)]:exact(cur,kind,i,'SALE',f['sale'],('SALES_RETURN',ident))
  returned.inverse(cur,f,ident);exact(cur,'SALES_RETURN',ident,'SALE',f['sale'],('SALES_RETURN',ident))
  return dict(status='PASS',actual_return_child_and_retained_inverse_source=True)
 def journals():
  f=misc.fixture(cur,today);saved=misc.command(cur,'SAVE',misc.save_payload(f));posted=misc.command(cur,'POST',misc.intent(saved));ident=posted['transaction_id'];original=cur.execute("select id from erp.journal_entries where source_type='MISC_FINANCE'and source_id=%s",(ident,)).fetchone()[0]
  exact(cur,'MISC_FINANCE',ident,'MISC_FINANCE',ident);misc.command(cur,'REVERSE',misc.intent(posted));inverse=cur.execute('select source_type,source_id from erp.journal_entries where reversal_of_id=%s',(original,)).fetchone();assert inverse
  exact(cur,inverse[0],inverse[1],'MISC_FINANCE',ident)
  return dict(status='PASS',actual_inverse_journal_link_follows_immutable_parent_not_guessed_UUID=True)
 def authority():
  f=material.fixture(cur,today);subject,role=auth.custom_actor(cur)
  auth.refused(cur,lambda:read(cur,'MATERIAL_PURCHASE_ROLL',f['roll'],subject),'CP7_TRANSACTION_SOURCE_ACCESS_DENIED')
  cur.execute('insert into erp.app_role_permissions(role_id,permission_key)values(%s,%s)',(role,'warehouse.procurement.view'))
  exact(cur,'MATERIAL_PURCHASE_ROLL',f['roll'],'RECEIPT',f['receipt']['purchase_id'],subject=subject)
  cur.execute('delete from erp.app_role_permissions where role_id=%s and permission_key=%s',(role,'warehouse.procurement.view'))
  auth.refused(cur,lambda:read(cur,'MATERIAL_PURCHASE_ROLL',f['roll'],subject),'CP7_TRANSACTION_SOURCE_ACCESS_DENIED')
  return dict(status='PASS',Native_current_permission_before_child_resolution_and_after_revoke=True)
 def malformed():
  before=b.boundary.snapshot(cur);missing=str(uuid.uuid4())
  for value in [None,{},dict(source_type='SALE',source_id=missing,amount='1'),dict(source_type='sale',source_id=missing),dict(source_type='SALE',source_id='broken')]:
   def attempt():
    auth.actor(cur);cur.execute('select public.erp_cp7_resolve_transaction_source_v1(%s)',(json.dumps(value),))
   auth.refused(cur,attempt,'CP7_TRANSACTION_SOURCE_FIELDS');b.api.admin(cur)
  auth.refused(cur,lambda:read(cur,'SALE_ITEM',missing),'CP7_TRANSACTION_SOURCE_UNAVAILABLE')
  unknown=read(cur,'UNREGISTERED_SOURCE',missing);assert unknown['document']is None and unknown['status']=='UNSUPPORTED_SOURCE'and unknown['business_DML']is False
  assert b.boundary.snapshot(cur)==before
  return dict(status='PASS',closed_fields_missing_source_explicit_unsupported_never_guessed=True)
 def least_privilege():
  bundle.verify(cur)
  for who in('anon','service_role'):assert not cur.execute('select has_function_privilege(%s,\'public.erp_cp7_resolve_transaction_source_v1(jsonb)\',\'EXECUTE\')',(who,)).fetchone()[0]
  assert cur.execute('select has_function_privilege(\'authenticated\',\'public.erp_cp7_resolve_transaction_source_v1(jsonb)\',\'EXECUTE\')').fetchone()[0]
  return dict(status='PASS',public_current_auth_only_private_resolver_and_ERP_DML_denied=True)
 functions=[receipts,invoices,transfers,counts,finished,sales,payments,returns,journals,authority,malformed,least_privilege]
 assert len(functions)==REQUIRED['native']
 return [('CP7_SOURCE_'+f.__name__.upper(),f)for f in functions]

def races(tools,today):return [('CP7_SOURCE_RETAINED_'+name,fn)for name,fn in combined.races(tools,today)]

def http_cases(http,today):
 def exact_http():
  owner=http.login('OWNER','cp7-source-owner')
  with http.connect()as conn,conn.cursor()as cur:f=material.fixture(cur,today);conn.commit()
  args=dict(p_source=dict(source_type='MATERIAL_PURCHASE_ROLL',source_id=f['roll']))
  assert http.anon_rpc(RPC,args)['status']in(401,403)
  r=owner.rpc(RPC,args);assert r['status']==200,r
  assert r['body']['actor_scope_id']==owner.auth_user_id and r['body']['document']['id']==f['receipt']['purchase_id']and r['body']['business_DML']is False
  with http.connect()as conn,conn.cursor()as cur:before=b.boundary.snapshot(cur);conn.rollback()
  assert owner.rpc(RPC,args)['body']['document']==r['body']['document']
  with http.connect()as conn,conn.cursor()as cur:assert b.boundary.snapshot(cur)==before;conn.rollback()
  return dict(status='PASS',real_Auth_HTTP_exact_child_parent_anonymous_denied_no_business_write=True)
 def current_http():
  admin=http.login('ADMIN','cp7-source-current-admin')
  with http.connect()as conn,conn.cursor()as cur:
   f=material.fixture(cur,today);role=cur.execute('select role_id from erp.app_users where auth_user_id=%s',(admin.auth_user_id,)).fetchone()[0];cur.execute('insert into erp.app_role_permissions(role_id,permission_key)values(%s,%s)on conflict do nothing',(role,'warehouse.procurement.view'));conn.commit()
  args=dict(p_source=dict(source_type='MATERIAL_PURCHASE_ROLL',source_id=f['roll']))
  assert admin.rpc(RPC,args)['status']==200
  with http.connect()as conn,conn.cursor()as cur:cur.execute('delete from erp.app_role_permissions where role_id=%s and permission_key=%s',(role,'warehouse.procurement.view'));conn.commit()
  assert admin.rpc(RPC,args)['status']==403
  return dict(status='PASS',real_Auth_CURRENT_native_role_permission_revocation_not_token_metadata=True)
 return [('CP7_SOURCE_HTTP_EXACT',exact_http),('CP7_SOURCE_HTTP_CURRENT_REVOKE',current_http)]
