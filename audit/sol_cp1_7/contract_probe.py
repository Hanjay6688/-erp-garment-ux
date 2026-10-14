"""Sol contract-designed cases on the unmodified final CP7/K3 installation.
Synthetic stock builders reused; expected dimensional amounts are literal.
SQL public facades, not a claim of real Auth transport for these five cases.
"""
import hashlib,json,sys,uuid
from decimal import Decimal as D
from pathlib import Path

CANDIDATE=Path(__file__).resolve().parents[3]/'auditor'
sys.path.insert(0,str(CANDIDATE/'scripts'))
import cp7_f05_analysis_probe as probe
import cp7_note_correction_cases as notes
import cp7_sales_draft_cases as drafts
import cp7_sales_return_cases as returns
import cp7_sales_payment_cases as payments
import cp7_finance_cases as finance
cmd,source,b,auth=drafts.cmd,drafts.source,drafts.b,drafts.auth
IDS=['SOL_DIMENSIONAL_CASH_RETURN','SOL_IDENTICAL_LINE_CORRECTION','SOL_ROLE_REDACTION_AND_REVOKE','SOL_REPORT_EXACT_READONLY','SOL_UUID_ATOMIC_REFUSAL']
original=probe.native.strict_group
own=[]

def stock(cur,today):
 return notes.stock(cur,today,qty=10)

def available(cur,f):
 rows=drafts.options(cur,'STOCK',f['sale_at'],q=f['sku'])['rows']
 return D(next(x['available_qty']for x in rows if str(x['product_id'])==str(f['product'])))

def accounts(cur,before,expected):
 actual=cmd.delta(before,cmd.accounts(cur))
 want={cmd.mapping(cur,key):D(value)for key,value in expected.items()}
 assert actual==want,('SOL_DIMENSIONAL_GL',actual,want)
 return {k:str(v)for k,v in actual.items()}

def post(cur,f):
 p,v=cmd.review(cur,f);return cmd.command(cur,'POST',p,v)

