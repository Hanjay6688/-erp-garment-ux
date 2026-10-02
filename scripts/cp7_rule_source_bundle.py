"""Exact private rule-source/episode/local-sink extension; no new Native grants."""
import hashlib
import cp7_reminder_bundle as previous
ROOT=previous.ROOT
FILES=('reminders/policy-history.sql','reminders/rule-condition-source.sql','reminders/rule-episodes.sql','reminders/local-sink.sql')
ROLES=previous.ROLES
GRANTS=previous.GRANTS
TABLE_GRANTS=previous.TABLE_GRANTS
FUNCTIONS=dict(policy_history='v',condition_policy='i',condition_rows='i',condition_source='v',guard_rule_episode='v',rule_episode_evaluate='v',
 guard_local_claim='v',local_access='v',local_recheck='v',local_binding_command='v',local_preview_command='v',local_finish='v',local_manual_resolution='v',local_workspace='v',local_command='v')
TABLES=('rule_episodes','rule_observations','local_bindings','local_claims','local_resolutions')
PUBLIC=('public.erp_cp7_get_reminder_policy_history_v1(jsonb)','public.erp_cp7_get_rule_conditions_v1(uuid)',
 'public.erp_cp7_evaluate_rule_episodes_v1(jsonb,uuid)','public.erp_cp7_get_rule_episode_request_v1(jsonb,uuid)',
 'public.erp_cp7_get_local_reminders_v1(uuid)','public.erp_cp7_save_local_binding_v1(jsonb,uuid)',
 'public.erp_cp7_claim_local_preview_v1(jsonb,uuid)','public.erp_cp7_finish_local_preview_v1(jsonb,uuid)',
 'public.erp_cp7_resolve_local_preview_v1(jsonb,uuid)','public.erp_cp7_get_local_reminder_request_v1(jsonb,uuid,text)')
def extension():return previous.extension()+'\n'+'\n'.join((ROOT/'scripts/cp7-src'/p).read_text()for p in FILES)
def bundle():return previous.predecessor.bundle()+'\n'+extension()
def verify(cur):
 previous.verify(cur,FUNCTIONS,TABLES,PUBLIC)
 for name in('local_bindings','local_claims','local_resolutions','rule_episodes','rule_observations'):
  assert cur.execute("select count(*)from pg_trigger where tgrelid=%s::regclass and not tgisinternal",('cp7_reminder_native.'+name,)).fetchone()[0]==1
 assert cur.execute("select count(*)from cp7_reminder_native.local_bindings where environment<>'LOCAL_TEST_SINK'").fetchone()[0]==0
 assert cur.execute("select count(*)from cp7_reminder_native.local_claims where environment<>'LOCAL_TEST_SINK'").fetchone()[0]==0
 return dict(stage='CURRENT_RULE_SOURCE_SHARED_EPISODES_PRIVATE_LOCAL_SINK_NO_EXTERNAL_DELIVERY',source_sha256=hashlib.sha256(bundle().encode()).hexdigest(),full_family_acceptance=False)
