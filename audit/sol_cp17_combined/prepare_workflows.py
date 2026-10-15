"""Own workflows; product checkout is always the frozen candidate, not copied SQL."""
from pathlib import Path
import copy,hashlib,json,subprocess,yaml
ROOT=Path(__file__).resolve().parents[2]
C='dfab13bf62398a69a02bf6221c06d29075e5e40b'
BRANCH='audit/sol-cp1-7-combined-dfab13bf-20261016'
CHECKOUT='actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683'
UPLOAD='actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02'
PINS={'actions/checkout@v4':CHECKOUT,'actions/setup-python@v5':'actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065',
 'actions/setup-node@v4':'actions/setup-node@49933ea5288caeca8642d1e84afbd3f7d6820020','actions/upload-artifact@v4':UPLOAD}
def load(name):return yaml.safe_load((ROOT/'.github/workflows'/name).read_text())
def identity_step():
 return dict(name='Sol verifies immutable candidate and runtime source',**{'working-directory':'auditor'},run="""set -euo pipefail
python - <<'PY'
import hashlib,json,os,subprocess
from pathlib import Path
c='dfab13bf62398a69a02bf6221c06d29075e5e40b'
g=lambda *a:subprocess.check_output(['git',*a],text=True).strip()
assert g('rev-parse','HEAD')==c
assert g('rev-parse','HEAD^{tree}')=='886f83312958b53781a450a4ea2a8fb2147b3be3'
assert not g('diff','HEAD','--name-only')
paths=['src','supabase/release','supabase/migrations','scripts/cp7-src','supabase/dev','scripts','.github/workflows']
d=dict(candidate_sha=c,candidate_tree=g('rev-parse','HEAD^{tree}'),workflow_sha=os.environ['GITHUB_SHA'],trees={p:g('rev-parse',c+':'+p)for p in paths},guide_sha256=hashlib.sha256(Path('docs/AUDIT_PANDUAN_PRO_MAX.md').read_bytes()).hexdigest(),evidence_origin='INDEPENDENT_NATIVE_RERUN',production_go=False)
assert d['guide_sha256']=='5752e96df751de5ebe4b86d3f572cffa1bbe94eb42bf8e283fa6e04f9f593639'
Path(os.environ['RUNNER_TEMP'],'SOL_SOURCE_IDENTITY.json').write_text(json.dumps(d,indent=2)+'\\n')
print(json.dumps(d))
PY
""")
def common(w,label,filename):
 w['name']='AUDIT/SOL/'+label
 w['run-name']='AUDIT/cp17-combined-20261016/SOL/dfab13bf/'+label+'/initial'
 w['on']={'push':{'branches':[BRANCH],'paths':['.github/workflows/'+filename]},'workflow_dispatch':{}}
 w.pop(True,None);w['concurrency']={'group':'sol-combined-'+label+'-${{ github.run_id }}','cancel-in-progress':False}
 for job in w['jobs'].values():
  steps=job['steps'];steps.insert(0,{'uses':CHECKOUT,'with':{'path':'sol','persist-credentials':False}})
  for step in steps:
   if step.get('uses') in PINS:step['uses']=PINS[step['uses']]
   if step.get('uses','').startswith('actions/checkout@'):
    step.setdefault('with',{})['persist-credentials']=False
    if step['with'].get('path')=='auditor':step['with']['ref']=C
   if step.get('uses','').startswith('actions/upload-artifact@'):
    step['with']['name']='cp17-combined-20261016-SOL-dfab13bf-'+label+'-'+step['with']['name']
    step['with']['retention-days']=90
  steps.insert(6,identity_step())
  steps.append({'uses':UPLOAD,'if':'always()','with':{'name':'cp17-combined-20261016-SOL-dfab13bf-'+label+'-${{ github.job }}-${{ strategy.job-index }}-identity','path':'${{ runner.temp }}/SOL_SOURCE_IDENTITY.json','retention-days':90,'if-no-files-found':'warn'}})
 return w
def save(w,name):
 (ROOT/'.github/workflows'/name).write_text(yaml.safe_dump(w,sort_keys=False,width=120))

