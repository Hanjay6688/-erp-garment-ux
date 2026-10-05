"""P18 fabric reminder rule on actual Native fabric facts.

FABRIC_NEED copies the immutable shared-analysis fabric row exactly. It adds no
business writer: the reminder episode/local-sink writers are unchanged. All
operands come from unchanged public commands (receipt SAVE/POST, recipe review,
OPEN_PURCHASE_ORDER import, plan draft bridge). Policy values below are explicit
fixture choices, never owner operating values; an assumed zero never becomes a
business resolution and an unknown never becomes zero.
"""
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal as D
import threading,uuid
import cp7_fabric_physical_cases as physical
import cp7_rule_source_cases as rules
parent,b,auth,plan=physical.parent,physical.b,physical.auth,physical.plan
policy=rules.previous
REQUIRED=dict(native=7,races=1,http=1,browser=2)
EXPECTED=sum(REQUIRED.values())
IDS=dict(native=['P18_FABRIC_RULE_ACTIVE_FROM_ORIGINAL','P18_FABRIC_RULE_POLICY_UNIT_EXACT','P18_FABRIC_RULE_ASSUMED_ZERO_NOT_RESOLVED',
  'P18_FABRIC_RULE_IDENTITY_UNKNOWN_NO_EPISODE','P18_FABRIC_RULE_UNREVIEWED_RECIPE','P18_FABRIC_RULE_SHARED_SPLIT_UNDECIDED','P18_FABRIC_RULE_LOCAL_PREVIEW'],
 races=['P18_FABRIC_RULE_REAL_CONCURRENT_EPISODE'],http=['P18_FABRIC_RULE_REAL_AUTH_HTTP'],
 browser=['P18_FABRIC_RULE_BROWSER_DESKTOP','P18_FABRIC_RULE_BROWSER_MOBILE'])
COVERAGE='COMPLETE_AUTHORIZED_ORIGINAL_UNKNOWN_PHYSICAL_AND_UNREVIEWED_RECIPE_RETAINED'

def fabric_rows(s,target=None):return[r for r in s['rows']if r['rule_id']=='FABRIC_NEED'and(target is None or r['target_key']==target)]
def one(s,target):
 rows=fabric_rows(s,target);assert len(rows)==1,rows;return rows[0]
def exact(s,e):
 """Every shared fabric row has exactly one condition with the same external fact."""
 needs=[m for m in e['analysis']['material_needs']if(m['material_key']or'').startswith('FABRIC_')]
 assert s['coverage']['fabric']==COVERAGE and len(fabric_rows(s))==len(needs),(s['coverage'],len(fabric_rows(s)),len(needs))
 for r in fabric_rows(s):
  m=next(x for x in needs if x['target_key']==r['target_key']and x['material_key']==r['material_key'])
  assert r['value']==m['additional_external']and r['key']=='FABRIC_NEED:'+r['target_key']+':'+r['material_key']and r['domain']=='FABRIC'
  assert r['financial_source']is None and r['economic_state']=='NOT_APPLICABLE'and r['delivery_sent']is False and r['scope']=='CURRENT_NATIVE_FABRIC_RECIPE_AND_PHYSICAL_ALLOCATION'
  assert r['business_resolved']is False,r # ASSUMED or UNKNOWN facts never resolve
 return s
def unit(e,target):return next(m for m in e['analysis']['material_needs']if m['target_key']==target and(m['material_key']or'').startswith('FABRIC_MATERIAL:'))['additional_external']['unit']
def episodes(cur,key):return cur.execute('select state,freshness,episode_number from cp7_reminder_native.rule_episodes where condition_key=%s order by episode_number',(key,)).fetchall()
def save_policy(cur,e,c,revision='0',target=None,subject=None):
 out=policy.command(cur,policy.intent(e,'FABRIC_NEED',revision,c,target),subject=subject);b.api.admin(cur);return out

