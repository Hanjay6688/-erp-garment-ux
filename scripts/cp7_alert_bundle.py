"""WA-2a (owner D17-3..D17-6): Pengingat sistem and their forwarding to the owner's WhatsApp through CallMeBot.

alerts/alerts.sql on top of reminders v2 (exact previous chain preserved; the reminder module is not changed). Schema
cp7_alert_native owned by the NOLOGIN role cp7_alert (BYPASSRLS, like cp7_payable_read, to read the Native rows its
sources read). Its sources: the Ringkasan Gudang fabric-below-minimum rule on the same Native tables, and the accepted
reminder sources receivable_source()/payable_source(), read as the owner who saved the WhatsApp settings. Four small
functions owned by postgres (the stack's Vault and pg_net user) hold every use of the CallMeBot key; only cp7_alert can
call them. The two ticks are executable by postgres only (pg_cron); their schedules (erp-wa-*) are rows of
cp7_alert_native.schedules(), never installed by this bundle. Uninstall is `drop owned by cp7_alert cascade` like every
other F03 role: the schema goes with everything in it.

WA-2b: PRODUCTION_GAP and FABRIC_NEED from the owner's own staged analysis, through the public functions the Analysis and
Reminder screens call (CALLS), with the owner's identity; cp7_alert reads only which staged jobs the owner has (six columns
of cp7_analysis_stage.jobs). A third tick (analysis_tick, schedule erp-wa-analysis) works through the owner's latest
finished run and asks for an automatic analysis when one is due.
"""
import hashlib
import cp7_reminder_v2_bundle as previous
ROOT=previous.ROOT
ROLE='cp7_alert'
ROLES=(ROLE,)+previous.ROLES
GRANTS={k:set(v)for k,v in previous.GRANTS.items()}
# No auth.uid()/auth.jwt(): the hosted postgres role cannot grant on schema auth; cp7_alert_native.uid()/jwt() read the same settings.
GRANTS[ROLE]={'erp.get_my_access_v1()','erp.has_permission(text)'}
READS=('erp.fabric_master_profiles','erp.locations','erp.manual_reminders','erp.material_stock_movements','erp.materials')
TABLE_GRANTS={**previous.TABLE_GRANTS,ROLE:{name:'SELECT'for name in READS}}
SCHEMA='cp7_alert_native'
# name -> (owner, security definer, volatility)
FUNCTIONS={
 **{name:(ROLE,True,'v')for name in('analysis_recheck','analysis_tick','analysis_unit','apply_kind','apply_one','claims_enter','claims_leave',
  'collect_kinds','collect_tick','dispatch','guard_alert','guard_analysis_request','guard_analysis_run','guard_append_only','guard_dispatch',
  'guard_outbox','owner_access','queue_alert','queue_manual','queue_repeats','reconcile','record_tick','require_owner','resolve_one','send_tick',
  'wa_key_set','wa_resolve','wa_settings_read','wa_settings_save','wa_test')},
 **{name:(ROLE,True,'s')for name in('alerts_read','analysis_row','analysis_status','ap_source','ar_source','current_settings','fabric_source',
  'in_quiet','item_line','label','num','outbox_items','render','require_tick_limit','rp','settings_json','tgl','ts_key','uid','jwt')},
 'analysis_open':(ROLE,True,'i'),'defaults':(ROLE,True,'i'),'schedules':(ROLE,False,'i'),
 'vault_key_present':('postgres',True,'s'),'vault_key_write':('postgres',True,'v'),'wa_post':('postgres',True,'v'),'wa_response':('postgres',True,'s')}
