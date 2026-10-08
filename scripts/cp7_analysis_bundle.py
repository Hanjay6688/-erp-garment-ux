"""Native source compiler into the byte-frozen CP7 analysis.v2 contract."""
import hashlib
import cp7_netting_bundle as predecessor
ROOT=predecessor.ROOT
FILES=('planning/material-requirements.sql','planning/fabric-requirements.sql','planning/analysis.sql','planning/analysis-finance.sql','planning/analysis-jobs.sql','planning/analysis-stages.sql','planning/analysis-stage-snapshot.sql','planning/fabric-commands.sql','planning/analysis-archive.sql','planning/report-publication.sql','plan-native/bootstrap.sql','plan-native/source.sql','plan-native/preflight.sql','plan-native/read.sql','plan-native/commands.sql','plan-native/actual.sql','plan-native/ownership.sql')
ROLES=('cp7_plan_writer',)+predecessor.ROLES
GRANTS={**predecessor.GRANTS,'cp7_plan_writer':('auth.uid()','auth.jwt()','erp.get_my_access_v1()','erp.has_permission(text)','cp7_private.immutable_run()','public.erp_save_cutting_group_before_sewing_v2(jsonb,uuid,bigint)')}
# P08: the open-PO remaining reader is the only new EXECUTE on a predecessor function (read-only, BB-owned).
GRANTS['cp7_capture']=tuple(GRANTS.get('cp7_capture',()))+('erp.bb_commitment_line_remaining_v1(uuid,uuid)',)
MATERIAL_TABLES=('erp.accessory_bom_versions','erp.accessory_bom_items','erp.accessory_categories','erp.materials','erp.production_patterns')
import cp7_transaction_source_bundle as transaction_source
# P08 physical fabric facts: exact read-only column grants (see cp7_fabric_verify.COLUMNS).
FABRIC_PHYSICAL_COLUMNS={'erp.material_rolls':'SELECT(id,material_id,status)','erp.material_stock_movements':'SELECT(material_id,roll_id,location_id,qty_signed,physical_at)',
 'erp.locations':'SELECT(id,location_type,is_active)','erp.bb_purchase_commitments_v1':'SELECT(id,po_number,location_id,expected_date)',
 'erp.bb_purchase_commitment_lines_v1':'SELECT(id,commitment_id,material_id,line_number)','cp7_plan_native.intents':'SELECT(id,target_key,cutting_group_id)',
 'cp7_plan_native.apply_own_drafts':'SELECT(cutting_group_id,txid)'}
