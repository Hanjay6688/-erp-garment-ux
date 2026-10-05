"""Exact metadata/read-only boundary; not a Native qualification receipt."""
FUNCTIONS={'validate':'i','source':'s','needs':'i','workspace':'v','save':'v'}
PUBLIC=('public.erp_cp7_get_fabric_recipe_v1(jsonb)','public.erp_cp7_save_fabric_recipe_v1(jsonb,uuid)')
def verify(cur):
 rows=cur.execute("select p.oid::regprocedure::text,p.proname,p.provolatile,pg_get_userbyid(p.proowner),p.prosecdef,p.proconfig from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='cp7_fabric_native'").fetchall()
 assert len(rows)==len(FUNCTIONS),rows
 for sig,name,volatility,owner,definer,config in rows:
  assert (owner,definer,volatility)==('cp7_capture',False,FUNCTIONS[name])and'search_path=""'in(config or[])and'TimeZone=UTC'in(config or[]),(sig,config)
  for who in('anon','authenticated','service_role'):assert not cur.execute("select has_function_privilege(%s,%s,'EXECUTE')",(who,sig)).fetchone()[0]
 for table in('recipes','commands'):
  sig='cp7_fabric_native.'+table
  assert cur.execute('select pg_get_userbyid(relowner),relrowsecurity from pg_class where oid=%s::regclass',(sig,)).fetchone()==('cp7_capture',True)
  assert cur.execute("select count(*)from pg_policy where polrelid=%s::regclass and pg_get_expr(polqual,polrelid)='false'and pg_get_expr(polwithcheck,polrelid)='false'",(sig,)).fetchone()[0]==1
  assert cur.execute("select count(*)from pg_trigger where tgrelid=%s::regclass and tgfoid='cp7_private.immutable_run()'::regprocedure and tgtype=27 and tgenabled='O'and not tgisinternal",(sig,)).fetchone()[0]==1
  for who in('anon','authenticated','service_role'):
   assert not cur.execute("select has_schema_privilege(%s,'cp7_fabric_native','USAGE')or has_table_privilege(%s,%s,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,TRIGGER')",(who,who,sig)).fetchone()[0]
 for sig in PUBLIC:
  assert cur.execute('select pg_get_userbyid(proowner),prosecdef,proconfig from pg_proc where oid=%s::regprocedure',(sig,)).fetchone()==('cp7_capture',True,['search_path=""'])
  assert cur.execute("select has_function_privilege('authenticated',%s,'EXECUTE')",(sig,)).fetchone()[0]
  for who in('anon','service_role'):assert not cur.execute("select has_function_privilege(%s,%s,'EXECUTE')",(who,sig)).fetchone()[0]
 for table in('erp.materials','erp.production_patterns'):
  assert cur.execute("select has_table_privilege('cp7_capture',%s,'SELECT')and not has_table_privilege('cp7_capture',%s,'INSERT,UPDATE,DELETE,TRUNCATE,TRIGGER')",(table,table)).fetchone()[0]
