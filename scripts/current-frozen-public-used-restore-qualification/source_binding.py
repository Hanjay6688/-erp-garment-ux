"""Preserve all eight recovery steps, seven fixtures and 34 controls; add public use."""
from pathlib import Path
from hashlib import sha256
import ast,importlib.util,json
HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'current-versioned-performance-used-restore-qualification'
FIXTURES=('fixture.py', 'opening_fixture.py', 'finance_fixture.py', 'model_fixture.py', 'target_fixture.py', 'history_fixture.py', 'scoped_model_fixture.py')
CHANGES=[('cp7_current_versioned_performance_recovery', 'cp7_current_frozen_public_recovery'), ('cp7_current_versioned_performance_installation', 'cp7_current_frozen_public_installation'), ('VERSIONED_PERFORMANCE_RESTORE_', 'FROZEN_PUBLIC_RESTORE_'), ('CP7_CURRENT_VERSIONED_PERFORMANCE_USED_RESTORE8', 'CP7_CURRENT_FROZEN_PUBLIC_USED_RESTORE8'), ('CURRENT_VERSIONED_PERFORMANCE_USED_RESTORE_MANIFEST.json', 'CURRENT_FROZEN_PUBLIC_USED_RESTORE_MANIFEST.json'), ('/tmp/current_versioned_performance_', '/tmp/current_frozen_public_'), ('scoped_composed=composed.predecessor.predecessor', 'scoped_composed=composed.predecessor.predecessor.predecessor.predecessor.predecessor'), ("['current_installation']['predecessor']", "['current_installation']['predecessor']['predecessor']['predecessor']['predecessor']"), ('composed.predecessor.selected.delta.SIGNATURE', 'composed.predecessor.predecessor.predecessor.predecessor.selected.delta.SIGNATURE'), ('import performance_controls\n', 'import performance_controls\nimport public_controls\nimport public_finance_fixture\n'), ('    def row():\n', '    public_controls.run(cur,backup,refused,bind,model_metadata,catalog,composed)\n    def row():\n'), ('            target_before_backup={}\n', "            held_public_finance=public_finance_fixture.prepare(cur,comparison['row']['query'],report)\n            target_before_backup={}\n"), ("            finance_fixture.assert_restored(cur,held_finance,report,'BEFORE_RESTORED_CLEAR')\n", "            finance_fixture.assert_restored(cur,held_finance,report,'BEFORE_RESTORED_CLEAR')\n            public_finance_fixture.assert_restored(cur,held_public_finance,report,'BEFORE_RESTORED_CLEAR')\n"), ("            finance_fixture.assert_restored(cur,held_finance,report,'AFTER_NEXT_NATIVE_RETURN')\n", "            finance_fixture.assert_restored(cur,held_finance,report,'AFTER_NEXT_NATIVE_RETURN')\n            public_finance_fixture.assert_restored(cur,held_public_finance,report,'AFTER_NEXT_NATIVE_RETURN')\n")]
def verify(probe_text=None):
    spec=importlib.util.spec_from_file_location('retained_performance_restore_guard',OLD/'source_binding.py')
    prior=importlib.util.module_from_spec(spec);spec.loader.exec_module(prior);previous=prior.verify()
    import cp7_current_frozen_public_recovery_check as recovery_guard
    recovery=recovery_guard.source_guard()
    files={}
    for name in FIXTURES:
        raw=(HERE/name).read_bytes();assert raw==(OLD/name).read_bytes(),name;files[name]=sha256(raw).hexdigest()
    expected=(OLD/'probe.py').read_text()
    for a,b in CHANGES:assert a in expected,a;expected=expected.replace(a,b)
    actual=(HERE/'probe.py').read_text()if probe_text is None else probe_text
    assert ast.dump(ast.parse(actual),include_attributes=False)==ast.dump(ast.parse(expected),include_attributes=False),'PUBLIC_RESTORE_UNDECLARED_RUNNER_CHANGE'
    controls=(OLD/'performance_controls.py').read_text().replace("['current_installation']['performance']","['current_installation']"+"['predecessor']"*3+"['performance']").replace('composed.performance.','composed'+'.predecessor'*3+'.performance.').replace('VERSIONED_PERFORMANCE_RESTORE_','FROZEN_PUBLIC_RESTORE_')
    assert(HERE/'performance_controls.py').read_text()==controls
    fixture=(OLD/'finance_fixture.py').read_text()
    for a,b in [('current-bounded-finance-native-qualification/cases.py','current-frozen-public-native-qualification/public_finance_cases.py'),('cp7.bounded-analysis-request.v1','cp7.bounded-analysis-request.v2'),('finance_before_full_used_backup','public_frozen_finance_before_full_used_backup'),('finance_full_restore_checks','public_frozen_finance_full_restore_checks')]:
        assert a in fixture;fixture=fixture.replace(a,b)
    assert(HERE/'public_finance_fixture.py').read_text()==fixture
    return dict(previous_guard=previous,recovery_source=recovery,unchanged_fixture_sha256=files,
        entire_retained_runner_AST_preserved=True,retained_runner_assertions=sum(isinstance(n,ast.Assert)for n in ast.walk(ast.parse(actual))),
        prior_negative_controls=34,added_public_negative_controls=8,required_steps=8,
        legacy_and_public_frozen_finance_both_used=True,production_go=False,actual_restore_qualified=False)