TABLE_GRANTS={'cp7_capture':{**{name:'SELECT'for name in MATERIAL_TABLES},**FABRIC_PHYSICAL_COLUMNS},'cp7_plan_writer':{'erp.cutting_group_rolls':'SELECT'},transaction_source.ROLE:{'erp.'+name:'SELECT'for name in transaction_source.TABLES}}
def extension():return '\n'.join((ROOT/'scripts/cp7-src'/p).read_text()for p in FILES)
def bundle():return predecessor.bundle()+'\n'+extension()
def verify(cur):
 predecessor.verify(cur)
 from cp7_fabric_verify import verify as verify_fabric
 verify_fabric(cur)
 from cp7_plan_bundle import verify as verify_plan
 verify_plan(cur)
 expected={'material_source':'s','material_needs':'i','source_within':'s','source':'s','fingerprint':'i','finance_mode':'i','source_for':'s','fact':'i','build_operational':'i','finance_apply':'i','finance_overlay':'i','build':'i','financial_source':'s','financial_fingerprint':'i','serve':'v','capture':'v','archives':'v','report_fact':'i','report_render':'i','report_document':'v','report_command':'v','report_index':'v','report_compare':'v'}
 rows=cur.execute("select p.oid::regprocedure::text,p.proname,pg_get_userbyid(p.proowner),p.prosecdef,p.proconfig,p.provolatile from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='cp7_analysis_native'").fetchall()
 assert len(rows)==len(expected)+1,rows # source() and source(jsonb)
 for sig,name,owner,definer,config,volatility in rows:
  assert (owner,definer)==(('cp7_finance_read',True)if name=='financial_source'else('cp7_finance_read',False)if name=='financial_fingerprint'else('cp7_capture',False))and expected.get(name)==volatility and 'search_path=\"\"'in(config or[])and'TimeZone=UTC'in(config or[]),(sig,owner,definer,config,volatility)
  for who in('anon','authenticated','service_role'):assert not cur.execute('select has_function_privilege(%s,%s,\'EXECUTE\')',(who,sig)).fetchone()[0]
 for sig in('public.erp_cp7_capture_analysis_v1(jsonb,uuid)','public.erp_cp7_capture_operational_analysis_v1(jsonb,uuid)','public.erp_cp7_read_analysis_v1(uuid)','public.erp_cp7_list_analysis_archives_v1(jsonb)','public.erp_cp7_publish_report_v1(jsonb,uuid)','public.erp_cp7_get_report_request_v1(jsonb,uuid)','public.erp_cp7_read_report_v1(uuid)','public.erp_cp7_list_reports_v1(jsonb)','public.erp_cp7_compare_reports_v1(uuid,uuid)'):
  assert cur.execute('select pg_get_userbyid(proowner),prosecdef,proconfig from pg_proc where oid=%s::regprocedure',(sig,)).fetchone()==('cp7_capture',True,['search_path=\"\"'])
  assert cur.execute('select has_function_privilege(\'authenticated\',%s,\'EXECUTE\')',(sig,)).fetchone()[0]
  for who in('anon','service_role'):assert not cur.execute('select has_function_privilege(%s,%s,\'EXECUTE\')',(who,sig)).fetchone()[0]
 for who in('anon','authenticated','service_role'):
  assert not cur.execute("select has_schema_privilege(%s,'cp7_analysis_native','USAGE')or has_table_privilege(%s,'cp7_analysis_native.runs','SELECT,INSERT,UPDATE,DELETE')",(who,who)).fetchone()[0]
 assert cur.execute("select relrowsecurity from pg_class where oid='cp7_analysis_native.runs'::regclass").fetchone()[0]
 assert cur.execute("select count(*)from pg_policy where polrelid='cp7_analysis_native.runs'::regclass and pg_get_expr(polqual,polrelid)='false'and pg_get_expr(polwithcheck,polrelid)='false'").fetchone()[0]==1
 for table in MATERIAL_TABLES:
  assert cur.execute("select has_table_privilege('cp7_capture',%s,'SELECT')and not has_table_privilege('cp7_capture',%s,'INSERT,UPDATE,DELETE,TRUNCATE,TRIGGER')",(table,table)).fetchone()[0]
 for table in('publications','report_requests'):
  sig='cp7_analysis_native.'+table
  assert cur.execute('select pg_get_userbyid(relowner),relrowsecurity from pg_class where oid=%s::regclass',(sig,)).fetchone()==('cp7_capture',True)
  assert cur.execute("select count(*)from pg_policy where polrelid=%s::regclass and pg_get_expr(polqual,polrelid)='false'and pg_get_expr(polwithcheck,polrelid)='false'",(sig,)).fetchone()[0]==1
  assert cur.execute("select count(*)from pg_trigger where tgrelid=%s::regclass and tgfoid='cp7_private.immutable_run()'::regprocedure and not tgisinternal",(sig,)).fetchone()[0]==1
  for who in('anon','authenticated','service_role'):assert not cur.execute("select has_table_privilege(%s,%s,'SELECT,INSERT,UPDATE,DELETE')",(who,sig)).fetchone()[0]
 from cp7_analysis_jobs_bundle import verify as verify_jobs
 verify_jobs(cur)
 from cp7_analysis_stages_bundle import verify as verify_stages
 verify_stages(cur)
 return dict(stage='NATIVE_FROZEN_ANALYSIS_V2_COMPILER_OPERATIONAL_PARTIAL',source_sha256=hashlib.sha256(bundle().encode()).hexdigest(),full_family_acceptance=False)
