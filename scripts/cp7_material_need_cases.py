"""Native BOM sources; synthetic O09/O10 are never ERP installed facts."""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from decimal import Decimal as D
from copy import deepcopy
import json,time,uuid
import psycopg
import cp7_f03_e24_issue_cases as issue
import cp6_bf_probe as native_master

def master(cur,today,parent):
 f=issue.bc.fixture(cur,today,purchase=False,zones=False);parent.b.api.admin(cur)
 category,unit=cur.execute('select accessory_category_id,unit_code from erp.materials where id=%s',(f['material'],)).fetchone();f.update(category_id=str(category),unit=unit);return f

def close_current(cur,root,parent,at):
 parent.b.api.admin(cur)
 # Close after committed financial uses; never rewrite a used item or flag.
 cur.execute('update erp.accessory_bom_versions set effective_to=%s where product_id=%s and is_active and effective_from<%s and(effective_to is null or effective_to>%s)',(at,root,at,at))

def bom(cur,root,parent,category=None,qty='2',at=None):
 parent.b.api.admin(cur);at=at or cur.execute('select clock_timestamp()').fetchone()[0]
 existing=cur.execute('select s.id::text,s.sku,s.revision,v.id::text,v.settings from erp.bf_sku_members_v1 m join erp.bf_sku_versions_v1 v on v.id=m.version_id join erp.bf_skus_v1 s on s.id=v.sku_id where m.product_root=%s and v.effective_to is null',(root,)).fetchone()
 roots=[root];settings=dict(price=None,bom=None,work_rates=[],laundry_rates=[])
 if existing:
  roots=[r[0]for r in cur.execute('select product_root::text from erp.bf_sku_members_v1 where version_id=%s order by product_root',(existing[3],))];settings=deepcopy(existing[4])
 # Keep the complete commercial membership and every other selected setting.
 # Only the unchanged Native shared-master command may create economic rows.
 settings['bom']=[]if category is None else[dict(category_id=category['category_id'],qty_per_good_fg_base=qty,hpp_method='BOM_STANDARD',hpp_standard_rate='1',hpp_uom_code=category['unit'],reimbursement_rate='0',reimbursement_uom_code=category['unit'])]
 g=native_master.group(cur,roots,at,sku=existing[1]if existing else None,gid=existing[0]if existing else None,revision=existing[2]if existing else 0,settings=settings)
 saved=native_master.save(cur,[g],at);version_id=saved['groups'][0]['version_id'];parent.b.api.admin(cur)
 ident=cur.execute('select bom_version_id::text from erp.bf_sku_members_v1 where version_id=%s and product_root=%s',(version_id,root)).fetchone()[0];assert ident is not None
 item=cur.execute('select id::text from erp.accessory_bom_items where bom_version_id=%s',(ident,)).fetchone()
 return dict(id=ident,item_id=item[0]if item else None,at=at,Native_shared_master_version=version_id)

def review_schedule(cur,today,parent):
 # A shared-master revision changes the full captured supply fingerprint,
 # even when physical roots, production consent and all selected quantities
 # remain unchanged. Rebind the *same explicit fixture work assumptions* via
 # the current Native source and public schedule CAS, never by editing a hash.
 parent.b.api.admin(cur);plan=cur.execute('select revision,config from cp7_schedule_native.plans order by revision desc limit 1').fetchone();assert plan is not None
 current=parent.previous.supply.capture(cur,today)
 selected=deepcopy(plan[1])
 # The real HTTP suite accumulates additional Native WIP fixtures. The same
 # explicitly selected work minutes need a sufficiently long selected fixture
 # window; never replace unknown ETA by an assumed zero-minute workload.
 # Browser preparation already selects this load+120/load+180 window.
 assert len(selected['windows'])==1 and all(step['remaining_minutes']is not None for position in selected['positions']for step in position['remaining_steps'])
 load=sum(int(step['remaining_minutes'])for position in selected['positions']for step in position['remaining_steps'])
 start=parent.schedule.datetime.fromisoformat(selected['windows'][0]['starts_at'].replace('Z','+00:00'))
 end=parent.schedule.datetime.fromisoformat(selected['windows'][0]['ends_at'].replace('Z','+00:00'));through=parent.schedule.datetime.fromisoformat(selected['through_at'].replace('Z','+00:00'))
 selected['windows'][0]['ends_at']=parent.schedule.stamp(max(end,start+timedelta(minutes=load+120)));selected['through_at']=parent.schedule.stamp(max(through,start+timedelta(minutes=load+180)))
 p=dict(source_run=current['run_id'],source_hash=current['source_hash'],expected_revision=str(plan[0]),
  reason='P06 explicit fixture review: retain selected work quantities/yield/routes and provide load+120/load+180 selected time on current Native shared master source',config=selected)
 parent.schedule.save(cur,p)

