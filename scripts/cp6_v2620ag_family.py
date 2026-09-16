#!/usr/bin/env python3
"""AG whole reservation family: unchanged peer oracles, normal paths and detectors."""
from pathlib import Path
from datetime import date,timedelta
import argparse,json,os,traceback,uuid
import psycopg
import cp6_af_independent_review as peer
import cp6_v2620af_family as af
import cp6_v2620ag_runtime as runtime
from cp6_v2620ag_build_sql import DIRTY_QUERY
from cp6_v2620n_rollback_guards import function_catalog
from cp6_v2620u_install_diagnostic import snapshot
actors,base,prior=af.actors,af.base,af.prior
sql_body,expected_refusal=af.sql_body,af.expected_refusal
ROOT=Path('cp6-proof/writer-ag');CHECK='V2620AG_SALE_RESERVATION_LINEAGE_MISMATCH'
MODES=('PRODUCT','LOCATION','CUSTOMER','DATE','MOVE_DRAFT')

def save(name,data):
 ROOT.mkdir(parents=True,exist_ok=True);(ROOT/(name+'.json')).write_text(json.dumps(data,indent=2,default=str)+'\n')

def report(cur,day,blocked=False):
 actors.owner(cur);state=base.one(cur,'select erp.get_owner_financial_snapshot_v2(%s,%s,%s)',(day,day,day))
 check=cur.execute('select severity,issue_count from erp.run_v268_financial_report_checks() where check_name=%s',(CHECK,)).fetchone();actors.admin(cur)
 assert state['data_confidence']['status']==('BLOCKED' if blocked else 'READY'),state
 assert check is not None and check[0]=='CRITICAL' and (check[1]>0)==blocked,check
 return {'status':'PASS','check':check,'state':state}

def install(cur):
 actors.admin(cur);cur.execute('set local role postgres');cur.execute(sql_body(runtime.MIGRATION),prepare=False)
 cur.execute('insert into supabase_migrations.schema_migrations(version,name,statements) values(%s,%s,%s)',(runtime.STAMP,runtime.NAME,[runtime.MIGRATION.read_text()]));assert len(runtime.verified_successor(cur))==690
 cur.execute('reset role')

def admission(mode):
 def run(cur,day):
  if mode=='CLEAN':
   before=function_catalog(cur);install(cur);actors.admin(cur);cur.execute(sql_body(runtime.ROLLBACK),prepare=False);runtime.verify_predecessor(cur);assert function_catalog(cur)==before
   return {'status':'PASS','clean_install_restore':True}
  if mode in MODES:
   evidence=peer.sale_case(mode)(cur,day);assert evidence['status']=='BUG_PROVEN',evidence
   actors.admin(cur);cur.execute('set local role postgres')
   refusal=expected_refusal(cur,lambda:cur.execute(sql_body(runtime.MIGRATION),prepare=False),'AG_PREEXISTING_SALE_LINEAGE_REVIEW_REQUIRED');cur.execute('reset role')
   return {'status':'PASS','original_af_business_counterexample':evidence,'refusal':refusal}
  mutations={
   'FUNCTION':("alter function erp.post_sale(uuid) set work_mem='64MB'",'AG_PREDECESSOR_FUNCTION_OWNER_ACL_MISMATCH'),
   'ACL':('grant execute on function erp.guard_child_by_parent_status() to authenticated','AG_PREDECESSOR_FUNCTION_OWNER_ACL_MISMATCH'),
   'PLATFORM':("update supabase_migrations.schema_migrations set statements=array['wrong'] where name='erp_v2_6_20af_cp6_posted_child_integrity'",'AG_REQUIRES_EXACT_AF_PLATFORM_CAPSULE'),
   'MARKER':("delete from erp.schema_migrations where version='v2.6.20af'",'AG_REQUIRES_EXACT_AF_WITHOUT_AG_RESIDUE')}
  actors.admin(cur);cur.execute(mutations[mode][0]);cur.execute('set local role postgres');e=expected_refusal(cur,lambda:cur.execute(sql_body(runtime.MIGRATION),prepare=False),mutations[mode][1]);cur.execute('reset role');return {'status':'PASS','refusal':e}
 return run

