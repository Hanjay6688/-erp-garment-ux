"""Prospective input candidate, separately qualified before final composition."""
import hashlib
import cp7_planning_bundle as planning
predecessor=planning.predecessor
ROOT,ROLES,GRANTS=planning.ROOT,planning.ROLES,planning.GRANTS
FILES=('cutting-yield/learning-kernel.sql','cutting-yield/inputs.sql')
def extension():return planning.extension()+'\n'+'\n'.join((ROOT/'scripts/cp7-src'/p).read_text()for p in FILES)
def bundle():return predecessor.bundle()+'\n'+extension()
def verify(cur):
 planning.verify(cur)
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
 return dict(stage='PROSPECTIVE_NATIVE_CUTTING_INPUT_CANDIDATE',source_sha256=hashlib.sha256(bundle().encode()).hexdigest(),trained_model=False,full_family_acceptance=False,production_go=False)
