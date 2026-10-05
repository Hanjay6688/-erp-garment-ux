"""One atomic source-bound bridge to the unchanged Native cutting draft writer."""
import hashlib
import cp7_analysis_bundle as predecessor
ROOT=predecessor.ROOT
FILES=('plan-native/bootstrap.sql','plan-native/source.sql','plan-native/preflight.sql','plan-native/read.sql','plan-native/commands.sql','plan-native/actual.sql','plan-native/ownership.sql')
ROLES=predecessor.ROLES
GRANTS={**predecessor.GRANTS,'cp7_plan_writer':('auth.uid()','auth.jwt()','erp.get_my_access_v1()','erp.has_permission(text)','cp7_private.immutable_run()','public.erp_save_cutting_group_before_sewing_v2(jsonb,uuid,bigint)')}
def extension():return '\n'.join((ROOT/'scripts/cp7-src'/p).read_text()for p in FILES)
def bundle():return predecessor.bundle() # The analysis bundle owns this extension.
def verify(cur):
 expected={'analysis_source':('v','cp7_capture',True),'actual_source':('v','cp7_capture',True),'actual':('v','cp7_plan_writer',False),'access_now':('v','cp7_plan_writer',False),'fields':('i','cp7_plan_writer',False),'decimal':('i','cp7_plan_writer',False),'material_pool':('s','cp7_plan_writer',False),'preflight':('v','cp7_plan_writer',False),'options':('v','cp7_plan_writer',False),'read':('v','cp7_plan_writer',False),'save':('v','cp7_plan_writer',False),'preview':('v','cp7_plan_writer',False),'apply':('v','cp7_plan_writer',False)}
 rows=cur.execute("select p.oid::regprocedure::text,p.proname,p.provolatile,pg_get_userbyid(p.proowner),p.prosecdef,p.proconfig from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='cp7_plan_native'").fetchall()
 assert len(rows)==len(expected),rows
 for sig,name,volatility,owner,definer,config in rows:
  assert expected.get(name)==(volatility,owner,definer)and'search_path=\"\"'in(config or[])and'TimeZone=UTC'in(config or[]),(sig,config)
  for who in('anon','authenticated','service_role'):assert not cur.execute('select has_function_privilege(%s,%s,\'EXECUTE\')',(who,sig)).fetchone()[0]
 for sig in('public.erp_cp7_save_plan_draft_v1(jsonb,uuid)','public.erp_cp7_preview_plan_action_v1(uuid)','public.erp_cp7_apply_plan_action_v1(jsonb,uuid)','public.erp_cp7_get_plan_options_v1(jsonb)','public.erp_cp7_read_plan_draft_v1(uuid)','public.erp_cp7_read_plan_actual_v1(uuid)'):
  assert cur.execute('select pg_get_userbyid(proowner),prosecdef,proconfig from pg_proc where oid=%s::regprocedure',(sig,)).fetchone()==('cp7_plan_writer',True,['search_path=\"\"'])
  assert cur.execute('select has_function_privilege(\'authenticated\',%s,\'EXECUTE\')',(sig,)).fetchone()[0]
  for who in('anon','service_role','cp7_capture'):assert not cur.execute('select has_function_privilege(%s,%s,\'EXECUTE\')',(who,sig)).fetchone()[0]
 assert cur.execute("select rolcanlogin,rolinherit,rolsuper,rolcreatedb,rolcreaterole,rolreplication,rolbypassrls from pg_roles where rolname='cp7_plan_writer'").fetchone()==(False,False,False,False,False,False,True)
 assert not cur.execute("select has_function_privilege('cp7_capture','public.erp_save_cutting_group_before_sewing_v2(jsonb,uuid,bigint)','EXECUTE')").fetchone()[0]
 for table in('drafts','commands','intents'):
  sig='cp7_plan_native.'+table
  assert cur.execute('select relrowsecurity from pg_class where oid=%s::regclass',(sig,)).fetchone()[0]
  assert cur.execute("select count(*)from pg_policy where polrelid=%s::regclass and pg_get_expr(polqual,polrelid)='false'and pg_get_expr(polwithcheck,polrelid)='false'",(sig,)).fetchone()[0]==1
  triggers=cur.execute("select tgtype,tgenabled,tgfoid='cp7_private.immutable_run()'::regprocedure,tgnargs from pg_trigger where tgrelid=%s::regclass and not tgisinternal",(sig,)).fetchall()
  assert triggers==[(27,'O',True,0)],(sig,triggers)
  for who in('anon','authenticated','service_role'):assert not cur.execute('select has_table_privilege(%s,%s,\'SELECT,INSERT,UPDATE,DELETE\')',(who,sig)).fetchone()[0]
 for table in('erp.material_rolls','erp.material_stock_movements','erp.cutting_groups','erp.cutting_group_rolls','erp.production_orders'):
  assert cur.execute("select has_table_privilege('cp7_plan_writer',%s,'SELECT')",(table,)).fetchone()[0]
  assert not cur.execute("select has_table_privilege('cp7_plan_writer',%s,'INSERT,UPDATE,DELETE')",(table,)).fetchone()[0]
 return dict(stage='ONE_NATIVE_SAVE_DRAFT_AND_LINKED_INTENT_ATOMIC_NO_RESERVATION_NO_POST',source_sha256=hashlib.sha256(bundle().encode()).hexdigest(),full_family_acceptance=False)
