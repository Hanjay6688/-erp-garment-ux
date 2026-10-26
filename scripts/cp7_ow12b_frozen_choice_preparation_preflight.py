"""Exact delta check; this does not execute Native, SAVE, Auth or the installer."""
import ast,json
from pglast import parse_sql
import cp7_frozen_choice_preparation as stage
from cp7_bounded_analysis_stage.source import once

stage.verify_sources();r=stage.render
for sig,old in r.originals().items():
 new=r.replacement(sig)
 reversed=once(new,'create or replace function ','create function ')
 reversed=once(reversed,r.SCHEMA+'.reference(j)','cp7_frozen_analysis_readers_v2.reference(j)')
 assert reversed==old
sql=r.render();parsed=parse_sql(sql)
assert sql.count('create or replace function ')==2
assert len(r.FUNCTIONS)==15 and len(r.PUBLIC)==3
reference=r.parent.block(sql,r.SCHEMA+'.reference')
assert 'cp7_frozen_analysis_v2.prepare'not in reference
assert sql.count('cp7_frozen_analysis_v2.prepare(')==1
assert sql.count('create table ')==1
assert 'create policy'not in sql and 'create extension'not in sql and 'cron.schedule'not in sql
assert 'cp7_frozen_analysis_choice_v2.apply('not in sql
assert 'cp7_bounded_analysis_stage.source_for'not in sql
assert 'FG_HPP_SALES_V2620C'not in sql # locks stay in the exact unchanged parent apply
assert r.parent.render()==(stage.ROOT.parent/'cp7_frozen_analysis_choice_v2/choice.prepared.sql').read_text()
for p in stage.ROOT.glob('*.py'):ast.parse(p.read_text())
print(json.dumps(dict(status='PASS_PREPARATION_ONLY',SQL_statements=len(parsed),exact_two_private_reference_substitutions=True,
 parent_apply_normalizer_locks_two_freshness_checks_unchanged=True,save_never_invokes_compiler=True,
 actual_Native=False,actual_Auth_HTTP_credit=False,Python_installer_qualified=False,default_adopted=False,production_go=False)))
