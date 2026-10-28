from copy import deepcopy
from unittest import TestCase,main
import evidence


def completed():
    frames=[]
    for at,done in ((0,0),(100,20),(200,40),(300,60),(400,80),(450,97)):
        state='DONE'if at==450 else'RUNNING'
        frames.append(dict(elapsed_seconds=at,jobs={'one':[state,done,97,True],
            'two':[state,done,97,True],'finance':['READY',2,2]}))
    return dict(status='TERMINAL_DONE_AND_READY',read_only=True,qualification_observation_only=True,
        actual_terminal_states_observed=True,total_limit_seconds=900,no_progress_limit_seconds=150,
        legacy_limit_seconds=300,elapsed_seconds=450,manual_steps=0,minute_schedule_changed=False,
        ordinary_statement_limits_changed=False,observed_job_states={'one':'DONE','two':'DONE'},
        observed_finance_state='READY',frames=frames,extended_past_legacy_limit=True,
        legacy_cutoff_observation=deepcopy(frames[3]))


class FactoryProgressAdmission(TestCase):
    def test_long_analysis_requires_actual_terminal_state(self):
        result=evidence.require_factory_progress(completed())
        self.assertEqual(result['status'],'PASS_TERMINAL_FACTORY_PROGRESS')
        self.assertTrue(result['extended_past_300'])

    def test_progress_alone_or_incomplete_watch_does_not_unlock(self):
        for changes in ({'status':'NO_PROGRESS_LIMIT'},{'actual_terminal_states_observed':False},
            {'observed_job_states':{'one':'DONE','two':'RUNNING'}},{'observed_finance_state':'RUNNING'}):
            proof=completed();proof.update(changes)
            with self.subTest(changes=changes),self.assertRaises(AssertionError):evidence.require_factory_progress(proof)

    def test_deadline_and_original_schedule_remain_bounded(self):
        for changes in ({'elapsed_seconds':900},{'total_limit_seconds':1800},
            {'no_progress_limit_seconds':300},{'manual_steps':1},{'read_only':False},
            {'minute_schedule_changed':True},{'ordinary_statement_limits_changed':True}):
            proof=completed();proof.update(changes)
            with self.subTest(changes=changes),self.assertRaises(AssertionError):evidence.require_factory_progress(proof)

    def test_regressing_or_missing_member_refuses(self):
        proof=completed();proof['frames'][2]['jobs']['one'][1]=10
        with self.assertRaises(AssertionError):evidence.require_factory_progress(proof)
        proof=completed();del proof['frames'][2]['jobs']['two']
        with self.assertRaises(AssertionError):evidence.require_factory_progress(proof)

    def test_financial_completion_cannot_certify_jobs(self):
        proof=completed();proof['frames'][-1]['jobs']['two'][0]='RUNNING'
        with self.assertRaises(AssertionError):evidence.require_factory_progress(proof)

    def test_legacy_cutoff_and_frame_deadline_are_observed(self):
        proof=completed();proof['legacy_cutoff_observation']['elapsed_seconds']=299
        with self.assertRaises(AssertionError):evidence.require_factory_progress(proof)
        proof=completed();proof['frames'][-1]['elapsed_seconds']=900
        with self.assertRaises(AssertionError):evidence.require_factory_progress(proof)


if __name__=='__main__':main()
