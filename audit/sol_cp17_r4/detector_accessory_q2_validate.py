"""Pure/static source-diff checks; no database or product case execution."""
import ast
from copy import deepcopy
import gzip,hashlib,json,subprocess
from pathlib import Path
import yaml
ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[1]

def main():
 m=json.loads((ROOT/'ACCESSORY_DETECTOR_Q2_PREEXECUTION_MANIFEST.json').read_text());old=json.loads((ROOT/'MUTABLE_DETECTOR_PREEXECUTION_MANIFEST.json').read_text())
 assert m['cases']==[old['cases'][3]] and len(m['excluded_PASS_ids'])==3
 for p,h in m['audit_tools'].items():assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h;ast.parse((ROOT/p).read_text())
 for p,h in m['pinned_product_sources'].items():assert hashlib.sha256((REPO/p).read_bytes()).hexdigest()==h
 original=(ROOT/'detector_mutable_controls.py').read_text();assert hashlib.sha256(original.encode()).hexdigest()==m['original_tool_sha256']
 tree=ast.parse(original);case=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='cases');fn=next(n for n in case.body if isinstance(n,ast.FunctionDef) and n.name=='accessory');lines=original.splitlines(keepends=True);body=''.join(lines[fn.lineno-1:fn.end_lineno])
 expected=original[:original.index('def cases(cur,today):')]+'def cases(cur,today):\n'+body.replace("'SOLR4-DETECTOR-MASTER'","'SR4DC'")+"\n    return [record('SOL_R4_D01_NEW_ACCESSORY_NULL_CATEGORY',accessory)]\n"
 assert expected==(ROOT/'detector_accessory_q2_control.py').read_text()
 assert len(('Z-AUD-'+'SOLR4-DETECTOR-MASTER'+'-'+'0'*36).encode())==64>60
 assert len(('Z-AUD-'+'SR4DC'+'-'+'0'*36).encode())==48<=60
 bootstrap=gzip.decompress((REPO/'supabase/tests/fixtures/erp_enteng_cp45a_catalog_bootstrap.sql.gz').read_bytes()).decode()
 assert '"material_sku" character varying(60) not null' in bootstrap
 helper=(REPO/'scripts/cp6_z_expanded_integrity_audit.py').read_text();assert 'material_id = uuid.uuid4()'in helper and "f'Z-AUD-{label}-{material_id}'"in helper
 qt=ast.parse((ROOT/'detector_accessory_q2_qualification.py').read_text());assign=next(n for n in ast.walk(qt)if isinstance(n,ast.Assign)and isinstance(n.value,ast.IfExp)and isinstance(n.targets[0],ast.Subscript)and isinstance(n.targets[0].slice,ast.Constant)and n.targets[0].slice.value=='status');gate=compile(ast.Expression(assign.value.test),'<actual accessory Q2 gate>','eval')
 ids=[m['cases'][0]['id']];report=dict(cp6_restored=True,observed_case_ids=ids,expected_case_ids=ids,counts={'PASS':1});n=dict(status='PASS',complete_boundary_restored=True,missing=[])
 assert eval(gate,{'report':report,'n':n})is True
 mutations=[('report','error','x'),('report','cp6_restored',False),('report','observed_case_ids',[]),('report','counts',{'INCOMPLETE':1}),('n','status','INCOMPLETE'),('n','complete_boundary_restored',False),('n','missing',ids),('n','error','x')]
 for target,key,value in mutations:
  context={'report':deepcopy(report),'n':deepcopy(n)};context[target][key]=value;assert eval(gate,context)is False
 before=yaml.safe_load((REPO/'.github/workflows/audit-sol-r4-mutable-detectors.yml').read_text());after=yaml.safe_load((REPO/'.github/workflows/audit-sol-r4-accessory-detector-q2.yml').read_text());want=deepcopy(before)
 for k in('name','run-name'):want[k]=after[k]
 want['on']['push']['paths']=after['on']['push']['paths'];want['concurrency']['group']=after['concurrency']['group'];want['jobs']['phase']['name']=after['jobs']['phase']['name']
 for i,step in enumerate(want['jobs']['phase']['steps']):
  if step.get('run')=="python '../sol/audit/sol_cp17_r4/detector_mutable_qualification.py'":step['run']="python '../sol/audit/sol_cp17_r4/detector_accessory_q2_qualification.py'";step['name']=after['jobs']['phase']['steps'][i]['name']
  if step.get('uses','').startswith('actions/upload-artifact@'):step['with']['name']=after['jobs']['phase']['steps'][i]['with']['name']
 assert want==after and after['permissions']=={'contents':'read','actions':'read'}
 assert not subprocess.check_output(['git','diff','--name-only',m['candidate_sha'],'--','src','supabase','scripts','package.json','package-lock.json','index.html','vite.config.ts'],cwd=REPO,text=True)
 result=dict(state='STATIC_AND_PURE_METADATA_ONLY_NO_PRODUCT_CASES_RUN',exact_same_accessory_ID_only=True,three_PASS_excluded=True,exact_tool_diff_prefix_only_plus_case_subset=True,original_SKU_bytes64_exceeds60=True,qualified_SKU_bytes48_fits60=True,Native_UUID_generation_unchanged=True,all_business_fields_predicates_expected_unchanged=True,actual_outer_gate_positive=1,actual_outer_gate_negative=len(mutations),all167_phase_gate_unchanged=True,parsed_workflow_diff_only_names_entrypoint_artifact=True,source_hashes_verified=True,product_diff_empty=True)
 (ROOT/'ACCESSORY_DETECTOR_Q2_PREEXECUTION_VALIDATION.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))

if __name__=='__main__':main()
