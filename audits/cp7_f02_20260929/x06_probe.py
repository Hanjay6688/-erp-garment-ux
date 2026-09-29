"""Supplemental independent reproduction of a disclosed private-kernel integration gap."""
from pathlib import Path
from copy import deepcopy
import os,json,hashlib,traceback
import psycopg
ROOT=Path(__file__).resolve().parents[2]
EXPECTED={
 'bootstrap.sql':'f13d218d6ef6c38bea1968081368cdf253538c79d36b67a51e61d126927c2769',
 'graph.sql':'3a6d3af1fdf5f1d0c262639652ec491a447e4abba5315463253f733f0623b9d9',
 'matching.sql':'6eba1327d2d94d197f665aa3336a6637cb34f3224ba18cccf36bd8a4d42b804f',
 'yield.sql':'56ebb415524603e86f34492b7eb186b95a58e9b4984c45d6809ede198c84d59c'}
def refs(key,revision='1'):return [dict(kind='AUDITOR_X06_FACT',id=key,revision=revision)]
def main():
 report=dict(status='INCOMPLETE',case='AUD_F02_X06_MATCH_BINDING_REPRO',origin='USER_SUPPLIED_PEER_FINDING_INDEPENDENTLY_REPRODUCED',candidate='17e85404c9c5f088875099d7875be6342ca6b266',production_go=False,scope='PRIVATE_POSTGRESQL_KERNEL_ONLY',product_source_changed=False)
 try:
  with psycopg.connect(os.environ['PGURL']) as conn,conn.cursor() as c:
   report['postgres_version']=c.execute('select version()').fetchone()[0]
   c.execute('create role cp7_capture nologin;create role anon nologin;create role authenticated nologin;create role service_role nologin',prepare=False)
   for name,expected in EXPECTED.items():
    raw=(ROOT/'scripts/cp7-src/wip'/name).read_bytes();assert hashlib.sha256(raw).hexdigest()==expected,name
    c.execute(raw.decode(),prepare=False)
   report['source_sha256']=EXPECTED
   def call(name,*args):
    sql={'graph':'select cp7_wip.reconcile(%s::jsonb)','yield':'select cp7_wip.project_yield(%s::jsonb,%s::jsonb)','match':'select cp7_wip.match_target(%s::jsonb,%s::jsonb)','allocate':'select cp7_wip.check_allocations(%s::jsonb,%s::jsonb)'}[name]
    return c.execute(sql,tuple(json.dumps(a) for a in args)).fetchone()[0]
   g=dict(contract_version='cp7.wip-graph.v1',snapshot_id='independent-x06-17',complete=True,
     pools=[dict(key='original',size_id='XS',input_pcs='17',origin='CUTTING',ownership='COMPANY',refs=refs('input'))],
     nodes=[dict(key='source',pool_key='original',stage='SEWING_ACTIVE',refs=refs('source'))],
     events=[dict(key='initial',pool_key='original',from_node=None,to_node='source',qty_pcs='17',ordinal='1',reverses_key=None,refs=refs('initial'))])
   positions=call('graph',g);assert positions['status']=='COMPLETE'
   positions=call('yield',positions,[dict(position_key='source',eligible_input_pcs='17',numerator='2',denominator='3',basis='ASSUMED',assumption_id='aud-x06-yield',refs=refs('yield'))])
   assert positions['positions'][0]['projection']['projected_good_pcs']=='11'
   source=dict(key='source',quality='COMPLETE',size_id='XS',confirmed_target=None,constraints=[dict(field='color',value='RED',required=True,basis='FACT')],refs=refs('source-facts'))
   target=dict(key='target',size_id='XS',constraints=[dict(field='color',value='RED',required=True,basis='FACT')],refs=refs('target-facts'))
   def allocation(label):return dict(scenario_id='one',scope_id='complete',complete_scope=True,edges=[dict(key='source-to-target',position_key='source',target_key='target',size_id='XS',input_pcs='17',projected_good_pcs='11',match=label,refs=refs('edge'))])
   good=call('match',source,target);assert good['match']=='CANDIDATE_MATCH',good
   valid=call('allocate',positions,allocation(good['match']));assert valid['status']=='FEASIBLE',valid
   changed=deepcopy(target);changed['constraints'][0]['value']='BLUE';changed['refs']=refs('target-facts','2')
   mismatch=call('match',source,changed);assert mismatch==dict(match='INCOMPATIBLE',reasons=['COLOR_MISMATCH']),mismatch
   c.execute('savepoint expected_rejection')
   rejected=None
   try:call('allocate',positions,allocation(mismatch['match']))
   except psycopg.Error as exc:rejected=str(exc).splitlines()[0]
   finally:c.execute('rollback to savepoint expected_rejection');c.execute('release savepoint expected_rejection')
   assert rejected=='CP7_WIP_INELIGIBLE_ALLOCATION',rejected
   forged=call('allocate',positions,allocation('CANDIDATE_MATCH'))
   missing=deepcopy(source);missing['constraints'][0].update(value=None,basis='UNKNOWN')
   missing_match=call('match',missing,changed);assert missing_match['match']=='NEEDS_CHECK',missing_match
   forged_confirmed=call('allocate',positions,allocation('CONFIRMED_TARGET'))
   report.update(status='COUNTEREXAMPLE' if forged['status']=='FEASIBLE' or forged_confirmed['status']=='FEASIBLE' else 'PASS',
     input=17,yield_ratio='2/3',projected_good=11,valid_control=dict(match=good,allocation=valid['status']),
     original_source=source,original_target=target,changed_target=changed,
     incompatible_match=mismatch,honest_label_refused=rejected,forged_candidate_allocation=forged,
     missing_required_match=missing_match,forged_confirmed_allocation=forged_confirmed,
     limitation='No operational caller is exercised. This proves absent matcher-to-allocator binding inside the private kernel API, not a live stock/auth bypass.')
   conn.rollback()
   assert c.execute("select count(*) from pg_namespace where nspname='cp7_wip'").fetchone()[0]==0
   assert c.execute("select count(*) from pg_roles where rolname in ('cp7_capture','anon','authenticated','service_role')").fetchone()[0]==0
   report['transaction_cleanup_restored']=True;conn.rollback()
 except Exception as exc:report.update(status='INCOMPLETE',error=str(exc),traceback=traceback.format_exc())
 out=ROOT/'cp6-proof/t3/CP7_F02_X06_REPRO.json';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps(report),flush=True)
 raise SystemExit(0 if report['status']=='PASS' else 1)
if __name__=='__main__':main()
