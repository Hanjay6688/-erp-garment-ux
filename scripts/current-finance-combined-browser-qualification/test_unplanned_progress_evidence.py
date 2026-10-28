from unittest import TestCase,main
from test_factory_progress_evidence import completed
import evidence

class UnplannedProgressEvidence(TestCase):
    def test_unknown_total_is_preserved_before_plan_and_ready(self):
        p=completed();p['frames'][0]['jobs']['finance']=['RUNNING',0,None]
        self.assertEqual(evidence.require_factory_progress(p)['status'],'PASS_TERMINAL_FACTORY_PROGRESS')

    def test_invalid_unknown_and_false_ready_are_refused(self):
        for row in (['READY',0,None],['RUNNING',1,None],['RUNNING',None,None],['READY',1,2]):
            p=completed();p['frames'][0]['jobs']['finance']=row
            with self.subTest(row=row),self.assertRaises(AssertionError):evidence.require_factory_progress(p)

    def test_known_plan_cannot_return_to_unknown(self):
        p=completed();p['frames'][1]['jobs']['finance']=['RUNNING',0,None]
        with self.assertRaises(AssertionError):evidence.require_factory_progress(p)

if __name__=='__main__':main()
