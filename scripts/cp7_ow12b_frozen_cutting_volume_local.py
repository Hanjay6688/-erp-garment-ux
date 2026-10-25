"""Actual volume fixture helper; controlled local authority, not Native/Auth."""
import json,sys,uuid
from cp7_local_stage_audit import Cursor,emit
import cp7_ow12b_frozen_cutting_cases as native

class LocalCursor(Cursor):
 def execute(self,statement,params=None,**kwargs):
  return super().execute(statement,json.loads(json.dumps(params,default=str))if params is not None else None,**kwargs)

cur=LocalCursor();cur.execute('begin')
native.plan.b.api.admin=lambda cursor:None
native.plan.monetary_state=lambda cursor:{} # Physical data is outside this local fixture.
def limited(cursor,name,args,actor):
 types=['uuid[]']if name.startswith('erp_cp7_get_')else['jsonb','uuid']
 return cursor.execute('select public.'+name+'('+','.join('%s::'+t for t in types)+')',args).fetchone()[0]
native.plan.staged.limited=limited
root='33333333-3333-4333-8333-333333333333';actor='11111111-1111-4111-8111-111111111111'
config=dict(mean_mode='SELECTED_MANUAL',daily_pcs='10',minimum_available_days='20',lead_days='3',review_days='7',buffer_days='0')
limited(cur,'erp_cp7_save_planning_profile_v1',(json.dumps(dict(root_id=root,product_version_id='22222222-2222-4222-8222-222222222222',expected_revision='0',config=config,reason='Explicit local fixture')),str(uuid.uuid4())),actor)
observed={};native.select_synthetic_volume_assumptions(cur,dict(root=root),actor,observed)
assert cur.execute('select count(*)from cp7_profile.commands').fetchone()[0]==4
assert cur.execute('select count(*)from cp7_identity.commands').fetchone()[0]==1
result=dict(status='PASS_LOCAL_FIXTURE_SQL_ONLY',actual_volume_preparation_helper=True,actual_profile_and_policy_function_bodies=True,
 controlled_identity_and_dimensional_tables=True,observed=observed,actual_Native=False,actual_Auth_HTTP_credit=False,production_go=False)
cur.execute('rollback');emit(dict(kind='ready',result=result))
assert json.loads(sys.stdin.readline())==dict(kind='after_use')
emit(dict(kind='done',result=result))
