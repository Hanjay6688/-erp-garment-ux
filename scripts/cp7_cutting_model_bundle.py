"""Separate prospective Native model producer, registered once in main planning."""
import hashlib
import cp7_cutting_observation_bundle as previous
ROOT,predecessor,ROLES,GRANTS=previous.ROOT,previous.predecessor,previous.ROLES,previous.GRANTS
def extension():return previous.extension()
def bundle():return predecessor.bundle()+'\n'+extension()
def verify(cur):
 previous.verify(cur)
 rows=cur.execute("select p.oid::regprocedure::text,pg_get_userbyid(p.proowner),p.prosecdef,p.proconfig from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='cp7_cutting_model'").fetchall()
 assert len(rows)==6,rows
 for signature,owner,definer,config in rows:
  assert owner=='cp7_capture'and not definer and 'search_path=\"\"'in(config or[]),(signature,owner,definer,config)
  for who in('anon','authenticated','service_role'):assert not cur.execute("select has_function_privilege(%s,%s,'EXECUTE')",(who,signature)).fetchone()[0]
 for who in('anon','authenticated','service_role'):assert not cur.execute("select has_schema_privilege(%s,'cp7_cutting_model','USAGE')",(who,)).fetchone()[0]
 for table,trigger in [('policies','cutting_model_policy_immutable'),('runs','cutting_model_run_immutable'),('requests','cutting_model_request_immutable')]:
  relation='cp7_cutting_model.'+table
  assert cur.execute('select relrowsecurity,pg_get_userbyid(relowner)from pg_class where oid=%s::regclass',(relation,)).fetchone()==(True,'cp7_capture')
  assert cur.execute("select tgtype,tgenabled,tgfoid='cp7_private.immutable_run()'::regprocedure,tgnargs from pg_trigger where tgrelid=%s::regclass and tgname=%s and not tgisinternal",(relation,trigger)).fetchone()==(27,'O',True,0)
  for who in('anon','authenticated','service_role'):assert not cur.execute("select has_table_privilege(%s,%s,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')",(who,relation)).fetchone()[0]
 for signature in('public.erp_cp7_get_cutting_model_workspace_v1(uuid,uuid)','public.erp_cp7_capture_cutting_model_v1(jsonb,uuid)','public.erp_cp7_get_cutting_model_request_v1(jsonb,uuid)'):
  assert cur.execute('select pg_get_userbyid(proowner),prosecdef,provolatile::text,proconfig from pg_proc where oid=%s::regprocedure',(signature,)).fetchone()==('cp7_capture',True,'v',['search_path=\"\"'])
  assert cur.execute("select has_function_privilege('authenticated',%s,'EXECUTE')and not has_function_privilege('anon',%s,'EXECUTE')and not has_function_privilege('service_role',%s,'EXECUTE')",(signature,signature,signature)).fetchone()[0]
 return dict(stage='NATIVE_PROSPECTIVE_MODEL_PRODUCER_CANDIDATE',source_sha256=hashlib.sha256(bundle().encode()).hexdigest(),factory_qualified=False,model_consumer_qualified=False,full_family_acceptance=False,production_go=False)
