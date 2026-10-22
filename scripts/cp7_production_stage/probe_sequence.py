"""One disposable stack, six unchanged case budgets, exact restore between suites.

No extra case credit for the mandatory 22-group delta/rollback preflight. A
failed/unrestored suite stops the sequence; no later suite hides its failure.
"""
from hashlib import sha256
from pathlib import Path
import json
import os
import subprocess
import sys
import shutil

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
OUT = ROOT/'cp6-proof/t3/CP7_PRODUCTION_STAGE.json'
SUITES = (
    ('cp7_ow14b_rule_probe.py', 'CP7_OW14B_RULES.json', 113),
    ('cp7_ow16_status_probe.py', 'CP7_OW16_AUTOMATIC_STATUS.json', 16),
    ('cp7_ow13_history_probe.py', 'CP7_OW13B_COMPLETE_HISTORY.json', 20),
    ('cp7_f04_baseline_probe.py', 'CP7_F04_NATIVE_BASELINE.json', 38),
    ('cp7_p19_staged_probe.py', 'CP7_P19_STAGED.json', 15),
    ('cp7_f04_netting_probe.py', 'CP7_F04_NATIVE_NETTING.json', 84),
)
WRITER_HEAD='ca7f09556397801c50a2277bdb65b1bf019f9a05'
CLONE_SHA256='c786ad04009547e2e78baf56f93c5dd6dd5847befdb16e721e01909a592285da'


def prepare_next(index):
    """The retained package drops cp6_rollback in finally, even after PASS."""
    writer=ROOT.parent/'writer'
    if subprocess.check_output(['git','-C',str(writer),'rev-parse','HEAD'],text=True).strip()!=WRITER_HEAD:
        raise ValueError('CP7_PRODUCTION_CLONE_WRITER_CHANGED')
    script=writer/'scripts/clone-cp6-disposable-database.sh'
    if sha256(script.read_bytes()).hexdigest()!=CLONE_SHA256:
        raise ValueError('CP7_PRODUCTION_CLONE_SCRIPT_CHANGED')
    subprocess.run(['bash',str(script),
        'postgresql://postgres:postgres@127.0.0.1:54322/postgres',
        'postgresql://postgres:postgres@127.0.0.1:54322/template1',
        'postgresql://postgres:postgres@127.0.0.1:54322/cp6_rollback',
        'cp6_rollback','supabase_db_cp5-local',str(OUT.parent/f'CLONE_suite_{index:02d}')],
        check=True,timeout=300)


def archive_package(index,probe):
    # Preserve complete package/backup Originals before the next package
    # writes the same retained filenames. No screenshots or case relabeling.
    target=OUT.parent/f'suite-{index:02d}-{Path(probe).stem}'
    target.mkdir(exist_ok=False)
    for source in sorted(OUT.parent.glob('T3_*.json')):
        shutil.move(str(source),str(target/source.name))
    return str(target.relative_to(OUT.parent))


def main():
    from cp7_production_stage import verify_sources
    import cp7_payment_source_owning_install as predecessor
    expected = json.loads((ROOT/'scripts/ow04-consumer-closure-qualification/SOURCE.json').read_text())['product_sources']
    assert predecessor.sources() == expected, 'CP7_PRODUCTION_FROZEN_OWNING_CHAIN_CHANGED'
    report = dict(contract='cp7.production-stage-sequence.v1', status='INCOMPLETE',
        auditor_head=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'], text=True).strip(),
        frozen_owning_source_gate=True, stage_sources=verify_sources(), expected_case_count=286,
        retained_case_budgets=[dict(probe=p,original=f,expected=n)for p,f,n in SUITES], suites=[],
        production_go=False, independent_acceptance=False, full_A_chain_acceptance=False)
    OUT.parent.mkdir(parents=True,exist_ok=True)
    def save():
        OUT.write_text(json.dumps(report,indent=2)+'\n')
    save()
    try:
        for index,(probe, filename, count) in enumerate(SUITES,1):
            if index>1:
                prepare_next(index)
            original = OUT.with_name(filename)
            if original.exists():
                raise ValueError('CP7_PRODUCTION_ORIGINAL_ALREADY_EXISTS: '+filename)
            result = subprocess.run([sys.executable,str(ROOT/'scripts'/probe)],check=False)
            package_path=archive_package(index,probe)
            raw = original.read_bytes() if original.exists() else b''
            r = json.loads(raw)if raw else {}
            entry = dict(probe=probe,original=filename,exit_code=result.returncode,bytes=len(raw),sha256=sha256(raw).hexdigest(),
                status=r.get('status'),observed_case_count=r.get('observed_case_count'),cp6_restored=r.get('cp6_restored'),
                advisor_gate=r.get('advisor_gate'),production_stage=r.get('production_stage'),package_Originals=package_path,
                fresh_aligned_AB_clone=index>1)
            report['suites'].append(entry);save()
            assert result.returncode == 0 and r.get('status') == 'PASS' and r.get('observed_case_count') == count, entry
            assert r.get('cp6_restored') is True and r.get('advisor_gate') is True, entry
            assert r.get('production_stage',{}).get('preuse_22_groups_exactly_restored') is True, entry
            print(json.dumps(dict(suite=filename,status='PASS',cases=count,restored_before_next_suite=True)),flush=True)
        assert sum(x['observed_case_count']for x in report['suites']) == 286
        report.update(status='PASS',observed_case_count=286)
        return 0
    except Exception as error:
        report['error'] = str(error)
        return 1
    finally:
        save()
        print(json.dumps({k:report.get(k)for k in ('contract','status','observed_case_count','error')}),flush=True)


if __name__ == '__main__':
    sys.exit(main())