def cases(cur,today):
 def active():
  f=physical.bound(cur,today);e=physical.capture(cur,today);before=b.boundary.snapshot(cur);s=exact(rules.source(cur,e),e);r=one(s,f['target'])
  assert r['state']=='ACTIVE'and r['value']['state']=='ASSUMED'and D(r['value']['value'])==176 and r['reason']=='SOURCE_BOUND_ADDITIONAL_EXTERNAL_FABRIC_NEED',r
  assert r['eligibility']=='UNCONFIGURED'and r['policy_binding']['basis']=='MISSING'and r['policy_binding']['policy']is None,r
  assert r['label']==next(l['sku']+' · '+l['product_name']for l in e['product_labels']if l['target_key']==f['target'])
  assert s['analysis']['analysis']==e['analysis']and b.boundary.snapshot(cur)==before
  return dict(status='PASS',bound_gap93_external176_ASSUMED_copied_exactly_ACTIVE=True,missing_policy_UNCONFIGURED_not_zero_or_disabled=True,reads_leave_Native_boundary_unchanged=True,complete_condition=r)
 def units():
  f=physical.bound(cur,today);e=physical.capture(cur,today);u=unit(e,f['target']);before=b.boundary.snapshot(cur);seen=[]
  other=u.upper()if u!=u.upper()else'PCS'if u!='PCS'else'KG' # different text: never case-folded or converted
  for revision,c,expected in(('0',policy.ready('100',u),'LOCAL_PREVIEW_ELIGIBLE'),('1',policy.ready('200',u),'BELOW_SELECTED_THRESHOLD'),('2',policy.ready('1',other),'UNIT_REVIEW_REQUIRED')):
   save_policy(cur,e,c,revision);r=one(rules.source(cur,e),f['target']);assert r['eligibility']==expected and r['policy_binding']['basis']=='GLOBAL',(expected,r);seen.append(expected)
  save_policy(cur,e,policy.ready('500',u),target=f['target']);r=one(rules.source(cur,e),f['target'])
  assert r['policy_binding']['basis']=='EXACT_TARGET'and r['eligibility']=='BELOW_SELECTED_THRESHOLD'and D(r['value']['value'])==176,r
  assert b.boundary.snapshot(cur)==before
  return dict(status='PASS',threshold_compared_only_in_exact_same_unit_text_no_case_folding_or_conversion=True,native_unit=u,other_unit=other,global_eligible_then_below_then_unit_review=seen,exact_target_version_overrides_global=True,value_unchanged176=True)
 def assumed_zero():
  f=physical.bound(cur,today);e=physical.capture(cur,today);key=one(rules.source(cur,e),f['target'])['key']
  first=rules.observation(rules.observe(cur,e),key);assert first['transition']=='OPENED'and first['episode']['state']=='ACTIVE'and first['episode']['freshness']=='ASSUMED',first
  physical.receive(cur,today,f,'200');old=rules.source(cur,e);assert one(old,f['target'])['state']=='SOURCE_CHANGED'
  fresh=physical.capture(cur,today);m=physical.expect(physical.row(fresh,f['target']),'0','186','0')
  s=exact(rules.source(cur,fresh),fresh);r=one(s,f['target']);assert r['key']==key and r['state']=='NO_CURRENT_GAP'and r['reason']=='SELECTED_FABRIC_RECIPE_SCENARIO_NOT_PHYSICAL_RESOLUTION'and not r['business_resolved'],r
  again=rules.observation(rules.observe(cur,fresh),key);assert again['transition']=='SCENARIO_NO_ALERT_EPISODE_RETAINED'and again['episode']['state']=='ACTIVE'and again['episode']['id']==first['episode']['id'],again
  assert episodes(cur,key)==[('ACTIVE','ASSUMED',1)]
  return dict(status='PASS',episode_opened_on_external176=True,actual_receipt200_stales_old_Original_SOURCE_CHANGED=True,fresh_external0_ASSUMED_is_NO_CURRENT_GAP_not_RESOLVED=True,same_episode_retained_not_closed=True,complete_material_row=m)
 def identity():
  f=physical.recipe(cur,today);e=physical.capture(cur,today);s=exact(rules.source(cur,e),e);r=one(s,f['payload']['target_key'])
  assert r['state']=='DATA_REVIEW'and r['reason']=='FABRIC_WIP_IDENTITY_UNRESOLVED'and r['value']['state']=='UNKNOWN'and'value'not in r['value']and r['eligibility']=='SOURCE_REVIEW_REQUIRED',r
  o=rules.observation(rules.observe(cur,e),r['key']);assert o['transition']=='OBSERVED_NO_ACTIVE_EPISODE'and o['episode']is None and episodes(cur,r['key'])==[],o
  return dict(status='PASS',ambiguous_same_model_WIP_external_UNKNOWN_stays_DATA_REVIEW=True,no_episode_no_zero_no_invented_number=True,complete_condition=r)
 def unreviewed():
  parent.setup(cur,today);e=physical.capture(cur,today);s=exact(rules.source(cur,e),e)
  rows=fabric_rows(s);assert rows and len(rows)==len(e['analysis']['recommendations'])
  assert all(r['material_key']=='FABRIC_UNREVIEWED:'+r['target_key']and r['state']=='DATA_REVIEW'and r['reason']=='FABRIC_RECIPE_NOT_REVIEWED'for r in rows),rows
  observed=rules.observe(cur,e);assert all(rules.observation(observed,r['key'])['episode']is None for r in rows)
  return dict(status='PASS',every_target_without_recipe_has_one_DATA_REVIEW_fabric_condition=True,unreviewed_recipe_never_zero_and_opens_no_episode=True,count=len(rows))
 def shared():
  first,second=plan.shared_material_setup(cur,today);[physical.review(cur,today,x)for x in(first,second)]
  e=physical.capture(cur,today);s=exact(rules.source(cur,e),e)
  rows=[one(s,x['payload']['target_key'])for x in(first,second)]
  assert all(r['state']=='DATA_REVIEW'and r['reason']=='FABRIC_SHARED_SUPPLY_SPLIT_UNDECIDED'and'value'not in r['value']for r in rows),rows
  return dict(status='PASS',shared_fabric_split_undecided_two_DATA_REVIEW_conditions_no_number_or_split_invented=True,conditions=rows)
 def preview():
  f=physical.bound(cur,today);e=physical.capture(cur,today);u=unit(e,f['target']);before=b.boundary.snapshot(cur)
  save_policy(cur,e,policy.ready('100',u));rules.bind(cur,e,rules=['FABRIC_NEED']);key=one(rules.source(cur,e),f['target'])['key'];rules.observe(cur,e)
  out=rules.claim(cur,e,key);c=rules.claim_row(out)
  assert c['rule_id']=='FABRIC_NEED'and c['condition_key']==key and'Kebutuhan kain'in c['body']and f'176 {u}'in c['body']and'BELUM DIKIRIM'in c['body'],c
  final=rules.finish(cur,e,c);assert rules.claim_row(final)['status']=='LOCAL_SINK_CAPTURED'and final['workspace']['sent']is False
  assert not rules.row(final['workspace']['source'],key)['business_resolved']and b.boundary.snapshot(cur)==before
  return dict(status='PASS',explicit_fixture_policy100_same_unit_local_preview_body_Kebutuhan_kain_176=True,local_sink_only_no_external_delivery_or_business_resolution=True)
 return list(zip(IDS['native'],[active,units,assumed_zero,identity,unreviewed,shared,preview]))

