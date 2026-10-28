"""Prove the infrastructure successor retains every original ERP diagnostic."""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import json,subprocess,yaml

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
NS='scripts/current-finance-consistent-capture-diagnostic'
GENERIC='scripts/cp7_disposable_qualification'
ADMISSION_ANCHOR="    guard=load('consistent_capture_probe_guard',here/'source_guard.py').check(repo,here)"


def original(repo,rule,path):
    return subprocess.check_output(['git','-C',str(repo),'show',rule['parent_head']+':'+path])


def admission_expected(raw):
    text=raw.decode();assert text.count(ADMISSION_ANCHOR)==1
    text=text.replace(ADMISSION_ANCHOR,ADMISSION_ANCHOR+
        "\n    infrastructure=load('consistent_capture_infrastructure_guard',here/'infra_source_guard.py').check(repo,here)",1)
    anchor='source_guard=guard,production_go=False'
    assert text.count(anchor)==1
    return text.replace(anchor,'source_guard=guard,infrastructure_guard=infrastructure,production_go=False',1)


def expected(repo,here):
    rule=json.loads((here/'INFRA_DERIVATION.json').read_bytes())
    raw=original(repo,rule,rule['parent_workflow'])
    assert sha256(raw).hexdigest()==rule['parent_workflow_sha256']
    value=deepcopy(yaml.safe_load(raw))
    value['name']='CP7 D17-18 unchanged consistency diagnostics with retained infrastructure'
    value['on']['push']['branches']=['astra-a/d17-18-consistent-capture-infra-qualification-20261028']
    value['on']['push']['paths']=[rule['target_workflow'],NS+'/**',GENERIC+'/**']
    value['concurrency']['group']='cp7-d17-18-consistent-infra-${{ github.run_id }}'
    job=value['jobs']['p21'];job['name']=value['name'];steps=job['steps']
    checkouts=[s for s in steps if s.get('uses','').startswith('actions/checkout@')]
    heads={s['with']['path']:s['with']['ref']for s in checkouts if s['with']['path']!='auditor'}
    assert heads==json.loads((repo/GENERIC/'FROZEN_SOURCE_ROOTS.json').read_bytes())
    auditor=[s for s in checkouts if s['with']['path']=='auditor']
    assert len(auditor)==1 and auditor[0]['with']['fetch-depth']==0
    steps[:]=[auditor[0],*[s for s in steps if not s.get('uses','').startswith('actions/checkout@')]]
    assert steps[1].get('id')=='qualified_heads'
    steps.insert(2,dict(name='Materialize exact original frozen heads from one full checkout',
        **{'working-directory':'auditor'},env={
            'QUALIFIED_NATIVE_HEAD':'${{ steps.qualified_heads.outputs.native }}',
            'QUALIFIED_B_HEAD':'${{ steps.qualified_heads.outputs.B }}'},
        run='python '+GENERIC+'/materialize_sources.py'))
    tests=[s for s in steps if s.get('name')=='Verify cron transformation and real phase timing before database']
    assert len(tests)==1
    tests[0]['run']+='\npython -m unittest discover -s '+GENERIC+' -p "test*.py"\n'
    startup=[s for s in steps if s.get('name')=='Start disposable database']
    assert len(startup)==1;marker='# ghcr.io can rate-limit image pulls before anything runs.'
    assert startup[0]['run'].count(marker)==1
    startup[0]['run']=startup[0]['run'].split(marker)[0]+(
        '# Retain every complete image-start attempt; return to GHCR after one ECR fallback.\n'
        'python ../auditor/'+GENERIC+'/disposable_start.py\n')
    upload=[s for s in steps if s.get('uses','').startswith('actions/upload-artifact@')]
    assert len(upload)==1 and 'overwrite'not in upload[0]['with']
    upload[0]['with']['name']='cp7-d17-18-consistent-infra-${{ github.run_attempt }}'
    return value


def check(repo,here,*,workflow=None,admission_body=None):
    rule=json.loads((here/'INFRA_DERIVATION.json').read_bytes())
    source=json.loads(original(repo,rule,NS+'/SOURCE.json'))
    unchanged=0
    for path,digest in source['files'].items():
        if path==NS+'/admission.py':continue
        assert sha256((repo/path).read_bytes()).hexdigest()==digest,'INFRA_CHANGED_ERP_DIAGNOSTIC:'+path
        unchanged+=1
    old=original(repo,rule,NS+'/admission.py')
    current=(here/'admission.py').read_text()if admission_body is None else admission_body
    assert current==admission_expected(old),'INFRA_UNDECLARED_ADMISSION_CHANGE'
    for path,digest in rule['copied_helper_sha256'].items():
        assert sha256((repo/path).read_bytes()).hexdigest()==digest,'INFRA_HELPER_CHANGED:'+path
    actual=yaml.safe_load((repo/rule['target_workflow']).read_bytes())if workflow is None else workflow
    assert actual==expected(repo,here),'INFRA_UNDECLARED_WORKFLOW_CHANGE'
    return dict(scope='INFRASTRUCTURE_ONLY_UNCHANGED_ERP_DIAGNOSTICS',
        unchanged_original_source_files=unchanged,ERP_SQL_and_business_cases_unchanged=True,
        original_probe_and_all_restoration_assertions_unchanged=True,
        single_full_history_checkout=True,original_frozen_heads_and_trees_required=True,
        retained_bounded_startup_attempts=4,maximum_ECR_attempts=1,
        application_statement_limits_and_image_tags_unchanged=True,
        same_source_retry_exhausted_and_retained=True,production_go=False,independent_acceptance=False)


if __name__=='__main__':
    rule=json.loads((HERE/'INFRA_DERIVATION.json').read_bytes());path=ROOT/rule['target_workflow']
    assert not path.exists();path.write_text(yaml.safe_dump(expected(ROOT,HERE),sort_keys=False,allow_unicode=True,width=110))
