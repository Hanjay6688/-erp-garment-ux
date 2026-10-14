"""Audit routing only: unchanged qualification bodies; product checkout pinned.
Runs on a separate Sol branch, never writes any candidate/product branch.
"""
import copy,datetime,hashlib,json,re,subprocess
from pathlib import Path
import yaml

ROOT=Path(__file__).resolve().parents[2]
SHA='0b7049d9203bac52b47a4c89f3e0d75646067a8f'
BRANCH='audit/sol-cp1-7-0b7049d9-20261014'
ROUND='cp1-7-20261014'
OUT=ROOT/'audit/sol_cp1_7'
registry=[]
originals={p.name:yaml.safe_load(p.read_text())for p in (ROOT/'.github/workflows').glob('*.yml')if not p.name.startswith('audit-sol-')}
by_name={d['name']:name for name,d in originals.items()}
receipt=json.loads((OUT/'WRITER_SCOPE_INPUT.json').read_text())
excluded={'CP7 Offsite Backup':'D13-9a CP7C deferred','CP7 Backup Kit Check':'D13-9a CP7C deferred','CP7 Astra Timeline Reuse':'independent Sol semantic probe will replace this author-owned oracle'}
selected=[by_name[x['workflow']]for x in receipt['runs']if x['workflow']not in excluded]
selected+=['cp6-g01-baseline.yml','cp6-t2-regression.yml','cp6-t3-release-package.yml','cp6-t3-rollback.yml','cp6-release-readiness.yml']
selected+=[f'cp6-{k}-t1-probe.yml'for k in ['aw','ax','ay','az','ba','bb','bc','bd','be']]
assert len(selected)==len(set(selected))
trees={name:subprocess.check_output(['git','rev-parse',SHA+':'+name],cwd=ROOT,text=True).strip()for name in ['src','supabase','supabase/migrations','supabase/release','supabase/dev','supabase/rollbacks','scripts','scripts/cp7-src','.github/workflows']}
guide=ROOT/'docs/AUDIT_PANDUAN_PRO_MAX.md'
assert len(guide.read_bytes())==63005 and hashlib.sha256(guide.read_bytes()).hexdigest()=='5752e96df751de5ebe4b86d3f572cffa1bbe94eb42bf8e283fa6e04f9f593639'
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()==SHA
pins={'actions/checkout@v4':'actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683','actions/setup-python@v5':'actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065','actions/setup-node@v4':'actions/setup-node@49933ea5288caeca8642d1e84afbd3f7d6820020','actions/upload-artifact@v4':'actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02'}
for original in selected:
 source=ROOT/'.github/workflows'/original
 name='audit-sol-full-'+original
 d=copy.deepcopy(originals[original]);d.pop(True,None);d.pop('on',None)
 suite=original.removesuffix('.yml')
 d['name']='AUDIT/SOL/'+suite
 d['run-name']='AUDIT/'+ROUND+'/SOL/0b7049d9/'+suite+'/${{ github.run_attempt }}'
 d['on']={'push':{'branches':[BRANCH],'paths':['.github/workflows/'+name]},'workflow_dispatch':{}}
 d['concurrency']={'group':'sol-full-'+suite+'-${{ github.run_id }}','cancel-in-progress':False}
 job_records=[]
 for key,j in d['jobs'].items():
  steps=j.get('steps',[]);checkouts=[];candidate_dir=None
  for i,s in enumerate(steps):
   if s.get('uses','').startswith('actions/checkout@'):
    w=s.setdefault('with',{});path=w.get('path','.')
    if not w.get('ref')or path=='.'and '${{'in str(w.get('ref','')):
     w['ref']=SHA;candidate_dir=path
    w['persist-credentials']=False
    checkouts.append({'path':path,'ref':w.get('ref'),'step_index':i})
   if s.get('uses')in pins:s['uses']=pins[s['uses']]
   if s.get('uses','').startswith('actions/upload-artifact@'):
    w=s.setdefault('with',{});w['name']=ROUND+'-SOL-0b7049d9-'+suite+'-'+str(w.get('name','artifact'))
  assert candidate_dir is not None,(original,key,'no product checkout')
  identity_code="set -euo pipefail\npython - <<'PY'\nimport hashlib,json,os,subprocess\nfrom pathlib import Path\nsha="+repr(SHA)+"\ntrees="+repr(trees)+"\nassert subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()==sha\nfor path,want in trees.items():assert subprocess.check_output(['git','rev-parse',sha+':'+path],text=True).strip()==want,path\nassert not subprocess.check_output(['git','diff','HEAD','--name-only'],text=True).strip()\nd={'candidate_sha':sha,'candidate_tree':subprocess.check_output(['git','rev-parse','HEAD^{tree}'],text=True).strip(),'workflow_sha':os.environ['GITHUB_SHA'],'trees':trees,'guide_sha256':hashlib.sha256(Path('docs/AUDIT_PANDUAN_PRO_MAX.md').read_bytes()).hexdigest(),'workflow_origin':"+repr(original)+",'oracle_origin':'UNCHANGED_PREEXISTING_PROVIDER','fixture_origin':'UNCHANGED_PREEXISTING_PROVIDER','evidence_origin':'INDEPENDENT_NATIVE_RERUN','production_go':False}\nPath(os.environ['RUNNER_TEMP'],'SOL_SOURCE_IDENTITY.json').write_text(json.dumps(d,indent=2)+'\\n')\nprint(json.dumps(d))\nPY\n"
  position=max(x['step_index']for x in checkouts)+1
  steps.insert(position,{'name':'SOL verify frozen candidate and product identity','working-directory':candidate_dir,'shell':'bash','run':identity_code})
  steps.append({'name':'SOL retain source identity separately','if':'always()','uses':pins['actions/upload-artifact@v4'],'with':{'name':ROUND+'-SOL-0b7049d9-'+suite+'-${{ github.job }}-${{ strategy.job-index }}-identity','path':'${{ runner.temp }}/SOL_SOURCE_IDENTITY.json','retention-days':30,'if-no-files-found':'warn'}})
  job_records.append({'job':key,'candidate_checkout':candidate_dir,'checkouts':checkouts,'matrix':j.get('strategy',{}).get('matrix'),'condition':j.get('if'),'needs':j.get('needs')})
 text=yaml.safe_dump(d,sort_keys=False,width=110);(ROOT/'.github/workflows'/name).write_text(text)
 registry.append({'suite':suite,'workflow_path':'.github/workflows/'+name,'workflow_name':d['name'],'original_path':str(source.relative_to(ROOT)),'original_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'audit_workflow_sha256':hashlib.sha256(text.encode()).hexdigest(),'jobs':job_records,'scope':'CP6_LAYER_ISOLATED_CURRENT_SOURCE'if suite.startswith('cp6-')else'FINAL_CP7_STACK_OR_FRONTEND','case_manifest':'provider declarations and hashes unchanged; runtime declares planned case IDs before execution, exact-set checks where supported; legacy metadata limits must be reported'})
manifest={'round_id':ROUND,'auditor':'SOL','candidate_sha':SHA,'candidate_tree':subprocess.check_output(['git','rev-parse',SHA+'^{tree}'],cwd=ROOT,text=True).strip(),'audit_branch':BRANCH,'frozen_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'rules_sha256':hashlib.sha256(guide.read_bytes()).hexdigest(),'rules_blob':'5df759c38e1ea98831a4dfdda3cfd1a2b8bb398b','product_trees':trees,'source_manifest':[{ 'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}for p in [ROOT/'package-lock.json',ROOT/'package.json',ROOT/'docs/cp7/OWNER_DECISIONS_20261008.md',ROOT/'docs/cp6-d11-kebijakan-dan-gbd03.md']], 'environment':{'os':'ubuntu-24.04 unless original explicitly differs','node':'22','supabase_cli':'2.116.0','postgres_image':'17.6.1.165','psycopg':'3.2.10'},'workflows':registry,'excluded_writer_workflows':excluded,'historical_workflows':'CP3/4/4.5/5 snapshot workflows are not acceptance for current composition; source immutability and T2 inherited regression must supply their own evidence','CP2':'evidence inventory required; no recovery-set/restore success assumed','own_contract_probes':'declared separately before their execution','production_go':False,'audit_complete':False}
(OUT/'ROUND_MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps({'workflows':len(registry),'workflow_paths':[x['workflow_path']for x in registry],'guide_hash':manifest['rules_sha256'],'product_trees':trees}))
