import importlib.util,unittest
from pathlib import Path
Q=Path(__file__).resolve().parent
def load(name):
    s=importlib.util.spec_from_file_location(name,Q/(name+'.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
live=load('heartbeat')
class Controls(unittest.TestCase):
    def job(self,key,active=True,state='DONE'):
        return dict(request_id=key,state=state,run_id='same-run-'+key,server_runner=dict(active=active,last_tick_at='2026-10-28T10:32:45+00:00'))
    def test_both_live_and_later_expiry_does_not_rewrite_first_observation(self):
        report={};calls=[]
        def status(cur,key):calls.append(key);return self.job(key)
        result=live.capture(None,['a','b'],status,report)
        after=self.job('a',False)
        self.assertFalse(after['server_runner']['active']);self.assertEqual(calls,['a','b'])
        self.assertTrue(result['jobs']['a']['server_runner']['active']);self.assertEqual(result['status'],'PASS')
    def test_inactive_during_live_phase_refused_and_preserved(self):
        report={}
        with self.assertRaisesRegex(AssertionError,'INACTIVE_WHILE_SCHEDULED'):
            live.capture(None,['a','b'],lambda cur,key:self.job(key,False),report)
        self.assertFalse(report['live_runner_observation']['jobs']['a']['server_runner']['active'])
    def test_not_terminal_refused(self):
        with self.assertRaisesRegex(AssertionError,'NOT_DONE'):
            live.capture(None,['a','b'],lambda cur,key:self.job(key,state='RUNNING'),{})
    def test_wrong_uuid_refused(self):
        with self.assertRaisesRegex(AssertionError,'REQUEST_MISMATCH'):
            live.capture(None,['a','b'],lambda cur,key:self.job('other'),{})
    def test_exact_derivation_and_oracle_tamper_refused(self):
        guard=load('source_guard');root=Q.parents[1]
        guard.check(root,Q)
        source=(Q/'factory.py').read_text().replace("assert len(wanted)==24","assert len(wanted)>=1")
        with self.assertRaisesRegex(AssertionError,'UNDECLARED_FACTORY_OBSERVER_CHANGE'):
            guard.check(root,Q,overrides={'factory.py':source})
if __name__=='__main__':unittest.main()
