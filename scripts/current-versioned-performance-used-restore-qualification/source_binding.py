"""Keep the entire previous restore runner and all seven fixtures exact."""
from pathlib import Path
from hashlib import sha256
import ast,importlib.util,json

HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'current-versioned-target-used-restore-qualification'
FIXTURES=('fixture.py','opening_fixture.py','finance_fixture.py','model_fixture.py','target_fixture.py','history_fixture.py','scoped_model_fixture.py')


def expected_probe():
    text=(OLD/'probe.py').read_text()
    changes=[
        ('cp7_current_versioned_target_recovery','cp7_current_versioned_performance_recovery'),
        ('cp7_current_versioned_target_installation','cp7_current_versioned_performance_installation'),
        ('VERSIONED_TARGET_RESTORE_','VERSIONED_PERFORMANCE_RESTORE_'),
        ('CP7_CURRENT_VERSIONED_TARGET_USED_RESTORE8','CP7_CURRENT_VERSIONED_PERFORMANCE_USED_RESTORE8'),
        ('CURRENT_VERSIONED_TARGET_USED_RESTORE_MANIFEST.json','CURRENT_VERSIONED_PERFORMANCE_USED_RESTORE_MANIFEST.json'),
        ('/tmp/current_versioned_target_','/tmp/current_versioned_performance_'),
        ('scoped_composed=composed.predecessor','scoped_composed=composed.predecessor.predecessor'),
        ("['current_installation']['predecessor']","['current_installation']['predecessor']['predecessor']"),
        ("['current_installation']['stages']","['current_installation']['predecessor']['stages']"),
        ('composed.selected.delta.SIGNATURE','composed.predecessor.selected.delta.SIGNATURE'),
        ('import scoped_model_fixture\n','import scoped_model_fixture\nimport performance_controls\n'),
        ('    def row():\n','    performance_controls.run(cur,backup,refused,bind,model_metadata,catalog,composed)\n    def row():\n')]
    counts=[]
    for before,after in changes:
        count=text.count(before);assert count>0,before
        counts.append(dict(before=before,after=after,count=count));text=text.replace(before,after)
    return text,counts


def verify(probe_text=None):
    spec=importlib.util.spec_from_file_location('qualified_previous_versioned_restore_sources',OLD/'source_binding.py')
    prior=importlib.util.module_from_spec(spec);spec.loader.exec_module(prior);previous=prior.verify()
    files={}
    for name in FIXTURES:
        raw=(HERE/name).read_bytes();assert raw==(OLD/name).read_bytes(),name
        files[name]=sha256(raw).hexdigest()
    expected,changes=expected_probe();actual=(HERE/'probe.py').read_text()if probe_text is None else probe_text
    assert ast.dump(ast.parse(expected),include_attributes=False)==ast.dump(ast.parse(actual),include_attributes=False),'PERFORMANCE_RESTORE_UNDECLARED_RUNNER_CHANGE'
    assertions=sum(isinstance(n,ast.Assert)for n in ast.walk(ast.parse(expected)))
    return dict(previous_guard=previous,unchanged_fixture_sha256=files,whole_previous_runner_AST_retained=True,
        explicit_composer_and_context_changes=changes,retained_runner_assertions=assertions,
        prior_negative_controls=29,added_performance_negative_controls=5,required_steps=8,
        production_go=False,Native_runtime_qualified=False)


if __name__=='__main__':print(json.dumps(verify(),indent=2))
