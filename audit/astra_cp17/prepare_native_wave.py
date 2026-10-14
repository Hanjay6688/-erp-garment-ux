"""Prepare an audit-only CI wave; candidate product and writer oracles stay pinned."""
from pathlib import Path
import datetime, hashlib, json, subprocess
import yaml

ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / 'audit/astra_cp17'
CANDIDATE = '0b7049d9203bac52b47a4c89f3e0d75646067a8f'
TREE = 'ce6aed0a0af920e8aa80248f3cabcd293688df18'
BRANCH = 'audit/astra-cp1-7-0b7049d9-20261014'
ROUND = 'cp17-20261014'

def digest(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()

def main():
    assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip() == CANDIDATE
    manifest = json.loads((ROOT/'scripts/cp7_f03_full_manifest.json').read_text())
    suites = []
    for bucket in ['p09','p10','p12','p13','cash_installments','supplier_credit','customer_refund']:
        spec = manifest['buckets'][bucket]
        suites.append(dict(suite='f03-'+bucket, probe='cp7_f03_full_probe.py', bucket=bucket,
                           args='', timeout=180, expected_cases=spec['expected_case_executions'],
                           expected_smoke=spec['expected_smoke_executions'], groups=spec['groups'],
                           scope=['CP3-5 consumers','CP6','CP7 F03']))
    for suite, probe, timeout in [
        ('pl-supply','cp7_f04_supply_probe.py',120),
        ('pl-model','cp7_f04_model_probe.py',120),
        ('pl-schedule','cp7_f04_schedule_probe.py',120),
        ('pl-netting','cp7_f04_netting_probe.py',120),
        ('p18-full-cycle','cp7_p18_full_cycle_probe.py',180),
        ('note-correction','cp7_note_correction_probe.py',180),
        ('receipt-correction','cp7_receipt_correction_probe.py',180),
        ('cutting-correction','cp7_cutting_correction_probe.py',180),
        ('sales-return-correction','cp7_sales_return_correction_probe.py',180),
        ('payment-correction','cp7_payment_correction_probe.py',180),
        ('misc-correction','cp7_misc_correction_probe.py',180),
        ('supplier-payment-correction','cp7_supplier_payment_correction_probe.py',180),
        ('p19-plan-v2','cp7_p19_plan_v2_probe.py',180),
        ('p19-report-v2','cp7_p19_report_v2_probe.py',180),
        ('p19-reminder-v2','cp7_p19_reminder_v2_probe.py',180),
        ('p19-ai-v2','cp7_p19_ai_v2_probe.py',180),
        ('pl5-history-yield','cp7_pl5_history_yield_probe.py',180),
        ('k2-retention','cp7_k2_retention_probe.py',180),
        ('k4-runner','cp7_k4_runner_probe.py',180),
        ('k6-proof-runner','cp7_k6_proof_runner_probe.py',180),
        ('p21-full-rehearsal','cp7_p21_full_rehearsal_probe.py',180),
        ('fabric-physical','cp7_fabric_physical_probe.py',180),
        ('cutting-model','cp7_cutting_model_probe.py',180),
        ('rule-lifecycle','cp7_rule_lifecycle_probe.py',180),
    ]:
        suites.append(dict(suite=suite,probe=probe,bucket='',args='',timeout=timeout,
                           scope=['CP7','affected CP3-6 Native sources']))
    for row in suites:
        row.update(oracle_origin='WRITER_UNCHANGED',fixture_origin='WRITER_UNCHANGED',
                   evidence_origin='INDEPENDENT_NATIVE_RERUN',
                   source_sha256=digest('scripts/'+row['probe']),
                   case_declaration='candidate probe and imported provider; runtime planned IDs persisted before first case')
    products = ['src','supabase','supabase/migrations','supabase/release','supabase/dev',
                'supabase/rollbacks','scripts','scripts/cp7-src','.github/workflows']
    receipt = dict(round_id=ROUND,candidate_sha=CANDIDATE,candidate_tree=TREE,
                   package_sha='00b0eb24b2f014d102f0082111d13ee3be429cf2',
                   product_trees={p:subprocess.check_output(['git','rev-parse','HEAD:'+p],cwd=ROOT,text=True).strip() for p in products},
                   guide=dict(path='docs/AUDIT_PANDUAN_PRO_MAX.md',sha256=digest('docs/AUDIT_PANDUAN_PRO_MAX.md')),
                   lockfile_sha256=digest('package-lock.json'),
                   owner_registers={p:digest(p) for p in [
                       'docs/cp7/OWNER_DECISIONS_20261008.md',
                       'docs/contracts/ERP_ADDENDUM_OWNER_DECISIONS_CP6_2026-09-25.md',
                       'docs/contracts/ERP_ADDENDUM_OWNER_DECISIONS_CP6_2026-09-25_LAMPIRAN_C6.md',
                       'docs/cp6-d11-kebijakan-dan-gbd03.md']},
                   created_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                   production_go=False,audit_complete=False)
    (HERE/'SOURCE_RECEIPT.json').write_text(json.dumps(receipt,indent=2)+'\n')
    (HERE/'NATIVE_CASE_MANIFEST.json').write_text(json.dumps(dict(round_id=ROUND,
        candidate_sha=CANDIDATE, status='PREDECLARED_BEFORE_EXECUTION',suites=suites,
        harness_adaptation='disable automatic business-day group retry; preserve original guard and first status (Pro Max 1.9)',
        no_acceptance_by_writer_tests_alone=True,
        additional_independent_contract_cases='separate manifest before their own execution',
        prior_same_candidate_runs=['38435365859','38435746105'],
        prior_credit='separate carried evidence, not new executions',
        conflict_of_interest={'pl-netting':'Astra authored PR44; examine but acceptance requires another auditor'}),indent=2)+'\n')
    workflow = yaml.safe_load((HERE/'xc2_workflow_template.yml').read_text())
    workflow['name'] = 'AUDIT/Astra/cp17-native'
    workflow['run-name'] = 'AUDIT/cp17-20261014/Astra/0b7049d9/native/${{ github.run_attempt }}'
    workflow['on'] = {'push':{'branches':[BRANCH], 'paths':['.github/workflows/audit-astra-cp17-native.yml','audit/astra_cp17/NATIVE_START']},'workflow_dispatch':{}}
    workflow['concurrency']['group'] = 'astra-cp17-native-${{ github.run_id }}'
    workflow['jobs'].pop('dozen-dom')
    job = workflow['jobs']['phase']
    job['name'] = 'AUDIT/Astra/${{ matrix.suite }}'
    job['strategy']['max-parallel'] = 6
    job['strategy']['matrix']['include'] = [{k:r[k] for k in ('suite','probe','timeout','args','bucket')} for r in suites]
    for step in job['steps']:
        name=step.get('name','')
        if name=='Prove pinned product and record evidence origins':
            step['run'] = '''set -euo pipefail
test "$(git rev-parse HEAD)" = 0b7049d9203bac52b47a4c89f3e0d75646067a8f
test "$(git rev-parse HEAD^{tree})" = ce6aed0a0af920e8aa80248f3cabcd293688df18
git diff --exit-code HEAD --
mkdir -p cp6-proof/t3
cp ../control/audit/astra_cp17/SOURCE_RECEIPT.json cp6-proof/t3/ASTRA_SOURCE_RECEIPT.json
cp ../control/audit/astra_cp17/NATIVE_CASE_MANIFEST.json cp6-proof/t3/ASTRA_CASE_MANIFEST.json
python - <<'PYIN'
import json,os,subprocess,pathlib
p=pathlib.Path('cp6-proof/t3/ASTRA_EXECUTION_ORIGIN.json')
p.write_text(json.dumps(dict(round_id='cp17-20261014',evidence_origin='INDEPENDENT_NATIVE_RERUN',oracle_origin='WRITER_UNCHANGED',fixture_origin='WRITER_UNCHANGED',candidate_sha=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),candidate_tree=subprocess.check_output(['git','rev-parse','HEAD^{tree}'],text=True).strip(),workflow_sha=os.environ['GITHUB_SHA'],run_id=os.environ['GITHUB_RUN_ID'],run_attempt=os.environ['GITHUB_RUN_ATTEMPT'],suite=os.environ['ASTRA_SUITE'],production_go=False),indent=2)+'\\n')
PYIN
'''
            step['env']={'ASTRA_SUITE':'${{ matrix.suite }}'}
        elif name=='Independently rerun unchanged writer cases on pinned product':
            step['run']='python "../control/audit/astra_cp17/rerun_product.py" "${{ matrix.probe }}" ${{ matrix.args }}'
        if 'with' in step and 'name' in step['with']:
            step['with']['name']=step['with']['name'].replace('cp7xc2-astra','cp17-astra')
    (ROOT/'.github/workflows/audit-astra-cp17-native.yml').write_text(yaml.safe_dump(workflow,sort_keys=False,width=120))
    assert receipt['guide']['sha256']=='5752e96df751de5ebe4b86d3f572cffa1bbe94eb42bf8e283fa6e04f9f593639'
    print(json.dumps({'suites':len(suites),'candidate':CANDIDATE,'branch':BRANCH}))

if __name__=='__main__':
    main()