KEY_FUNCTIONS=('vault_key_present()','vault_key_write(text)','wa_post(text,text)','wa_response(bigint)')
TICKS=('collect_tick()','send_tick()','analysis_tick()','schedules()')
TABLES=('alerts','analysis_requests','analysis_runs','dispatch_items','dispatches','key_events','outbox','settings','source_state','ticks','transport')
TRIGGERS={('alerts','alerts_guard'),('alerts','alerts_queue'),('analysis_requests','analysis_requests_guard'),('analysis_runs','analysis_runs_guard'),
 ('dispatch_items','dispatch_items_append_only'),('dispatches','dispatches_guard'),
 ('key_events','key_events_append_only'),('outbox','outbox_guard'),('settings','settings_append_only'),('transport','transport_no_delete')}
PUBLIC={'public.erp_cp7_get_alerts_v1(jsonb)':'s','public.erp_cp7_get_wa_settings_v1()':'v','public.erp_cp7_save_wa_settings_v1(jsonb,uuid)':'v',
 'public.erp_cp7_set_wa_key_v1(text,uuid)':'v','public.erp_cp7_send_wa_test_v1(uuid)':'v','public.erp_cp7_resolve_wa_dispatch_v1(jsonb,uuid)':'v'}
SCHEDULES=('erp-wa-collect','erp-wa-send','erp-wa-analysis')
# Functions of other modules cp7_alert may call: the sales reader receivable_source() reads (invoker), and the public
# functions of the Analysis and Reminder screens, each checking the caller's own access (WA-2b, with the owner's identity).
CALLS=('public.erp_cp7_get_sales_v1(jsonb)','public.erp_cp7_read_reminder_conditions_v2(jsonb)','public.erp_cp7_recheck_reminder_v2(uuid,text)',
 'public.erp_cp7_request_staged_analysis_v1(jsonb,uuid)','public.erp_cp7_staged_snapshot_freshness_v1(uuid)','public.erp_cp7_step_reminder_conditions_v2(uuid)')
JOB_COLUMNS=('actor','captured_at','created_at','query','run_id','state')
CALLMEBOT='https://api.callmebot.com/whatsapp.php'
OUTSIDERS=('anon','authenticated','service_role','cp7_capture','cp7_reminder','cp7_payable_read')
# SS-1 (D17-8/D17-9): the finished-goods reorder point (stock-formula/formula.sql), installed before alerts.sql, whose
# collector reads it through cp7_stock_formula.fg_source(). Schema cp7_stock_formula is owned by cp7_capture (the role
# that already reads the FG stock, sales, production and WIP sources and the planning profile); no new Native read.
FORMULA='scripts/cp7-src/stock-formula/formula.sql'
FORMULA_SCHEMA='cp7_stock_formula'
FORMULA_TABLES=('evaluations','manual_points','runs','settings','wip_models')
FORMULA_FUNCTIONS={'access_now':'v','alert_row':'s','append_only':'v','compute':'v','current_settings':'s','fg_source':'v','model_wip':'v',
 'open_groups':'s','refresh':'v','save_manual':'v','save_settings':'v','workspace':'v','z':'i'}
FORMULA_PUBLIC={'public.erp_cp7_get_fg_reorder_v1(jsonb)':'v','public.erp_cp7_refresh_fg_reorder_v1()':'v',
 'public.erp_cp7_save_fg_reorder_manual_v1(jsonb,uuid)':'v','public.erp_cp7_save_stock_formula_settings_v1(jsonb,uuid)':'v'}
def extension():return previous.extension()+'\n'+(ROOT/FORMULA).read_text()+'\n'+(ROOT/'scripts/cp7-src/alerts/alerts.sql').read_text()
def bundle():return previous.bundle()+'\n'+(ROOT/FORMULA).read_text()+'\n'+(ROOT/'scripts/cp7-src/alerts/alerts.sql').read_text()
def verify(cur):
 previous.verify(cur)
 verify_formula(cur)
 return verify_alert(cur)
