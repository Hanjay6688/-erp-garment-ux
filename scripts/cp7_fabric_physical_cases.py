"""P08 physical fabric facts on actual Native rolls, drafts and open commitments.

Every operand is created through an unchanged Native or CP7 public command: the
real receipt SAVE/POST, the explicit plan draft/apply bridge, the Native cutting
SAVE_DRAFT/POST writer and the opening-balance OPEN_PURCHASE_ORDER import. No
movement, draft, intent or commitment row is injected. Rates are explicit
fixture choices, never owner operating values; one kernel case is explicitly
synthetic and gives no Native credit.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from decimal import Decimal as D
from queue import Queue
import copy,json,time,uuid
import psycopg
import cp7_fabric_recipe_cases as fabric
plan=fabric.plan;parent=fabric.parent;b=fabric.b;auth=fabric.auth;receipt=plan.receipt
REQUIRED=dict(native=16,races=2,http=1,browser=2)
EXPECTED=sum(REQUIRED.values())
IDS=dict(native=['P08_PHYSICAL_SINGLE_FREE_STOCK','P08_PHYSICAL_SUFFICIENT_FREE_STOCK','P08_PHYSICAL_WIP_IDENTITY_UPPER_BOUND','P08_PHYSICAL_LINKED_DRAFT_KNOWN','P08_PHYSICAL_LINKED_DRAFT_PLUS_FREE',
  'P08_PHYSICAL_WRONG_MATERIAL_DRAFT','P08_PHYSICAL_OVERCOMMITTED_DRAFT','P08_PHYSICAL_UNLINKED_NATIVE_DRAFT','P08_PHYSICAL_INCOMING_ON_TIME',
  'P08_PHYSICAL_INCOMING_LATE','P08_PHYSICAL_INCOMING_NO_DATE','P08_PHYSICAL_INCOMING_OVERDUE','P08_PHYSICAL_SHARED_SPLIT_THEN_DRAFTS',
  'P08_PHYSICAL_RECEIPT_STALES_ORIGINAL','P08_PHYSICAL_POSTED_ISSUE_ONCE','P08_PHYSICAL_KERNEL_BRANCHES_SYNTHETIC'],
 races=['P08_PHYSICAL_REAL_MVCC_RECEIPT','P08_PHYSICAL_REAL_MVCC_NATIVE_POST'],http=['P08_PHYSICAL_REAL_AUTH_HTTP'],
 browser=['P08_PHYSICAL_BROWSER_DESKTOP','P08_PHYSICAL_BROWSER_MOBILE'])
KEYS=('installed_proven','unused_allocated_proven','additional_external')

def row(e,target):
 m=fabric.rows(e,target);assert len(m)==1,m;return m[0]
def value(f):return None if 'value'not in f else D(f['value'])
def expect(m,installed='0',unused=None,external=None,unused_state='ASSUMED',external_reason=None,unused_reason=None):
 """Exact physical oracle. A None value requires UNKNOWN with the named reason."""
 recipe=next(r for r in m['gross']['refs']if r['kind']=='CP7_FABRIC_RECIPE')
 for f in(m[k]for k in KEYS):assert any(r['kind']=='CP7_FABRIC_RECIPE'and r['id']==recipe['id']for r in f['refs']),m
 i,u,e=(m[k]for k in KEYS)
 if installed is None:assert i['state']=='UNKNOWN'and'value'not in i,m
 else:assert i['state']=='ASSUMED'and value(i)==D(installed)and recipe['id']in i['assumption_ids'],m
 if unused is None:assert u['state']=='UNKNOWN'and'value'not in u and(unused_reason is None or u['reason']==unused_reason),m
 else:assert u['state']==unused_state and value(u)==D(unused),m
 if external is None:assert e['state']=='UNKNOWN'and'value'not in e and(external_reason is None or e['reason']==external_reason),m
 else:assert e['state']=='ASSUMED'and value(e)==D(external)and recipe['id']in e['assumption_ids'],m
 g=value(m['gross'])
 if None not in(g,value(i),value(u),value(e)):assert value(e)<=max(D(0),g-value(i)-value(u)),m
 return m
def recipe(cur,today,rate='2',subject=None):
 f=fabric.setup(cur,today,subject);p=copy.deepcopy(f['payload']);p['config']['qty_per_good_pcs']=rate
 f['recipe']=fabric.save(cur,p,subject=subject);f['payload']=p;return f
def capture(cur,today,subject=None):
 fresh=parent.capture(cur,today,subject=subject);parent.checked(fresh);return fresh
def bound(cur,today,rate='2',subject=None):
 """Analysis fixture whose only WIP is an opening item bound to the exact
 product (CONFIRMED_TARGET): gap93, no ambiguous same-model WIP. One real
 posted ten-unit receipt of a fresh fabric; explicit recipe via the public
 command. Pattern stays unselected (optional, never guessed)."""
 opening,root,_,_=parent.setup(cur,today)
 fab=receipt.fixture(cur,today,qty='10',price='10');receipt.post(cur,receipt.command(cur,'SAVE_DRAFT',fab['payload']));b.api.admin(cur)
 e=parent.capture(cur,today,subject=subject);target=parent.recommendation(e['analysis'],root)['target']['key']
 assert D(parent.recommendation(e['analysis'],root)['q_conditional']['value'])==93
 sku=cur.execute('select material_sku from erp.materials where id=%s',(fab['material'],)).fetchone()[0]
 w=fabric.workspace(cur,dict(run_id=e['run_id'],target_key=target,material_query=sku,material_offset='0',pattern_offset='0',limit='50'),subject)
 m=next(x for x in w['materials']if x['id']==fab['material'])
 cfg=dict(basis='SELECTED_ASSUMPTIONS',effective_from=parent.schedule.stamp(cur.execute('select clock_timestamp()').fetchone()[0]-timedelta(minutes=1)),effective_to=None,
  material_id=m['id'],material_hash=m['source_hash'],unit=m['unit'],qty_per_good_pcs=rate,pattern_id=None,pattern_hash=None)
 payload=dict(run_id=w['run_id'],target_key=target,source_hash=w['source_hash'],expected_revision=w['revision'],config=cfg,reason='Explicit synthetic fixture rate per PCS; not factory recipe or consumption')
 out=fabric.save(cur,payload,subject=subject);b.api.admin(cur)
 roll=str(cur.execute('select id from erp.material_rolls where material_id=%s',(fab['material'],)).fetchone()[0])
 return dict(root=root,target=target,payload=payload,recipe=out,opening=opening,query=e['query'],
  plan=dict(payload=dict(cutting=dict(source_location_id=fab['location'],rolls=[dict(roll_id=roll)]))))
def upper(m,bound_value):
 """External is UNKNOWN for ambiguous same-model WIP, with the exact bound."""
 assert m['additional_external']['reason']=='FABRIC_WIP_IDENTITY_UNRESOLVED'and f'paling banyak {bound_value} 'in m['reason'],m
 return m
def material(f):return f['payload']['config']['material_id']
def roll(f):return f['plan']['payload']['cutting']['rolls'][0]['roll_id']
def location(f):return f['plan']['payload']['cutting']['source_location_id']
CLOCK_KEYS={'captured_at','generated_at','planning_time_bucket'}
def clock_only(a,b):
 """True when two captured sources differ only in capture-clock fields."""
 if isinstance(a,dict)and isinstance(b,dict):
  return set(a)==set(b)and all(k in CLOCK_KEYS or clock_only(a[k],b[k])for k in a)
 if isinstance(a,list)and isinstance(b,list):return len(a)==len(b)and all(clock_only(x,y)for x,y in zip(a,b))
 return a==b
def link(cur,today,f,issued,roll_id=None,location_id=None):
 """Explicit reviewed CP7 plan -> unchanged Native SAVE_DRAFT, linked by intent.
 The Original dependency includes the minute capacity clock. Only when the
 refused source differs from the stored one in capture-clock fields alone is
 the same composition re-reviewed once on a fresh Original; any physical or
 business difference still fails the case."""
 for attempt in(1,2):
  p=plan.current_payload(cur,today,f['plan'],issued)
  if roll_id:p['cutting']['rolls'][0]['roll_id']=roll_id;p['cutting']['source_location_id']=location_id
  d=plan.save(cur,p);cur.execute('savepoint p08_link')
  try:
   out=plan.apply(cur,plan.action(d));cur.execute('release savepoint p08_link');return out['native']['cutting_group_id'],p
  except psycopg.Error as error:
   cur.execute('rollback to savepoint p08_link');b.api.admin(cur)
   if attempt==2 or error.diag.message_primary!='CP7_PLAN_SOURCE_CHANGED':raise
   r=plan.source_diagnostic(cur,p['run_id'])
   assert clock_only(r['stored'],r['current']),('P08_LINK_SOURCE_CHANGED_BEYOND_CLOCK',r['stored_hash'],r['current_hash'])
def manual(cur,f,issued):
 """Unchanged Native SAVE_DRAFT without any CP7 intent (a cutting operator's own draft)."""
 cut=copy.deepcopy(f['plan']['payload']['cutting']);cut['rolls'][0].update(qty_issued=issued,qty_consumed=str(D(issued)/2),qty_reported_remaining=str(D(issued)/2))
 cut['notes']='P08 manual Native draft without CP7 intent'
 out=b.chain.production.rpc(cur,'public.erp_save_cutting_group_before_sewing_v2',dict(cut,action='SAVE_DRAFT',change_reason='P08 explicit manual Native draft'))
 b.api.admin(cur);return out
def receive(cur,today,f,qty):
 """Real receipt SAVE/POST of the same Native fabric at the same raw warehouse."""
 tag='P08R-'+uuid.uuid4().hex[:12];day=today-timedelta(days=3)
 payload=dict(purchase_number=tag,supplier_id=str(receipt.aa.prior.BASE_SUPPLIER),location_id=location(f),physical_at=receipt.aa.at(day,11).isoformat(),
  change_reason='P08 explicit second receipt of the reviewed fabric',lines=[dict(material_id=material(f),qty=qty,unit_price='10',price_state='ESTIMATED',
   price_source='MANUAL_ESTIMATE',rolls=[dict(roll_number=tag+'-R',qty=qty)])])
 return receipt.post(cur,receipt.command(cur,'SAVE_DRAFT',payload))
def commitment(cur,today,f,remaining,expected):
 """ALL-P04 opening OPEN_PURCHASE_ORDER through the unchanged import validate/finalize."""
 import cp6_bb_probe as bb
 sku=cur.execute('select material_sku from erp.materials where id=%s',(material(f),)).fetchone()[0]
 line=dict(po_number='PO-{C}',po_line_number='1',po_date=str(today-timedelta(days=15)),supplier_code='{C}',location_code='{C}',material_sku=sku,
  ordered_qty=remaining,received_before_cutover_qty='0',cancelled_before_cutover_qty='0',remaining_qty=remaining,unit_price='3')
 if expected is not None:line['expected_date']=str(expected)
 rows={'SUPPLIER':[dict(supplier_code='{C}',supplier_name='P08 PO supplier',supplier_type='MATERIAL')],
  'LOCATION':[dict(location_code='{C}',location_name='P08 PO gudang',location_type='RAW_MATERIAL_WAREHOUSE')],'OPEN_PURCHASE_ORDER':[line]}
 batch,code,cutover=bb.post_batch(cur,today,rows,prefix='P08');b.api.admin(cur)
 return cur.execute('select l.id from erp.bb_purchase_commitment_lines_v1 l join erp.bb_purchase_commitments_v1 c on c.id=l.commitment_id where c.batch_id=%s',(batch,)).fetchone()[0]
def refs(f,kind):return[r for r in f['refs']if r['kind']==kind]

def cases(cur,today):
 def single():
  f=bound(cur,today);before=b.boundary.snapshot(cur);e=capture(cur,today);m=expect(row(e,f['target']),'0','10','176')
  assert D(m['gross']['value'])==186 and refs(m['unused_allocated_proven'],'CP7_FABRIC_FREE_STOCK')and b.boundary.snapshot(cur)==before
  assert parent.recommendation(e['analysis'],f['root'])['feasible_new']['state']=='UNKNOWN'
  return dict(status='PASS',bound_gap93_rate2_gross186_installed0_unique_free10_external176=True,Native_boundary_unchanged_by_reads=True,global_feasibility_still_UNKNOWN=True,complete_material_row=m)
 def sufficient():
  f=bound(cur,today,'0.1');e=capture(cur,today);m=expect(row(e,f['target']),'0','9.3','0')
  return dict(status='PASS',gross9_3_covered_by_free_stock10_external0=True,complete_material_row=m)
 def identity():
  f=recipe(cur,today);e=capture(cur,today);m=expect(row(e,f['target']),None,'10',None,external_reason='FABRIC_WIP_IDENTITY_UNRESOLVED');upper(m,'160')
  assert m['installed_proven']['reason']=='FABRIC_WIP_IDENTITY_UNRESOLVED'
  return dict(status='PASS',unbound_same_model_WIP_NEEDS_CHECK_installed_and_external_UNKNOWN_upper_bound160=True,allocated10_still_proved=True,complete_material_row=m)
 def linked_known():
  f=recipe(cur,today);gid,_=link(cur,today,f,'10');e=capture(cur,today)
  m=expect(row(e,f['target']),None,'10',None,unused_state='KNOWN',external_reason='FABRIC_WIP_IDENTITY_UNRESOLVED');upper(m,'160')
  assert[r['id']for r in refs(m['unused_allocated_proven'],'erp.cutting_groups')]==[gid]and not refs(m['unused_allocated_proven'],'CP7_FABRIC_FREE_STOCK')
  return dict(status='PASS',linked_unposted_Native_draft10_covers_roll10_KNOWN_not_reservation=True,complete_material_row=m)
 def linked_plus_free():
  f=recipe(cur,today);gid,_=link(cur,today,f,'6');e=capture(cur,today)
  m=expect(row(e,f['target']),None,'10',None,external_reason='FABRIC_WIP_IDENTITY_UNRESOLVED');upper(m,'160')
  assert[r['id']for r in refs(m['unused_allocated_proven'],'erp.cutting_groups')]==[gid]and refs(m['unused_allocated_proven'],'CP7_FABRIC_FREE_STOCK')
  return dict(status='PASS',linked_draft6_plus_free4_counted_once=True,complete_material_row=m)
 def wrong_material():
  f=recipe(cur,today);other=receipt.fixture(cur,today,qty='10',price='10');receipt.post(cur,receipt.command(cur,'SAVE_DRAFT',other['payload']))
  b.api.admin(cur);other_roll=str(cur.execute('select id from erp.material_rolls where material_id=%s',(other['material'],)).fetchone()[0])
  gid,_=link(cur,today,f,'6',other_roll,other['location']);e=capture(cur,today)
  m=expect(row(e,f['target']),None,None,None,unused_reason='FABRIC_LINKED_DRAFT_NOT_ELIGIBLE',external_reason='FABRIC_LINKED_DRAFT_NOT_ELIGIBLE')
  return dict(status='PASS',linked_draft_on_other_fabric_never_counted_for_recipe_material=True,complete_material_row=m,draft=gid)
 def overcommitted():
  # Native SAVE_DRAFT checks each draft against roll stock alone, and the plan
  # budget counts linked drafts only. A later operator draft can therefore
  # over-commit the roll: linked6 + manual6 > stock10 covers no allocation.
  f=recipe(cur,today);gid,_=link(cur,today,f,'6');out=manual(cur,f,'6');e=capture(cur,today)
  m=expect(row(e,f['target']),None,None,None,unused_reason='FABRIC_LINKED_DRAFT_NOT_ELIGIBLE',external_reason='FABRIC_LINKED_DRAFT_NOT_ELIGIBLE')
  return dict(status='PASS',linked6_plus_manual6_above_roll_stock10_not_allocated=True,manual_native_outcome=out,complete_material_row=m)
 def unlinked():
  f=recipe(cur,today);out=manual(cur,f,'4');e=capture(cur,today)
  m=expect(row(e,f['target']),None,'0',None,unused_state='KNOWN',external_reason='FABRIC_UNLINKED_NATIVE_DRAFT')
  return dict(status='PASS',manual_unlinked_Native_draft_makes_split_UNKNOWN=True,manual_native_outcome=out,complete_material_row=m)
 def incoming(kind):
  def run():
   f=bound(cur,today);expected={'ON_TIME':today+timedelta(days=2),'LATE':today+timedelta(days=30),'NO_DATE':None,'OVERDUE':today-timedelta(days=1)}[kind]
   line=commitment(cur,today,f,'50',expected);e=capture(cur,today);m=row(e,f['target'])
   if kind=='ON_TIME':expect(m,'0','10','126');assert refs(m['additional_external'],'CP7_FABRIC_OPEN_COMMITMENTS')
   elif kind=='LATE':expect(m,'0','10','176')
   elif kind=='NO_DATE':expect(m,'0','10',None,external_reason='FABRIC_INCOMING_ETA_UNKNOWN')
   else:expect(m,'0','10',None,external_reason='FABRIC_INCOMING_OVERDUE')
   return dict(status='PASS',open_commitment_line=str(line),expected_date=str(expected),kind=kind,complete_material_row=m)
  return run
 def shared():
  first,second=plan.shared_material_setup(cur,today)
  ones=[review(cur,today,f)for f in(first,second)]
  e=capture(cur,today);rows=[row(e,f['payload']['target_key'])for f in(first,second)]
  for m in rows:expect(m,None,'0',None,unused_state='KNOWN',external_reason='FABRIC_SHARED_SUPPLY_SPLIT_UNDECIDED')
  g1,_=link(cur,today,dict(plan=first),'6');g2,_=link(cur,today,dict(plan=second),'4');e=capture(cur,today)
  after=[row(e,f['payload']['target_key'])for f in(first,second)]
  for m,own in zip(after,('6','4')):
   expect(m,None,own,None,unused_state='KNOWN',external_reason='FABRIC_WIP_IDENTITY_UNRESOLVED');upper(m,str(D(m['gross']['value'])-D(own)))
  return dict(status='PASS',two_claimants_free10_split_UNKNOWN_then_explicit_drafts6_and4_allocated=True,recipes=ones,before=rows,after=after)
 def stales():
  f=bound(cur,today);e=capture(cur,today);expect(row(e,f['target']),'0','10','176');receive(cur,today,f,'20')
  old=parent.read(cur,e['run_id']);assert old['source_state']=='ARCHIVED_STALE'and old['analysis']==e['analysis']
  fresh=capture(cur,today);m=expect(row(fresh,f['target']),'0','30','156')
  return dict(status='PASS',actual_second_receipt20_stales_immutable_original_fresh_free30_external156=True,complete_material_row=m)
 def posted_once():
  from cp7_plan_actual_cases import post
  f=recipe(cur,today);gid,p=link(cur,today,f,'6');p['cutting']['rolls'][0].update(qty_consumed='6',qty_reported_remaining='0')
  b.chain.production.rpc(cur,'public.erp_save_cutting_group_before_sewing_v2',dict(p['cutting'],id=gid,action='SAVE_DRAFT',change_reason='P08 consume whole issue'),expected_version=int(b.chain.base.group_version(cur,gid)))
  b.api.admin(cur);post(cur,dict(payload=p,group=gid));b.api.admin(cur);e=capture(cur,today);m=row(e,f['target'])
  expect(m,None,'4',None,external_reason='FABRIC_WIP_IDENTITY_UNRESOLVED');upper(m,str(max(D(0),D(m['gross']['value'])-4)))
  assert not refs(m['unused_allocated_proven'],'erp.cutting_groups')
  return dict(status='PASS',actual_Native_POST_issue6_stock10_to4_counted_once_issue_not_allocation=True,complete_material_row=m)
 def kernel():
  out=synthetic(cur)
  return dict(status='PASS',SYNTHETIC_KERNEL_ORACLE_NO_NATIVE_CREDIT=True,branches=out)
 return list(zip(IDS['native'],[single,sufficient,identity,linked_known,linked_plus_free,wrong_material,overcommitted,unlinked,
  incoming('ON_TIME'),incoming('LATE'),incoming('NO_DATE'),incoming('OVERDUE'),shared,stales,posted_once,kernel]))

def analysis_run(cur,today):return parent.capture(cur,today)['run_id']
def sku_of(cur,f):
 b.api.admin(cur);return cur.execute('select m.material_sku from erp.material_rolls r join erp.materials m on m.id=r.material_id where r.id=%s',(f['payload']['cutting']['rolls'][0]['roll_id'],)).fetchone()[0]
def review(cur,today,f):
 """Same explicit synthetic rate2 recipe for one plan target through the public command."""
 run=analysis_run(cur,today);q=dict(run_id=run,target_key=f['payload']['target_key'],material_query=sku_of(cur,f),material_offset='0',pattern_offset='0',limit='50')
 w=fabric.workspace(cur,q);roll_material=cur.execute('select material_id from erp.material_rolls where id=%s',(f['payload']['cutting']['rolls'][0]['roll_id'],)).fetchone()[0]
 m=next(x for x in w['materials']if x['id']==str(roll_material));p=w['patterns'][0]
 cfg=dict(basis='SELECTED_ASSUMPTIONS',effective_from=parent.schedule.stamp(cur.execute('select clock_timestamp()').fetchone()[0]-timedelta(minutes=1)),effective_to=None,
  material_id=m['id'],material_hash=m['source_hash'],unit=m['unit'],qty_per_good_pcs='2',pattern_id=p['id'],pattern_hash=p['source_hash'])
 return fabric.save(cur,dict(run_id=w['run_id'],target_key=w['target_key'],source_hash=w['source_hash'],expected_revision=w['revision'],config=cfg,
  reason='Explicit synthetic fixture rate2 per PCS; not factory recipe or consumption'))

def synthetic(cur):
 """Trusted-kernel branches on explicit synthetic source/netting JSON, as cp7_capture."""
 mat=str(uuid.uuid4());loc=str(uuid.uuid4());rid=str(uuid.uuid4());recipe_id=str(uuid.uuid4());pattern=None
 b.api.admin(cur)
 material_row=dict(id=mat,material_name='Synthetic fabric',material_type='FABRIC',unit_code='M',is_active=True)
 digest=lambda v:cur.execute('select cp7_fabric_native.material_hash(%s::jsonb)',(json.dumps(v),)).fetchone()[0]
 def source(rolls,drafts=(),locations=None,commitments=(),targets=('t1',)):
  selected=[dict(id=recipe_id if t=='t1'else str(uuid.uuid4()),target_key=t,revision=1,config=dict(material_id=mat,material_hash=digest(material_row),unit='M',qty_per_good_pcs='2',pattern_id=None,pattern_hash=None))for t in targets]
  return dict(captured_at='2026-10-05T03:00:00.000000Z',fabric_source=dict(contract_version='cp7.fabric-source.v2',selected=selected,materials=[material_row],patterns=[],
   physical=dict(contract_version='cp7.fabric-physical.v1',drafts=list(drafts),rolls=list(rolls),commitments=list(commitments),
    locations=locations if locations is not None else[dict(id=loc,location_type='RAW_MATERIAL_WAREHOUSE',is_active=True)])))
 def netting(rows,matches=()):
  return dict(rows=[dict(target_key=t,conditional_gap_pcs=g,production_policy=dict(policy=dict(state=s)),net=dict(inputs=dict(deadline=d)))for t,g,s,d in rows],
   match_results=[dict(position_key='p',target_key=t,result=dict(match=x))for t,x in matches])
 stock=lambda q:[dict(id=rid,material_id=mat,status='AVAILABLE',consistent=True,stock=[dict(location_id=loc,qty=q)])]
 deadline='2026-10-15T03:00:00.000000Z'
 def run(c,n):
  cur.execute('set local role cp7_capture')
  try:return cur.execute('select cp7_fabric_native.plan(%s::jsonb,%s::jsonb)',(json.dumps(c),json.dumps(n))).fetchone()[0]
  finally:b.api.admin(cur)
 out={}
 p=run(source(stock('10')),netting([('t1','85','ACTIVE',deadline)],[('t1','NEEDS_CHECK')]))['targets']['t1']
 assert p['installed']is None and p['installed_code']=='FABRIC_WIP_IDENTITY_UNRESOLVED'and p['unused']=='10'and p['external']is None and p['external_code']=='FABRIC_WIP_IDENTITY_UNRESOLVED'and p['external_upper_bound']=='160';out['identity_unresolved_upper_bound']=p
 p=run(source(stock('200')),netting([('t1','85','ACTIVE',deadline)],[('t1','UNKNOWN')]))['targets']['t1']
 assert p['installed']is None and p['external']is None and p['external_upper_bound']=='0'and p['unused']=='170';out['identity_unresolved_stock_covers_bound_still_UNKNOWN']=p
 p=run(source(stock('-1')),netting([('t1','85','ACTIVE',deadline)]))['targets']['t1']
 assert p['external_code']=='FABRIC_STOCK_INCONSISTENT'and p['installed']=='0';out['negative_stock']=p
 bad=stock('10');bad[0]['consistent']=False
 p=run(source(bad),netting([('t1','85','ACTIVE',deadline)]))['targets']['t1'];assert p['external_code']=='FABRIC_STOCK_INCONSISTENT';out['material_mismatch']=p
 line=dict(id=str(uuid.uuid4()),commitment_id=str(uuid.uuid4()),po_number='PO',line_number='1',material_id=mat,location_id=str(uuid.uuid4()),expected_date='2026-10-07',remaining='50')
 p=run(source(stock('10'),commitments=[line],locations=[dict(id=loc,location_type='RAW_MATERIAL_WAREHOUSE',is_active=True),dict(id=line['location_id'],location_type='RAW_MATERIAL_WAREHOUSE',is_active=False)]),netting([('t1','85','ACTIVE',deadline)]))['targets']['t1']
 assert p['external_code']=='FABRIC_INCOMING_LOCATION_NOT_ELIGIBLE';out['inactive_commitment_location']=p
 ok=dict(line,location_id=loc)
 p=run(source(stock('10'),commitments=[ok]),netting([('t1','85','ACTIVE',None)]))['targets']['t1'];assert p['external_code']=='FABRIC_DEADLINE_UNKNOWN';out['deadline_unknown']=p
 p=run(source(stock('10'),commitments=[ok]),netting([('t1','85','ACTIVE',deadline)]))['targets']['t1'];assert p['external']=='110'and p['unused']=='10';out['on_time_O09']=p
 p=run(source(stock('10')),netting([('t1','85','STOPPED',deadline)]))['targets']['t1'];assert p['external_code']=='FABRIC_PRODUCTION_DISABLED'and p['unused']=='0';out['production_disabled']=p
 p=run(source(stock('10')),netting([('t1','85','ACTIVE',deadline),('other','5','ACTIVE',deadline)]))['targets']['t1']
 assert p['external_code']=='FABRIC_OTHER_NEEDS_UNREVIEWED'and p['unused']=='0';out['other_unreviewed_need']=p
 p=run(source(stock('0')),netting([('t1','85','ACTIVE',deadline),('other','5','ACTIVE',deadline)]))['targets']['t1']
 assert p['external']=='170'and p['unused']=='0';out['nothing_shared_to_split']=p
 p=run(source(stock('10')),netting([('t1','85','ACTIVE',deadline),('other','0','ACTIVE',deadline)]))['targets']['t1']
 assert p['external']=='160';out['known_zero_gap_not_claimant']=p
 old=source(stock('10'));old['fabric_source'].pop('physical')
 p=run(old,netting([('t1','85','ACTIVE',deadline)]));assert p['physical_source']is False and p['targets']=={};out['v1_without_physical']=p
 return out

def races(tools,today):
 def prepared(link_first=False):
  with tools.connect()as conn,conn.cursor()as cur:
   gid=p=None
   if link_first:f=recipe(cur,today);gid,p=link(cur,today,f,'6')
   else:f=bound(cur,today)
   before=plan.monetary_state(cur);conn.commit();return f,gid,p,before
 def mvcc(kind):
  def run():
   f,gid,p,before=prepared(kind=='POST')
   with tools.connect()as holder,holder.cursor()as h:
    if kind=='RECEIPT':receive(h,today,f,'20')
    else:
     from cp7_plan_actual_cases import post
     p['cutting']['rolls'][0].update(qty_consumed='6',qty_reported_remaining='0')
     b.chain.production.rpc(h,'public.erp_save_cutting_group_before_sewing_v2',dict(p['cutting'],id=gid,action='SAVE_DRAFT',change_reason='P08 consume whole issue'),expected_version=int(b.chain.base.group_version(h,gid)))
     b.api.admin(h);post(h,dict(payload=p,group=gid))
    holder_pid=h.execute('select pg_backend_pid()').fetchone()[0]
    with tools.connect()as conn,conn.cursor()as cur:
     reader_pid=cur.execute('select pg_backend_pid()').fetchone()[0];e=capture(cur,today);conn.commit()
    m=row(e,f['target'])
    if kind=='RECEIPT':expect(m,'0','10','176')
    else:expect(m,None,'10',None,external_reason='FABRIC_WIP_IDENTITY_UNRESOLVED');upper(m,'160');assert refs(m['unused_allocated_proven'],'erp.cutting_groups')
    holder.commit()
   with tools.connect()as conn,conn.cursor()as cur:
    old=parent.read(cur,e['run_id']);assert old['source_state']=='ARCHIVED_STALE'and old['analysis']==e['analysis']
    fresh=capture(cur,today);n=row(fresh,f['target'])
    if kind=='RECEIPT':expect(n,'0','30','156')
    else:expect(n,None,'4',None,external_reason='FABRIC_WIP_IDENTITY_UNRESOLVED');upper(n,str(max(D(0),D(n['gross']['value'])-4)));assert not refs(n['unused_allocated_proven'],'erp.cutting_groups')
    conn.rollback()
   return dict(status='PASS',distinct_backend_pids=[holder_pid,reader_pid],uncommitted_physical_change_invisible_to_capture=True,
    commit_archives_immutable_original=True,fresh_capture_counts_once=True,before=m,after=n,kind=kind)
  return run
 return[(IDS['races'][0],mvcc('RECEIPT')),(IDS['races'][1],mvcc('POST'))]

def http_cases(http,today):
 def actual():
  owner=http.login('OWNER','p08-physical-owner');other=http.login('OWNER','p08-physical-foreign')
  with http.connect()as conn,conn.cursor()as cur:f=fabric.setup(cur,today,owner.auth_user_id);before=plan.monetary_state(cur);conn.commit()
  args=dict(p_payload=f['payload'],p_request=str(uuid.uuid4()));one=owner.rpc('erp_cp7_save_fabric_recipe_v1',args);assert one['status']==200,one
  fresh=owner.rpc('erp_cp7_capture_analysis_v1',dict(p_query=f['plan']['original']['query'],p_request=str(uuid.uuid4())));assert fresh['status']==200,fresh
  parent.checked(fresh['body']);m=expect(row(fresh['body'],f['target']),None,'10',None,external_reason='FABRIC_WIP_IDENTITY_UNRESOLVED');upper(m,'160')
  assert other.rpc('erp_cp7_read_analysis_v1',dict(p_run=fresh['body']['run_id']))['status']in(403,404)and http.anon_rpc('erp_cp7_capture_analysis_v1',dict(p_query=f['plan']['original']['query'],p_request=str(uuid.uuid4())))['status']in(401,403)
  with http.connect()as conn,conn.cursor()as cur:assert plan.monetary_state(cur)==before
  return dict(status='PASS',actual_Auth_HTTP_physical_installed_UNKNOWN_allocated10_external_UNKNOWN_upper160=True,foreign_and_anonymous_denied=True,Native_stock_money_HPP_unchanged=True,complete_material_row=m)
 return[(IDS['http'][0],actual)]
