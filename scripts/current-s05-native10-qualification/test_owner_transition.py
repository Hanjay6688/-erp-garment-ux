"""Semantic controls over the exact original reader/acceptance boundaries."""
from pathlib import Path
import importlib.util
import unittest

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('s05_owner_transition_control',HERE/'owner_transfer/transition.py')
transition=importlib.util.module_from_spec(spec);spec.loader.exec_module(transition)


class OwnerTransitionControls(unittest.TestCase):
    def setUp(self):
        self.old=(HERE/'owner_transfer/retained/stage.py').read_text()
        self.current=(HERE.parents[1]/'scripts/cp7_accessory_standard_report/stage.py').read_text()
    def test_exact_bounded_successor(self):
        result=transition.check()
        self.assertEqual(result['report_sql_sha256'],transition.ORIGINAL_SQL)
        self.assertEqual(result['Native_executions'],0)
    def test_verify_and_catalog_oracle_cannot_be_changed(self):
        for needle in ('len(before) != 22','S05_ROLE_MEMBERSHIP','S05_NO_DIRECT_ERP_GRANTS'):
            bad=self.current.replace(needle,needle+'_MUTATED',1)
            with self.assertRaises((ValueError,SyntaxError)):
                transition.stage_transition(self.old,bad)
    def test_inherited_atomic_cannot_be_removed(self):
        bad=self.current.replace('with predecessor.atomic(cur):','with local_unqualified_atomic(cur):',1)
        with self.assertRaisesRegex(ValueError,'INHERITED_ATOMIC'):
            transition.stage_transition(self.old,bad)
    def test_new_reader_or_parent_rewrite_is_out_of_scope(self):
        with self.assertRaisesRegex(ValueError,'FUNCTION_SCOPE'):
            transition.stage_transition(self.old,self.current+'\ndef repair_posted():\n    pass\n')


if __name__=='__main__':unittest.main()
