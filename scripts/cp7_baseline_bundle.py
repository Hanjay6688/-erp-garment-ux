"""P06 native profile/target source slice on the qualified P05/F03 predecessor."""
import hashlib
import cp7_planning_bundle as predecessor
ROOT=predecessor.ROOT
FILES=('planning/profile.sql','planning/baseline-source.sql')
ROLES=predecessor.ROLES
GRANTS={principal:tuple(signatures)for principal,signatures in predecessor.GRANTS.items()}
# These are explicit, pure private helper capabilities; never ERP writer EXEC.
GRANTS['cp7_policy']=GRANTS.get('cp7_policy',())+('cp7_wip.fields(jsonb,text[])','cp7_demand.decimal(jsonb)')
def extension():return '\n'.join((ROOT/'scripts/cp7-src'/p).read_text()for p in FILES)
def bundle():return predecessor.bundle()+'\n'+extension()
def verify(cur):
 predecessor.verify(cur)
 expected={
  'cp7_profile':{'source':('cp7_policy',False),'workspace':('cp7_capture',False),'apply':('cp7_policy',False)},
  'cp7_baseline_native':{n:('cp7_capture',False)for n in('source_within','source','build','serve','capture')},
 }
 for schema,functions in expected.items():
  rows=cur.execute('select p.oid::regprocedure::text,p.proname,pg_get_userbyid(p.proowner),p.prosecdef,p.proconfig,p.provolatile from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname=%s',(schema,)).fetchall()
  assert len(rows)==len(functions),(schema,rows)
  for sig,name,owner,definer,config,volatility in rows:
   assert functions.get(name)==(owner,definer)and 'search_path=""'in(config or[])and'TimeZone=UTC'in(config or[]),(sig,owner,definer,config)
   assert volatility==('s'if name in('source','source_within')else'i'if name=='build'else'v'),(sig,volatility)
   for who in('anon','authenticated','service_role'):
    assert not cur.execute('select has_function_privilege(%s,%s,\'EXECUTE\')',(who,sig)).fetchone()[0]
  for who in('anon','authenticated','service_role'):
   assert not cur.execute('select has_schema_privilege(%s,%s,\'USAGE\')',(who,schema)).fetchone()[0]
 for sig,owner in [('public.erp_cp7_get_planning_profiles_v1(uuid[])','cp7_capture'),('public.erp_cp7_save_planning_profile_v1(jsonb,uuid)','cp7_policy'),('public.erp_cp7_capture_baseline_v1(jsonb,uuid)','cp7_capture'),('public.erp_cp7_read_baseline_v1(uuid)','cp7_capture')]:
  assert cur.execute('select pg_get_userbyid(proowner),prosecdef,proconfig from pg_proc where oid=%s::regprocedure',(sig,)).fetchone()==(owner,True,['search_path=""'])
  for who in('anon','service_role'):
   assert not cur.execute('select has_function_privilege(%s,%s,\'EXECUTE\')',(who,sig)).fetchone()[0]
  assert cur.execute('select has_function_privilege(\'authenticated\',%s,\'EXECUTE\')',(sig,)).fetchone()[0]
 for table in('cp7_profile.profiles','cp7_profile.commands','cp7_baseline_native.runs'):
  assert cur.execute('select relrowsecurity from pg_class where oid=%s::regclass',(table,)).fetchone()[0]
  assert cur.execute("select count(*)from pg_policy where polrelid=%s::regclass and pg_get_expr(polqual,polrelid)='false'and pg_get_expr(polwithcheck,polrelid)='false'",(table,)).fetchone()[0]==1
 return dict(stage='P06_NATIVE_PROFILE_TARGET_SCOPE_WIP_CALENDAR_UNKNOWN_APPLY_FALSE',source_sha256=hashlib.sha256(bundle().encode()).hexdigest(),full_family_acceptance=False)
