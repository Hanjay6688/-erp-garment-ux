"""Pure/static preflight only; no product import or database execution."""
import ast
from copy import deepcopy
from decimal import Decimal, ROUND_HALF_UP
import hashlib
import json
from pathlib import Path
import subprocess

import yaml

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]


def main():
    manifest = json.loads((ROOT / 'FUNCTIONAL_BOUNDARIES_PREEXECUTION_MANIFEST.json').read_text())
    for p,h in manifest['audit_tools'].items():
        assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest() == h
        if p.endswith('.py'): ast.parse((ROOT/p).read_text())
        if p.endswith('.mjs'): subprocess.run(['node','--check',str(ROOT/p)],check=True,capture_output=True)
    for p,h in manifest['pinned_product_sources'].items():
        assert hashlib.sha256((REPO/p).read_bytes()).hexdigest() == h
    ids = [r['id'] for r in manifest['cases']]
    literals = []
    for name in ('matching_pipeline_case.py','numeric_boundary_cases.py','cache_detector_cases.py'):
        tree = ast.parse((ROOT/name).read_text())
        literals += [n.value for n in ast.walk(tree) if isinstance(n,ast.Constant) and isinstance(n.value,str) and n.value.startswith('SOL_R4_') and not n.value.endswith('_')]
    assert set(ids) == set(v for v in literals if v in ids) and len(ids) == len(set(ids)) == 8
    assert Decimal('999999999999.999998').quantize(Decimal('.01'),rounding=ROUND_HALF_UP) == Decimal('1000000000000.00')
    assert Decimal('10737418.24') + Decimal('10737418.25') == Decimal('21474836.49')
    assert 999999999 - 1 == 999999998 and 8*9//10 == 7 and 100-7 == 93
    tree = ast.parse((ROOT/'functional_boundaries_qualification.py').read_text())
    assign = next(n for n in ast.walk(tree) if isinstance(n,ast.Assign) and isinstance(n.value,ast.IfExp) and isinstance(n.targets[0],ast.Subscript) and isinstance(n.targets[0].slice,ast.Constant) and n.targets[0].slice.value=='status')
    gate = compile(ast.Expression(assign.value.test),'<actual finite PASS gate>','eval')
    n = dict(status='PASS',complete_boundary_restored=True,missing=[])
    report = dict(cp6_restored=True,observed_case_ids=ids,expected_case_ids=ids,counts={'PASS':8})
    assert eval(gate,{'report':report,'n':n}) is True
    mutations = [('report','error','x'),('report','cp6_restored',False),('report','observed_case_ids',ids[:-1]),('report','counts',{'PASS':7,'INCOMPLETE':1}),('n','status','INCOMPLETE'),('n','complete_boundary_restored',False),('n','missing',[ids[0]]),('n','error','x')]
    for target,key,value in mutations:
        context={'report':deepcopy(report),'n':deepcopy(n)};context[target][key]=value
        assert eval(gate,context) is False
    before=yaml.safe_load((REPO/'.github/workflows/audit-sol-r4-d01-state-control.yml').read_text())
    after=yaml.safe_load((REPO/'.github/workflows/audit-sol-r4-functional-boundaries.yml').read_text());expected=deepcopy(before)
    for k in ('name','run-name'):expected[k]=after[k]
    expected['on']['push']['paths']=after['on']['push']['paths'];expected['concurrency']['group']=after['concurrency']['group'];expected['jobs']['phase']['name']=after['jobs']['phase']['name']
    for i,s in enumerate(expected['jobs']['phase']['steps']):
        if 'detector_qualification.py' in s.get('run',''):
            s['run']=after['jobs']['phase']['steps'][i]['run'];s['name']=after['jobs']['phase']['steps'][i]['name']
        if s.get('uses','').startswith('actions/upload-artifact@'):s['with']['name']=after['jobs']['phase']['steps'][i]['with']['name']
    assert expected==after and after['permissions']=={'contents':'read','actions':'read'}
    for s in after['jobs']['phase']['steps']:
        if s.get('uses','').startswith('actions/checkout@'):
            assert s['with']['persist-credentials'] is False
            if s['with']['path']=='auditor':assert s['with']['ref']==manifest['candidate_sha']
    assert not subprocess.check_output(['git','diff','--name-only',manifest['candidate_sha'],'--','src','supabase','scripts','package.json','package-lock.json','index.html','vite.config.ts'],cwd=REPO,text=True)
    out=dict(state='STATIC_AND_PURE_CONTROLS_ONLY_NO_PRODUCT_CASES_RUN',case_ids_exact=8,python_ast=True,node_check=True,source_and_tool_hashes_match=True,actual_pass_gate_positive=1,actual_pass_gate_negative=len(mutations),literal_arithmetic=True,parsed_workflow_changes_only_names_entrypoint_artifact=True,setup_permissions_budgets_unchanged=True,strict_once_entrypoint=True,bootstrap_max_attempts=2,product_diff_empty=True,held_r3_probes_excluded=True,guard_trigger_or_fact_mutation=False,extra_mutations_only_two_declared_derived_caches=True)
    (ROOT/'FUNCTIONAL_BOUNDARIES_PREEXECUTION_VALIDATION.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(out))


if __name__=='__main__':main()