def prepared(cur,today,parent,subject=None,empty=False):
 f,root,_,_=parent.setup(cur,today);category=None if empty else master(cur,today,parent);version=bom(cur,root,parent,category);review_schedule(cur,today,parent)
 return dict(root=root,opening=f,category=category,bom=version,original=parent.capture(cur,today,subject=subject))
def rows(envelope,root):return [m for m in envelope['analysis']['material_needs']if m['target_key'].split(':')[0]==root]
def unknown_installation(row):
 assert all(row[k]['state']=='UNKNOWN'and'value'not in row[k]for k in('installed_proven','unused_allocated_proven','additional_external')),row

def cases(cur,today,parent):
 b,auth=parent.b,parent.auth
 def missing():
  _,root,_,_=parent.setup(cur,today);at=cur.execute('select clock_timestamp()').fetchone()[0];close_current(cur,root,parent,at)
  before=b.boundary.snapshot(cur);e=parent.capture(cur,today);parent.checked(e);m=rows(e,root)[0]
  assert m['material_key']is None and m['gross']['state']=='UNKNOWN';unknown_installation(m);assert b.boundary.snapshot(cur)==before
  return dict(status='PASS',no_effective_Native_BOM_not_implicit_empty_or_zero=True,Native_full_boundary_unchanged_by_read=True)
 def empty():
  f=prepared(cur,today,parent,empty=True);parent.checked(f['original']);m=rows(f['original'],f['root'])[0]
  assert m['material_key']=='NO_ACCESSORY:'+f['root']and all(m[k]['state']=='KNOWN'and D(m[k]['value'])==0 for k in('gross','installed_proven','unused_allocated_proven','additional_external'))
  assert parent.recommendation(f['original']['analysis'],f['root'])['feasible_new']['state']=='UNKNOWN'
  assert all(any(r['kind']=='erp.accessory_bom_versions'and r['id']==f['bom']['id']for r in m[k]['refs'])for k in('gross','installed_proven','unused_allocated_proven','additional_external'))
  return dict(status='PASS',explicit_Native_empty_BOM_zero_accessory_requirement_only=True,no_fabric_or_capacity_inference=True)
 def gross():
  f=prepared(cur,today,parent);e=f['original'];parent.checked(e);m=rows(e,f['root'])[0]
  assert m['material_key']=='ACCESSORY_CATEGORY:'+f['category']['category_id']and m['gross']['state']=='ASSUMED'and D(m['gross']['value'])==D(93)*2 and m['gross']['unit']==f['category']['unit'];unknown_installation(m)
  assert {'erp.accessory_bom_versions','erp.accessory_bom_items','erp.accessory_categories'}<={x['kind']for x in m['gross']['refs']}
  before=b.boundary.snapshot(cur);assert parent.read(cur,e['run_id'])['source_state']=='UNCHANGED'and b.boundary.snapshot(cur)==before
  cur.execute('update erp.accessory_categories set is_active=false where id=%s',(f['category']['category_id'],));fresh=parent.capture(cur,today);parent.checked(fresh);assert rows(fresh,f['root'])[0]['gross']['state']=='UNKNOWN'
  return dict(status='PASS',actual_Native_BOM2_times_conditional_gap93_equals186=True,selected_quantity_stays_ASSUMED=True,inactive_category_not_physical_ready=True)
 def successor():
  f=prepared(cur,today,parent);old=f['original'];new_version=bom(cur,f['root'],parent,f['category'],qty='3')
  stale=parent.read(cur,old['run_id']);assert stale['source_state']=='ARCHIVED_STALE'and stale['analysis']==old['analysis']
  review_schedule(cur,today,parent)
  fresh=parent.capture(cur,today);parent.checked(fresh);m=rows(fresh,f['root'])[0];assert D(m['gross']['value'])==D(93)*3 and any(r['id']==new_version['id']for r in m['gross']['refs'])and D(rows(stale,f['root'])[0]['gross']['value'])==186
  return dict(status='PASS',lawful_Native_BOM_successor_stales_Original=True,original186_preserved_fresh279=True,no_used_item_rewrite=True)
 def issued():
  _,root,_,_=parent.setup(cur,today);f=issue.receipt(cur,today,qty='80');b.api.admin(cur)
  category,unit=cur.execute('select accessory_category_id,unit_code from erp.materials where id=%s',(f['material'],)).fetchone();f.update(category_id=str(category),unit=unit);bom(cur,root,parent,f)
  p=issue.payload(f);p.update(location_id=f['main'],po_id=None);p['items'][0]['qty']='80';p['reason']='Explicit Native issue80, not installation'
  d=issue.bc.note_call(cur,'SAVE_DRAFT',p);p.update(id=d['id'],expected_version=d['row_version']);posted=issue.bc.note_call(cur,'POST',p);b.api.admin(cur)
  document=issue.bc.note_read(cur,dict(id=posted['id']))['document'];assert document['status']=='POSTED'and issue.bc.stock(cur,f['material'],f['main'])==0;b.api.admin(cur)
  review_schedule(cur,today,parent)
  before=b.boundary.snapshot(cur);e=parent.capture(cur,today);parent.checked(e);m=rows(e,root)[0];assert D(m['gross']['value'])==186;unknown_installation(m);assert b.boundary.snapshot(cur)==before
  return dict(status='PASS',real_Native_receipt80_issue80_no_seeded_movements=True,issue80_not_installed_or_allocated_unused=True,external_need_UNKNOWN_not20_or_zero=True)
 def o09():
  refs=[dict(kind='SYNTHETIC_CONTRACT_ORACLE',id='O09',revision='1')];deadline='2026-10-10T00:00:00Z'
  unused=dict(physical_key='unused-20',kind='UNUSED',quantity='20',verified_eligible_allocated=True,eta=None,refs=refs)
  p=dict(contract_version='cp7.material-need-input.v1',snapshot_id='O09',scope_id='explicit-synthetic-contract',material_id='O09-button',unit='PCS',gross_need='100',proven_installed='60',deadline=deadline,supplies=[unused],refs=refs)
  call=lambda v:cur.execute('select cp7_baseline.material(%s::jsonb)',(json.dumps(v),)).fetchone()[0]
  r=call(p);assert r['status']=='SCENARIO'and D(r['remaining_need'])==40 and D(r['external_need'])==20
  unknown=deepcopy(p);unknown['proven_installed']=None;unknown['supplies']=[dict(unused,physical_key='issue80',kind='ISSUED',quantity='80')];r=call(unknown);assert r['status']=='UNKNOWN'and r['external_need']is None
  incoming=dict(unused,physical_key='incoming10',kind='INCOMING',quantity='10',eta=deadline);extra=deepcopy(p)
  extra['supplies']+=[incoming,deepcopy(incoming),dict(incoming,physical_key='late',quantity='1000',eta='2026-10-11T00:00:00Z'),dict(unused,physical_key='customer-or-quarantine',quantity='1000',verified_eligible_allocated=False)]
  r=call(extra);assert D(r['remaining_need'])==40 and D(r['external_need'])==10
  mismatch=deepcopy(extra);mismatch['supplies'][2]['quantity']='11';auth.refused(cur,lambda:call(mismatch),'CP7_BASELINE_MATERIAL_DUPLICATE')
  return dict(status='PASS',fixture_kind='SYNTHETIC_CONTRACT_ORACLE',not_an_ERP_installed60_claim=True,worksheet='100-60=40;40-20=20;40-20-unique10=10',actual_server_kernel_matches_independent_arithmetic=True,issue_customer_quarantine_late_duplicate_guards=True)
 def o10():
  refs=[dict(kind='SYNTHETIC_CONTRACT_ORACLE',id='O10',revision='1')];p=dict(contract_version='cp7.feasibility-input.v1',snapshot_id='O10',scope_id='explicit-synthetic-contract',target_key='O10-product',size_id='O10-size',production_status='ACTIVE',need_pcs='100',multiple_pcs='1',capacity_pcs='100',material_cap_pcs='60',refs=refs)
  call=lambda v:cur.execute('select cp7_baseline.feasibility(%s::jsonb)',(json.dumps(v),)).fetchone()[0]
  r=call(p);assert r['need_pcs']=='100'and r['start_new_pcs']=='60'and r['unresolved_pcs']=='40'
  r=call(dict(p,material_cap_pcs=None));assert r['status']=='UNKNOWN'and r['start_new_pcs']is None
  r=call(dict(p,production_status='STOP'));assert r['need_pcs']=='100'and r['start_new_pcs']=='0'and r['unresolved_pcs']=='100'
  return dict(status='PASS',fixture_kind='SYNTHETIC_CONTRACT_ORACLE',needed100_feasible60_unresolved40=True,unknown_not_zero_STOP_not_hide_gap=True)
 def clock_private():
  f=prepared(cur,today,parent);current=cur.execute('select facts from cp7_analysis_native.runs where id=%s',(f['original']['run_id'],)).fetchone()[0];at=cur.execute('select clock_timestamp()').fetchone()[0]
  bom(cur,f['root'],parent,f['category'],qty='3',at=at+timedelta(hours=1));at=cur.execute('select clock_timestamp()').fetchone()[0]
  # Both counter-clocks are after the real master was created: do not mistake
  # newly known future-version facts for a pure capture-clock change.
  source=lambda t:cur.execute('select cp7_analysis_native.material_source(%s::jsonb,%s)',(json.dumps(current['facts']['products']),t)).fetchone()[0]
  before=source(at);same=source(at+timedelta(minutes=1));after=source(at+timedelta(hours=1,seconds=1))
  assert {k:v for k,v in before.items()if k!='captured_at'}=={k:v for k,v in same.items()if k!='captured_at'}and before['selected']!=after['selected']
  for who in('anon','authenticated','service_role'):
   for sig in('cp7_analysis_native.material_source(jsonb,timestamp with time zone)','cp7_analysis_native.material_needs(jsonb,jsonb,jsonb)'):assert not cur.execute('select has_function_privilege(%s,%s,\'EXECUTE\')',(who,sig)).fetchone()[0]
  for table in('erp.accessory_bom_versions','erp.accessory_bom_items','erp.accessory_categories'):assert not cur.execute("select has_table_privilege('cp7_capture',%s,'INSERT,UPDATE,DELETE,TRUNCATE,TRIGGER')",(table,)).fetchone()[0]
  return dict(status='PASS',clock_counterfixture_not_future_Native_business_event=True,raw_clock_not_material_change_effective_boundary_is_change=True,private_read_only_capability_no_Native_writer=True)
 return [('P06_MATERIAL_'+n,fn)for n,fn in [('NATIVE_MISSING_UNKNOWN',missing),('NATIVE_EMPTY_EXPLICIT',empty),('NATIVE_GROSS_ASSUMED',gross),('NATIVE_BOM_SUCCESSOR',successor),('NATIVE_ISSUE_NOT_INSTALLED',issued),('O09_TRUSTED_KERNEL_CONTRACT',o09),('O10_TRUSTED_KERNEL_CONTRACT',o10),('NATIVE_CLOCK_PRIVATE',clock_private)]]

