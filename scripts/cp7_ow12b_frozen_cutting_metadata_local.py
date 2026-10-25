"""Real metadata SQL across session zones; controlled local administrator only."""
from cp7_local_stage_audit import Cursor,emit
import cp7_ow12b_frozen_cutting_cases as native
import cp7_ow12b_frozen_cutting_transport_cases as transport
import json
import ast,os,subprocess

original_head=os.environ.get('CP7_METADATA_ORIGINAL_HEAD')
if original_head:
 source=subprocess.check_output(['git','show',original_head+':scripts/cp7_ow12b_frozen_cutting_cases.py'],text=True)
 function=next(n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef)and n.name=='metadata')
 exec(compile(ast.fix_missing_locations(ast.Module(body=[function],type_ignores=[])),'metadata-original/'+original_head,'exec'),native.__dict__)

cur=Cursor();cur.execute('begin')
native.plan.b.api.admin=lambda cursor:None # Local PGlite administrator; no Auth/Native claim.
cur.execute("select set_config('TimeZone','UTC',true)");before=native.metadata(cur)
zones=('UTC','Asia/Jakarta','America/Los_Angeles')
for zone in zones:
 cur.execute("select set_config('TimeZone',%s,true)",(zone,))
 assert native.metadata(cur)==before,('CUTTING_METADATA_SESSION_TIMEZONE_CHANGED_MEANING',zone)
 assert cur.execute("select current_setting('TimeZone')").fetchone()[0]==zone
 transport.check(cur,before,0)
cur.execute("update cp7_plan_native.intents set recorded_at=recorded_at+interval '1 microsecond'")
try:transport.check(cur,before,0)
except AssertionError:pass
else:raise AssertionError('CUTTING_METADATA_REAL_MICROSECOND_CHANGE_IGNORED')
cur.execute('rollback');result=dict(status='PASS_LOCAL_SQL_ONLY',session_zones=list(zones),actual_metadata_and_transport_check=True,real_stored_microsecond_change_refused=True,session_timezone_restored=True,actual_Native=False,actual_Auth_HTTP_credit=False,production_go=False)
emit(dict(kind='ready',result=result))
assert json.loads(__import__('sys').stdin.readline())==dict(kind='after_use')
emit(dict(kind='done',result=result))
