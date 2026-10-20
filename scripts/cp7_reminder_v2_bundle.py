"""Reminders v2 from a staged analysis snapshot: snapshot conditions built once per run, a live recheck before a
local preview is claimed and when it is finished, receivables/payables read live. Exact previous chain preserved."""
import hashlib
import cp7_obligation_report_bundle as previous
ROOT=previous.ROOT
ROLES=previous.ROLES
GRANTS={k:set(v)for k,v in previous.GRANTS.items()}
# The live recheck counts the plans of a target recorded after a snapshot: their recording time and row transaction.
TABLE_GRANTS={**previous.TABLE_GRANTS,'cp7_capture':{**previous.TABLE_GRANTS['cp7_capture'],
 'cp7_plan_native.intents':'SELECT(id,target_key,cutting_group_id,recorded_at,xmin)'}}
CAPABILITIES=('staged_authority','staged_page_inputs','staged_target_now','accessory_target_now')
FUNCTIONS=dict(staged_authority='v',staged_page_inputs='v',staged_target_now='v',guard_staged_set='v',guard_staged_episode='v',guard_staged_claim='v',
 staged_wib='i',staged_access='v',staged_policy_rows='v',staged_row='i',staged_live_hash='i',staged_page_rows='i',staged_set_status='s',
 staged_set_unit='v',staged_set_step='v',staged_conditions_read='v',staged_obligation_rows='v',staged_obligations='v',staged_verdict='v',
 staged_recheck='v',staged_body='i',staged_payload='v',staged_policy_scope='v',staged_policy_command='v',staged_binding_command='v',
 staged_last_local='s',staged_record='v',staged_recheck_json='s',staged_claim_json='s',staged_claim='v',staged_finish='v',staged_resolution='v',
 staged_command='v',staged_workspace='v',accessory_target_now='v',accessory_capture='s',accessory_category_locks='v')
CONTRACTS={name:('cp7_capture',True)for name in CAPABILITIES}
CONTRACTS.update(accessory_capture=('cp7_capture',False),accessory_category_locks=('postgres',True))
TABLES=('staged_condition_sets','staged_conditions','staged_episodes','staged_rechecks','staged_claims','staged_claim_resolutions')
PUBLIC=('public.erp_cp7_step_reminder_conditions_v2(uuid)','public.erp_cp7_read_reminder_conditions_v2(jsonb)',
 'public.erp_cp7_get_reminder_obligations_v2(uuid)','public.erp_cp7_recheck_reminder_v2(uuid,text)','public.erp_cp7_get_reminder_workspace_v2(uuid)',
 'public.erp_cp7_save_reminder_policy_v2(jsonb,uuid)','public.erp_cp7_save_reminder_binding_v2(jsonb,uuid)','public.erp_cp7_claim_reminder_v2(jsonb,uuid)',
 'public.erp_cp7_finish_reminder_v2(jsonb,uuid)','public.erp_cp7_resolve_reminder_claim_v2(jsonb,uuid)','public.erp_cp7_get_reminder_request_v2(jsonb,uuid,text)')