def factory(cur,today):
 b.api.admin(cur)
 role=cur.execute('select r.role_code from erp.app_users a join erp.app_roles r on r.id=a.role_id where a.auth_user_id=%s',(auth.base.OPERATOR_AUTH,)).fetchone()[0]
 assert role in('OWNER','ADMIN'),('SOL_PRIMARY_ROLE_NOT_OWNER_ADMIN',role)
 def wrap(fn):
  def run():
   result=fn();result.update(evidence_origin='INDEPENDENT_NATIVE_RERUN',oracle_origin='SOL_LITERAL_BUSINESS_CONTRACT',fixture_origin='REUSED_NATIVE_FOUND_AT_OPNAME_BUILDER_SYNTHETIC_UNIT_VALUE_10',session_role=role,private_setup_role='postgres',business_calls='public P11/P13 commands/readers as authenticated app actor',source_sha='0b7049d9203bac52b47a4c89f3e0d75646067a8f')
   return result
  return run
 def dimensional():
  f,g=stock(cur,today),stock(cur,today);p=drafts.payload(f,'3','17.25');p['items']+=drafts.payload(g,'2','9.15')['items']
  before=cmd.accounts(cur);drafts.create(cur,f,p)
  assert available(cur,f)==7 and available(cur,g)==8 and cmd.accounts(cur)==before
  assert source.read(cur,f)['detail']['financial']['gross_total']=='70.05'
  post(cur,f);gl=accounts(cur,before,{'AR_CUSTOMER':'70.05','SALES_REVENUE':'-70.05','FG_INVENTORY':'-50','COGS':'50'})
  f['bank']=str(source.bc.bank_account(cur,'SOL-BANK-'+uuid.uuid4().hex[:8]));f['destination']=f['location'];rows=returns.read(cur,f)['page']['rows']
  by_product={str(x['product_id']):x['allocation_id']for x in rows};assert set(by_product)=={str(f['product']),str(g['product'])}
  r,v=returns.payload(cur,f,qty='1',refund='17.25',allocation=by_product[str(f['product'])],destination=f['location'])
  r['items'].append(dict(r['items'][0],allocation_id=by_product[str(g['product'])],refund_amount='9.15'))
  cmd.command(cur,'RETURN',r,v);payments.pay(cur,f,'35.00');detail=source.read(cur,f)['detail']
  assert {k:detail['financial'][k]for k in ['gross_total','return_total','net_total','paid_total','open_balance']}=={'gross_total':'70.05','return_total':'26.40','net_total':'43.65','paid_total':'35.00','open_balance':'8.65'},detail
  assert available(cur,f)==8 and available(cur,g)==9
  bank=payments.bank_account(cur,f);actual=cmd.delta(before,cmd.accounts(cur));expected={cmd.mapping(cur,'AR_CUSTOMER'):D('8.65'),cmd.mapping(cur,'SALES_REVENUE'):D('-43.65'),cmd.mapping(cur,'FG_INVENTORY'):D('-30'),cmd.mapping(cur,'COGS'):D('30'),bank:D('35')};assert actual==expected,(actual,expected)
  return dict(status='PASS',expected_per_product=[dict(product=str(f['product']),initial='10',sold='3',returned='1',available='8',unit_cost='10'),dict(product=str(g['product']),initial='10',sold='2',returned='1',available='9',unit_cost='10')],draft_reservation_has_no_GL_effect=True,post_GL=gl,expected_money=detail['financial'],final_GL={k:str(v)for k,v in actual.items()})
 def identical():
  f=stock(cur,today);p=drafts.payload(f,'3','17.25');p['items'].append(dict(p['items'][0]));before=cmd.accounts(cur);drafts.create(cur,f,p);post(cur,f)
  old=notes.unchanged_facts(cur,f['sale']);root=f['sale'];detail=source.read(cur,f)['detail'];ids=[i['id']for i in detail['items']];assert len(ids)==len(set(ids))==2
  assert all(i['qty_pcs']=='3'and i['financial']['unit_price']=='17.25'for i in detail['items'])
  movements={str(i):str(m)for i,m in cur.execute("select i.id,m.id from erp.sales_items i join erp.fg_stock_movements m on m.source_id=i.id where i.sale_id=%s and m.movement_type='SALE'",(f['sale'],)).fetchall()}
  e,v=notes.edit(cur,f);assert [x['id']for x in source.read(cur,f)['detail']['items']]==ids
  e['item_lineage']=ids;e['items'][1]['qty_pcs']='2';out=notes.correct(cur,e,v);f['sale']=out['sale_id']
  assert notes.unchanged_facts(cur,root)==old
  book=notes.complete_book(cur,f);observed={old_id:str(book[movements[old_id]]['physical_delta'])for old_id in ids};assert observed=={ids[0]:'-3',ids[1]:'-2'},observed
  assert available(cur,f)==5 and source.read(cur,f)['detail']['financial']['gross_total']=='86.25'
  gl=accounts(cur,before,{'AR_CUSTOMER':'86.25','SALES_REVENUE':'-86.25','FG_INVENTORY':'-50','COGS':'50'})
  return dict(status='PASS',exact_duplicate_input=dict(qty='3',unit_price='17.25',lines=2),root=root,revised=out['sale_id'],expected_lineage={ids[0]:'-3',ids[1]:'-2'},observed_lineage=observed,original_posted_facts_immutable=True,available='5',AR='86.25',COGS='50',GL=gl)
 def redaction():
  f=stock(cur,today);drafts.create(cur,f,drafts.payload(f,'3','17.25'));post(cur,f)
  subject,custom=auth.custom_actor(cur);cur.execute('delete from erp.app_role_permissions where role_id=%s',(custom,));cur.execute("insert into erp.app_role_permissions(role_id,permission_key)values(%s,'sales.invoice.view')",(custom,))
  view=source.read(cur,f,subject);assert view['financial_captured']is False
  text=json.dumps(view);assert not any(s in text for s in ['17.25','51.75','unit_price','line_total','unit_hpp'])and 'financial'not in text.replace('financial_captured','')
  before=b.boundary.snapshot(cur);code=auth.refused(cur,lambda:finance.read(cur,today,subject),'CP7_FINANCE_ACCESS_DENIED');assert b.boundary.snapshot(cur)==before
  cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='sales.invoice.view'",(custom,));before=b.boundary.snapshot(cur);revoke=auth.refused(cur,lambda:source.read(cur,f,subject),'CP7_SALES_ACCESS_DENIED');assert b.boundary.snapshot(cur)==before
  owner=source.read(cur,f);assert owner['financial_captured']is True and owner['detail']['financial']['gross_total']=='51.75'
  return dict(status='PASS',custom_session_role='CUSTOM_STAFF_WITH_ONLY_SALES_INVOICE_VIEW',selected_owner_document_id=f['sale'],money_and_HPP_absent_in_operational_response=True,finance_refusal=code,current_revocation_refusal=revoke,no_refused_read_business_effect=True,authorized_owner_admin_control='51.75')
 def report():
  f=stock(cur,today);drafts.create(cur,f,drafts.payload(f,'3','17.25'));baseline=finance.fixture_read(cur,today,f['sale_at']);post(cur,f);boundary=b.boundary.snapshot(cur);one=finance.fixture_read(cur,today,f['sale_at']);two=finance.fixture_read(cur,today,f['sale_at'])
  assert b.boundary.snapshot(cur)==boundary
  assert one['snapshot']['financial_position']==two['snapshot']['financial_position']and one['snapshot']['performance']==two['snapshot']['performance']
  expected={('financial_position','customer_ar'):'51.75',('financial_position','fg_inventory'):'-30',('performance','sales_revenue_gl'):'51.75',('performance','cogs_gl'):'30',('performance','gross_profit'):'21.75'}
  got={s+'/'+k:str(D(one['snapshot'][s][k])-D(baseline['snapshot'][s][k]))for s,k in expected}
  assert got=={s+'/'+k:str(D(n))for(s,k),n in expected.items()},got
  return dict(status='PASS',literal_expected={s+'/'+k:str(D(n))for(s,k),n in expected.items()},observed=got,two_public_reads_same_business_values=True,all_ERP_platform_Auth_schema_ACL_boundary_unchanged=True)
 def replay():
  f=stock(cur,today);p=drafts.payload(f,'3','17.25');key=uuid.uuid4();one=drafts.create(cur,f,p,key);assert drafts.create(cur,f,p,key)==one and available(cur,f)==7
  bad=json.loads(json.dumps(p));bad['items'][0]['qty_pcs']='4';before=b.boundary.snapshot(cur);changed=auth.refused(cur,lambda:drafts.create(cur,f,bad,key),'CP7_SALES_REQUEST_CHANGED');assert b.boundary.snapshot(cur)==before
  e,v=drafts.edit_payload(cur,f,p);e['items'][0]['qty_pcs']='11';before=b.boundary.snapshot(cur);short=auth.refused(cur,lambda:cmd.command(cur,'EDIT',e,v),'Insufficient FG stock');assert b.boundary.snapshot(cur)==before
  assert source.read(cur,f)['detail']['reserved_qty']=='3'and available(cur,f)==7
  before=cmd.accounts(cur);post(cur,f);assert available(cur,f)==7;gl=accounts(cur,before,{'AR_CUSTOMER':'51.75','SALES_REVENUE':'-51.75','FG_INVENTORY':'-30','COGS':'30'})
  assert cur.execute('select count(*)from erp.sales_headers where sale_number=%s',(f['tag'],)).fetchone()[0]==1
  e,v=drafts.edit_payload(cur,f,p);before=b.boundary.snapshot(cur);posted=auth.refused(cur,lambda:cmd.command(cur,'EDIT',e,v),'CP7_SALES_DRAFT_ONLY');assert b.boundary.snapshot(cur)==before
  return dict(status='PASS',request_id=str(key),same_payload_one_effect=True,changed_payload_refusal=changed,late_shortage_refusal=short,posted_edit_refusal=posted,original_reservation_retained='3',available='7',post_no_second_stock_deduction=True,GL=gl)
 return list(zip(IDS,map(wrap,[dimensional,identical,redaction,report,replay])))

def wrapped(name,case_factory,verify):
 normal=original(name,case_factory,verify)
 if name=='CP7_K3_CLEANUP':
  result=original('SOL_CP1_7_CONTRACT',factory,verify);own.append(result)
  result.update(candidate_sha='0b7049d9203bac52b47a4c89f3e0d75646067a8f',probe_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),expected_ids=IDS,expected_count=5,production_go=False)
  (probe.OUT.parent/'SOL_CONTRACT_CASES.json').write_text(json.dumps(result,indent=2,default=str)+'\n')
  print(json.dumps({'sol_contract_result':result},default=str),flush=True)
 return normal

probe.native.strict_group=wrapped
def runtime(browser_mode=False):
 normal=probe.run(k3_cleanup=True)
 assert len(own)==1,'Sol contract group was not executed'
 if own[0].get('counts')!={'PASS':5}or set(own[0].get('cases',{}))!=set(IDS)or not own[0].get('complete_boundary_restored'):
  normal=dict(normal,status='INCOMPLETE',sol_contract_failure=True)
 return normal
probe.package._writer_runtime=runtime
if __name__=='__main__':probe.package.run('install')
