"""Source-bound selected schedule and yield on the qualified global supply layer."""
import hashlib
import cp7_supply_bundle as predecessor
ROOT=predecessor.ROOT
FILES=('planning/schedule.sql','planning/schedule-scenario.sql')
ROLES=predecessor.ROLES
GRANTS=predecessor.GRANTS

def extension():return '\n'.join((ROOT/'scripts/cp7-src'/p).read_text()for p in FILES)
def bundle():return predecessor.bundle()+'\n'+extension()

def verify(cur):
 predecessor.verify(cur)
 expected={'access_now':'s','route':'i','position_model':'i','validate':'i',
  'source_at':'s','workspace':'v','save':'v','source_within':'s','source':'s','fingerprint':'i',
  'build':'i','serve':'v','capture':'v'}
 rows=cur.execute("select p.oid::regprocedure::text,p.proname,pg_get_userbyid(p.proowner),p.prosecdef,p.proconfig,p.provolatile from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='cp7_schedule_native'").fetchall()
 assert len(rows)==len(expected),rows
 for sig,name,owner,definer,config,volatility in rows:
  assert owner=='cp7_capture'and not definer and expected.get(name)==volatility and 'search_path=\"\"'in(config or[])and'TimeZone=UTC'in(config or[]),(sig,owner,definer,config,volatility)
  for who in('anon','authenticated','service_role'):
   assert not cur.execute('select has_function_privilege(%s,%s,\'EXECUTE\')',(who,sig)).fetchone()[0]
 public=('public.erp_cp7_get_production_schedule_v1(uuid)',
  'public.erp_cp7_save_production_schedule_v1(jsonb,uuid)',
  'public.erp_cp7_capture_planning_scenario_v1(jsonb,uuid)',
  'public.erp_cp7_read_planning_scenario_v1(uuid)')
 for sig in public:
  assert cur.execute('select pg_get_userbyid(proowner),prosecdef,proconfig from pg_proc where oid=%s::regprocedure',(sig,)).fetchone()==('cp7_capture',True,['search_path=\"\"'])
  assert cur.execute('select has_function_privilege(\'authenticated\',%s,\'EXECUTE\')',(sig,)).fetchone()[0]
  for who in('anon','service_role'):
   assert not cur.execute('select has_function_privilege(%s,%s,\'EXECUTE\')',(who,sig)).fetchone()[0]
 for table in('plans','commands','runs'):
  name='cp7_schedule_native.'+table
  for who in('anon','authenticated','service_role'):
   assert not cur.execute("select has_schema_privilege(%s,'cp7_schedule_native','USAGE')or has_table_privilege(%s,%s,'SELECT,INSERT,UPDATE,DELETE')",(who,who,name)).fetchone()[0]
  assert cur.execute('select relrowsecurity from pg_class where oid=%s::regclass',(name,)).fetchone()[0]
  assert cur.execute("select count(*)from pg_policy where polrelid=%s::regclass and pg_get_expr(polqual,polrelid)='false'and pg_get_expr(polwithcheck,polrelid)='false'",(name,)).fetchone()[0]==1
 return dict(stage='NATIVE_SOURCE_BOUND_SELECTED_WORK_CALENDAR_YIELD_AND_SHARED_QUEUE',source_sha256=hashlib.sha256(bundle().encode()).hexdigest(),full_family_acceptance=False)
