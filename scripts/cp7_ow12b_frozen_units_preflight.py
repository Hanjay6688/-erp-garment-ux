"""Static admission for the private prepared adapter; no Native qualification."""
import ast
import json
import re
from pathlib import Path
from pglast import parse_sql
import cp7_frozen_analysis_units_v2 as stage
import cp7_ow12b_frozen_units_cases as cases

stage.verify_sources();stage.capsule.verify_sources()
originals=stage.render.originals();replacements=stage.render.replacements()
assert len(originals)==len(replacements)==len(stage.FUNCTIONS)==8
assert len(cases.IDS['native'])==cases.EXPECTED==cases.DECLARED==4
assert cases.REQUIRED==dict(native=4)
count=0
for group in(originals,replacements,stage.private_definitions()):
 for sig,sql in group.items():
  node=parse_sql(sql)[0].stmt;types=[]
  for p in node.parameters or():
   names=[x.sval for x in p.argType.names]
   types.append('boolean'if names==['pg_catalog','bool']else'.'.join(names))
  assert '.'.join(x.sval for x in node.funcname)+'('+','.join(types)+')'==sig,sig
  count+=1
# The outer unit boundary only swaps the local-reference loader. Every
# PAGE early return, allocation/quantity expression and failure path remains.
assert stage._body(stage.render.run_hook()).replace('c:=cp7_frozen_analysis_units_v2.unit_reference(j,u);',"c:=j.reference||'{}'::jsonb;")==stage._body(stage.render.original_run())
request=stage.render.request_candidate()
old=stage.render.block(stage.render.BOUNDED.read_text(),'cp7_bounded_analysis_stage.request')
back=request.replace('cp7_frozen_analysis_units_v2.request(','cp7_bounded_analysis_stage.request(',1)
back=back.replace('cp7.bounded-analysis-request.v2','cp7.bounded-analysis-request.v1')
back=back.replace('cp7_frozen_analysis_units_v2.source(q,true)','cp7_bounded_analysis_stage.source(q,true)',1)
assert back==old
# No new call to the compiler in the request or any live-source read in cache.
cache=(stage.ROOT/'cache.sql').read_text()
assert cache.count('cp7_frozen_analysis_v2.prepare(')==1
assert 'cp7_history_bounded.compile('not in request and '.source('not in cache
assert 'update cp7_analysis_stage.jobs'not in cache and 'on conflict'not in cache.lower()
assert not re.search(r'create\s+(?:or replace\s+)?(?:table|function public\.)','\n'.join(p.read_text()for p in stage.ROOT.glob('*.sql')),re.I)
for p in (*stage.ROOT.glob('*.py'),Path(cases.__file__)):ast.parse(p.read_text())
report=dict(status='PASS',exact_SQL_signatures_checked=count,private_functions=8,existing_replacements=8,
 source_pins=len(stage.sources()),Native4_provider_prepared=True,Native4_F05_route_wired=False,
 actual_outer_unit_math_unchanged=True,actual_request_access_lock_replay_and_scope_guards_unchanged=True,
 no_live_source_in_unit_cache=True,jobs_reference_never_updated=True,
 actual_Native=False,actual_Auth_HTTP_credit=False,default_request_adopted=False,production_go=False)
print(json.dumps(report))
