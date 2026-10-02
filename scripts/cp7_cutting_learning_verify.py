"""Exact inherited private cutting guards for the combined main planner.

These are the unchanged input34/observation44/model53 ownership, role ACL,
schema, table and immutability checks; no child-bundle recursion.
"""

def verify(cur):
 for schema,count in [('cp7_cutting_learning',9),('cp7_cutting_inputs',8)]:
  rows=cur.execute("select p.oid::regprocedure::text,pg_get_userbyid(p.proowner),p.prosecdef,p.proconfig from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname=%s",(schema,)).fetchall()
  assert len(rows)==count,(schema,rows)
  for signature,owner,definer,config in rows:
   assert owner=='cp7_capture'and not definer and 'search_path=\"\"'in(config or[]),(signature,owner,definer,config)
   for who in('anon','authenticated','service_role'):assert not cur.execute('select has_function_privilege(%s,%s,\'EXECUTE\')',(who,signature)).fetchone()[0],(who,signature)
  for who in('anon','authenticated','service_role'):assert not cur.execute('select has_schema_privilege(%s,%s,\'USAGE\')',(who,schema)).fetchone()[0]
 for relation,trigger in [('plans','cutting_plan_immutable'),('requests','cutting_input_request_immutable')]:
  table='cp7_cutting_inputs.'+relation
  assert cur.execute('select relrowsecurity from pg_class where oid=%s::regclass',(table,)).fetchone()[0]
  assert cur.execute("select tgtype,tgenabled,tgfoid='cp7_private.immutable_run()'::regprocedure,tgnargs from pg_trigger where tgrelid=%s::regclass and tgname=%s and not tgisinternal",(table,trigger)).fetchone()==(27,'O',True,0)
  for who in('anon','authenticated','service_role'):assert not cur.execute("select has_table_privilege(%s,%s,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')",(who,table)).fetchone()[0]
 for signature in ('public.erp_cp7_get_cutting_input_workspace_v1(uuid)','public.erp_cp7_record_cutting_inputs_v1(jsonb,uuid)','public.erp_cp7_get_cutting_input_request_v1(jsonb,uuid)'):
  assert cur.execute('select pg_get_userbyid(proowner),prosecdef,provolatile::text,proconfig from pg_proc where oid=%s::regprocedure',(signature,)).fetchone()==('cp7_capture',True,'v',['search_path=\"\"'])
  assert cur.execute("select has_function_privilege('authenticated',%s,'EXECUTE')and not has_function_privilege('anon',%s,'EXECUTE')and not has_function_privilege('service_role',%s,'EXECUTE')",(signature,signature,signature)).fetchone()[0]
 for table in ('erp.cutting_groups','erp.cutting_group_rolls','erp.cutting_roll_yields','erp.material_stock_movements','erp.journal_entries'):
  assert not cur.execute("select has_table_privilege('cp7_capture',%s,'INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')",(table,)).fetchone()[0],table
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
 return dict(main_registered=True,automatic_activation=False,production_go=False)
