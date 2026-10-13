"""The group-end/per-case difference detail of cp6_auditor_runner (diagnosis only; it never decides a result)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cp6_auditor_runner as runner  # noqa: E402

FUNCTIONS = [['public.a(uuid)', '1'], ['public.b()', '2'], ['public.c(text)', '3']]
BOUNDARY = dict(erp={'x': dict(count=1, sha256='a'), 'y': dict(count=0, sha256='b')}, platform=[1, 2], auth=[], schemas=[['erp', 'acl']])
PUBLIC = dict(relations=[['t', 'r']], functions=FUNCTIONS, rows={'t': '0:'})


class StateDifference(unittest.TestCase):
    def test_equal_states_have_no_difference(self):
        self.assertEqual(runner.state_difference(BOUNDARY, dict(BOUNDARY), PUBLIC, dict(PUBLIC)), {})

    def test_reordered_function_listing_is_order_only(self):
        after = dict(PUBLIC, functions=[FUNCTIONS[1], FUNCTIONS[0], FUNCTIONS[2]])
        self.assertNotEqual(after, PUBLIC)
        d = runner.state_difference(BOUNDARY, BOUNDARY, PUBLIC, after)
        self.assertEqual(list(d), ['public.functions'])
        self.assertEqual((d['public.functions']['kind'], d['public.functions']['first_difference_at']), ('ORDER_ONLY', 0))

    def test_changed_function_is_content(self):
        after = dict(PUBLIC, functions=[FUNCTIONS[0], ['public.b()', '9'], FUNCTIONS[2]])
        d = runner.state_difference(BOUNDARY, BOUNDARY, PUBLIC, after)['public.functions']
        self.assertEqual((d['kind'], d['removed'], d['added']), ('CONTENT', ['["public.b()", "2"]'], ['["public.b()", "9"]']))

    def test_erp_table_and_public_rows_are_named(self):
        b_after = dict(BOUNDARY, erp={'x': dict(count=2, sha256='c'), 'y': BOUNDARY['erp']['y']})
        p_after = dict(PUBLIC, rows={'t': '1:z'})
        d = runner.state_difference(BOUNDARY, b_after, PUBLIC, p_after)
        self.assertEqual(d, {'boundary.erp': ['x'], 'public.rows': ['t']})

    def test_auth_rows_reordered_or_added(self):
        before = dict(BOUNDARY, auth=[{'id': 1}, {'id': 2}])
        self.assertEqual(runner.state_difference(before, dict(before, auth=[{'id': 2}, {'id': 1}]), PUBLIC, PUBLIC),
                         {'boundary.auth': 'ORDER_ONLY'})
        self.assertEqual(runner.state_difference(before, dict(before, auth=[{'id': 1}]), PUBLIC, PUBLIC),
                         {'boundary.auth': dict(before_count=2, after_count=1)})


if __name__ == '__main__':
    unittest.main()
