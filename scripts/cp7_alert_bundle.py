"""WA-2a (owner D17-3..D17-6): Pengingat sistem and their forwarding to the owner's WhatsApp through CallMeBot.

alerts/alerts.sql on top of reminders v2 (exact previous chain preserved; the reminder module is not changed). Schema
cp7_alert_native owned by the NOLOGIN role cp7_alert (BYPASSRLS, like cp7_payable_read, to read the Native rows its
sources read). Its sources: the Ringkasan Gudang fabric-below-minimum rule on the same Native tables, and the accepted
reminder sources receivable_source()/payable_source(), read as the owner who saved the WhatsApp settings. Four small
functions owned by postgres (the stack's Vault and pg_net user) hold every use of the CallMeBot key; only cp7_alert can
call them. The two ticks are executable by postgres only (pg_cron); their schedules (erp-wa-*) are rows of
cp7_alert_native.schedules(), never installed by this bundle. Uninstall is `drop owned by cp7_alert cascade` like every
other F03 role: the schema goes with everything in it.
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
 **{name:(ROLE,True,'v')for name in('apply_kind','claims_enter','claims_leave','collect_kinds','collect_tick','dispatch','guard_alert',
  'guard_append_only','guard_dispatch','guard_outbox','owner_access','queue_alert','queue_manual','queue_repeats','reconcile','record_tick',
  'require_owner','send_tick','wa_key_set','wa_resolve','wa_settings_read','wa_settings_save','wa_test')},
 **{name:(ROLE,True,'s')for name in('alerts_read','ap_source','ar_source','current_settings','fabric_source','in_quiet','item_line','label','num',
  'outbox_items','render','require_tick_limit','rp','settings_json','tgl','ts_key','uid','jwt')},
 'defaults':(ROLE,True,'i'),'schedules':(ROLE,False,'i'),
 'vault_key_present':('postgres',True,'s'),'vault_key_write':('postgres',True,'v'),'wa_post':('postgres',True,'v'),'wa_response':('postgres',True,'s')}
KEY_FUNCTIONS=('vault_key_present()','vault_key_write(text)','wa_post(text,text)','wa_response(bigint)')
TICKS=('collect_tick()','send_tick()','schedules()')
TABLES=('alerts','dispatch_items','dispatches','key_events','outbox','settings','source_state','ticks','transport')
TRIGGERS={('alerts','alerts_guard'),('alerts','alerts_queue'),('dispatch_items','dispatch_items_append_only'),('dispatches','dispatches_guard'),
 ('key_events','key_events_append_only'),('outbox','outbox_guard'),('settings','settings_append_only'),('transport','transport_no_delete')}
PUBLIC={'public.erp_cp7_get_alerts_v1(jsonb)':'s','public.erp_cp7_get_wa_settings_v1()':'v','public.erp_cp7_save_wa_settings_v1(jsonb,uuid)':'v',
 'public.erp_cp7_set_wa_key_v1(text,uuid)':'v','public.erp_cp7_send_wa_test_v1(uuid)':'v','public.erp_cp7_resolve_wa_dispatch_v1(jsonb,uuid)':'v'}
SCHEDULES=('erp-wa-collect','erp-wa-send')
CALLMEBOT='https://api.callmebot.com/whatsapp.php'
OUTSIDERS=('anon','authenticated','service_role','cp7_capture','cp7_reminder','cp7_payable_read')
def extension():return previous.extension()+'\n'+(ROOT/'scripts/cp7-src/alerts/alerts.sql').read_text()
def bundle():return previous.bundle()+'\n'+(ROOT/'scripts/cp7-src/alerts/alerts.sql').read_text()
def verify(cur):
 previous.verify(cur)
 return verify_alert(cur)
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
