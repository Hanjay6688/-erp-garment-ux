"""Prospective Native model evaluation, source-bound to immutable own captures."""
import hashlib
import cp7_planning_bundle as predecessor
ROOT=predecessor.ROOT
FILES=('model-native/bootstrap.sql','model-native/source.sql','model-native/evaluation.sql','model-native/ownership.sql')
ROLES=predecessor.ROLES
GRANTS=predecessor.GRANTS
def extension():return '\n'.join((ROOT/'scripts/cp7-src'/p).read_text()for p in FILES)
def bundle():return predecessor.bundle() # The planning bundle owns this extension.
def verify(cur):
 expected={'query':'i','dataset':'s','build':'i','serve':'v','capture':'v'}
 rows=cur.execute("select p.oid::regprocedure::text,p.proname,pg_get_userbyid(p.proowner),p.prosecdef,p.provolatile,p.proconfig from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='cp7_model_native'").fetchall()
 assert len(rows)==len(expected),rows
 for sig,name,owner,definer,volatility,config in rows:
  assert owner=='cp7_capture'and not definer and expected.get(name)==volatility and'search_path=\"\"'in(config or[])and'TimeZone=UTC'in(config or[]),(sig,owner,volatility,config)
  for who in('anon','authenticated','service_role'):assert not cur.execute('select has_function_privilege(%s,%s,\'EXECUTE\')',(who,sig)).fetchone()[0]
 for sig in('public.erp_cp7_capture_model_evaluation_v1(jsonb,uuid)','public.erp_cp7_read_model_evaluation_v1(uuid)'):
  assert cur.execute('select pg_get_userbyid(proowner),prosecdef,proconfig from pg_proc where oid=%s::regprocedure',(sig,)).fetchone()==('cp7_capture',True,['search_path=\"\"'])
  assert cur.execute('select has_function_privilege(\'authenticated\',%s,\'EXECUTE\')',(sig,)).fetchone()[0]
  for who in('anon','service_role'):assert not cur.execute('select has_function_privilege(%s,%s,\'EXECUTE\')',(who,sig)).fetchone()[0]
 for table in('registry','runs'):
  sig='cp7_model_native.'+table
  assert cur.execute('select relrowsecurity from pg_class where oid=%s::regclass',(sig,)).fetchone()[0]
  assert cur.execute("select count(*)from pg_policy where polrelid=%s::regclass and pg_get_expr(polqual,polrelid)='false'and pg_get_expr(polwithcheck,polrelid)='false'",(sig,)).fetchone()[0]==1
  for who in('anon','authenticated','service_role'):assert not cur.execute('select has_schema_privilege(%s,\'cp7_model_native\',\'USAGE\')or has_table_privilege(%s,%s,\'SELECT,INSERT,UPDATE,DELETE\')',(who,who,sig)).fetchone()[0]
 return dict(stage='NATIVE_PROSPECTIVE_MODEL_EVALUATION',source_sha256=hashlib.sha256(bundle().encode()).hexdigest(),full_family_acceptance=False)
