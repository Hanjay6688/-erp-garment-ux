"""Actual failure/rollback helper; controlled command, no timing qualification."""
from cp7_local_stage_audit import Cursor,emit
import cp7_ow12b_frozen_choice_cases as native
import json,sys

class LocalCursor(Cursor):
 def execute(self,statement,params=None,**kwargs):
  try:return super().execute(statement,params,**kwargs)
  except RuntimeError as error:
   if 'LOCAL_CONTROLLED_57014'in str(error):error.sqlstate='57014'
   raise

cur=LocalCursor();cur.execute('begin');native.plan.b.api.admin=lambda cursor:None
calls=[];first_errors=[]
def limited(cursor,name,args,actor):
 assert name==native.RPC
 calls.append(args)
 prior=cursor.execute('show statement_timeout').fetchone()[0]
 cursor.execute("select set_config('statement_timeout','8s',true)")
 try:r=cursor.execute('select local_choice.command(%s::jsonb,%s::uuid)',args).fetchone()[0]
 except RuntimeError as error:
  first_errors.append(error);raise
 cursor.execute("select set_config('statement_timeout',%s,true)",(prior,));return r
native.plan.staged.limited=limited
results=[]
for fail_baseline in (False,True):
 cur.execute("select set_config('track_functions','none',true)")
 cur.execute("select set_config('local_choice.always_fail',%s,true)",('yes'if fail_baseline else'no',))
 before=native.choice.metadata(cur);physical=native.plan.monetary_state(cur);observed={};calls.clear();first_errors.clear()
 try:native.profiled_save(cur,dict(subject='CONTROLLED'),dict(explicit_control=True),observed=observed,phase='CONTROLLED_K3')
 except RuntimeError as error:assert error is first_errors[0]and error.sqlstate=='57014'
 else:raise AssertionError('ORIGINAL_TIMEOUT_SWALLOWED')
 assert len(calls)==2 and calls[0]==calls[1]
 assert native.choice.metadata(cur)==before and native.plan.monetary_state(cur)==physical
 assert cur.execute('show track_functions').fetchone()[0]=='none'
 assert cur.execute('show statement_timeout').fetchone()[0]=='0'
 diag=observed['timeout_calibrations'][0]
 assert diag['status']==('DIAGNOSTIC_FAILED'if fail_baseline else'DIAGNOSTIC_COMPLETED_NOT_QUALIFICATION')
 assert diag['all_effects_rolled_back']and diag['qualification_credit']is False
 assert 'write_millis'not in observed and observed['failed_save']['sqlstate']=='57014'
 results.append(dict(baseline_also_failed=fail_baseline,original_exception_rethrown=True,same_UUID_payload=True,metadata_and_physical_rollback=True,tracking_and_timeout_restored=True,qualification_credit=False))
cur.execute('rollback');result=dict(status='PASS_LOCAL_CONTROL_FLOW_ONLY',cases=results,actual_profiled_save_and_calibration_helpers=True,controlled_command_and_identity=True,latency_or_Native_or_Auth_credit=False,production_go=False)
emit(dict(kind='ready',result=result));assert json.loads(sys.stdin.readline())==dict(kind='after_use');emit(dict(kind='done',result=result))