def verify_formula(cur):
 one=lambda sql,*args:cur.execute(sql,args or None).fetchone()[0]
 assert one('select pg_get_userbyid(nspowner)from pg_namespace where nspname=%s',FORMULA_SCHEMA)=='cp7_capture'
 for who in OUTSIDERS:
  if who!='cp7_capture':assert not one("select has_schema_privilege(%s,%s,'USAGE')",who,FORMULA_SCHEMA),who
 rows=cur.execute("select p.oid::regprocedure::text,p.proname,pg_get_userbyid(p.proowner),p.prosecdef,p.provolatile::text,p.proconfig "
  "from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname=%s",(FORMULA_SCHEMA,)).fetchall()
 assert sorted(r[1]for r in rows)==sorted(FORMULA_FUNCTIONS),rows
 for sig,name,owner,definer,volatility,config in rows:
  assert(owner,definer,volatility,config)==('cp7_capture',True,FORMULA_FUNCTIONS[name],
   ['search_path=""','TimeZone=UTC']+(['jit=off']if name=='compute'else[])),sig
  for who in('anon','authenticated','service_role','cp7_reminder','cp7_payable_read'):assert not one("select has_function_privilege(%s,%s,'EXECUTE')",who,sig),(who,sig)
  if name!='fg_source':assert not one("select has_function_privilege(%s,%s,'EXECUTE')",ROLE,sig),sig
 assert one("select has_function_privilege(%s,'cp7_stock_formula.fg_source()','EXECUTE')",ROLE)
 tables=cur.execute("select c.relname,pg_get_userbyid(c.relowner),c.relrowsecurity from pg_class c join pg_namespace n on n.oid=c.relnamespace "
  "where n.nspname=%s and c.relkind in('r','p','v','m','f')order by 1",(FORMULA_SCHEMA,)).fetchall()
 assert[t[0]for t in tables]==list(FORMULA_TABLES),tables
 for name,owner,rls in tables:
  assert owner=='cp7_capture'and rls,(name,owner)
  assert one("select count(*)from pg_policy where polrelid=%s::regclass and pg_get_expr(polqual,polrelid)='false'and pg_get_expr(polwithcheck,polrelid)='false'",
   FORMULA_SCHEMA+'.'+name)==1,name
  for who in('anon','authenticated','service_role',ROLE,'cp7_reminder'):
   assert not one("select has_table_privilege(%s,%s,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')",who,FORMULA_SCHEMA+'.'+name),(who,name)
 assert set(cur.execute("select c.relname,t.tgname from pg_trigger t join pg_class c on c.oid=t.tgrelid join pg_namespace n on n.oid=c.relnamespace "
  "where n.nspname=%s and not t.tgisinternal",(FORMULA_SCHEMA,)).fetchall())=={('settings','settings_append_only'),('manual_points','manual_points_append_only')}
 for sig,volatility in FORMULA_PUBLIC.items():
  assert cur.execute("select pg_get_userbyid(proowner),prosecdef,provolatile::text,proconfig from pg_proc where oid=%s::regprocedure",(sig,)).fetchone()==(
   'cp7_capture',True,volatility,['search_path=""']),sig
  assert one("select has_function_privilege('authenticated',%s,'EXECUTE')",sig),sig
  for who in('anon','service_role',ROLE):assert not one("select has_function_privilege(%s,%s,'EXECUTE')",who,sig),(who,sig)
 # Writes only its own tables: no Native table may be written by cp7_capture (the accepted F03 rule, checked again here).
 assert not one("select exists(select 1 from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='erp'and c.relkind in('r','p','v')"
  "and has_table_privilege('cp7_capture',c.oid,'INSERT,UPDATE,DELETE,TRUNCATE,TRIGGER'))")
 assert not one("select has_schema_privilege('cp7_capture','public','CREATE')")
 for name in FORMULA_TABLES:assert one('select count(*)from cp7_stock_formula.'+name)==0,name