def races(tools,today,parent):
 def revoke():
  with tools.connect()as conn,conn.cursor()as cur:
   subject,role=parent.auth.custom_actor(cur);f=prepared(cur,today,parent,subject);original=cur.execute("select pg_get_functiondef('cp7_analysis_native.material_source(jsonb,timestamp with time zone)'::regprocedure)").fetchone()[0]
   needle="with roots as materialized(select distinct (x->>'root_id')::uuid id from jsonb_array_elements(products)x),";assert needle in original
   gated="with gate as materialized(select pg_advisory_xact_lock(8062026)), roots as materialized(select distinct (x->>'root_id')::uuid id from jsonb_array_elements(products)x cross join gate),";cur.execute(original.replace(needle,gated),prepare=False);conn.commit()
  try:
   with tools.connect()as holder,holder.cursor()as h:
    h.execute('select pg_advisory_xact_lock(8062026)')
    def send():
     with tools.connect()as conn,conn.cursor()as cur:
      try:r=parent.read(cur,f['original']['run_id'],subject);conn.commit();return r
      except psycopg.Error as e:conn.rollback();return dict(error=str(e),sqlstate=e.sqlstate)
    with ThreadPoolExecutor(max_workers=1)as pool:
     job=pool.submit(send);waiting=False;deadline=time.monotonic()+12
     try:
      with tools.connect(autocommit=True)as conn,conn.cursor()as cur:
       while time.monotonic()<deadline:
        waiting=cur.execute("select exists(select 1 from pg_stat_activity where datname=current_database()and wait_event='advisory'and query like 'select public.erp_cp7_read_analysis_v1%%')").fetchone()[0]
        if waiting:break
        time.sleep(.03)
      assert waiting,'P06_MATERIAL_PUBLIC_SOURCE_WAIT_NOT_OBSERVED'
      with tools.connect()as conn,conn.cursor()as cur:cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='production.wip.view'",(role,));conn.commit()
     finally:holder.rollback()
     result=job.result(45)
   assert result.get('sqlstate')=='42501'and result.get('error','').splitlines()[0]=='CP7_ACCESS_DENIED',result
   return dict(status='PASS',two_real_connections_current_authority_after_observed_material_capture_wait=True,only_private_CP7_reader_instrumented=True)
  finally:
   with tools.connect()as conn,conn.cursor()as cur:cur.execute(original,prepare=False);conn.commit();assert cur.execute("select pg_get_functiondef('cp7_analysis_native.material_source(jsonb,timestamp with time zone)'::regprocedure)").fetchone()[0]==original
 return [('P06_MATERIAL_RACE_CURRENT_SOURCE_AUTH',revoke)]

