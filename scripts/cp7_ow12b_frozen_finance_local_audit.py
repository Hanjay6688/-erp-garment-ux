"""Actual new B stage/catalog APIs via the explicit local SQL test transport."""
from cp7_local_stage_audit import Cursor,emit
from cp7_ow04_restore_bundle import _catalog_rows
import cp7_frozen_finance_bridge as stage
import json,sys
from copy import deepcopy

assert sys.argv[1]=='cp7_frozen_finance_bridge'
cur=Cursor();cur.execute('begin');before=_catalog_rows(cur)
def predecessor(cursor):
 if _catalog_rows(cursor)!=before:raise ValueError('LOCAL_FROZEN_FINANCE_PARENT_CHANGED')
state=stage.install_delta(cur,predecessor)
stage.admit_catalog(before,_catalog_rows(cur),state)
after=_catalog_rows(cur);refused=0
for mutation in('missing_group','other_function','changed_owner','new_public','private_grant'):
 changed=deepcopy(after)
 if mutation=='missing_group':changed.pop(next(iter(changed)))
 if mutation=='other_function':
  row=changed['functions']['cp7_schedule_native.access_now(boolean)'];row[0]+=' '
 if mutation=='changed_owner':changed['functions'][stage.patches.REQUEST][1]='postgres'
 if mutation=='new_public':changed['functions']['public.unexpected()']=deepcopy(changed['functions'][stage.READER])
 if mutation=='private_grant':changed['functions'][stage.READER][-1].append(['authenticated','cp7_capture','EXECUTE',False])
 try:stage.admit_catalog(before,changed,state)
 except ValueError:refused+=1
 else:raise AssertionError('LOCAL_FROZEN_FINANCE_UNDECLARED_DELTA_ACCEPTED:'+mutation)
assert refused==5
cur.execute('savepoint source_tamper')
original=state['official']['cp7_finance_capture.start(text,uuid,jsonb,timestamp with time zone)'][0]
cur.execute(original.replace('declare a jsonb;','declare a jsonb; -- changed source\n',1),prepare=False)
try:stage.verify(cur,state)
except ValueError as error:assert 'OFFICIAL_A_SOURCE_OR_AUTHORITY_CHANGED'in str(error)
else:raise AssertionError('LOCAL_FROZEN_FINANCE_CHANGED_OFFICIAL_A_ACCEPTED')
cur.execute('rollback to savepoint source_tamper')
stage.rollback_preuse(cur,state)
assert _catalog_rows(cur)==before,'LOCAL_FROZEN_FINANCE_PREUSE_NOT_EXACT22'
state=stage.install_delta(cur,predecessor)
stage.admit_catalog(before,_catalog_rows(cur),state)
result=dict(status='PASS_LOCAL_PREPARATION_ONLY',actual_B_installer_and_22_catalog_groups=True,preuse_inverse_and_reapply_exact=True,
 actual_A_three_private_API_bodies_pinned=True,identity_operational_source_and_ready_financial_source_controlled=True,
 undeclared_catalog_mutations_refused=refused,changed_actual_official_A_body_refused=True,
 actual_Native=False,actual_Auth_HTTP_credit=False,official_report_factory_parity=False,production_go=False)
cur.execute('commit');emit(dict(kind='ready',result=result))
assert json.loads(sys.stdin.readline())==dict(kind='after_use')
cur.execute('begin');cur.ddl=[]
try:stage.rollback_preuse(cur,state)
except ValueError as error:assert str(error)=='FROZEN_FINANCE_AFTER_USE_REQUIRES_COMPOSED_BACKUP_RESTORE'
else:raise AssertionError('LOCAL_FROZEN_FINANCE_AFTER_USE_NOT_REFUSED')
assert not cur.ddl,'LOCAL_FROZEN_FINANCE_DDL_BEFORE_AFTER_USE_REFUSAL'
cur.execute('rollback');cur.execute('begin');stage.verify(cur,state);cur.execute('rollback')
result['purged_operational_jobs_with_official_capture_retained_refused_before_DDL']=True
emit(dict(kind='done',result=result))