def verify_alert(cur):
 one=lambda sql,*args:cur.execute(sql,args or None).fetchone()[0]
 assert cur.execute('select rolcanlogin,rolinherit,rolsuper,rolcreatedb,rolcreaterole,rolreplication,rolbypassrls from pg_roles where rolname=%s',
  (ROLE,)).fetchone()==(False,False,False,False,False,False,True)
 assert one('select pg_get_userbyid(nspowner)from pg_namespace where nspname=%s',SCHEMA)==ROLE
 # Granted to the installing role only so it can hand objects over (PostgreSQL 16+); cp7_alert itself is in no role.
 assert not one("select exists(select 1 from pg_auth_members where member=%s::regrole)",ROLE)
 assert not one("select has_schema_privilege(%s,'auth','USAGE')",ROLE)
 rows=cur.execute("select p.oid::regprocedure::text,p.proname,pg_get_userbyid(p.proowner),p.prosecdef,p.provolatile::text,p.proconfig "
  "from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname=%s",(SCHEMA,)).fetchall()
 assert sorted(r[1]for r in rows)==sorted(FUNCTIONS),rows
 for sig,name,owner,definer,volatility,config in rows:
  assert(owner,definer,volatility)==FUNCTIONS[name],(sig,owner,definer,volatility)
  assert config==(['search_path=""']if owner=='postgres'else['search_path=""','TimeZone=UTC']),(sig,config)
  for who in OUTSIDERS:assert not one("select has_function_privilege(%s,%s,'EXECUTE')",who,sig),(who,sig)
 for sig in KEY_FUNCTIONS:assert one("select has_function_privilege(%s,%s,'EXECUTE')",ROLE,SCHEMA+'.'+sig),sig
 for sig in TICKS:assert one("select has_function_privilege('postgres',%s,'EXECUTE')",SCHEMA+'.'+sig),sig
 for who in OUTSIDERS:assert not one("select has_schema_privilege(%s,%s,'USAGE')",who,SCHEMA),who
 tables=cur.execute("select c.relname,pg_get_userbyid(c.relowner),c.relrowsecurity from pg_class c join pg_namespace n on n.oid=c.relnamespace "
  "where n.nspname=%s and c.relkind in('r','p','v','m','f')order by 1",(SCHEMA,)).fetchall()
 assert[t[0]for t in tables]==list(TABLES),tables
 for name,owner,rls in tables:
  assert owner==('postgres'if name=='transport'else ROLE)and rls,(name,owner,rls)
  assert one("select count(*)from pg_policy where polrelid=%s::regclass and pg_get_expr(polqual,polrelid)='false'and pg_get_expr(polwithcheck,polrelid)='false'",
   SCHEMA+'.'+name)==1,name
  for who in OUTSIDERS:assert not one("select has_table_privilege(%s,%s,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')",who,SCHEMA+'.'+name),(who,name)
 assert one("select has_table_privilege(%s,'cp7_alert_native.transport','SELECT')",ROLE)
 assert not one("select has_table_privilege(%s,'cp7_alert_native.transport','INSERT,UPDATE,DELETE,TRUNCATE')",ROLE)
 assert set(cur.execute("select c.relname,t.tgname from pg_trigger t join pg_class c on c.oid=t.tgrelid join pg_namespace n on n.oid=c.relnamespace "
  "where n.nspname=%s and not t.tgisinternal",(SCHEMA,)).fetchall())==TRIGGERS
 # Reads exactly the five Native tables of its sources, writes none; the reminder sources it calls and nothing else there.
 reads=cur.execute("select n.nspname||'.'||c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='erp'"
  "and c.relkind in('r','p','v','m')and has_table_privilege(%s,c.oid,'SELECT')order by 1",(ROLE,)).fetchall()
 assert[r[0]for r in reads]==list(READS),reads
 assert not one("select exists(select 1 from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='erp'and c.relkind in('r','p','v','m')"
  "and has_table_privilege(%s,c.oid,'INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER'))",ROLE)
 called=cur.execute("select p.proname from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='cp7_reminder_native'"
  "and has_function_privilege(%s,p.oid,'EXECUTE')order by 1",(ROLE,)).fetchall()
 assert[r[0]for r in called]==['payable_source','receivable_source'],called
 assert not one("select exists(select 1 from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='cp7_reminder_native'"
  "and has_table_privilege(%s,c.oid,'SELECT,INSERT,UPDATE,DELETE'))",ROLE)
 # Outside its schema and the reminder sources: exactly the public functions it calls, and six columns of the staged job list.
 granted=cur.execute("select n.nspname||'.'||p.proname||'('||replace(oidvectortypes(p.proargtypes),' ','')||')'from pg_proc p "
  "join pg_namespace n on n.oid=p.pronamespace cross join lateral aclexplode(p.proacl)x where x.grantee=%s::regrole and x.privilege_type='EXECUTE'"
  "and n.nspname<>%s and p.proowner<>%s::regrole order by 1",(ROLE,SCHEMA,ROLE)).fetchall()
 assert[r[0]for r in granted]==sorted(CALLS+tuple(GRANTS[ROLE])+('cp7_reminder_native.payable_source()','cp7_reminder_native.receivable_source()',
  'cp7_stock_formula.fg_source()')),granted
 assert not one("select exists(select 1 from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='cp7_analysis_stage'"
  "and has_table_privilege(%s,c.oid,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER'))",ROLE)
 columns=cur.execute("select a.attname from pg_attribute a where a.attrelid='cp7_analysis_stage.jobs'::regclass and a.attnum>0 and not a.attisdropped "
  "and has_column_privilege(%s,a.attrelid,a.attnum,'SELECT')order by 1",(ROLE,)).fetchall()
 assert[r[0]for r in columns]==list(JOB_COLUMNS),columns
 assert not one("select exists(select 1 from pg_attribute a where a.attrelid='cp7_analysis_stage.jobs'::regclass and a.attnum>0 and not a.attisdropped "
  "and has_column_privilege(%s,a.attrelid,a.attnum,'INSERT,UPDATE,REFERENCES'))",ROLE)
 for sig,volatility in PUBLIC.items():
  assert cur.execute("select pg_get_userbyid(proowner),prosecdef,provolatile::text,proconfig,prolang=(select oid from pg_language where lanname='sql')"
   " from pg_proc where oid=%s::regprocedure",(sig,)).fetchone()==(ROLE,True,volatility,['search_path=""'],True),sig
  assert one("select has_function_privilege('authenticated',%s,'EXECUTE')",sig),sig
  for who in('anon','service_role','cp7_capture'):assert not one("select has_function_privilege(%s,%s,'EXECUTE')",who,sig),(who,sig)
 assert one("select count(*)from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='public'and p.proowner=%s::regrole",ROLE)==len(PUBLIC)
 assert not one("select has_schema_privilege(%s,'public','CREATE')",ROLE)
 # Installed empty, pointed at CallMeBot, no key written, no schedule registered.
 assert cur.execute('select base_url,timeout_ms from cp7_alert_native.transport').fetchall()==[(CALLMEBOT,5000)]
 for name in TABLES:
  if name!='transport':assert one('select count(*)from cp7_alert_native.'+name)==0,name
 assert not one("select exists(select 1 from vault.secrets where name='cp7_callmebot_apikey')")
 assert[j['name']for j in one('select cp7_alert_native.schedules()')]==list(SCHEDULES)
 if one("select to_regclass('cron.job')is not null"):assert not one("select exists(select 1 from cron.job where jobname like 'erp-wa-%%')")
 return dict(stage='WA_SYSTEM_REMINDERS_AND_WHATSAPP_FORWARDING_BUILT_NOT_INSTALLED_NO_KEY_NO_SCHEDULE',
  source_sha256=hashlib.sha256(bundle().encode()).hexdigest(),full_family_acceptance=False,real_message_sent=False)