def original(mode):
 def run(cur,day):
  r=peer.sale_case(mode)(cur,day);assert r['status']=='CONTROL_PASS',r
  r['status']='PASS';r['unchanged_original_af_oracle']=True;return r
 return run

def reject_direct(mode):
 def run(cur,day):
  f=peer.fixture(cur,day);sale=f['sale']['sale_id'];actors.admin(cur);before=actors.boundary(cur)
  queries={
   'HEADER_DELETE':('delete from erp.sales_headers where id=%s',(sale,)),
   'ITEM_DELETE':('delete from erp.sales_items where id=%s',(f['item'],)),
   'ITEM_INSERT':('insert into erp.sales_items(sale_id,product_id,qty_pcs,unit_price_snapshot) values(%s,%s,1,20)',(sale,f['products'][1]))}
  q,p=queries[mode];r=peer.operation(cur,q,p);assert r['refused'] and 'AG_RESERVED_SALE_EDIT_REQUIRES_SAVE_RPC' in r['error']['message'],r
  actors.admin(cur);assert actors.boundary(cur)==before
  return {'status':'PASS','refusal':r,'report':report(cur,day)}
 return run

def rpc(mode):
 def run(cur,day):
  f=peer.fixture(cur,day);sale=f['sale']['sale_id'];payload=dict(f['payload'],sale_id=sale,reason='AG lawful whole draft edit');line=dict(payload['items'][0]);payload['items']=[line]
  if mode in('CUSTOMER','COMBINED'):payload['customer_id']=f['customers'][1]
  if mode in('DATE','COMBINED'):payload['sale_date']=(day+timedelta(days=1)).isoformat()+'T00:15:00+07:00'
  if mode=='COMBINED':line['product_id']=f['products'][1]
  if mode in('LOCATION','COMBINED'):
   payload['source_location_id']=f['second_location'];ordinary=peer.ordinary(cur);h=uuid.uuid4()
   cur.execute("insert into erp.opening_balance_headers(id,opening_number,opening_date,status) values(%s,%s,%s,'DRAFT')",(h,'AG-NEW-WH-'+h.hex,day-timedelta(days=2)))
   cur.execute("insert into erp.opening_balance_items(opening_id,balance_type,product_id,location_id,qty,unit_cost_snapshot,quality_grade,hpp_input_method) values(%s,'FINISHED_GOODS',%s,%s,10,1.25,'GRADE_A','MANUAL')",(h,line['product_id'],f['second_location']))
   cur.execute('select erp.post_opening_balance(%s)',(h,))
  if mode=='INSUFFICIENT':line['qty_pcs']=99
  actors.admin(cur);boundary=actors.boundary(cur);version=f['sale']['row_version']-(1 if mode=='STALE' else 0);req=uuid.uuid4()
  change=peer.operation(cur,'select erp.save_sale_draft_v2(%s::jsonb,%s,%s)',(json.dumps(payload),req,version))
  if mode in('INSUFFICIENT','STALE'):
   assert change['refused'],change;actors.admin(cur);assert actors.boundary(cur)==boundary
   return {'status':'PASS','atomic_refusal':change,'report':report(cur,day)}
  assert not change['refused'],change
  saved=change['rows'][0][0];retry=peer.operation(cur,'select erp.save_sale_draft_v2(%s::jsonb,%s,%s)',(json.dumps(payload),req,version));assert retry['rows']==change['rows']
  before=peer.observe(cur,sale);assert before['active_stock_qty']==3 and before['journal_count']==0 and not before['mismatches'],before
  req=uuid.uuid4();post=peer.operation(cur,'select erp.post_sale_v2(%s,%s,%s)',(sale,req,saved['row_version']));assert not post['refused'],post
  retry=peer.operation(cur,'select erp.post_sale_v2(%s,%s,%s)',(sale,req,saved['row_version']));assert retry['rows']==post['rows']
  after=peer.observe(cur,sale);assert not after['mismatches'] and after['stock']==before['stock'] and after['journal_count']==1,after
  return {'status':'PASS','saved':saved,'post':post,'stock_neutral':True,'idempotent':True,'report':report(cur,day+timedelta(days=1))}
 return run

