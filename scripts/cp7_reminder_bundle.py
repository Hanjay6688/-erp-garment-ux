"""Actor-bound durable attention plus delegated Native own-user reminders."""
import hashlib
import cp7_analysis_bundle as predecessor
ROOT=predecessor.ROOT
FILES=('reminders/attention.sql',)
ROLES=(*predecessor.ROLES,'cp7_reminder')
GRANTS={k:set(v)for k,v in predecessor.GRANTS.items()}
GRANTS['cp7_reminder']={
 'auth.uid()','auth.jwt()','erp.get_my_access_v1()','erp.has_permission(text)',
 'public.erp_cp7_read_analysis_v1(uuid)','public.erp_list_my_reminders_v1(text,integer)',
 'public.erp_save_my_reminder_v1(jsonb,uuid,bigint)',
 'public.erp_set_my_reminder_done_v1(uuid,boolean,uuid,bigint)',
 'public.erp_cancel_my_reminder_v1(uuid,text,uuid,bigint)'}
TABLE_GRANTS={'cp7_reminder':{'erp.manual_reminders':'SELECT'}}
def extension():return '\n'.join((ROOT/'scripts/cp7-src'/p).read_text()for p in FILES)
def bundle():return predecessor.bundle()+'\n'+extension()
def verify(cur):
 predecessor.verify(cur)
 expected={'immutable_request':'v','guard_attention':'v','exact_numbers':'i','access_now':'v','workspace':'v','command':'v','manual_source':'v','request_status':'v'}
 rows=cur.execute("select p.oid::regprocedure::text,p.proname,pg_get_userbyid(p.proowner),p.prosecdef,p.proconfig,p.provolatile from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='cp7_reminder_native'").fetchall()
 assert len(rows)==len(expected),rows
 for sig,name,owner,definer,config,volatility in rows:
  assert owner=='cp7_reminder'and not definer and expected.get(name)==volatility and'search_path=\"\"'in(config or[])and'TimeZone=UTC'in(config or[]),(sig,owner,definer,config,volatility)
  for who in('anon','authenticated','service_role'):assert not cur.execute('select has_function_privilege(%s,%s,\'EXECUTE\')',(who,sig)).fetchone()[0]
 for table in('attention','requests'):
  for who in('anon','authenticated','service_role'):
   assert not cur.execute("select has_schema_privilege(%s,'cp7_reminder_native','USAGE')or has_table_privilege(%s,%s,'SELECT,INSERT,UPDATE,DELETE')",(who,who,'cp7_reminder_native.'+table)).fetchone()[0]
  assert cur.execute("select relrowsecurity from pg_class where oid=%s::regclass",('cp7_reminder_native.'+table,)).fetchone()[0]
  assert cur.execute("select count(*)from pg_policy where polrelid=%s::regclass and pg_get_expr(polqual,polrelid)='false'and pg_get_expr(polwithcheck,polrelid)='false'",('cp7_reminder_native.'+table,)).fetchone()[0]==1
 assert not cur.execute("select exists(select 1 from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='erp'and c.relkind in('r','p','v')and has_table_privilege('cp7_reminder',c.oid,'INSERT,UPDATE,DELETE,TRUNCATE,TRIGGER'))").fetchone()[0]
 assert cur.execute("select has_table_privilege('cp7_reminder','erp.manual_reminders','SELECT')").fetchone()[0]
 reads=cur.execute("select n.nspname||'.'||c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='erp'and c.relkind in('r','p','v')and has_table_privilege('cp7_reminder',c.oid,'SELECT')order by 1").fetchall()
 assert reads==[('erp.manual_reminders',)],reads
 for sig in('public.erp_cp7_get_analysis_attention_v1(uuid)','public.erp_cp7_save_analysis_attention_v1(jsonb,uuid)','public.erp_cp7_get_analysis_attention_request_v1(jsonb,uuid)'):
  assert cur.execute('select pg_get_userbyid(proowner),prosecdef,proconfig from pg_proc where oid=%s::regprocedure',(sig,)).fetchone()==('cp7_reminder',True,['search_path=\"\"'])
  assert cur.execute('select has_function_privilege(\'authenticated\',%s,\'EXECUTE\')',(sig,)).fetchone()[0]
  for who in('anon','service_role'):assert not cur.execute('select has_function_privilege(%s,%s,\'EXECUTE\')',(who,sig)).fetchone()[0]
 return dict(stage='DURABLE_SOURCE_ATTENTION_NATIVE_MANUAL_REMINDER_NO_BUSINESS_CLOSURE',source_sha256=hashlib.sha256(bundle().encode()).hexdigest(),full_family_acceptance=False)
