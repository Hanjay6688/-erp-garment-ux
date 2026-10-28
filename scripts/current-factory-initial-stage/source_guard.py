from pathlib import Path
from hashlib import sha256
import ast,importlib.util,json
def check(repo,here,*,overrides=None):
    rules=json.loads((here/'ORIGIN.json').read_bytes());proof={}
    assert (here/'BINDING.json').read_bytes()==(repo/'scripts/current-finance-factory-progress-followup-qualification/BINDING.json').read_bytes()
    for name,rule in rules.items():
        raw=(repo/rule['path']).read_bytes();assert sha256(raw).hexdigest()==rule['sha256'],name
        expected=raw.decode()
        for change in rule['changes']:
            assert expected.count(change['old'])==change['count'],name
            expected=expected.replace(change['old'],change['new'])
        actual=(overrides or{}).get(name,(here/name).read_text())
        assert actual==expected,'INITIAL_WORKER_UNDECLARED_QUALIFICATION_CHANGE:'+name
        count=sum(isinstance(n,ast.Assert)for n in ast.walk(ast.parse(actual)))
        assert count==rule['assertions']and count>=rule['original_assertions'],name
        proof[name]=dict(exact_declared_derivation=True,original_assertions=rule['original_assertions'],assertions=count)
    s=importlib.util.spec_from_file_location('initial_stage_workflow_guard',here/'workflow_guard.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
    return dict(files=proof,workflow=m.check(repo,here),unchanged_seven_groups=True,unchanged_business_oracles=True,
        complete_database_restoration_preserved=True,ordinary_limit_ms=8000,initial_private_limit_ms=16000)
