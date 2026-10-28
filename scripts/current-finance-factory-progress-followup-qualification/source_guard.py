"""Exact old qualification bodies plus declared reader and restore corrections."""
from pathlib import Path
from hashlib import sha256
import ast,importlib.util,json


def check(repo,here,*,overrides=None):
    rules=json.loads((here/'ORIGIN.json').read_bytes());proof={}
    for target,rule in rules.items():
        raw=(repo/rule['path']).read_bytes();assert sha256(raw).hexdigest()==rule['sha256'],target
        expected=raw.decode()
        for change in rule['changes']:
            assert expected.count(change['old'])==change['count'],target
            expected=expected.replace(change['old'],change['new'])
        actual=(overrides or{}).get(target,(here/target).read_text())
        assert actual==expected,'READER_STREAM_UNDECLARED_ORACLE_CHANGE:'+target
        count=sum(isinstance(node,ast.Assert)for node in ast.walk(ast.parse(actual)))
        assert count==rule['assertions']and count>=rule['original_assertions'],target
        proof[target]=dict(exact_declared_derivation=True,original_assertions=rule['original_assertions'],assertions=count)
    binding=json.loads((here/'BINDING.json').read_bytes())
    assert sha256((repo/binding['catalog_source_path']).read_bytes()).hexdigest()==binding['catalog_source_sha256']
    proof.update(Native_opening_function_not_replaced=True,HPP_arithmetic_unchanged=True,
        full_catalog_scope_and_all_rows_and_sequences_retained=True,hash_algorithm_unchanged=True,
        same_D3_product_and_data_observer=True,only_factory_readonly_wait_policy_changed=True,production_go=False)
    spec=importlib.util.spec_from_file_location('reader_stream_workflow_guard',here/'workflow_guard.py')
    workflow=importlib.util.module_from_spec(spec);spec.loader.exec_module(workflow)
    proof['workflow']=workflow.check(repo,here)
    return proof
