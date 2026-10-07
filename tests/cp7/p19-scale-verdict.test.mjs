// @vitest-environment node
import {test,expect} from 'vitest'
import {execFileSync} from 'node:child_process'

test('retained Native completion is valid below a possible timeout; structural caps and corrupt results remain failures',()=>{
 // Exercise the actual pure Python verdict without importing the Native-only
 // psycopg harness. The input is the exact first-failing Native Original, whose
 // INCOMPLETE receipt and failed cleanup gates are retained without rewriting.
 const result=execFileSync('python3',['-c',String.raw`
import ast,copy,gzip,json
from pathlib import Path
source=Path('scripts/cp7_p19_scale_cases.py')
tree=ast.parse(source.read_text())
nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('cap_of','verdict')
 or isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in ('CAPS','STAGED_PATH') for t in n.targets)]
ns={};exec(compile(ast.Module(body=nodes,type_ignores=[]),str(source),'exec'),ns)
envelope=json.loads(gzip.decompress(Path('docs/cp7/evidence/gpt-staged-5000-20261008/43d26996-scale5-first-failure-retained/ORIGINAL_REPORTS.json.gz').read_bytes()))
report=json.loads(envelope['root_json_utf8']['CP7_P19_SCALE.json'])
assert report['status']=='INCOMPLETE'
points=report['native']['cases']['P19S_NATIVE_ROLLED_BACK_100_GRID_CAP']['points']
point=next(p for p in points if p['path']==ns['STAGED_PATH'])
assert point['verdict']['kind']=='BEYOND_CAP_NOT_REFUSED'
assert point['expected_caps']==['STATEMENT_TIMEOUT_8S','STAGED_UNIT_STOPPED_8S']
assert all(point[k] is True for k in ('coverage_complete','frozen_contract_valid','transport_exact','original_recorded'))
assert ns['verdict'](point)==dict(kind='COMPLETE_RESULT',acceptable=True,counterexample=False)
checks=1
for cap in ('STAGED_TARGETS_5000','STAGED_HISTORY_CELLS_500000','HISTORY_GRID_100000'):
 p=copy.deepcopy(point);p['expected_caps'].append(cap)
 v=ns['verdict'](p);assert v['kind']=='BEYOND_CAP_NOT_REFUSED' and v['caps']==[cap] and not v['acceptable'];checks+=1
for flag in ('coverage_complete','frozen_contract_valid','transport_exact'):
 p=copy.deepcopy(point);p[flag]=False
 v=ns['verdict'](p);assert v['kind']=='RESULT_DEFECT' and v['failed']==[flag] and not v['acceptable'];checks+=1
p=copy.deepcopy(point);p['original_recorded']=False
assert ns['verdict'](p)['kind']=='EVIDENCE_MISSING';checks+=1
for code in ('57014','CP7_ANALYSIS_STAGE_STOPPED'):
 p=copy.deepcopy(point);p['phases'].append(dict(name='step',outcome='JOB_FAILED',code=code,sqlstate='57014'))
 assert ns['verdict'](p)['kind']=='HONEST_CAP_REFUSAL';checks+=1
 p['result_saved_after_refusal']=True
 assert ns['verdict'](p)['kind']=='REFUSAL_SAVED_A_RESULT';checks+=1
print(json.dumps(dict(checks=checks,source_commit=envelope['source_commit'],original_status_unchanged=report['status'])))
`],{encoding:'utf8',maxBuffer:1000000})
 expect(JSON.parse(result)).toEqual({checks:12,source_commit:'43d26996d767f47bb21d86e988b92c9dcf994703',original_status_unchanged:'INCOMPLETE'})
})
