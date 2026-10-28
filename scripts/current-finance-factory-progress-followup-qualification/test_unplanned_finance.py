"""Respect the stored pre-report NULL total, never invent completion or progress."""
from unittest import TestCase,main
from test_waiting import Clock,Cursor,rows
import waiting

class UnplannedFinanceCounter(TestCase):
    def run_watch(self,finance,**limits):
        clock=Clock();report={};cursor=Cursor(clock,lambda t:rows(t,finish=120),finance)
        result=waiting.observe(cursor,['a','b'],'capture',report,now=clock.now,pause=clock.pause,**limits)
        return result,report,cursor

    def test_real_capture_starts_unplanned_and_becomes_ready(self):
        finance=lambda t:('RUNNING',0,None,None)if t<40 else(('RUNNING',1,7,None)if t<80 else('READY',7,7,None))
        result,report,cursor=self.run_watch(finance)
        self.assertEqual(result,([('a','DONE'),('b','DONE')],'READY'))
        frames=report['factory_progress_observation']['frames']
        self.assertEqual(frames[0]['jobs']['finance'],['RUNNING',0,None])
        self.assertEqual(report['factory_progress_observation']['elapsed_seconds'],120)
        self.assertTrue(all(q.startswith('select ')for q in cursor.calls))

    def test_unplanned_capture_still_stalls_at_original_limit(self):
        with self.assertRaisesRegex(AssertionError,'NO_PROGRESS_LIMIT'):
            self.run_watch(lambda t:('RUNNING',0,None,None))

    def test_invalid_unplanned_or_terminal_counters_are_refused(self):
        for row in [('READY',0,None,None),('RUNNING',1,None,None),('RUNNING',None,None,None),
                    ('RUNNING',-1,None,None),('RUNNING',True,None,None),('RUNNING',0,1,None),
                    ('READY',6,7,None),('RUNNING',8,7,None),('RUNNING',0,'7',None)]:
            with self.subTest(row=row),self.assertRaisesRegex(AssertionError,'FINANCE_COUNTER_INVALID'):
                self.run_watch(lambda t:row)

    def test_known_finance_plan_cannot_regress_to_unknown(self):
        with self.assertRaisesRegex(AssertionError,'FINANCE_PLAN_CHANGED'):
            self.run_watch(lambda t:('RUNNING',0,7,None)if t==0 else('RUNNING',0,None,None))

    def test_known_finance_plan_cannot_change(self):
        with self.assertRaisesRegex(AssertionError,'FINANCE_PLAN_CHANGED'):
            self.run_watch(lambda t:('RUNNING',1,7 if t==0 else 8,None))

    def test_finance_done_counter_cannot_regress(self):
        with self.assertRaisesRegex(AssertionError,'COUNTER_REGRESSED'):
            self.run_watch(lambda t:('RUNNING',2 if t==0 else 1,7,None))

    def test_finance_failure_still_refuses_completion(self):
        with self.assertRaisesRegex(AssertionError,'FINANCE_TERMINAL_FAILURE'):
            self.run_watch(lambda t:('FAILED',0,None,'failure'))

if __name__=='__main__':main()
