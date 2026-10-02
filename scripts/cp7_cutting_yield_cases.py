"""Actual Native cutting source oracles; no trained interval acceptance."""
import json,uuid
from decimal import Decimal
import cp7_planning_history_cases as previous
import cp7_f03_e01_cases as e01
import cp7_cutting_yield_bundle as bundle
auth,b=previous.auth,previous.b

def capture(cur,groups,key=None):
 auth.actor(cur);out=cur.execute('select public.erp_cp7_capture_cutting_yield_v1(%s,%s)',(json.dumps(dict(group_ids=groups)),key or uuid.uuid4())).fetchone()[0]
 b.api.admin(cur);return out

def read(cur,run):
 auth.actor(cur);out=cur.execute('select public.erp_cp7_read_cutting_yield_v1(%s)',(run,)).fetchone()[0]
 b.api.admin(cur);return out

def cases(cur,today):
 def actual():
  f=e01.production(cur,today);before=b.boundary.snapshot(cur);key=uuid.uuid4();r=capture(cur,[f['group']],key)
  assert len(r['rows'])==1 and r['rows'][0]['actual']['total_pcs']=='60'
  actual=r['rows'][0]['actual'];unit=cur.execute('select m.unit_code from erp.material_rolls roll join erp.materials m on m.id=roll.material_id where roll.id=%s',(f['roll'],)).fetchone()[0]
  assert Decimal(actual['consumed'])==60 and actual['unit']==unit
  assert r['knowledge_basis']=='CURRENT_CAPTURE_ONLY'and r['source_state']=='UNCHANGED'and not r['business_write']
  assert not r['model_qualified']and r['rows'][0]['interval']is None and r['rows'][0]['planned_mix']is None
  assert r['rows'][0]['recorded_width_cm']is None and r['rows'][0]['measured_remaining']is None
  assert r['rows'][0]['reason']=='PROSPECTIVE_FAMILY_MIX_AND_VALIDATED_INTERVAL_REQUIRED'
  assert capture(cur,[f['group']],key)==r and read(cur,r['run_id'])==r and b.boundary.snapshot(cur)==before
  assert cur.execute('select count(*)from cp7_cutting_yield.runs where request_id=%s',(key,)).fetchone()[0]==1
  return dict(status='PASS',actual_Native_receipt_cutting_pickup_sewing_laundry_QC=True,one_roll_slice60_counted_once=True,exact_Native_unit_preserved=True,same_UUID_one_immutable_original=True,no_Native_business_write=True,missing_family_preknown_mix_width_measurement_and_validated_model_explicit=True)
 def closed():
  before=b.boundary.snapshot(cur);bundle.verify(cur)
  for q in ({'group_ids':[]},{'group_ids':[str(uuid.uuid4())],'width_cm':'0'},{'group_ids':[3]},{'group_ids':[str(uuid.uuid4())],'normal_pcs':'100'}):
   code='CP7_WIP_FIELDS'if len(q)>1 else'CP7_CUTTING_YIELD_QUERY'
   def send():
    auth.actor(cur);cur.execute('select public.erp_cp7_capture_cutting_yield_v1(%s,%s)',(json.dumps(q),uuid.uuid4()))
   auth.refused(cur,send,code)
  auth.refused(cur,lambda:capture(cur,[str(uuid.uuid4())]),'CP7_CUTTING_YIELD_GROUP_UNAVAILABLE')
  uid=str(uuid.uuid4());auth.refused(cur,lambda:capture(cur,[uid,uid.upper()]),'CP7_CUTTING_YIELD_DUPLICATE')
  assert b.boundary.snapshot(cur)==before and cur.execute('select count(*)from cp7_cutting_yield.runs').fetchone()[0]==0
  return dict(status='PASS',unknown_partial_source_and_duplicate_slice_scope_denied=True,caller_cannot_inject_width_range_or_actual_values=True,private_metadata_and_functions_unreachable=True,refusals_no_native_effect_or_saved_original=True)
 def immutable():
  f=e01.production(cur,today);r=capture(cur,[f['group']]);original=cur.execute('select source,result from cp7_cutting_yield.runs where id=%s',(r['run_id'],)).fetchone()
  auth.refused(cur,lambda:cur.execute('update cp7_cutting_yield.runs set result=\'{}\' where id=%s',(r['run_id'],)),'CP7_RUN_IMMUTABLE')
  auth.refused(cur,lambda:cur.execute('delete from cp7_cutting_yield.runs where id=%s',(r['run_id'],)),'CP7_RUN_IMMUTABLE')
  cur.execute("create function cp7_cutting_yield.test_engine_successor()returns text language sql as $$select 'deliberate disposable model-engine revision'::text$$")
  archived=read(cur,r['run_id']);assert archived['source_state']=='ARCHIVED_STALE'and archived['rows']==r['rows']
  assert cur.execute('select source,result from cp7_cutting_yield.runs where id=%s',(r['run_id'],)).fetchone()==original
  cur.execute('drop function cp7_cutting_yield.test_engine_successor()');assert read(cur,r['run_id'])==r
  return dict(status='PASS',immutable_source_and_result_update_delete_denied=True,engine_revision_archives_without_rewriting_values=True,actual_knowledge_clock_not_backdated=True)
 return [('CUTTING_NATIVE_SLICE_ONCE',actual),('CUTTING_SOURCE_CLOSED_SCOPE',closed),('CUTTING_IMMUTABLE_ENGINE_ARCHIVE',immutable)]

def http_cases(http,today):
 def flow():
  owner=http.login('OWNER','cutting-source-owner')
  with http.connect()as conn,conn.cursor()as cur:f=e01.production(cur,today);conn.commit()
  args=dict(p_query=dict(group_ids=[f['group']]),p_request=str(uuid.uuid4()));r=owner.rpc('erp_cp7_capture_cutting_yield_v1',args)
  assert r['status']==200 and r['body']['rows'][0]['actual']['total_pcs']=='60',r
  assert owner.rpc('erp_cp7_capture_cutting_yield_v1',args)['body']==r['body']
  assert http.anon_rpc('erp_cp7_capture_cutting_yield_v1',args)['status']in(401,403)
  with http.connect()as conn,conn.cursor()as cur:cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(owner.auth_user_id,));conn.commit()
  assert owner.rpc('erp_cp7_capture_cutting_yield_v1',args)['status']==403
  assert owner.rpc('erp_cp7_read_cutting_yield_v1',dict(p_run=r['body']['run_id']))['status']==403
  return dict(status='PASS',actual_Auth_PostgREST_Native60=True,current_deactivation_denies_cached_original=True,anonymous_refused=True,no_range_or_width_imputed=True)
 return [('CUTTING_ACTUAL_AUTH_HTTP',flow)]