def races(tools,today):
 def episode():
  with tools.connect()as conn,conn.cursor()as cur:
   f=physical.bound(cur,today);e=physical.capture(cur,today);s=rules.source(cur,e);key=one(s,f['target'])['key'];p=dict(run_id=e['run_id'],source_hash=s['source_hash']);conn.commit()
  gate=threading.Barrier(2)
  def send():
   with tools.connect()as conn,conn.cursor()as cur:gate.wait(5);r=rules.command(cur,'EPISODES',p);conn.commit();return r
  with ThreadPoolExecutor(max_workers=2)as pool:results=[j.result(120)for j in[pool.submit(send),pool.submit(send)]]
  observed=[rules.observation(r,key)for r in results]
  with tools.connect()as conn,conn.cursor()as cur:rows=episodes(cur,key)
  assert rows==[('ACTIVE','ASSUMED',1)]and{o['episode']['id']for o in observed}=={observed[0]['episode']['id']},(rows,observed)
  assert sorted(o['transition']for o in observed)==['ACTIVE_RETAINED','OPENED'],observed
  return dict(status='PASS',two_actual_transactions_same_fabric_condition_one_episode=True,transitions=sorted(o['transition']for o in observed))
 return[(IDS['races'][0],episode)]

def http_cases(http,today):
 def actual():
  owner=http.login('OWNER','p18-fabric-rule-owner');other=http.login('OWNER','p18-fabric-rule-foreign')
  with http.connect()as conn,conn.cursor()as cur:f=physical.bound(cur,today,subject=owner.auth_user_id);before=plan.monetary_state(cur);conn.commit()
  c=owner.rpc('erp_cp7_capture_analysis_v1',dict(p_query=f['query'],p_request=str(uuid.uuid4())));assert c['status']==200,c;e=c['body'];parent.checked(e)
  s=owner.rpc('erp_cp7_get_rule_conditions_v1',dict(p_run=e['run_id']));assert s['status']==200,s;exact(s['body'],e);r=one(s['body'],f['target'])
  assert r['state']=='ACTIVE'and D(r['value']['value'])==176 and r['value']['state']=='ASSUMED',r
  assert other.rpc('erp_cp7_get_rule_conditions_v1',dict(p_run=e['run_id']))['status']==403 and http.anon_rpc('erp_cp7_get_rule_conditions_v1',dict(p_run=e['run_id']))['status']in(401,403)
  with http.connect()as conn,conn.cursor()as cur:assert plan.monetary_state(cur)==before
  return dict(status='PASS',actual_Auth_PostgREST_FABRIC_NEED_ACTIVE176_ASSUMED=True,foreign_and_anonymous_denied=True,Native_stock_money_HPP_unchanged=True,complete_condition=r)
 return[(IDS['http'][0],actual)]
