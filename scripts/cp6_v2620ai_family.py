#!/usr/bin/env python3
"""AI work-source qualification, relevant AH business cases and exact boundaries."""
from pathlib import Path
from datetime import date,timedelta
from decimal import Decimal
import argparse,json,os,traceback,uuid
import psycopg
import cp6_v2620ai_runtime as runtime
import cp6_v2620ah_family as ah
import cp6_ah_independent_review as original
from cp6_v2620n_rollback_guards import function_catalog
from cp6_v2620u_install_diagnostic import snapshot
actors,base,prior,peer=ah.actors,ah.base,ah.prior,ah.peer
ROOT=Path('cp6-proof/writer-ai')
CHECK='V2620AI_WORK_SOURCE_LINEAGE_MISMATCH'

def save(name,value):
 ROOT.mkdir(parents=True,exist_ok=True);(ROOT/(name+'.json')).write_text(json.dumps(value,indent=2,default=str)+'\n')

def report(cur,day,blocked=False):
 result=peer.confidence(cur,day)
 check=cur.execute('select severity,issue_count from erp.run_v268_financial_report_checks() where check_name=%s',(CHECK,)).fetchone()
 assert result['data_confidence']['status']==('BLOCKED' if blocked else 'READY'),result
 assert check[0]=='CRITICAL' and (check[1]>0)==blocked,check
 actors.admin(cur);return dict(status='PASS',check=check,snapshot=result)

def install(cur):
 actors.admin(cur);cur.execute('set local role postgres')
 cur.execute(ah.ag.sql_body(runtime.MIGRATION),prepare=False)
 cur.execute('insert into supabase_migrations.schema_migrations(version,name,statements) values(%s,%s,%s)',(runtime.STAMP,runtime.NAME,[runtime.MIGRATION.read_text()]))
 assert len(runtime.verified_successor(cur))==690;cur.execute('reset role')

def admission(mode):
 def case(cur,day):
  if mode=='CLEAN':
   before=function_catalog(cur);install(cur);actors.admin(cur)
   cur.execute(ah.ag.sql_body(runtime.ROLLBACK),prepare=False)
   runtime.verify_predecessor(cur);assert function_catalog(cur)==before
   return dict(status='PASS',exact_install_restore=True)
  if mode=='VALID_WORK_DRAFT':
   f=original.work_draft(cur,day,Decimal('1.25'));install(cur)
   result=original.qualified_work_control(cur,f);return dict(status='PASS',valid_draft_control=result)
  if mode=='ORIGINAL_WORK_SOURCE':
   proof=original.work_case('HEADER_PO')(cur,day);assert proof['status']=='BUG_PROVEN',proof
   actors.admin(cur);cur.execute('set local role postgres')
   error=ah.ag.expected_refusal(cur,lambda:cur.execute(ah.ag.sql_body(runtime.MIGRATION),prepare=False),'AI_PREEXISTING_WORK_SOURCE_REVIEW_REQUIRED')
   cur.execute('reset role');return dict(status='PASS',original_counterexample=proof,refusal=error)
  mutations={
   'FUNCTION':("alter function erp.validate_work_completion() set work_mem='64MB'",'AI_PREDECESSOR_FUNCTION_OWNER_ACL_MISMATCH'),
   'ACL':('grant execute on function erp.validate_work_completion() to authenticated','AI_PREDECESSOR_FUNCTION_OWNER_ACL_MISMATCH'),
   'PLATFORM':("update supabase_migrations.schema_migrations set statements=array['wrong'] where name='erp_v2_6_20ah_cp6_return_allocation_eligibility'",'AI_REQUIRES_EXACT_AH_PLATFORM_CAPSULE'),
   'MARKER':("delete from erp.schema_migrations where version='v2.6.20ah'",'AI_REQUIRES_EXACT_AH_WITHOUT_AI_RESIDUE')}
  actors.admin(cur)
  if mode=='UNRELATED_FUNCTION_BINDING':
   cur.execute("alter function erp.post_sale_v2(uuid,uuid,bigint) set work_mem='64MB'")
   try:runtime.verify_predecessor(cur)
   except AssertionError as exc:
    assert 'AH_LIVE_FUNCTION_DRIFT' in str(exc),str(exc)
    return dict(status='PASS',preapply_full_catalog_refusal=str(exc))
   raise AssertionError('Unrelated function drift accepted')
  query,error=mutations[mode];cur.execute(query);cur.execute('set local role postgres')
  result=ah.ag.expected_refusal(cur,lambda:cur.execute(ah.ag.sql_body(runtime.MIGRATION),prepare=False),error)
  cur.execute('reset role');return dict(status='PASS',refusal=result)
 return case