ret='audit-sol-combined-retest.yml'
w=common(load('claude-cp17-fixes.yml'),'combined-retest',ret)
for step in w['jobs']['phase']['steps']:
 if step.get('run')=="python '../auditor/scripts/cp7_cp17_fix_probe.py'":
  step['name']='Original CP17 suite and Sol literal cash / sewing oracles';step['run']="python '../sol/audit/sol_cp17_combined/retest_probe.py'"
 if 'drain_test.py' in step.get('run','') or 'public_state_test.py' in step.get('run',''):
  step['if']='always()'
  if 'drain_test.py' in step['run']:
   step['run']="python scripts/cp6_readiness_owner_drain_test.py | tee cp6-proof/t3/OWNER_DRAIN_TEST.json"
save(w,ret)

be='audit-sol-combined-be.yml'
w=common(load('cp6-be-t1-probe.yml'),'BE-output-retest',be)
w['jobs']['phase']['strategy']['matrix']['include']=[r for r in w['jobs']['phase']['strategy']['matrix']['include']if r['phase']=='after']
save(w,be)

f03='audit-sol-combined-f03.yml'
w=common(load('cp7-f03-full.yml'),'full-F03-final-stack',f03)
save(w,f03)

owner='audit-sol-combined-owner.yml'
w=common(load('claude-cp17-fixes.yml'),'owner-full-58-files',owner)
job=w['jobs']['phase'];job['name']='Non-superuser owner install: full 58 files from declared v2.6.20 baseline'
out=[]
for step in job['steps']:
 name=step.get('name','')
 if name in ['Install candidate browser dependencies'] or 'drain wait' in name or 'stable public-schema comparator' in name:continue
 if name.startswith('Rebuild to v2.6.20'):
  step['name']='Rebuild frozen chain only to declared v2.6.20 baseline'
  step['run']=step['run'].replace('PYTHONPATH=scripts python ../auditor/scripts/cp6_t3_aligned_chain.py ../auditor/cp6-proof/t3/ALIGNED_CHAIN.json --stop-after-ab','PYTHONPATH=../auditor/scripts:scripts python ../auditor/scripts/cp6_readiness_owner_aligned.py')
 if step.get('run')=="python '../auditor/scripts/cp7_cp17_fix_probe.py'":
  step['name']='Actual 58-file owner installation and all pre-admission refusal guards'
  step['run']="python ../auditor/scripts/cp6_readiness_owner_test.py"
 out.append(step)
job['steps']=out
save(w,owner)

declaration={
 'round_id':'cp17-combined-20261016','candidate_sha':C,'candidate_tree':'886f83312958b53781a450a4ea2a8fb2147b3be3',
 'workflows':[ret,be,f03,owner],
 'provider_cases':'Original candidate declarations unchanged: CP17 61, BE after 16, F03 8 retained buckets; owner10 and drain6 controls',
 'own_case_ids':__import__('ast').literal_eval(next(n.value for n in __import__('ast').parse((ROOT/'audit/sol_cp17_combined/independent_cases.py').read_text()).body if isinstance(n,__import__('ast').Assign) and any(isinstance(t,__import__('ast').Name)and t.id=='IDS'for t in n.targets))),
 'own_oracles':{'empty_bank':'refuse CP7_CASH_NEGATIVE atomically, balance0 AP1000','funded_public_payment':'sales income34.50 supplier paid1 => bank33.50 AP999',
 'backdate':'capital10 today cannot pay1 before capital day','later_day':'income10 payment10 leaves0; extra earlier1 refuses final later deficit',
 'funding_reversal':'capital10 paid8 => bank2; reversing capital refuses -8',
 'payment_correction_final_positive':'receipt30.01 supplier paid20; correcting receipt to25.01 succeeds atomically, bank5.01. Same unspent correction is positive control.',
 'sewing':'4pcs*4=16;6pcs*4=24; original total40 split Mandor30 Obras10. Reverse first restores remaining4/ready6/wage24.'},
 'known_limits':['No hosted SQL, deployment, main or writer branch mutation','Fixture origins and test-layer labels must stay explicit','Original AZ cause not proven by a later passing install','FABLE012 owner-deferred to CP7C; no reopening already approved policy','An inventory visit is not positive business-flow acceptance'],
 'production_go':False,'peer_round_reports_read':False}
(ROOT/'audit/sol_cp17_combined/ROUND_MANIFEST.json').write_text(json.dumps(declaration,indent=2)+'\n')
print(json.dumps({'workflows':declaration['workflows'],'own_ids':declaration['own_case_ids']},indent=2))
