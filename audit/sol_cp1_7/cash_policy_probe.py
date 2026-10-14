"""Sol INV-U05 paired public-command audit; no product or oracle patches.
Funded payment must pass. An empty newly created active bank without an explicit
overdraft policy must refuse atomically under Pro Max INV-U05. Any other refusal
is incomplete evidence, not a successful cash-balance guard. Fixture is synthetic.
"""
import hashlib,json,sys,uuid
from decimal import Decimal as D
from pathlib import Path
import psycopg
CANDIDATE=Path(__file__).resolve().parents[3]/'auditor'
sys.path.insert(0,str(CANDIDATE/'scripts'))
import cp7_f05_analysis_probe as probe
import cp7_supplier_payment_create_cases as pay
import cp7_note_correction_cases as notes
import cp7_sales_draft_cases as drafts
import cp7_sales_payment_cases as salespay
IDS=['SOL_CASH_FUNDED_PUBLIC_PAYMENT','SOL_CASH_EMPTY_BANK_WITHOUT_OVERDRAFT_POLICY']
original=probe.native.strict_group;observed=[]
def cases(cur,today):
 def info(f):
  pay.b.api.admin(cur)
  role=cur.execute('select r.role_code from erp.app_users a join erp.app_roles r on r.id=a.role_id where a.auth_user_id=%s',(pay.auth.base.OPERATOR_AUTH,)).fetchone()[0]
  assert role in ('OWNER','ADMIN')
  row=cur.execute('select to_jsonb(a)from erp.cash_accounts a where a.id=%s',(f['cash'],)).fetchone()[0]
  policy_columns=[x[0]for x in cur.execute("select column_name from information_schema.columns where table_schema='erp'and table_name='cash_accounts'and(column_name ilike '%negative%'or column_name ilike '%overdraft%')").fetchall()]
  return dict(actor_role=role,bank_master=row,overdraft_configuration_columns=policy_columns,
    evidence_origin='INDEPENDENT_NATIVE_RERUN',oracle_origin='SOL_LITERAL_INV_U05',
    fixture_origin='SYNTHETIC_REUSED_NATIVE_WRITERS_PLUS_FRESH_BANK_MASTER',production_go=False)
 def funded():
  f=pay.fixture(cur,today);assert pay.misc.cash_balance(cur,f['cash'])==0
  s=notes.stock(cur,today,qty=10);s['bank']=f['cash']
  drafts.create(cur,s,drafts.payload(s,'2','17.25'))
  p,v=drafts.cmd.review(cur,s);drafts.cmd.command(cur,'POST',p,v)
  salespay.pay(cur,s,'34.50')
  assert pay.misc.cash_balance(cur,f['cash'])==D('34.50')
  r=pay.command(cur,pay.payload(cur,f,'1.00'))
  assert r['status']=='POSTED'and r['remaining_after']=='999.00'
  assert pay.misc.cash_balance(cur,f['cash'])==D('33.50')
  return dict(info(f),status='PASS',expected_bank_before='34.50',expected_bank_after='33.50',
    actual_bank_after=str(pay.misc.cash_balance(cur,f['cash'])),public_payment_outcome=r,
    funding_from_real_public_sale_payment=True)
 def empty():
  f=pay.fixture(cur,today);setup=info(f);balance=pay.misc.cash_balance(cur,f['cash']);assert balance==0
  q=pay.payload(cur,f,'1.00');before=pay.b.boundary.snapshot(cur)
  error=None;result=None
  cur.execute('savepoint sol_cash_empty')
  try:result=pay.command(cur,q)
  except psycopg.Error as exc:
   error=dict(sqlstate=exc.sqlstate,message=exc.diag.message_primary)
   cur.execute('rollback to savepoint sol_cash_empty')
  finally:cur.execute('release savepoint sol_cash_empty');pay.b.api.admin(cur)
  after=pay.misc.cash_balance(cur,f['cash']);unchanged=pay.b.boundary.snapshot(cur)==before
  if result is not None:
   assert result['status']=='POSTED'and after==D('-1.00')and not unchanged,(result,after)
   status='COUNTEREXAMPLE'
  elif error and error['message'].startswith(('CP7_CASH_INSUFFICIENT_FUNDS','CASH_BALANCE_WOULD_BE_NEGATIVE'))and unchanged:status='PASS'
  else:status='INCOMPLETE'
  return dict(setup,status=status,expected='ATOMIC_CASH_CAPACITY_REFUSAL_UNLESS_EXPLICIT_OWNER_OVERDRAFT_POLICY',
    bank_before=str(balance),bank_after=str(after),requested_payment='1.00',
    public_payment_outcome=result,refusal=error,business_boundary_unchanged=unchanged,
    guide_inv='INV-U05',owner_policy_exception_not_found_in_authority_inventory=True)
 return [(IDS[0],funded),(IDS[1],empty)]
def wrapped(name,factory,verify):
 normal=original(name,factory,verify)
 if name=='CP7_K3_CLEANUP':
  r=original('SOL_CASH_POLICY',cases,verify);r.update(candidate_sha='0b7049d9203bac52b47a4c89f3e0d75646067a8f',
    probe_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),expected_ids=IDS,production_go=False)
  observed.append(r);(probe.OUT.parent/'SOL_CASH_POLICY.json').write_text(json.dumps(r,indent=2,default=str)+'\n')
  print(json.dumps(dict(sol_cash_policy=r),default=str),flush=True)
 return normal
probe.native.strict_group=wrapped
def runtime(browser_mode=False):
 normal=probe.run(k3_cleanup=True)
 assert len(observed)==1,'SOL_CASH_CASES_NOT_EXECUTED'
 assert set(observed[0]['cases'])==set(IDS)
 # A proved counterexample must remain red even if its fixture/cleanup passed.
 if observed[0].get('counts')!={'PASS':2}or not observed[0].get('complete_boundary_restored'):
  normal=dict(normal,status='INCOMPLETE',sol_cash_policy_counterexample_or_incomplete=True)
 return normal
probe.package._writer_runtime=runtime
if __name__=='__main__':probe.package.run('install')
