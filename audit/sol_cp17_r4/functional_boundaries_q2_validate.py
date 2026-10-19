"""Static and pure metadata qualification; no Native product case runs here."""
import ast
from copy import deepcopy
from decimal import Decimal, ROUND_HALF_UP
import hashlib
import json
from pathlib import Path
import subprocess
import yaml

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[1]

def blocks(path):
    text=path.read_text(); lines=text.splitlines(keepends=True)
    case=next(n for n in ast.parse(text).body if isinstance(n,ast.FunctionDef) and n.name=='cases')
    return {n.name:''.join(lines[n.lineno-1:n.end_lineno]) for n in case.body if isinstance(n,ast.FunctionDef)}

def main():
    m=json.loads((ROOT/'FUNCTIONAL_BOUNDARIES_Q2_PREEXECUTION_MANIFEST.json').read_text())
    old=json.loads((ROOT/'FUNCTIONAL_BOUNDARIES_PREEXECUTION_MANIFEST.json').read_text())
    ids=[r['id'] for r in m['cases']]
    assert len(ids)==len(set(ids))==3
    assert set(ids).isdisjoint(m['excluded_pass_case_ids']) and len(m['excluded_pass_case_ids'])==5
    for p,h in m['audit_tools'].items():
        assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h
        if p.endswith('.py'): ast.parse((ROOT/p).read_text())
        if p.endswith('.mjs'): subprocess.run(['node','--check',str(ROOT/p)],check=True,capture_output=True)
    for p,h in m['pinned_product_sources'].items(): assert hashlib.sha256((REPO/p).read_bytes()).hexdigest()==h
    for p,h in m['original_tool_hashes'].items(): assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h
    prior={row['id']:row for row in old['cases']}
    assert m['cases'][1]==prior[ids[1]] and m['cases'][2]==prior[ids[2]]
    numeric=blocks(ROOT/'numeric_boundary_q2_cases.py')
    assert set(numeric)=={'procurement_prices','client_helpers'}
    original=blocks(ROOT/'numeric_boundary_cases.py')
    assert numeric['client_helpers']==original['client_helpers'].replace("ROOT / 'numeric_boundary_client.mjs'", "ROOT / 'numeric_boundary_client_q2.mjs'").replace("        o['stderr'] = result.stderr", "        o['stderr'] = result.stderr\n        o['stdout'] = result.stdout")
    before=(ROOT/'numeric_boundary_client.mjs').read_text()
    after=(ROOT/'numeric_boundary_client_q2.mjs').read_text()
    expected=before.replace("import {createRequire} from 'node:module'", "import {stripTypeScriptTypes} from 'node:module'").replace("const root=resolve(process.argv[2]),require=createRequire(resolve(root,'package.json')),ts=require('typescript')", "const root=resolve(process.argv[2])").replace('const output=ts.transpileModule(source+extra,{compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.ES2022}}).outputText', "const output=stripTypeScriptTypes(source+extra,{mode:'strip',sourceUrl:path})").replace('transpile in-memory','erase TypeScript types in-memory with node:module.stripTypeScriptTypes').replace("status:'PASS',controls,sources", "status:'PASS',controls,sources,type_eraser:{api:'node:module.stripTypeScriptTypes',mode:'strip',node_version:process.version}")
    assert after==expected, 'ONLY_ERASER_AND_ITS_METADATA_CHANGED'
    cache=blocks(ROOT/'cache_detector_q2_cases.py'); oldcache=blocks(ROOT/'cache_detector_cases.py')
    assert set(cache)=={'check','daily'} and cache['check']==oldcache['check']
    # Parse-only the exact actual source derivatives. Do not import/evaluate helpers.
    erasure = """import {stripTypeScriptTypes} from 'node:module';import{readFileSync}from'node:fs';import{execFileSync}from'node:child_process';for(const p of process.argv.slice(1)){const s=readFileSync(p,'utf8')+(p.endsWith('hppPoolContract.ts')?'\\nexport {money as solMoney,unit as solUnit,count as solCount}\\n':'');const d=stripTypeScriptTypes(s,{mode:'strip',sourceUrl:p});execFileSync(process.execPath,['--check','--input-type=module'],{input:d,stdio:['pipe','pipe','pipe']})}console.log(JSON.stringify({node:process.version,source_derivatives_syntax_only:true,helpers_executed:false}))"""
    syntax=json.loads(subprocess.check_output(['node','--input-type=module','-e',erasure,*[str(REPO/p) for p in ('src/procurementContract.ts','src/laundryBd.ts','src/hppPoolContract.ts')]],text=True))
    for value in ('999999999999.999998','999999999999.999999'):
        assert Decimal(value).quantize(Decimal('.01'),rounding=ROUND_HALF_UP)==Decimal('1000000000000.00')
        assert Decimal(value)!=Decimal('1000000000000.00')
    tree=ast.parse((ROOT/'functional_boundaries_q2_qualification.py').read_text())
    assign=next(n for n in ast.walk(tree) if isinstance(n,ast.Assign) and isinstance(n.value,ast.IfExp) and isinstance(n.targets[0],ast.Subscript) and isinstance(n.targets[0].slice,ast.Constant) and n.targets[0].slice.value=='status')
    gate=compile(ast.Expression(assign.value.test),'<actual finite Q2 gate>','eval')
    n=dict(status='PASS',complete_boundary_restored=True,missing=[])
    report=dict(cp6_restored=True,observed_case_ids=ids,expected_case_ids=ids,counts={'PASS':3})
    assert eval(gate,{'report':report,'n':n}) is True
    changes=[('report','error','x'),('report','cp6_restored',False),('report','observed_case_ids',ids[:-1]),('report','counts',{'PASS':2,'INCOMPLETE':1}),('n','status','INCOMPLETE'),('n','complete_boundary_restored',False),('n','missing',[ids[0]]),('n','error','x')]
    for target,key,value in changes:
        context={'report':deepcopy(report),'n':deepcopy(n)};context[target][key]=value
        assert eval(gate,context) is False
    before=yaml.safe_load((REPO/'.github/workflows/audit-sol-r4-functional-boundaries.yml').read_text());after=yaml.safe_load((REPO/'.github/workflows/audit-sol-r4-functional-boundaries-q2.yml').read_text());expected=deepcopy(before)
    for k in ('name','run-name'):expected[k]=after[k]
    expected['on']['push']['paths']=after['on']['push']['paths'];expected['concurrency']['group']=after['concurrency']['group'];expected['jobs']['phase']['name']=after['jobs']['phase']['name']
    for i,s in enumerate(expected['jobs']['phase']['steps']):
        if s.get('run')=="python '../sol/audit/sol_cp17_r4/functional_boundaries_qualification.py'":s['run']="python '../sol/audit/sol_cp17_r4/functional_boundaries_q2_qualification.py'";s['name']=after['jobs']['phase']['steps'][i]['name']
        if s.get('uses','').startswith('actions/upload-artifact@'):s['with']['name']=after['jobs']['phase']['steps'][i]['with']['name']
    assert expected==after and after['permissions']=={'contents':'read','actions':'read'}
    assert not subprocess.check_output(['git','diff','--name-only',m['candidate_sha'],'--','src','supabase','scripts','package.json','package-lock.json','index.html','vite.config.ts'],cwd=REPO,text=True)
    out=dict(state='STATIC_AND_PURE_METADATA_ONLY_NO_PRODUCT_CASES_RUN',three_stable_ids_only=True,five_original_PASS_excluded=True,all_hashes_verified=True,actual_pass_gate_positive=1,actual_pass_gate_negative=len(changes),client27_controls_and_literals_unchanged=True,cache_check_body_and_two_named_deltas_unchanged=True,raw_ap_and_GL_cent_dimensions_separate=True,source_derivative_syntax=syntax,parsed_workflow_changes_only_names_entrypoint_artifact=True,permissions_setup_budget_unchanged=True,product_diff_empty=True)
    (ROOT/'FUNCTIONAL_BOUNDARIES_Q2_PREEXECUTION_VALIDATION.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))

if __name__=='__main__':main()
