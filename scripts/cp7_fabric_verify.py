"""Exact metadata/read-only boundary; not a Native qualification receipt."""
FUNCTIONS={'material_hash':'i','validate':'i','source':'s','physical_source':'s','index':'i','recipe_state':'i','plan':'i','needs':'i','workspace':'v','save':'v'}
# P08 physical facts: exact read-only columns, never cost/price columns or writers.
COLUMNS={'erp.material_rolls':('id','material_id','status'),'erp.material_stock_movements':('material_id','roll_id','location_id','qty_signed','physical_at'),
 'erp.locations':('id','location_type','is_active'),'erp.bb_purchase_commitments_v1':('id','po_number','location_id','expected_date'),
 'erp.bb_purchase_commitment_lines_v1':('id','commitment_id','material_id','line_number'),'cp7_plan_native.intents':('id','target_key','cutting_group_id')}
PRIVATE_COLUMNS={'erp.material_stock_movements':('unit_cost_snapshot','input_unit_cost','original_unit_cost_snapshot'),'erp.bb_purchase_commitment_lines_v1':('unit_price',),'cp7_plan_native.intents':('actor','core_hash','request_id','draft_id')}
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
 for table,columns in COLUMNS.items():
  for column in columns:assert cur.execute("select has_column_privilege('cp7_capture',%s,%s,'SELECT')",(table,column)).fetchone()[0],(table,column)
  assert not cur.execute("select has_table_privilege('cp7_capture',%s,'INSERT,UPDATE,DELETE,TRUNCATE,TRIGGER')",(table,)).fetchone()[0],table
 for table,columns in PRIVATE_COLUMNS.items():
  for column in columns:assert not cur.execute("select has_column_privilege('cp7_capture',%s,%s,'SELECT')",(table,column)).fetchone()[0],(table,column)
 assert cur.execute("select has_function_privilege('cp7_capture','erp.bb_commitment_line_remaining_v1(uuid,uuid)','EXECUTE')").fetchone()[0]
 # P08 plan-apply own-draft marker: private, read-only to capture, empty outside one apply transaction.
 t='cp7_plan_native.apply_own_drafts'
 assert cur.execute('select pg_get_userbyid(relowner),relrowsecurity from pg_class where oid=%s::regclass',(t,)).fetchone()==('cp7_plan_writer',True)
 assert cur.execute("select count(*)from pg_policy where polrelid=%s::regclass and pg_get_expr(polqual,polrelid)='false'and pg_get_expr(polwithcheck,polrelid)='false'",(t,)).fetchone()[0]==1
 for who in('anon','authenticated','service_role'):assert not cur.execute("select has_table_privilege(%s,%s,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE')",(who,t)).fetchone()[0],who
 assert all(cur.execute("select has_column_privilege('cp7_capture',%s,%s,'SELECT')",(t,c)).fetchone()[0]for c in('cutting_group_id','txid'))
 assert not cur.execute("select has_table_privilege('cp7_capture',%s,'INSERT,UPDATE,DELETE,TRUNCATE')",(t,)).fetchone()[0]
 assert cur.execute('select count(*)from '+t).fetchone()[0]==0
