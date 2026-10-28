from pathlib import Path
from copy import deepcopy
import importlib.util,json,unittest
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
def load(name):
    s=importlib.util.spec_from_file_location('initial_test_'+name,HERE/(name+'.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
worker=load('worker');guard=load('source_guard');admission=load('admission');workflow=load('workflow_guard')
class BoundaryTests(unittest.TestCase):
    def test_complete_oracles_and_workflow_are_retained(self):
        proof=guard.check(ROOT,HERE);self.assertTrue(proof['unchanged_seven_groups'])
        rules=json.loads((HERE/'ORIGIN.json').read_bytes())
        for name in rules:
            original=(HERE/name).read_text()
            with self.subTest(name=name),self.assertRaises(AssertionError):guard.check(ROOT,HERE,overrides={name:original+'\n# undeclared mutation\n'})
    def test_no_backend_unlock_or_relaxed_limit(self):
        cfg=json.loads((HERE/'CONFIG.json').read_bytes());admission.gate(cfg)
        for key,value in [('allow_database_execution',False),('initial_statement_limit_ms',32000),('ordinary_statement_limit_ms',16000),('lock_limit_ms',0),('minimum_targets',0),('added_schedule_count',2),('production_go',True),('independent_acceptance',True)]:
            altered=deepcopy(cfg);altered[key]=value
            with self.subTest(field=key),self.assertRaises(AssertionError):admission.gate(altered)
    def test_all22_delta_rejects_authority_or_unrelated_change(self):
        groups=['functions']+['group'+str(i)for i in range(21)]
        before={g:{}for g in groups};before['functions']={k:['old','owner','acl']for k in worker.REPLACED}
        after=deepcopy(before);after['functions']={k:['new','owner','acl']for k in worker.REPLACED|worker.ADDED}
        worker.transition(before,after)
        for group,key,value in [('group0','hidden','write'),('functions',worker.STEP,['new','postgres','acl']),('functions','unexpected()',['new','owner','acl'])]:
            changed=deepcopy(after);changed[group][key]=value
            with self.subTest(group=group,key=key),self.assertRaises(AssertionError):worker.transition(before,changed)
    def test_required_restoration_and_runtime_cannot_be_replaced(self):
        expected=workflow.expected(ROOT,HERE)
        for fragment in ('probe.py','admission.py','fetch_profile.py'):
            modified=deepcopy(expected)
            candidates=[s for s in modified['jobs']['p21']['steps']if fragment in s.get('run','')and workflow.FOLDER in s.get('run','')]
            self.assertTrue(candidates);candidates[0]['run']='true'
            with self.subTest(fragment=fragment),self.assertRaises(AssertionError):workflow.check(ROOT,HERE,actual=modified)
if __name__=='__main__':unittest.main()