def repaired(fn):
 def run(cur,day):
  result=fn(cur,day);assert result['status']=='CONTROL_PASS',result
  if result.get('refusal') and result.get('change'):
   assert 'AI_WORK_SOURCE_SNAPSHOT_MISMATCH' in result['refusal']['error']['message'],result
  result['status']='PASS';return result
 return run

def work_lifecycle(mode):
 def run(cur,day):
  f=original.work_draft(cur,day,Decimal('1.25'))
  if mode in ('REBUILD','ROUND_TRIP'):
   other=original.work_draft(cur,day,Decimal('2.50'))
   original.returns.success(peer.operation(cur,'update erp.work_completion_events set po_id=%s,cutting_group_id=%s where id=%s',(other['po'],other['group'],f['completion'])))
   if mode=='ROUND_TRIP':
    original.returns.success(peer.operation(cur,'update erp.work_completion_events set po_id=%s,cutting_group_id=%s where id=%s',(f['po'],f['group'],f['completion'])))
   else:
    original.returns.success(peer.operation(cur,'update erp.work_completion_lines set po_component_snapshot_id=%s where completion_id=%s',(other['snapshot'],f['completion'])))
    f['rate']=Decimal('2.50')
  elif mode=='RATE_NORMALIZATION':
   original.returns.success(peer.operation(cur,'update erp.work_completion_lines set rate_snapshot=99 where completion_id=%s',(f['completion'],)))
  elif mode=='USED_SNAPSHOT':
   refusal=original.returns.refusal(cur,'update erp.po_work_component_snapshots set rate_per_pcs_snapshot=99 where id=%s',(f['snapshot'],),'already used by work completion and is immutable')
  result=original.qualified_work_control(cur,f)
  return dict(status='PASS',control=result,report=report(cur,day))
 return run

def partial_work(cur,day):
 f=original.work_draft(cur,day,Decimal('1.25'))
 original.returns.success(peer.operation(cur,'update erp.work_completion_lines set qty_completed=4,qty_payable=4 where completion_id=%s',(f['completion'],)))
 first=peer.operation(cur,'select erp.post_work_completion(%s)',(f['completion'],));original.returns.success(first)
 actors.admin(cur);header=base.one(cur,'select to_jsonb(h) from erp.work_completion_events h where id=%s',(f['completion'],))
 def next_draft(qty):
  target=uuid.uuid4();peer.ordinary(cur)
  cur.execute("insert into erp.work_completion_events(id,completion_number,po_id,contractor_id,cutting_group_id,physical_at,status) values(%s,%s,%s,%s,%s,%s,'DRAFT')",(target,'AI-PART-'+target.hex,header['po_id'],header['contractor_id'],header['cutting_group_id'],header['physical_at']))
  cur.execute('insert into erp.work_completion_lines(completion_id,po_component_snapshot_id,work_component_id,qty_completed,qty_payable,rate_snapshot) values(%s,%s,%s,%s,%s,0)',(target,f['snapshot'],f['component'],qty,qty))
  return target
 second=next_draft(6);original.returns.success(peer.operation(cur,'select erp.post_work_completion(%s)',(second,)))
 third=next_draft(1)
 error=original.returns.refusal(cur,'select erp.post_work_completion(%s)',(third,),'melebihi Potongan efektif')
 actors.admin(cur)
 amount=base.one(cur,"select sum(l.amount_payable) from erp.work_completion_lines l join erp.work_completion_events e on e.id=l.completion_id where e.po_id=%s and e.status='POSTED'",(f['po'],))
 assert amount==Decimal('12.50'),amount
 return dict(status='PASS',expected_total='12.50',actual=amount,over_limit=error,report=report(cur,day))

def detector(mode):
 def run(cur,day):
  f=original.work_draft(cur,day,Decimal('1.25'))
  other=original.work_draft(cur,day,Decimal('2.50'))
  original.returns.success(peer.operation(cur,'select erp.post_work_completion(%s)',(f['completion'],)))
  actors.admin(cur);cur.execute('set local session_replication_role=replica')
  if mode=='PO':cur.execute('update erp.work_completion_events set po_id=%s,cutting_group_id=%s where id=%s',(other['po'],other['group'],f['completion']))
  elif mode=='SNAPSHOT':cur.execute('update erp.work_completion_lines set po_component_snapshot_id=%s where completion_id=%s',(other['snapshot'],f['completion']))
  elif mode=='RATE':cur.execute('update erp.work_completion_lines set rate_snapshot=9 where completion_id=%s',(f['completion'],))
  elif mode=='GROUP':cur.execute('update erp.work_completion_events set cutting_group_id=%s where id=%s',(other['group'],f['completion']))
  elif mode=='EMPTY':cur.execute('delete from erp.work_completion_lines where completion_id=%s',(f['completion'],))
  else:raise AssertionError(mode)
  cur.execute('set local session_replication_role=origin')
  result=report(cur,day,True);result.update(synthetic_detector_control=True,not_a_new_business_counterexample=True)
  return result
 return run

