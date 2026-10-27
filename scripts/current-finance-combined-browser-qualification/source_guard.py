"""Preserve the exact UI/fixture oracles and the two-copy real-Auth boundaries."""
from hashlib import sha256
import ast,importlib.util,json,subprocess

B_HEAD='1dd83782dcaa4500bace7bf392a76f58be0271c3'


def check(repo,here,*,overrides=None):
    rules=json.loads((here/'UI_ORIGIN.json').read_bytes());proof={}
    for target,rule in rules.items():
        raw=(repo/rule['path']).read_bytes()
        assert sha256(raw).hexdigest()==rule['sha256'],'COMBINED_UI_PARENT_CHANGED:'+target
        expected=raw.decode()
        for change in rule['changes']:
            assert expected.count(change['old'])==change['count']
            expected=expected.replace(change['old'],change['new'])
        actual=(overrides or{}).get(target,(here/target).read_text())
        assert actual==expected,'COMBINED_UI_UNDECLARED_ORACLE_CHANGE:'+target
        if target.endswith('.py'):
            assertions=sum(isinstance(node,ast.Assert)for node in ast.walk(ast.parse(actual)))
            if 'assertions'in rule:assert assertions==rule['assertions']
        proof[target]=dict(exact_declared_derivation=True,original_business_oracles_unchanged=True)
    old=repo/'scripts/current-progress-finance-ui-browser-qualification'
    spec=importlib.util.spec_from_file_location('combined_UI_exact_old_host_guards',old/'source_guard.py')
    guard=importlib.util.module_from_spec(spec);spec.loader.exec_module(guard)
    proof['original_host_and_business_guards']=guard.check(repo,old)
    host=repo/'scripts/cp7_current_progress_finance_ui'
    B=json.loads((host/'B_SOURCE.json').read_bytes());assert len(B['files'])==91
    for entry in B['files']:
        raw=(host/entry['vendored_path']).read_bytes()
        assert len(raw)==entry['bytes']and sha256(raw).hexdigest()==entry['sha256']
        target=subprocess.check_output(['git','-C',str(repo),'show',B_HEAD+':'+entry['path']])
        assert target==raw,'COMBINED_UI_CURRENT_B_SOURCE_CHANGED:'+entry['path']
    proof.update(host_exact_files=113,current_B_head=B_HEAD,current_B_exact_files=91,
        real_Auth_and_two_complete_copies_unchanged=True,actual_browser_executed=False)
    return proof
