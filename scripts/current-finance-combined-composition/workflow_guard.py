"""Derive only the combined entry points and retained pre-test startup retries."""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import json,yaml

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
PARENT='.github/workflows/cp7-d17-18-consistent-capture.yml'
TARGET='.github/workflows/cp7-d17-18-combined-finance.yml'
PARENT_SHA256='305f54fc7a56bea85041e8ca1d5ea09f7553703129401967594d971063940770'
LABEL='CP7_D17_18_COMBINED_FINANCE_NATIVE_SOURCE_FACTORY_CRON7'


def expected(repo):
    raw=(repo/PARENT).read_bytes()
    assert sha256(raw).hexdigest()==PARENT_SHA256,'COMBINED_WORKFLOW_PARENT_CHANGED'
    value=deepcopy(yaml.safe_load(raw))
    value['name']='CP7 D17-18 combined finance Native source factory cron qualification'
    value['on']['push']['branches']=['astra-a/d17-18-combined-finance-qualification-20261028']
    value['on']['push']['paths']=[TARGET,'scripts/current-finance-combined-composition/**']
    value['concurrency']['group']='cp7-d17-18-combined-finance-${{ github.run_id }}'
    job=value['jobs']['p21'];job['name']=value['name'];steps=job['steps']
    checkouts=[s for s in steps if s.get('uses','').startswith('actions/checkout@')]
    roots={s['with']['path']:s['with']['ref']for s in checkouts if s['with']['path']!='auditor'}
    assert roots==json.loads((HERE/'FROZEN_SOURCE_ROOTS.json').read_bytes())
    auditor=[s for s in checkouts if s['with']['path']=='auditor']
    assert len(auditor)==1 and auditor[0]['with']['fetch-depth']==0
    steps[:]=[auditor[0],*[s for s in steps if not s.get('uses','').startswith('actions/checkout@')]]
    selected=[s for s in steps if s.get('id')=='qualified_heads']
    assert len(selected)==1 and steps[1]is selected[0]
    steps.insert(2,dict(name='Materialize every exact frozen source from one full checkout',
        **{'working-directory':'auditor'},env={
            'QUALIFIED_NATIVE_HEAD':'${{ steps.qualified_heads.outputs.native }}',
            'QUALIFIED_B_HEAD':'${{ steps.qualified_heads.outputs.B }}'},
        run='python scripts/current-finance-combined-composition/materialize_sources.py'))

    def step(name):
        matches=[s for s in steps if s.get('name')==name]
        assert len(matches)==1,name
        return matches[0]

    anchor=step('Admit exact retained first diagnostics and consistency candidate before database')
    additions=[
        dict(name='Fetch exact retained84 and focused Native20 cron component bytes',
            **{'working-directory':'auditor'},env={'GH_TOKEN':'${{ github.token }}'},
            run='python scripts/current-finance-combined-composition/fetch_consistency.py'),
        dict(name='Verify closed combined boundaries and retained pre-test retry logs',
            **{'working-directory':'auditor'},
            run='python -m unittest discover -s scripts/current-finance-combined-composition -p "test*.py"'),
        dict(name='Admit exact accepted consistency and complete combined source before database',
            **{'working-directory':'auditor'},
            run='python scripts/current-finance-combined-composition/qualification_admission.py')]
    index=steps.index(anchor)+1;steps[index:index]=additions
    start=step('Start disposable database');marker='# ghcr.io can rate-limit image pulls before anything runs.'
    assert start['run'].count(marker)==1
    start['run']=start['run'].split(marker)[0]+(
        '# Retain every startup attempt; ECR is used once before returning to GHCR.\n'
        'python ../auditor/scripts/current-finance-combined-composition/disposable_start.py\n')
    execute=step('Run seven isolated report book consistency diagnostics with full database restoration')
    execute['name']='Run actual combined Native source report factory and minute cron groups with full restoration'
    execute['run']="python '../auditor/scripts/current-finance-combined-composition/qualification_probe.py'"
    logs=step('Preserve exact original JSON report bytes in a bounded compressed log receipt')
    assert logs['run'].count('CP7_D17_18_FINANCE_REPORT_BOOK_CONSISTENCY_ISOLATED7')==1
    logs['run']=logs['run'].replace('CP7_D17_18_FINANCE_REPORT_BOOK_CONSISTENCY_ISOLATED7',LABEL)
    upload=[s for s in steps if s.get('uses','').startswith('actions/upload-artifact@')]
    assert len(upload)==1 and 'overwrite'not in upload[0]['with']
    upload[0]['with']['name']='cp7-d17-18-combined-finance-${{ github.run_attempt }}'
    return value


def check(repo):
    assert yaml.safe_load((repo/TARGET).read_bytes())==expected(repo),'COMBINED_UNDECLARED_WORKFLOW_CHANGE'
    return dict(exact_declared_derivation=True,source_and_DB_restore_steps_retained=True,
        startup_attempts_bounded_to_four=True,full_first_attempt_logs_retained=True,
        existing_ERP_test_not_retried=True,image_tags_and_timeouts_unchanged=True,
        single_full_history_checkout=True,every_original_frozen_head_and_tree_verified=True,
        artifact_name_includes_attempt=True,previous_artifact_not_overwritten=True)


if __name__=='__main__':
    path=ROOT/TARGET;assert not path.exists()
    path.write_text(yaml.safe_dump(expected(ROOT),sort_keys=False,allow_unicode=True,width=110))
    print(json.dumps(check(ROOT)))
