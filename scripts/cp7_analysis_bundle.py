"""Native source compiler into the byte-frozen CP7 analysis.v2 contract."""
import hashlib
import cp7_netting_bundle as predecessor
ROOT=predecessor.ROOT
FILES=('planning/analysis.sql','planning/analysis-finance.sql','planning/analysis-archive.sql')
ROLES=predecessor.ROLES
GRANTS=predecessor.GRANTS
def extension():return '\n'.join((ROOT/'scripts/cp7-src'/p).read_text()for p in FILES)
def bundle():return predecessor.bundle()+'\n'+extension()
def verify(cur):
 predecessor.verify(cur)
 expected={'source':'s','fingerprint':'i','fact':'i','build_operational':'i','build':'i','financial_source':'s','serve':'v','capture':'v','archives':'v'}
 rows=cur.execute("select p.oid::regprocedure::text,p.proname,pg_get_userbyid(p.proowner),p.prosecdef,p.proconfig,p.provolatile from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='cp7_analysis_native'").fetchall()
 assert len(rows)==len(expected)+1,rows # source() and source(jsonb)
 for sig,name,owner,definer,config,volatility in rows:
  assert (owner,definer)==(('cp7_finance_read',True)if name=='financial_source'else('cp7_capture',False))and expected.get(name)==volatility and 'search_path=\"\"'in(config or[])and'TimeZone=UTC'in(config or[]),(sig,owner,definer,config,volatility)
  for who in('anon','authenticated','service_role'):assert not cur.execute('select has_function_privilege(%s,%s,\'EXECUTE\')',(who,sig)).fetchone()[0]
 for sig in('public.erp_cp7_capture_analysis_v1(jsonb,uuid)','public.erp_cp7_read_analysis_v1(uuid)','public.erp_cp7_list_analysis_archives_v1(jsonb)'):
  assert cur.execute('select pg_get_userbyid(proowner),prosecdef,proconfig from pg_proc where oid=%s::regprocedure',(sig,)).fetchone()==('cp7_capture',True,['search_path=\"\"'])
  assert cur.execute('select has_function_privilege(\'authenticated\',%s,\'EXECUTE\')',(sig,)).fetchone()[0]
  for who in('anon','service_role'):assert not cur.execute('select has_function_privilege(%s,%s,\'EXECUTE\')',(who,sig)).fetchone()[0]
 for who in('anon','authenticated','service_role'):
  assert not cur.execute("select has_schema_privilege(%s,'cp7_analysis_native','USAGE')or has_table_privilege(%s,'cp7_analysis_native.runs','SELECT,INSERT,UPDATE,DELETE')",(who,who)).fetchone()[0]
 assert cur.execute("select relrowsecurity from pg_class where oid='cp7_analysis_native.runs'::regclass").fetchone()[0]
 assert cur.execute("select count(*)from pg_policy where polrelid='cp7_analysis_native.runs'::regclass and pg_get_expr(polqual,polrelid)='false'and pg_get_expr(polwithcheck,polrelid)='false'").fetchone()[0]==1
 return dict(stage='NATIVE_FROZEN_ANALYSIS_V2_COMPILER_OPERATIONAL_PARTIAL',source_sha256=hashlib.sha256(bundle().encode()).hexdigest(),full_family_acceptance=False)