def tamper(cur,f,mode,day):
 actors.admin(cur);sale=f['sale']['sale_id']
 queries={
  'PRODUCT':('update erp.sales_items set product_id=%s where id=%s',(f['products'][1],f['item'])),
  'LOCATION':('update erp.sales_headers set source_location_id=%s where id=%s',(f['second_location'],sale)),
  'CUSTOMER':('update erp.sales_headers set customer_id=%s where id=%s',(f['customers'][1],sale)),
  'DATE':('update erp.sales_headers set sale_date=%s where id=%s',((day+timedelta(days=1)).isoformat()+'T10:00:00+07:00',sale)),
  'QUANTITY':('update erp.sales_items set qty_pcs=2 where id=%s',(f['item'],)),
  'ALLOCATION':('update erp.sale_stock_allocations set lot_id=(select id from erp.fg_lots where product_id=%s limit 1) where sale_item_id=%s',(f['products'][1],f['item']))}
 q,p=queries[mode];cur.execute(q,p)

def detector(mode,posted):
 def run(cur,day):
  f=peer.fixture(cur,day)
  if posted:
   r=peer.operation(cur,'select erp.post_sale_v2(%s,%s,%s)',(f['sale']['sale_id'],uuid.uuid4(),f['sale']['row_version']));assert not r['refused'],r
  report(cur,day);tamper(cur,f,mode,day)
  r=report(cur,day,True);r.update(synthetic_detector_control=True,not_a_new_business_counterexample=True)
  if not posted:
   before=actors.boundary(cur);post=peer.operation(cur,'select erp.post_sale(%s)',(f['sale']['sale_id'],));assert post['refused'],post
   expected='Sale Draft reservation mismatch' if mode=='QUANTITY' else 'AG_SALE_RESERVATION_LINEAGE_MISMATCH'
   assert expected in post['error']['message'],post
   actors.admin(cur);assert actors.boundary(cur)==before;r['legacy_post_refusal']=post
  return r
 return run

def original_sql(cur,day):
 actors.owner(cur);cur.execute(Path('supabase/tests/sale_draft_reservation_rollback.sql').read_text(),prepare=False)
 return {'status':'PASS','original_oracle':'supabase/tests/sale_draft_reservation_rollback.sql'}

def phase_cases(phase):
 if phase=='admission':return [(m,admission(m)) for m in ('CLEAN',*MODES,'FUNCTION','ACL','PLATFORM','MARKER')]
 if phase=='focused':
  cases=[('ORIGINAL_'+m,original(m)) for m in ('BASE_POST','RPC_EDIT_PRODUCT','RPC_EDIT_QUANTITY','CANCEL','PRODUCT','QUANTITY','LOCATION','CUSTOMER','DATE','MOVE_DRAFT','PRICE_ONLY','NOTES')]
  cases += [('RPC_'+m,rpc(m)) for m in ('CUSTOMER','DATE','LOCATION','COMBINED','INSUFFICIENT','STALE')]
  cases += [('DIRECT_'+m,reject_direct(m)) for m in ('HEADER_DELETE','ITEM_DELETE','ITEM_INSERT')]
  return cases+[('AF_'+n,fn) for n,fn in af.phase_cases('focused')]
 if phase=='detector':return [(m+('_POSTED' if p else '_DRAFT'),detector(m,p)) for m in ('PRODUCT','LOCATION','CUSTOMER','DATE','QUANTITY','ALLOCATION') for p in (False,True)]+[('AF_'+n,fn) for n,fn in af.phase_cases('detector')]
 if phase=='crossflow':
  import cp6_v2620f_final_runtime_regression as f
  import cp6_v2620h_adversarial_regression as h
  def old(fn):
   def run(cur,day):
    actors.owner(cur);r=fn(cur);assert r.get('status')=='PASS',r;return r
   return run
  return list(af.phase_cases('crossflow'))+[(n,old(fn)) for n,fn in [('F_A01',f.case_a01),('F_A02',f.case_a02),('F_A03',f.case_a03),('H_R02',h.case_r02),('H_R03_UNDERPAID',h.case_r03_underpaid),('H_R03_PAID_RETURN',h.case_r03_paid_return),('H_R03_OVERPAID',h.case_r03_overpaid)]]+[('ORIGINAL_DRAFT_LIFECYCLE',original_sql)]
 raise AssertionError(phase)

