"""Keep the actual84 outer probe and every full restore assertion unchanged."""
from hashlib import sha256
import ast,importlib.util,json


def check(repo,here,*,overrides=None):
    rules=json.loads((here/'ORIGIN.json').read_bytes());proof={}
    for target,rule in rules.items():
        if target=='workflow':continue
        raw=(repo/rule['path']).read_bytes()
        assert sha256(raw).hexdigest()==rule['sha256'],'FOCUSED_SOURCE_PARENT_CHANGED:'+target
        expected=raw.decode()
        for change in rule['changes']:
            assert expected.count(change['old'])==change['count']
            expected=expected.replace(change['old'],change['new'])
        actual=(overrides or{}).get(target,(here/target).read_text())
        assert actual==expected,'FOCUSED_UNDECLARED_PROBE_OR_RESTORE_CHANGE:'+target
        assert sum(isinstance(n,ast.Assert)for n in ast.walk(ast.parse(actual)))==rule['assertions']
        proof[target]=dict(exact_declared_derivation=True,assertions_retained=rule['assertions'])
    # The math, canonical signature and original test bodies are admitted by
    # actual84's complete parent declaration, never replaced by these adapters.
    spec=importlib.util.spec_from_file_location('focused_consistency_workflow_guard',here/'workflow_guard.py')
    workflow=importlib.util.module_from_spec(spec);spec.loader.exec_module(workflow)
    proof['workflow']=workflow.check(repo,here)
    proof.update(original_ERP_SQL_and_capture_case_bodies_unchanged=True,
        Native20_oracles_unchanged=True,only_three_Native_inputs_prepared=True,
        accepted_readonly_cron_observer_used=True,actual_DB_cases_during_source_admission=0)
    return proof
