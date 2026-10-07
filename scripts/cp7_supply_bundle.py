"""Authoritative global production source on qualified native P05/P06 targets."""
import hashlib
import cp7_baseline_bundle as predecessor
ROOT=predecessor.ROOT
FILES=('planning/supply-source.sql',)
ROLES=predecessor.ROLES
GRANTS=predecessor.GRANTS

def extension():return '\n'.join((ROOT/'scripts/cp7-src'/p).read_text()for p in FILES)
def bundle():return predecessor.bundle()+'\n'+extension()

def verify(cur):
 predecessor.verify(cur)
 expected={'merge_facts':'i','capture_at':'s','classify':'i','exhausted_groups':'i','proof_kernel':'s','batch_reuse':'s',
  'batch_verdict':'s','wip_source_parts':'s','wip_source_at':'s','source_parts_within':'s','source_parts':'s','source_within':'s','source':'s','store_proofs':'v','prove_exhausted':'v',
  'fingerprint':'i','build':'i','serve':'v','capture':'v'}
 rows=cur.execute("select p.oid::regprocedure::text,p.proname,pg_get_userbyid(p.proowner),p.prosecdef,p.proconfig,p.provolatile from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='cp7_supply_native'").fetchall()
 assert len(rows)==len(expected),rows
 for sig,name,owner,definer,config,volatility in rows:
  assert owner=='cp7_capture'and not definer and expected.get(name)==volatility and 'search_path=\"\"'in(config or[])and'TimeZone=UTC'in(config or[]),(sig,owner,definer,config,volatility)
  for who in('anon','authenticated','service_role'):
   assert not cur.execute('select has_function_privilege(%s,%s,\'EXECUTE\')',(who,sig)).fetchone()[0]
 for sig in('public.erp_cp7_capture_production_supply_v1(jsonb,uuid)','public.erp_cp7_read_production_supply_v1(uuid)'):
  assert cur.execute('select pg_get_userbyid(proowner),prosecdef,proconfig from pg_proc where oid=%s::regprocedure',(sig,)).fetchone()==('cp7_capture',True,['search_path=\"\"'])
  assert cur.execute('select has_function_privilege(\'authenticated\',%s,\'EXECUTE\')',(sig,)).fetchone()[0]
  for who in('anon','service_role'):
   assert not cur.execute('select has_function_privilege(%s,%s,\'EXECUTE\')',(who,sig)).fetchone()[0]
 for table in('cp7_supply_native.runs','cp7_supply_native.exhaustion_proofs'):
  for who in('anon','authenticated','service_role'):
   assert not cur.execute("select has_schema_privilege(%s,'cp7_supply_native','USAGE')or has_table_privilege(%s,%s,'SELECT,INSERT,UPDATE,DELETE')",(who,who,table)).fetchone()[0]
  assert cur.execute("select relrowsecurity and pg_get_userbyid(relowner)='cp7_capture'from pg_class where oid=%s::regclass",(table,)).fetchone()[0]
  assert cur.execute("select count(*)from pg_policy where polrelid=%s::regclass and pg_get_expr(polqual,polrelid)='false'and pg_get_expr(polwithcheck,polrelid)='false'",(table,)).fetchone()[0]==1
  assert cur.execute("select count(*)from pg_trigger where tgrelid=%s::regclass and tgfoid='cp7_private.immutable_run()'::regprocedure and not tgisinternal",(table,)).fetchone()[0]==1
 return dict(stage='GLOBAL_NATIVE_WIP_SOURCE_BATCHES_ONE_CONSERVED_GRAPH',source_sha256=hashlib.sha256(bundle().encode()).hexdigest(),full_family_acceptance=False)