def extension():return previous.extension()+'\n'+(ROOT/'scripts/cp7-src/reminders/staged-reminders.sql').read_text()+'\n'+(ROOT/'scripts/cp7-src/reminders/accessory-source.sql').read_text()+'\n'+(ROOT/'scripts/cp7-src/ops/background.sql').read_text()
def bundle():return previous.previous.previous.previous.predecessor.bundle()+'\n'+extension()
def verify(cur):
 previous.verify(cur,FUNCTIONS,TABLES,PUBLIC,CONTRACTS)
 for name in TABLES:
  assert cur.execute("select count(*)from pg_trigger where tgrelid=%s::regclass and not tgisinternal",('cp7_reminder_native.'+name,)).fetchone()[0]==1,name
 for name in CAPABILITIES:
  sig=cur.execute("select p.oid::regprocedure::text from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='cp7_reminder_native'and p.proname=%s",(name,)).fetchone()[0]
  assert cur.execute("select has_function_privilege('cp7_reminder',%s,'EXECUTE')",(sig,)).fetchone()[0],sig
  for who in('anon','authenticated','service_role','cp7_obligation_read','cp7_payable_read'):
   assert not cur.execute('select has_function_privilege(%s,%s,\'EXECUTE\')',(who,sig)).fetchone()[0],(who,sig)
 for sig in('cp7_reminder_native.accessory_capture(uuid,text,text,integer,timestamp with time zone)',
            'cp7_reminder_native.accessory_category_locks(uuid,text)'):
  assert cur.execute("select has_function_privilege('cp7_capture',%s,'EXECUTE')",(sig,)).fetchone()[0],sig
  for who in('cp7_reminder','cp7_obligation_read','cp7_payable_read','anon','authenticated','service_role'):
   assert not cur.execute("select has_function_privilege(%s,%s,'EXECUTE')",(who,sig)).fetchone()[0],(who,sig)
 # Hosted postgres is NON-superuser: the row-lock helper calls only the
 # explicit own-run capability, not inherited private capture-table rights.
 assert cur.execute("select has_schema_privilege('postgres','cp7_reminder_native','USAGE')and "
  "has_function_privilege('postgres','cp7_reminder_native.staged_authority(uuid,text[])','EXECUTE')").fetchone()[0]
 for column in('id','target_key','cutting_group_id','recorded_at','xmin'):
  assert cur.execute("select has_column_privilege('cp7_capture','cp7_plan_native.intents',%s,'SELECT')",(column,)).fetchone()[0],column
 for column in('actor','core_hash','request_id','draft_id'):
  assert not cur.execute("select has_column_privilege('cp7_capture','cp7_plan_native.intents',%s,'SELECT')",(column,)).fetchone()[0],column
 assert not cur.execute("select has_schema_privilege('cp7_capture','cp7_reminder_native','CREATE')or has_schema_privilege('cp7_reminder','public','CREATE')").fetchone()[0]
 assert not cur.execute("select exists(select 1 from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname in('cp7_analysis_stage','cp7_plan_native')and c.relkind in('r','p','v')and has_table_privilege('cp7_reminder',c.oid,'SELECT,INSERT,UPDATE,DELETE'))").fetchone()[0]
 assert cur.execute("select count(*)from cp7_reminder_native.staged_claims where environment<>'LOCAL_TEST_SINK'").fetchone()[0]==0
 verify_background(cur)
 return dict(stage='REMINDERS_V2_STAGED_SNAPSHOT_CONDITIONS_LIVE_RECHECK_BEFORE_LOCAL_PREVIEW_NO_EXTERNAL_DELIVERY',
  source_sha256=hashlib.sha256(bundle().encode()).hexdigest(),full_family_acceptance=False)

def verify_background(cur):
 """OW-02 private dispatcher: no new client capability or Native writes."""
 expected={'reminder_pending_at':('cp7_reminder',True,'s'),'reminder_next':('cp7_reminder',True,'v'),
  'report_next':('cp7_capture',False,'v'),'analysis_next':('cp7_capture',False,'v'),'run_next':('cp7_capture',False,'v')}
 rows=cur.execute("select p.oid::regprocedure::text,p.proname,pg_get_userbyid(p.proowner),p.prosecdef,p.provolatile::text,p.proconfig "
  "from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='cp7_background'").fetchall()
 assert sorted(r[1]for r in rows)==sorted(expected),rows
 for sig,name,owner,definer,volatility,config in rows:
  assert(owner,definer,volatility)==expected[name]and config==['search_path=\"\"','TimeZone=UTC'],(sig,owner,definer,volatility,config)
  assert cur.execute("select has_function_privilege('cp7_capture',%s,'EXECUTE')",(sig,)).fetchone()[0],sig
  for who in('anon','authenticated','service_role','cp7_obligation_read','cp7_payable_read'):
   assert not cur.execute("select has_function_privilege(%s,%s,'EXECUTE')",(who,sig)).fetchone()[0],(who,sig)
  assert cur.execute("select has_function_privilege('cp7_reminder',%s,'EXECUTE')",(sig,)).fetchone()[0]==(owner=='cp7_reminder'),sig
 assert cur.execute("select pg_get_userbyid(nspowner)from pg_namespace where nspname='cp7_background'").fetchone()[0]=='cp7_capture'
 assert not cur.execute("select has_schema_privilege('cp7_reminder','cp7_background','CREATE')").fetchone()[0]
 assert not cur.execute("select exists(select 1 from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='cp7_background')").fetchone()[0]
 assert cur.execute("select prosrc from pg_proc where oid='cp7_ops.analysis_tick()'::regprocedure").fetchone()[0].strip()==(
  "select cp7_background.run_next()||jsonb_build_object('tick','cp7-staged-runner','at',clock_timestamp())")