def phase_cases(phase):
 if phase=='admission':return [(m,admission(m)) for m in ('CLEAN','VALID_WORK_DRAFT','ORIGINAL_WORK_SOURCE','FUNCTION','ACL','PLATFORM','MARKER','UNRELATED_FUNCTION_BINDING')]
 if phase=='focused':return [(n,repaired(fn)) for n,fn in original.cases()]+[(m,work_lifecycle(m)) for m in ('REBUILD','ROUND_TRIP','RATE_NORMALIZATION','USED_SNAPSHOT')]+[('PARTIAL_WORK',partial_work)]+[('AH_'+n,fn) for n,fn in ah.phase_cases('focused')]
 if phase=='detector':return [(m,detector(m)) for m in ('PO','SNAPSHOT','RATE','GROUP','EMPTY')]+[('AH_'+n,fn) for n,fn in ah.phase_cases('detector')]
 if phase=='crossflow':return ah.phase_cases('crossflow')
 raise AssertionError(phase)

def run(phase):
 head,tree=runtime.verify_audit_source();assert os.environ.get('PGURL')==peer.URL and os.environ.get('CP6_AI_CONFIRM')=='postgres'
 result=dict(status='INCOMPLETE',phase=phase,head=head,tree=tree,run_id=os.environ.get('GITHUB_RUN_ID'),cases={},production_go=False,http_ui_csv_reachability_proven=False)
 with psycopg.connect(peer.URL.replace('postgres:postgres@','supabase_admin:postgres@')) as conn,conn.cursor() as cur:
  cur.execute("set local timezone='Asia/Jakarta';set local statement_timeout='240s';set local lock_timeout='8s'")
  untouched=actors.boundary(cur);catalog=function_catalog(cur)
  if phase=='admission':
   runtime.verify_predecessor(cur);save('AH_COMPLETE_CATALOG',catalog);save('AH_COMPLETE_BOUNDARY',snapshot(cur))
  else:assert len(runtime.verified_successor(cur))==690
  usage=base.one(cur,"select has_schema_privilege('authenticated','erp','USAGE')");result['schema_usage_fixture_grant']=not usage
  if not usage:cur.execute('grant usage on schema erp to authenticated')
  cur.execute("select set_config('request.jwt.claims',%s,true)",(json.dumps(dict(sub=base.OPERATOR_AUTH,role='authenticated')),))
  base.load_fixture_foundation(cur);actors.admin(cur)
  day=base.one(cur,"select (statement_timestamp() at time zone 'Asia/Jakarta')::date")-timedelta(days=3)
  prior.set_open_period(cur,date(2026,8,31) if phase=='crossflow' else day-timedelta(days=5))
  for name,case in phase_cases(phase):
   actors.admin(cur);before=actors.boundary(cur);cur.execute('savepoint ai_case')
   try:record=case(cur,day)
   except Exception as exc:record=dict(status='FAIL',error=str(exc),traceback=traceback.format_exc())
   finally:cur.execute('rollback to savepoint ai_case');actors.admin(cur);cur.execute('release savepoint ai_case')
   record['full_boundary_restored']=actors.boundary(cur)==before
   if not record['full_boundary_restored']:record['status']='FAIL'
   result['cases'][name]=record;save(phase,result)
   print(json.dumps(dict(phase=phase,case=name,status=record['status'],error=record.get('error'))),flush=True)
  actors.admin(cur);result['function_catalog_unchanged']=function_catalog(cur)==catalog
  conn.rollback();cur.execute("set local timezone='Asia/Jakarta'")
  result['unseeded_boundary_restored']=actors.boundary(cur)==untouched
  result['schema_usage_restored']=base.one(cur,"select has_schema_privilege('authenticated','erp','USAGE')")==usage
  result['auth_users'],result['app_users']=cur.execute('select (select count(*) from auth.users),(select count(*) from erp.app_users)').fetchone();conn.rollback()
 result.update(passed=sum(c['status']=='PASS' for c in result['cases'].values()),failed=sum(c['status']!='PASS' for c in result['cases'].values()))
 if all(result[k] for k in ('function_catalog_unchanged','unseeded_boundary_restored','schema_usage_restored')) and result['auth_users']==result['app_users']==result['failed']==0:result['status']='PASS'
 save(phase,result);return result

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--phase',choices=('admission','focused','detector','crossflow'),required=True);phase=parser.parse_args().phase
 try:result=run(phase)
 except Exception as exc:result=dict(status='FAIL',phase=phase,error=str(exc),traceback=traceback.format_exc(),production_go=False);save(phase,result)
 print(json.dumps({k:v for k,v in result.items() if k!='cases'}));raise SystemExit(0 if result['status']=='PASS' else 1)
