from unittest import TestCase,main
import waiting


class Clock:
    def __init__(self):self.t=0
    def now(self):return self.t
    def pause(self,n):self.t+=n


class Cursor:
    def __init__(self,clock,job,finance=None):self.clock=clock;self.job=job;self.finance=finance;self.query=None;self.calls=[]
    def execute(self,query,args):
        assert query.lstrip().startswith('select '),'WATCH_MUST_REMAIN_READ_ONLY'
        self.query=query;self.calls.append(query);return self
    def fetchall(self):return self.job(self.clock.t)
    def fetchone(self):return self.finance(self.clock.t)if self.finance else('READY',7,7,None)


def rows(t,finish=420):
    done=min(int(t//4),97);state='DONE'if t>=finish else'RUNNING'
    return[(key,state,97 if state=='DONE'else done,97,True,0,None)for key in('a','b')]


class RealProgressQualificationWatch(TestCase):
    def run_watch(self,job=rows,**limits):
        clock=Clock();cursor=Cursor(clock,job);report={}
        result=waiting.observe(cursor,['a','b'],'capture',report,now=clock.now,pause=clock.pause,**limits)
        return result,report,cursor

    def test_progress_beyond_300_is_not_completion_and_waits_for_both_real_done(self):
        result,report,cursor=self.run_watch()
        proof=report['factory_progress_observation']
        self.assertEqual(result,([('a','DONE'),('b','DONE')],'READY'))
        self.assertEqual(proof['elapsed_seconds'],420)
        self.assertTrue(proof['extended_past_legacy_limit'])
        self.assertEqual(proof['legacy_cutoff_observation']['jobs']['a'][0],'RUNNING')
        self.assertTrue(all(query.startswith('select ')for query in cursor.calls))

    def test_one_finished_job_cannot_hide_another_stalled_job(self):
        job=lambda t:[('a','DONE',97,97,True,0,None),('b','RUNNING',86,97,True,0,None)]
        with self.assertRaisesRegex(AssertionError,'NO_PROGRESS_LIMIT'):self.run_watch(job)

    def test_continued_progress_still_has_a_finite_total_limit(self):
        job=lambda t:[(key,'RUNNING',int(t),10000,True,0,None)for key in('a','b')]
        with self.assertRaisesRegex(AssertionError,'TOTAL_OBSERVATION_LIMIT'):self.run_watch(job,total=360)

    def test_completion_at_or_after_total_limit_is_not_relabelled_within_budget(self):
        job=lambda t:rows(t,finish=10)
        with self.assertRaisesRegex(AssertionError,'TOTAL_OBSERVATION_LIMIT'):self.run_watch(job,total=10)

    def test_failed_job_or_missing_job_is_never_reported_done(self):
        for job,reason in ((lambda t:[('a','FAILED',40,97,True,1,'FAILED'),('b','DONE',97,97,True,0,None)],'TERMINAL_FAILURE'),
            (lambda t:[('a','DONE',97,97,True,0,None)],'EXPECTED_TWO_JOBS')):
            with self.subTest(reason=reason),self.assertRaisesRegex(AssertionError,reason):self.run_watch(job)

    def test_regressing_progress_is_refused(self):
        job=lambda t:[(key,'RUNNING',20 if t==0 else 19,97,True,0,None)for key in('a','b')]
        with self.assertRaisesRegex(AssertionError,'COUNTER_REGRESSED'):self.run_watch(job)


if __name__=='__main__':main()
