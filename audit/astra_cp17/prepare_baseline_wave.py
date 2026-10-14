from pathlib import Path
import hashlib,json,yaml

ROOT=Path(__file__).resolve().parents[2]
HERE=ROOT/'audit/astra_cp17'
def sha(path):return hashlib.sha256((ROOT/path).read_bytes()).hexdigest()

def main():
    original=json.loads((ROOT/'docs/evidence/cp6-regression-expected-au-run35822980561.json').read_text())
    sources=['scripts/cp6_t2_regression.py','scripts/cp6_av_trial.py','scripts/cp6_ar_trial.py',
             'scripts/cp6_as_cases.py','scripts/cp6_at_cases.py','scripts/cp6_at_races.py',
             'scripts/cp6_au_cases.py','scripts/cp6_au_races.py','scripts/cp6_successor_specs.py',
             'scripts/cp6_regression_identity.py','scripts/cp7_p21_full_rehearsal_probe.py',
             'docs/evidence/cp6-regression-expected-au-run35822980561.json']
    manifest=dict(round_id='cp17-20261014',candidate_sha='0b7049d9203bac52b47a4c89f3e0d75646067a8f',
        status='PREDECLARED_BEFORE_EXECUTION',oracle_origin='FROZEN_LEGACY_UNCHANGED',
        fixture_origin='CANDIDATE_T2_REVIEWED_ADAPTER',evidence_origin='INDEPENDENT_NATIVE_RERUN',
        source_sha256={p:sha(p) for p in sources},
        baseline_expected=original['expected'],
        original_groups={k:len(v) for k,v in original['expected'].items()},
        phases=[dict(phase='regression',expected_original=360,additional='AO12, approved supplements and C0-25 retained as separate IDs'),
                dict(phase='ar',expected_original=174,additional='one BC FREE-policy superseding case; original zero-price case retained'),
                dict(phase='temporal',expected_original=31,expected_races=10)],
        harness_adaptations=[
            'P21 FULL composition installed once; repeated AU/AV/dev installation calls replaced by exact installed-runtime verification only',
            'frozen T2 case factories, expected maps, approved supplements and race operations not edited',
            'legacy raw status preserved; per-case catalog/public/session/date checks added',
            'first case-ID list persisted before any operation; no automatic case retry'],
        dispositions='Moved case results remain DISPOSITION_REQUIRED until source/owner-rule review; no unknown status becomes PASS',
        runtime_claim='CP1-CP7 candidate FULL composition; synthetic captured baseline, not current hosted state')
    (HERE/'BASELINE_CASE_MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n')
    w=yaml.safe_load((ROOT/'.github/workflows/audit-astra-cp17-native.yml').read_text())
    w['name']='AUDIT/Astra/cp17-baseline'
    w['run-name']='AUDIT/cp17-20261014/Astra/0b7049d9/baseline/${{ github.run_attempt }}'
    w['on']['push']['paths']=['.github/workflows/audit-astra-cp17-baseline.yml','audit/astra_cp17/BASELINE_START']
    w['concurrency']['group']='astra-cp17-baseline-${{ github.run_id }}'
    j=w['jobs']['phase'];j['name']='AUDIT/Astra/baseline-${{ matrix.phase }}'
    j['timeout-minutes']=180;j['strategy']['max-parallel']=3
    j['strategy']['matrix']['include']=[dict(phase=p,suite='baseline-'+p,seed='AS_IS' if p=='temporal' else 'QUIETED',bucket='') for p in ('regression','ar','temporal')]
    j['env'].update(CP6_T2_SEED='${{ matrix.seed }}',CP6_T2_LABEL='T2_REGRESSION',CP6_T2_FIXTURE='PAYROLL_APPROVED')
    for s in j['steps']:
        n=s.get('name','')
        if n=='Prove pinned product and record evidence origins':
            s['run']=s['run'].replace('NATIVE_CASE_MANIFEST.json','BASELINE_CASE_MANIFEST.json').replace("oracle_origin='WRITER_UNCHANGED'","oracle_origin='FROZEN_LEGACY_UNCHANGED'")
        elif n=='Independently rerun unchanged writer cases on pinned product':
            s['name']='Run original baseline contracts on pinned FULL composition'
            s['run']='python "../control/audit/astra_cp17/baseline_full.py" "${{ matrix.phase }}"'
        if 'with' in s and 'name' in s['with']:
            s['with']['name']='cp17-astra-0b7049d9-${{ matrix.suite }}-'+('json' if s['with']['name'].endswith('-json') else 'raw')
    (ROOT/'.github/workflows/audit-astra-cp17-baseline.yml').write_text(yaml.safe_dump(w,sort_keys=False,width=120))
    print(json.dumps({'predeclared_original_groups':manifest['original_groups'],'original_total':sum(manifest['original_groups'].values()),'phases':3}))

if __name__=='__main__':main()
