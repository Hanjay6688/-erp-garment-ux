"""Separately installed Native observation candidate; main planning registration."""
import hashlib
import cp7_cutting_input_bundle as inputs
ROOT,predecessor,ROLES,GRANTS=inputs.ROOT,inputs.predecessor,inputs.ROLES,inputs.GRANTS
def extension():return inputs.extension()
def bundle():return predecessor.bundle()+'\n'+extension()
def verify(cur):
 inputs.verify(cur)
 rows=cur.execute("select p.oid::regprocedure::text,pg_get_userbyid(p.proowner),p.prosecdef,p.proconfig from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='cp7_cutting_observations'").fetchall()
 assert len(rows)==4,rows
 for signature,owner,definer,config in rows:
  assert owner=='cp7_capture'and not definer and 'search_path=\"\"'in(config or[]),(signature,owner,definer,config)
  for who in('anon','authenticated','service_role'):assert not cur.execute("select has_function_privilege(%s,%s,'EXECUTE')",(who,signature)).fetchone()[0],(who,signature)
 for who in('anon','authenticated','service_role'):assert not cur.execute("select has_schema_privilege(%s,'cp7_cutting_observations','USAGE')",(who,)).fetchone()[0]
 for table,trigger in [('runs','cutting_observation_immutable'),('requests','cutting_observation_request_immutable')]:
  relation='cp7_cutting_observations.'+table
  assert cur.execute('select relrowsecurity,pg_get_userbyid(relowner)from pg_class where oid=%s::regclass',(relation,)).fetchone()==(True,'cp7_capture')
  assert cur.execute('select exists(select 1 from pg_trigger where tgrelid=%s::regclass and tgname=%s and not tgisinternal)',(relation,trigger)).fetchone()[0]
  for who in('anon','authenticated','service_role'):assert not cur.execute("select has_table_privilege(%s,%s,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,TRIGGER')",(who,relation)).fetchone()[0]
 for signature in ('public.erp_cp7_capture_cutting_observation_v1(jsonb,uuid)','public.erp_cp7_get_cutting_observation_request_v1(jsonb,uuid)'):
  assert cur.execute('select pg_get_userbyid(proowner),prosecdef,provolatile::text,proconfig from pg_proc where oid=%s::regprocedure',(signature,)).fetchone()==('cp7_capture',True,'v',['search_path=\"\"'])
  assert cur.execute("select has_function_privilege('authenticated',%s,'EXECUTE')and not has_function_privilege('anon',%s,'EXECUTE')and not has_function_privilege('service_role',%s,'EXECUTE')",(signature,signature,signature)).fetchone()[0]
 return dict(stage='NATIVE_CUTTING_OBSERVATION_CANDIDATE',source_sha256=hashlib.sha256(bundle().encode()).hexdigest(),trained_model=False,full_family_acceptance=False,production_go=False)
