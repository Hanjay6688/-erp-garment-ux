"""Actor-bound durable attention plus delegated Native own-user reminders."""
import hashlib
import cp7_analysis_bundle as predecessor
ROOT=predecessor.ROOT
FILES=('reminders/attention.sql','reminders/receivable-source.sql','reminders/payable-source.sql','reminders/obligation-episodes.sql','reminders/obligation-history.sql','reminders/rule-policy.sql')
ROLES=('cp7_payable_read',*predecessor.ROLES,'cp7_reminder')
GRANTS={k:set(v)for k,v in predecessor.GRANTS.items()}
GRANTS['cp7_reminder']={
 'auth.uid()','auth.jwt()','erp.get_my_access_v1()','erp.has_permission(text)',
 'public.erp_cp7_read_analysis_v1(uuid)','public.erp_list_my_reminders_v1(text,integer)',
 'public.erp_save_my_reminder_v1(jsonb,uuid,bigint)',
 'public.erp_set_my_reminder_done_v1(uuid,boolean,uuid,bigint)',
 'public.erp_cancel_my_reminder_v1(uuid,text,uuid,bigint)','public.erp_cp7_get_sales_v1(jsonb)'}
GRANTS['cp7_payable_read']={'auth.uid()','auth.jwt()','erp.get_my_access_v1()','erp.has_permission(text)','public.erp_get_supplier_credit_v1(jsonb)','erp.material_purchase_final_ap_total(uuid)','erp.material_purchase_grni_total(uuid)','erp.material_purchase_total_liability(uuid)','erp.material_purchase_invoice_capacity(uuid)','erp.material_purchase_posted_invoice_qty(uuid)'}
AP_TABLES=('erp.v_material_purchase_liability_status','erp.material_purchase_headers','erp.material_purchase_items','erp.suppliers','erp.supplier_payments','erp.material_supplier_invoices','erp.material_supplier_invoice_lines')
TABLE_GRANTS={**predecessor.TABLE_GRANTS,'cp7_reminder':{'erp.manual_reminders':'SELECT'},'cp7_payable_read':{name:'SELECT'for name in AP_TABLES}}
def extension():return '\n'.join((ROOT/'scripts/cp7-src'/p).read_text()for p in FILES)
def bundle():return predecessor.bundle()+'\n'+extension()
def verify(cur,extension_functions=None,extension_tables=(),extension_public=()):
 predecessor.verify(cur)
 expected={'immutable_request':'v','guard_attention':'v','exact_numbers':'i','access_now':'v','recheck':'v','workspace':'v','command':'v','manual_source':'v','request_status':'v','receivable_source':'s','receivable_conditions':'v','payable_exact_numbers':'i','payable_source':'s','payable_conditions':'v','guard_obligation_episode':'v','obligation_access':'v','obligation_evaluate':'v','obligation_history':'v'}
 expected.update(policy_validate='i',policy_scope_access='v',policy_rows='s',policy_workspace='v',policy_resolve='i',policy_timing='i',policy_command='v')
 expected.update(extension_functions or{})
 rows=cur.execute("select p.oid::regprocedure::text,p.proname,pg_get_userbyid(p.proowner),p.prosecdef,p.proconfig,p.provolatile from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='cp7_reminder_native'").fetchall()
 assert len(rows)==len(expected),rows
 for sig,name,owner,definer,config,volatility in rows:
  assert owner==('cp7_payable_read'if name in('payable_source','payable_exact_numbers')else'cp7_reminder')and definer==(name=='payable_source')and expected.get(name)==volatility and'search_path=\"\"'in(config or[])and'TimeZone=UTC'in(config or[]),(sig,owner,definer,config,volatility)
  for who in('anon','authenticated','service_role'):assert not cur.execute('select has_function_privilege(%s,%s,\'EXECUTE\')',(who,sig)).fetchone()[0]
 for table in('attention','requests','obligation_episodes','obligation_observations','rule_policies',*extension_tables):
  for who in('anon','authenticated','service_role'):
   assert not cur.execute("select has_schema_privilege(%s,'cp7_reminder_native','USAGE')or has_table_privilege(%s,%s,'SELECT,INSERT,UPDATE,DELETE')",(who,who,'cp7_reminder_native.'+table)).fetchone()[0]
  assert cur.execute("select relrowsecurity from pg_class where oid=%s::regclass",('cp7_reminder_native.'+table,)).fetchone()[0]
  assert cur.execute("select count(*)from pg_policy where polrelid=%s::regclass and pg_get_expr(polqual,polrelid)='false'and pg_get_expr(polwithcheck,polrelid)='false'",('cp7_reminder_native.'+table,)).fetchone()[0]==1
 assert not cur.execute("select exists(select 1 from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='erp'and c.relkind in('r','p','v')and has_table_privilege('cp7_reminder',c.oid,'INSERT,UPDATE,DELETE,TRUNCATE,TRIGGER'))").fetchone()[0]
 assert cur.execute("select has_table_privilege('cp7_reminder','erp.manual_reminders','SELECT')").fetchone()[0]
 reads=cur.execute("select n.nspname||'.'||c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='erp'and c.relkind in('r','p','v')and has_table_privilege('cp7_reminder',c.oid,'SELECT')order by 1").fetchall()
 assert reads==[('erp.manual_reminders',)],reads
 for sig in('public.erp_cp7_get_analysis_attention_v1(uuid)','public.erp_cp7_save_analysis_attention_v1(jsonb,uuid)','public.erp_cp7_get_analysis_attention_request_v1(jsonb,uuid)','public.erp_cp7_get_analysis_receivable_conditions_v1(uuid)','public.erp_cp7_get_analysis_payable_conditions_v1(uuid)','public.erp_cp7_evaluate_obligation_episodes_v1(jsonb,uuid)','public.erp_cp7_get_obligation_episode_request_v1(jsonb,uuid)','public.erp_cp7_get_obligation_episode_history_v1(jsonb)','public.erp_cp7_get_reminder_policy_v1(uuid)','public.erp_cp7_save_reminder_policy_v1(jsonb,uuid)','public.erp_cp7_get_reminder_policy_request_v1(jsonb,uuid)',*extension_public):
  assert cur.execute('select pg_get_userbyid(proowner),prosecdef,proconfig from pg_proc where oid=%s::regprocedure',(sig,)).fetchone()==('cp7_reminder',True,['search_path=\"\"'])
  assert cur.execute('select has_function_privilege(\'authenticated\',%s,\'EXECUTE\')',(sig,)).fetchone()[0]
  for who in('anon','service_role'):assert not cur.execute('select has_function_privilege(%s,%s,\'EXECUTE\')',(who,sig)).fetchone()[0]
 assert cur.execute("select rolcanlogin,rolinherit,rolsuper,rolcreatedb,rolcreaterole,rolreplication,rolbypassrls from pg_roles where rolname='cp7_payable_read'").fetchone()==(False,False,False,False,False,False,True)
 assert not cur.execute("select exists(select 1 from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='erp'and c.relkind in('r','p','v')and has_table_privilege('cp7_payable_read',c.oid,'INSERT,UPDATE,DELETE,TRUNCATE,TRIGGER'))").fetchone()[0]
 reads=cur.execute("select n.nspname||'.'||c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='erp'and c.relkind in('r','p','v')and has_table_privilege('cp7_payable_read',c.oid,'SELECT')order by 1").fetchall()
 assert reads==[(name,)for name in sorted(AP_TABLES)],reads
 return dict(stage='DURABLE_SOURCE_ATTENTION_NATIVE_MANUAL_REMINDER_NO_BUSINESS_CLOSURE',source_sha256=hashlib.sha256(bundle().encode()).hexdigest(),full_family_acceptance=False)