def http_cases(http,today,parent):
 def actual():
  owner=http.login('OWNER','p06-material-owner');other=http.login('OWNER','p06-material-foreign')
  with http.connect()as conn,conn.cursor()as cur:f=prepared(cur,today,parent,owner.auth_user_id);conn.commit()
  args=dict(p_run=f['original']['run_id']);r=owner.rpc('erp_cp7_read_analysis_v1',args);assert r['status']==200;r=r['body'];parent.checked(r);m=rows(r,f['root'])[0]
  if m['gross']['state']!='ASSUMED':raise AssertionError(json.dumps(dict(code='P06_MATERIAL_HTTP_EXPLICIT_WORK_REVIEW_REQUIRED',root=f['root'],gross=m['gross'],recommendation=parent.recommendation(r['analysis'],f['root']),quality=r['analysis']['quality'],source_state=r['source_state']),default=str))
  assert D(m['gross']['value'])==186;unknown_installation(m)
  assert other.rpc('erp_cp7_read_analysis_v1',args)['status']==403 and http.anon_rpc('erp_cp7_read_analysis_v1',args)['status']in(401,403)
  with http.connect()as conn,conn.cursor()as cur:cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(owner.auth_user_id,));conn.commit()
  assert owner.rpc('erp_cp7_read_analysis_v1',args)['status']==403
  return dict(status='PASS',actual_Auth_HTTP_current_own_BOM_gross186_unknown_installation=True,foreign_anonymous_deactivated_denied=True)
 return [('P06_MATERIAL_HTTP_CURRENT_AUTH',actual)]