def run(phase):
 head,tree=runtime.verify_audit_source();assert os.environ.get('PGURL')==peer.URL and os.environ.get('CP6_AG_CONFIRM')=='postgres'
 result=dict(status='INCOMPLETE',phase=phase,head=head,tree=tree,run_id=os.environ.get('GITHUB_RUN_ID'),cases={},production_go=False,http_ui_csv_reachability_proven=False,hosted_database_used=False)
 with psycopg.connect(peer.URL.replace('postgres:postgres@','supabase_admin:postgres@')) as conn,conn.cursor() as cur:
  cur.execute("set local timezone='Asia/Jakarta';set local statement_timeout='240s';set local lock_timeout='8s'")
  untouched=actors.boundary(cur);before_catalog=function_catalog(cur)
  if phase=='admission':
   runtime.verify_predecessor(cur);save('AF_COMPLETE_CATALOG',before_catalog);save('AF_COMPLETE_BOUNDARY',snapshot(cur))
  else:assert len(runtime.verified_successor(cur))==690
  usage=base.one(cur,"select has_schema_privilege('authenticated','erp','USAGE')");result['schema_usage_fixture_grant']=not usage
  if not usage:cur.execute('grant usage on schema erp to authenticated')
  cur.execute("select set_config('request.jwt.claims',%s,true)",(json.dumps({'sub':base.OPERATOR_AUTH,'role':'authenticated'}),));base.load_fixture_foundation(cur);actors.admin(cur)
  day=base.one(cur,"select (statement_timestamp() at time zone 'Asia/Jakarta')::date")-timedelta(days=3);prior.set_open_period(cur,date(2026,8,31) if phase=='crossflow' else day-timedelta(days=4))
  for name,fn in phase_cases(phase):
   actors.admin(cur);before=actors.boundary(cur);cur.execute('savepoint ag_case')
   try:r=fn(cur,day)
   except Exception as exc:r=dict(status='FAIL',error=str(exc),traceback=traceback.format_exc())
   finally:cur.execute('rollback to savepoint ag_case');actors.admin(cur);cur.execute('release savepoint ag_case')
   r['full_boundary_restored']=actors.boundary(cur)==before
   if not r['full_boundary_restored']:r['status']='FAIL'
   result['cases'][name]=r;save(phase,result);print(json.dumps(dict(phase=phase,case=name,status=r['status'],error=r.get('error'))),flush=True)
  actors.admin(cur);result['function_catalog_unchanged']=function_catalog(cur)==before_catalog
  conn.rollback();cur.execute("set local timezone='Asia/Jakarta'");result['unseeded_boundary_restored']=actors.boundary(cur)==untouched
  result['schema_usage_restored']=base.one(cur,"select has_schema_privilege('authenticated','erp','USAGE')")==usage;conn.rollback()
 result['passed']=sum(c['status']=='PASS' for c in result['cases'].values());result['failed']=len(result['cases'])-result['passed']
 if result['passed']==len(phase_cases(phase)) and result['failed']==0 and all(result[k] for k in ('function_catalog_unchanged','unseeded_boundary_restored','schema_usage_restored')):result['status']='PASS'
 save(phase,result);return result

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--phase',required=True,choices=('admission','focused','detector','crossflow'));a=p.parse_args()
 try:r=run(a.phase)
 except Exception as exc:r=dict(status='FAIL',error=str(exc),traceback=traceback.format_exc(),production_go=False);save(a.phase,r)
 print(json.dumps({k:v for k,v in r.items() if k!='cases'},default=str));raise SystemExit(0 if r['status']=='PASS' else 1)
