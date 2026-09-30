"""F04 kernels and authoritative planner adapters on the explicit F03 stack.

The kernels are the byte-verified F04 contribution. Source adapters are owned
by the integrator and build every private input from current native facts.
No consumer-supplied completeness, matching, allocation or cost is trusted.
"""
from pathlib import Path
import hashlib
import cp7_f03_bundle as predecessor

ROOT=Path(__file__).resolve().parents[1]
KERNEL_FILES=(
 'demand/bootstrap.sql','demand/history.sql','demand/estimate.sql',
 'baseline/target.sql','baseline/timeline.sql','baseline/feasibility.sql',
 'baseline/allocation.sql','baseline/capacity.sql','baseline/dependencies.sql',
 'models/kernels.sql','models/evaluation.sql','models/comparison.sql',
 'models/ownership.sql',
)
ADAPTER_FILES=('planning/bootstrap.sql','planning/history-source.sql','planning/history.sql','planning/ownership.sql')
ROLES=predecessor.ROLES
GRANTS=predecessor.GRANTS

def extension():
 return '\n'.join((ROOT/'scripts/cp7-src'/name).read_text()for name in KERNEL_FILES+ADAPTER_FILES)

def bundle():return predecessor.bundle()+'\n'+extension()

def source_hashes():
 return {name:hashlib.sha256((ROOT/'scripts/cp7-src'/name).read_bytes()).hexdigest()for name in KERNEL_FILES+ADAPTER_FILES}

def verify(cur):
 for name in KERNEL_FILES+ADAPTER_FILES:
  assert (ROOT/'scripts/cp7-src'/name).is_file(),name
 # Adapters and kernels remain private invoker routines. The only public
 # wrappers are source-bound to the no-login native read principal.
 assert cur.execute("select count(*)from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname in('cp7_demand','cp7_baseline','cp7_models')and(pg_get_userbyid(p.proowner)<>'cp7_capture'or p.prosecdef or p.provolatile<>'i' or has_function_privilege('authenticated',p.oid,'EXECUTE')or has_function_privilege('anon',p.oid,'EXECUTE')or has_function_privilege('service_role',p.oid,'EXECUTE'))").fetchone()[0]==0
 assert cur.execute("select count(*)from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname in('cp7_demand','cp7_baseline','cp7_models')").fetchone()[0]==22
 rows=cur.execute("select p.oid::regprocedure::text,pg_get_userbyid(p.proowner),p.prosecdef,p.proconfig from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='cp7_planning'order by p.proname").fetchall()
 assert len(rows)==8,rows
 for sig,owner,definer,config in rows:
  assert owner=='cp7_capture'and not definer and 'search_path=\"\"'in(config or[]),(sig,owner,definer,config)
  assert any(x.startswith('TimeZone=')for x in config),(sig,config)
  for who in('anon','authenticated','service_role'):
   assert not cur.execute('select has_function_privilege(%s,%s,\'EXECUTE\')',(who,sig)).fetchone()[0],(sig,who)
 for sig in('public.erp_cp7_capture_demand_history_v1(jsonb,uuid)','public.erp_cp7_read_demand_history_v1(uuid)'):
  owner,definer,config=cur.execute('select pg_get_userbyid(proowner),prosecdef,proconfig from pg_proc where oid=%s::regprocedure',(sig,)).fetchone()
  assert owner=='cp7_capture'and definer and 'search_path=\"\"'in(config or[]),(sig,owner,config)
  assert cur.execute('select has_function_privilege(\'authenticated\',%s,\'EXECUTE\')',(sig,)).fetchone()[0]
  for who in('anon','service_role'):
   assert not cur.execute('select has_function_privilege(%s,%s,\'EXECUTE\')',(who,sig)).fetchone()[0]
 for schema in('cp7_planning','cp7_demand','cp7_baseline','cp7_models'):
  for who in('anon','authenticated','service_role'):
   assert not cur.execute('select has_schema_privilege(%s,%s,\'USAGE\')',(who,schema)).fetchone()[0]
 assert cur.execute("select relrowsecurity from pg_class where oid='cp7_planning.history_runs'::regclass").fetchone()[0]
 assert cur.execute("select count(*)from pg_policy where polrelid='cp7_planning.history_runs'::regclass and pg_get_expr(polqual,polrelid)='false'and pg_get_expr(polwithcheck,polrelid)='false'").fetchone()[0]==1
 return dict(stage='F04_NATIVE_SOURCE_ADAPTERS',source_sha256=hashlib.sha256(bundle().encode()).hexdigest(),source_files_sha256=source_hashes(),private_kernels=22,private_adapters=8,full_family_acceptance=False)
