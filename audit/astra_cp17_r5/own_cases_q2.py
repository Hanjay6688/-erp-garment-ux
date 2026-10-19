"""Astra r5 independent expected values; fixture provenance in manifest.
All private DDL/corruption is disposable diagnostic setup, never app reachability.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from decimal import Decimal as D, ROUND_HALF_UP
import hashlib,json,re,time,uuid
import psycopg
import cp6_bd_probe as bd
import cp7_nota_source_cases as src
import cp7_nota_cases as nota
import cp7_finance_analysis_cases as fin
import cp7_report_accounts_bundle as ra
import cp7_payroll_checks_bundle as pc
from reader_fixtures import reader_fixtures,reader_inputs

NATIVE=['ASTRA_R5_FG_HEALTHY_8000','ASTRA_R5_FG_DETECTOR_0_1_0','ASTRA_R5_FG_REVERSED_REUSE',
 'ASTRA_R5_READERS_NONEMPTY','ASTRA_R5_READERS_EMPTY','ASTRA_R5_MAPPING_REBIND',
 'ASTRA_R5_CORE_MAPPING_GUARDS','ASTRA_R5_INSTALL_ROUNDTRIP_REFUSALS',
 'ASTRA_R5_FINANCE_DECIMAL_ORACLE','ASTRA_R5_READER_CONTEXTS']
RACE=['ASTRA_R5_MAPPING_COMMIT_SNAPSHOT']
EXPECTED=len(NATIVE)+len(RACE)
OWNER_AUTH=str(bd.chain.production.base.OPERATOR_AUTH)
TARGET='run_v263a_payroll_integrity_checks:payroll_work_wrong_contractor'
GUARD='trg_guard_fg_unsourced_repair_wages_v1_immutable'
WRAP=re.compile(r"\(select erp\.account_id\('([A-Z0-9_]+)'\)\)")

def one(cur,s,args=()):return cur.execute(s,args).fetchone()[0]
def ctx(cur,subject=OWNER_AUTH):
 bd.api.admin(cur)
 cur.execute("select set_config('request.jwt.claims',%s,true)",(json.dumps(dict(sub=subject,role='authenticated')),))
def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True,default=str).encode()).hexdigest()
def detectors(cur):
 out={}
 for fn in bd.bcp.DETECTORS:
  bd.api.admin(cur);bd.chain.production.owner(cur)
  rows=cur.execute('select check_name,severity,issue_count,details from erp.'+fn+'()').fetchall()
  for name,severity,n,details in rows:
   key=fn+':'+name;assert key not in out
   out[key]=dict(count=int(n),severity=severity,details=details)
 bd.api.admin(cur);return out
def counts(d):return {k:v['count'] for k,v in d.items()}
def diff(a,b):
 assert set(a)==set(b)
 return {k:b[k]['count']-a[k]['count'] for k in a if b[k]['count']!=a[k]['count']}
def repair_note(cur,today):
 f=src.ax.repair_fixture(cur,today)
 receipts=[src.ax.post(cur,src.ax.repair_payload(f,q)) for q in (1,3)]
 bd.api.admin(cur);before=nota.facts(cur)
 draft=nota.command(cur,'SAVE',nota.payload(cur,f,today));key=uuid.uuid4()
 posted=nota.act(cur,'POST',draft,key)
 assert nota.act(cur,'POST',draft,key)==posted
 assert cur.execute('select count(*),sum(qty_payable),sum(amount) from erp.payroll_work_items where payroll_id=%s',(posted['payroll_id'],)).fetchone()==(2,D(4),D(8000))
 assert cur.execute('select labor_total,net_payable,settled_at from erp.payroll_settlements where id=%s',(posted['payroll_id'],)).fetchone()==(D(8000),D(8000),None)
 assert nota.facts(cur)==before,'NOTA_REPEATED_PHYSICAL_OR_MONEY_FACTS'
 return f,posted,receipts
def prior_payroll(cur):
 definition=one(cur,'select pg_get_functiondef(%s::regprocedure)',(pc.SIGNATURE,))
 start=definition.index('  -- R5-01 (Sol SOL-R4-001,')
 end=definition.index("  where ps.status <> 'REVERSED'",start)
 old=definition[:start]+definition[end:]
 old=old.replace('coalesce(wce.contractor_id, ro.contractor_id, fgw.contractor_id)','coalesce(wce.contractor_id, ro.contractor_id)')
 assert 'fgw.' not in old and old!=definition
 return old
def clones(cur):
 ctx(cur);cur.execute('create schema astra_r5_before')
 defs={}
 for sig,n in ra.READERS.items():
  current=one(cur,'select pg_get_functiondef(%s::regprocedure)',(sig,))
  old,count=WRAP.subn(lambda m:"erp.account_id('"+m[1]+"')",current)
  assert count==n and old!=current,(sig,count,n)
  name=sig.split('(')[0]
  cur.execute(old.replace('FUNCTION '+name+'(','FUNCTION astra_r5_before.'+name.split('.')[1]+'(',1),prepare=False)
  defs[sig]=dict(current=current,prior=old)
 return defs
def answer(cur,fn,args,subject=OWNER_AUTH):
 ctx(cur,subject);cur.execute('savepoint astra_answer')
 try:
  rows=cur.execute('select to_jsonb(x)::text from '+fn+'('+','.join(['%s']*len(args))+') x',args).fetchall()
  return dict(kind='ROWS',rows=sorted(r[0] for r in rows))
 except psycopg.Error as e:
  cur.execute('rollback to savepoint astra_answer')
  return dict(kind='ERR',code=e.sqlstate,message=str(e).splitlines()[0])
 finally:cur.execute('release savepoint astra_answer');bd.api.admin(cur)
def compare(cur,inputs,subject=OWNER_AUTH):
 out={}
 for sig in ra.READERS:
  fn=sig.split('(')[0];pairs=[]
  for args in inputs.get(sig,[()]):
   a=answer(cur,fn,args,subject);b=answer(cur,fn.replace('erp.','astra_r5_before.',1),args,subject)
   pairs.append(dict(args=list(args),candidate=a,prior=b,equal=a==b))
  assert pairs,('VACUOUS_READER',sig)
  out[sig]=pairs
 return out
def assert_same(observed):
 differences=[dict(signature=s,**p) for s,rows in observed.items() for p in rows if not p['equal']]
 assert not differences,('READER_ANSWER_CHANGED',differences)
def mutation(cur,sql,args=()):
 bd.api.admin(cur);cur.execute('savepoint astra_mutation')
 try:cur.execute(sql,args if args else None,prepare=False);return dict(kind='ALLOW')
 except psycopg.Error as e:
  cur.execute('rollback to savepoint astra_mutation')
  return dict(kind='ERR',code=e.sqlstate,message=str(e).splitlines()[0])
 finally:cur.execute('release savepoint astra_mutation');bd.api.admin(cur)
def alternative(cur,key):
 ctx(cur)
 old=one(cur,'select account_id from erp.accounting_account_mappings where mapping_key=%s',(key,))
 new=one(cur,"""insert into erp.chart_accounts(account_code,account_name,account_type,report_group,normal_balance,is_postable,is_active)
 select %s,'Astra alternate mapping',account_type,report_group,normal_balance,true,true from erp.chart_accounts where id=%s returning id""",('ASR5'+uuid.uuid4().hex[:10],old))
 return old,new
def replace_mapping(cur,key,new):
 ctx(cur);cur.execute('update erp.accounting_account_mappings set account_id=%s where mapping_key=%s',(new,key))
 assert one(cur,'select erp.account_id(%s)',(key,))==new

def cases(cur,today):
 def healthy():
  before=detectors(cur);assert all(v==0 for v in counts(before).values()),counts(before)
  f,n,receipts=repair_note(cur,today);after=detectors(cur)
  assert diff(before,after)=={},diff(before,after)
  ctx(cur);cur.execute('create schema astra_r5_old_payroll')
  old=prior_payroll(cur).replace('FUNCTION erp.run_v263a_payroll_integrity_checks()','FUNCTION astra_r5_old_payroll.checks()',1)
  cur.execute(old,prepare=False)
  original=list(cur.execute('select check_name,severity,issue_count,details from astra_r5_old_payroll.checks()').fetchall())
  assert next(x[2] for x in original if x[0]=='payroll_work_wrong_contractor')==2,original
  assert src.ax.payable_balance(cur,f['contractor'])==D(8000)
  return dict(status='PASS',expected=dict(qty=4,labor='8000',payable='8000',paid=False,legacy_false_alarms=2),before=before,after=after,legacy=original,receipt_ids=receipts)
 def corrupted():
  before=detectors(cur);f,n,_=repair_note(cur,today);healthy=detectors(cur);assert diff(before,healthy)=={}
  wages=[x[0] for x in cur.execute('select source_id from erp.payroll_work_items where payroll_id=%s order by qty_payable',(n['payroll_id'],)).fetchall()]
  other=src.ax.repair_fixture(cur,today)['contractor'];bd.api.admin(cur)
  blocked=mutation(cur,'update erp.fg_unsourced_repair_wages_v1 set contractor_id=%s where id=%s',(other,wages[0]))
  assert blocked['kind']=='ERR' and 'IMMUTABLE' in blocked['message'].upper(),blocked
  snapshots={}
  for label,sql,args in [('wrong','update erp.fg_unsourced_repair_wages_v1 set contractor_id=%s where id=%s',(other,wages[0])),('missing','delete from erp.fg_unsourced_repair_wages_v1 where id=%s',(wages[1],))]:
   cur.execute('savepoint astra_corrupt');cur.execute('alter table erp.fg_unsourced_repair_wages_v1 disable trigger '+GUARD)
   cur.execute(sql,args);cur.execute('alter table erp.fg_unsourced_repair_wages_v1 enable trigger '+GUARD)
   snapshots[label]=detectors(cur);assert diff(healthy,snapshots[label]).get(TARGET)==1
   cur.execute('rollback to savepoint astra_corrupt');cur.execute('release savepoint astra_corrupt')
   snapshots[label+'_rollback']=detectors(cur);assert snapshots[label+'_rollback']==healthy
  assert one(cur,'select tgenabled from pg_trigger where tgname=%s',(GUARD,))=='O'
  return dict(status='PASS',append_only_refusal=blocked,before=before,healthy=healthy,injections=snapshots,diagnostic_only=True)
 def reversed_reuse():
  f,n,_=repair_note(cur,today);before=nota.facts(cur)
  bd.chain.production.owner(cur);cur.execute('select erp.cancel_unpaid_payroll(%s,%s)',(n['payroll_id'],'Astra lawful cancellation and reallocation'));bd.api.admin(cur)
  assert one(cur,'select status from erp.payroll_settlements where id=%s',(n['payroll_id'],))=='REVERSED'
  cancelled=detectors(cur);assert cancelled[TARGET]['count']==0
  wage=one(cur,'select source_id from erp.payroll_work_items where payroll_id=%s limit 1',(n['payroll_id'],))
  cur.execute('savepoint astra_reversed_missing');cur.execute('alter table erp.fg_unsourced_repair_wages_v1 disable trigger '+GUARD)
  cur.execute('delete from erp.fg_unsourced_repair_wages_v1 where id=%s',(wage,));cur.execute('alter table erp.fg_unsourced_repair_wages_v1 enable trigger '+GUARD)
  ignored=detectors(cur);assert ignored[TARGET]['count']==0
  cur.execute('rollback to savepoint astra_reversed_missing');cur.execute('release savepoint astra_reversed_missing')
  again=nota.act(cur,'POST',nota.command(cur,'SAVE',nota.payload(cur,f,today)))
  assert again['payroll_id']!=n['payroll_id']
  assert one(cur,"select sum(i.amount) from erp.payroll_work_items i join erp.payroll_settlements p on p.id=i.payroll_id where p.contractor_id=%s and p.status<>'REVERSED'",(f['contractor'],))==D(8000)
  assert nota.facts(cur)==before and src.ax.payable_balance(cur,f['contractor'])==D(8000)
  final=detectors(cur);assert all(v==0 for v in counts(final).values()),counts(final)
  return dict(status='PASS',cancelled=cancelled,reversed_missing_diagnostic=ignored,final=final,active_labor='8000',payable='8000',physical_and_economic_facts_unchanged=True)
 def nonempty():
  fixture=reader_fixtures(cur,today);clones(cur);inputs=reader_inputs(cur,today)
  before=nota.facts(cur);out=compare(cur,inputs);assert_same(out)
  assert all(any(p['candidate']['kind']=='ROWS' for p in rows) for rows in out.values()),out
  assert nota.facts(cur)==before
  return dict(status='PASS',fixture=fixture,observed=out,business_facts_unchanged=True)
 def empty():
  clones(cur);u=uuid.uuid4();inputs={}
  for sig in ra.READERS:
   if sig.endswith('(uuid)'):inputs[sig]=[(u,),(None,)]
   elif sig.endswith('(uuid,uuid)'):inputs[sig]=[(u,u),(None,None)]
   elif sig.endswith('(date,date,date)'):inputs[sig]=[(today-timedelta(days=1000),)*3]
  out=compare(cur,inputs);assert_same(out)
  return dict(status='PASS',observed=out,empty_source_and_null_arguments=True)
 def mapping():
  fixture=reader_fixtures(cur,today);clones(cur);inputs=reader_inputs(cur,today);before=compare(cur,inputs);assert_same(before)
  old,new=alternative(cur,'WIP');replace_mapping(cur,'WIP',new)
  changed=[]
  for i in range(7):
   current=compare(cur,inputs);assert_same(current)
   changed.append(dict(iteration=i,sha256=digest(current)))
  assert digest(current)!=digest(before),'MAPPING_REBIND_FIXTURE_DID_NOT_AFFECT_ANY_READER'
  replace_mapping(cur,'WIP',old);after=compare(cur,inputs);assert_same(after);assert after==before
  return dict(status='PASS',fixture=fixture,prior_mapping=str(old),alternate=str(new),before=before,changed=current,repeated=changed,restored=after)
 def mapping_guards():
  ctx(cur);before=list(cur.execute('select mapping_key,account_id from erp.accounting_account_mappings order by mapping_key').fetchall());out={}
  for key in ra.KEYS:
   for kind,sql,args in [('delete','delete from erp.accounting_account_mappings where mapping_key=%s',(key,)),('rename','update erp.accounting_account_mappings set mapping_key=%s where mapping_key=%s',('ASTRA_'+key,key))]:
    r=mutation(cur,sql,args);out[key+':'+kind]=r
    assert r['kind']=='ERR' and r['code']=='P0001' and 'mapping' in r['message'].lower(),(key,kind,r)
  assert list(cur.execute('select mapping_key,account_id from erp.accounting_account_mappings order by mapping_key').fetchall())==before
  return dict(status='PASS',refusals=out,all_17_keys_unchanged=True)
 def roundtrip():
  defs=clones(cur);catalog=lambda:{s:cur.execute('select pg_get_functiondef(oid),pg_get_userbyid(proowner),proacl::text,provolatile::text,proconfig from pg_proc where oid=%s::regprocedure',(s,)).fetchone() for s in list(ra.READERS)+[pc.SIGNATURE]}
  ctx(cur);before=catalog();old_payroll=prior_payroll(cur)
  for d in defs.values():cur.execute(d['prior'],prepare=False)
  cur.execute(old_payroll,prepare=False)
  cur.execute(pc.extension(),prepare=False);cur.execute(ra.extension(),prepare=False)
  assert catalog()==before,'ROUNDTRIP_DEFINITION_OWNER_ACL_VOLATILITY_CONFIG_CHANGED'
  refusals={}
  cur.execute('savepoint astra_missing_mapping')
  for d in defs.values():cur.execute(d['prior'],prepare=False)
  cur.execute('alter table erp.accounting_account_mappings disable trigger user')
  cur.execute("delete from erp.accounting_account_mappings where mapping_key='WIP'")
  cur.execute('alter table erp.accounting_account_mappings enable trigger user')
  refusals['missing_mapping']=mutation(cur,ra.extension())
  assert refusals['missing_mapping'].get('message')=='CP7_R5_02_ACCOUNT_MAPPING_MISSING',refusals
  assert all(one(cur,'select pg_get_functiondef(%s::regprocedure)',(s,))==d['prior'] for s,d in defs.items())
  cur.execute('rollback to savepoint astra_missing_mapping');cur.execute('release savepoint astra_missing_mapping')
  sig='erp.run_v268_financial_report_checks()';drift=defs[sig]['prior'].replace('begin',"begin perform erp.account_id('WIP');",1)
  cur.execute('savepoint astra_drift');cur.execute(drift,prepare=False)
  refusals['extra_literal']=mutation(cur,ra.block(sig))
  assert 'CP7_R5_02_READER_SOURCE_CHANGED' in refusals['extra_literal'].get('message',''),refusals
  assert one(cur,'select pg_get_functiondef(%s::regprocedure)',(sig,))==drift
  cur.execute('rollback to savepoint astra_drift');cur.execute('release savepoint astra_drift')
  assert catalog()==before
  return dict(status='PASS',refusals=refusals,definitions={s:digest(v) for s,v in before.items()},restored_metadata_exact=True,missing_mapping_is_diagnostic_corruption=True)
 def numbers():
  day=today-timedelta(days=1);fin.receipt.aa.prior.set_open_period(cur,day-timedelta(days=4));q=fin.query(day)
  before=fin.read(cur,q);assert D(before['comparison']['current']['performance']['sales_revenue_gl'])==0
  fin.dated_sale(cur,day-timedelta(days=1),'100.01','66.67');fin.dated_sale(cur,day,'221.11','97.03')
  facts=nota.facts(cur);r=fin.read(cur,q);c=r['comparison']
  assert [D(c[k]['performance']['sales_revenue_gl']) for k in ('baseline','current')]==[D('100.01'),D('221.11')]
  assert [D(c[k]['performance']['cogs_gl']) for k in ('baseline','current')]==[D('66.67'),D('97.03')]
  assert [D(c[k]['performance']['gross_profit']) for k in ('baseline','current')]==[D('33.34'),D('124.08')]
  growth=((D('221.11')-D('100.01'))/D('100.01')*100).quantize(D('.0001'),rounding=ROUND_HALF_UP)
  margin=(D('124.08')/D('221.11')*100-D('33.34')/D('100.01')*100).quantize(D('.0001'),rounding=ROUND_HALF_UP)
  assert D(c['revenue_growth_pct'])==growth and D(c['gross_margin_change_pp'])==margin
  again=fin.read(cur,q);assert again['comparison']==c and nota.facts(cur)==facts
  return dict(status='PASS',expected=dict(revenue=['100.01','221.11'],hpp=['66.67','97.03'],profit=['33.34','124.08'],growth=str(growth),margin_delta=str(margin)),observed=c,no_read_side_effect=True,role='authenticated OWNER through public finance facade')
 def contexts():
  clones(cur);inputs={s:[(uuid.uuid4(),)] for s in ra.READERS if s.endswith('(uuid)')}
  inputs['erp.sale_lifecycle_po_hpp_amount_v2620d(uuid,uuid)']=[(uuid.uuid4(),uuid.uuid4())]
  inputs['erp.get_owner_financial_snapshot_v2(date,date,date)']=[(today,today,today)]
  out=compare(cur,inputs,str(uuid.uuid4()))
  differences=[dict(signature=s,**p) for s,rows in out.items() for p in rows if not p['equal']]
  return dict(status='COUNTEREXAMPLE' if differences else 'PASS',observed=out,differences=differences,scope='database owner invoking internal helpers with unknown app actor; not public HTTP reachability')
 return [('ASTRA_R5_INSTALL_ROUNDTRIP_REFUSALS',roundtrip)]

def races(tools,today):
 def snapshot():
  with tools.connect() as conn,conn.cursor() as cur:
   day=today-timedelta(days=1);fin.dated_sale(cur,day,'221.11','97.03');ctx(cur)
   old,new=alternative(cur,'COGS');conn.commit()
  with tools.connect() as reader,reader.cursor() as r, tools.connect() as writer,writer.cursor() as w:
   ctx(r);pid=one(r,'select pg_backend_pid()');baseline=one(r,'select erp.get_owner_financial_snapshot_v2(%s,%s,%s)',(day,day,day));reader.commit()
   def reading():
    ctx(r)
    rows=r.execute('select g,erp.get_owner_financial_snapshot_v2(%s,%s,%s),pg_sleep(0.2) from generate_series(1,8) g',(day,day,day)).fetchall();reader.commit();return rows
   with ThreadPoolExecutor(max_workers=1) as pool:
    future=pool.submit(reading);deadline=time.monotonic()+15;observed=None
    while time.monotonic()<deadline:
     w.execute('select pg_stat_clear_snapshot()')
     observed=w.execute('select state,wait_event,query_start from pg_stat_activity where pid=%s',(pid,)).fetchone()
     if observed and observed[1]=='PgSleep':break
     time.sleep(.02)
    assert observed and observed[1]=='PgSleep',('READ_BARRIER_NOT_OBSERVED',observed)
    replace_mapping(w,'COGS',new);writer.commit();commit_at=one(w,'select clock_timestamp()');writer.commit()
    rows=future.result(timeout=30)
   assert len(rows)==8 and all(row[1]==baseline for row in rows),'ONE_STATEMENT_MIXED_MAPPING_SNAPSHOTS'
   ctx(r);after=one(r,'select erp.get_owner_financial_snapshot_v2(%s,%s,%s)',(day,day,day))
   assert D(str(baseline['performance']['cogs_gl']))==D('97.03') and D(str(after['performance']['cogs_gl']))==0,dict(baseline=baseline,after=after)
   assert after['data_confidence']['status']=='BLOCKED','REMAPPED_BOOK_FALSE_READY'
  return dict(status='PASS',reader_pid=pid,barrier=observed,mapping_commit_at=commit_at,old_account=str(old),new_account=str(new),within_statement=baseline,next_statement=after,all_eight_rows_same_snapshot=True)
 return [(RACE[0],snapshot)]

# New tool qualification, same case IDs and contract; no successful first-run case repeated.
NATIVE=['ASTRA_R5_INSTALL_ROUNDTRIP_REFUSALS']
EXPECTED=len(NATIVE)+len(RACE)
