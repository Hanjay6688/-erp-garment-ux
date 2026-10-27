"""Closed until actual prerequisites and the complete combined source are bound."""
from hashlib import sha256
from pathlib import Path
import ast,importlib.util,json,subprocess


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def gate(config):
    if config.get('allow_database_execution')is not True:
        raise ValueError('COMBINED_QUALIFICATION_NOT_ADMITTED')
    assert config['production_go']is config['independent_acceptance']is False


def source_guard(repo,here):
    rules=json.loads((here/'QUALIFICATION_ORIGIN.json').read_bytes())
    proof={}
    for target,rule in rules.items():
        raw=(repo/rule['path']).read_bytes()
        assert sha256(raw).hexdigest()==rule['sha256'],'COMBINED_QUALIFICATION_PARENT_CHANGED:'+target
        expected=raw.decode()
        for change in rule['changes']:
            assert expected.count(change['old'])==change['count']
            expected=expected.replace(change['old'],change['new'])
        actual=(here/target).read_text()
        assert actual==expected,'COMBINED_UNDECLARED_QUALIFICATION_CHANGE:'+target
        assert sum(isinstance(n,ast.Assert)for n in ast.walk(ast.parse(actual)))==rule['assertions']
        proof[target]=dict(exact_declared_derivation=True,unchanged_assertions=rule['assertions'])
    workflow=load('combined_qualification_workflow_guard',here/'workflow_guard.py')
    proof['workflow']=workflow.check(repo)
    return proof


def admitted(repo,here,ids,product,native):
    gate(json.loads((here/'QUALIFICATION_CONFIG.json').read_bytes()))
    combined=product.sources();original,_=product.qualification()
    source=json.loads((here/'QUALIFICATION_SOURCE.json').read_bytes())
    assert source['case_ids']==list(ids)
    assert source['production_go']is source['independent_acceptance']is False
    for path,digest in source['files'].items():
        assert sha256((repo/path).read_bytes()).hexdigest()==digest,path
    parent_dir=repo/'scripts/current-finance-consistency-corrected-qualification'
    readonly=load('combined_acceptance_exact_readonly_parent',repo/'scripts/current-finance-readonly-integration-qualification/composition.py')
    admission=load('combined_acceptance_focused_component_admission',parent_dir/'admission.py')
    parent_source=json.loads((parent_dir/'SOURCE.json').read_bytes())
    exact_parent=admission.admitted(repo,parent_dir,parent_source['case_ids'],readonly,native)
    assert original['source_declaration']==exact_parent,'COMBINED_FULL_PREREQUISITE_SOURCE_CHANGED'
    guard=source_guard(repo,here)
    assert not subprocess.check_output(['git','-C',str(repo),'status','--porcelain','--untracked-files=no'],text=True).strip()
    return dict(qualification=source,current_installation=combined,accepted_consistency=exact_parent,
        source_guard=guard,production_go=False,independent_acceptance=False)


if __name__=='__main__':
    here=Path(__file__).resolve().parent
    probe=load('combined_qualification_admission_probe',here/'qualification_probe.py')
    result=probe.admitted()
    print(json.dumps(dict(status='SOURCE_ADMITTED',pins=len(result['qualification']['files']),
        actual_cases_executed=False)))
