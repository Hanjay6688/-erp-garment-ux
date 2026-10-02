"""Additive immutable report appendix, exact previous obligations preserved."""
import hashlib
import cp7_other_obligation_bundle as previous
ROOT=previous.ROOT
ROLES=previous.ROLES
GRANTS={k:set(v)for k,v in previous.GRANTS.items()}
TABLE_GRANTS={**previous.TABLE_GRANTS,'cp7_reminder':{**previous.TABLE_GRANTS['cp7_reminder'],'cp7_analysis_native.publications':'SELECT'}}
FUNCTIONS=dict(obligation_report_fields='i',obligation_report_visible='s',obligation_report_render='i',
 obligation_report_base='s',obligation_report_preview='v',obligation_report_document='v',obligation_report_command='v',obligation_report_index='v')
TABLES=('obligation_reports','obligation_report_requests')
PUBLIC=('public.erp_cp7_get_obligation_report_preview_v1(uuid)','public.erp_cp7_read_obligation_report_v1(uuid)',
 'public.erp_cp7_publish_obligation_report_v1(jsonb,uuid)','public.erp_cp7_get_obligation_report_request_v1(jsonb,uuid)',
 'public.erp_cp7_list_obligation_reports_v1(jsonb)')
def extension():return previous.extension()+'\n'+(ROOT/'scripts/cp7-src/reminders/obligation-report.sql').read_text()
def bundle():return previous.previous.previous.predecessor.bundle()+'\n'+extension()
def verify(cur):
 previous.verify(cur,FUNCTIONS,TABLES,PUBLIC)
 for name in TABLES:
  assert cur.execute("select count(*)from pg_trigger where tgrelid=%s::regclass and not tgisinternal and tgfoid='cp7_reminder_native.immutable_request()'::regprocedure",('cp7_reminder_native.'+name,)).fetchone()[0]==1
 assert cur.execute("select has_table_privilege('cp7_reminder','cp7_analysis_native.publications','SELECT')and not has_table_privilege('cp7_reminder','cp7_analysis_native.publications','INSERT,UPDATE,DELETE,TRUNCATE,TRIGGER')").fetchone()[0]
 assert not cur.execute("select has_table_privilege('cp7_reminder','cp7_analysis_native.runs','SELECT,INSERT,UPDATE,DELETE')").fetchone()[0]
 return dict(stage='IMMUTABLE_NATIVE_REPORT_APPENDIX_DATED_CURRENT_KNOWLEDGE_NO_AGGREGATION',source_sha256=hashlib.sha256(bundle().encode()).hexdigest(),full_family_acceptance=False)
