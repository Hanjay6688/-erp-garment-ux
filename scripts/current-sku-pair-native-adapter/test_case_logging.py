"""Regression for the exact result envelope that stopped Native805 diagnostics.

This evaluates only the inverse case's metadata return. No Native execution or
database qualification is claimed by this test.
"""
from pathlib import Path
import ast
import unittest

ROOT = Path(__file__).resolve().parents[2]


class CaseLoggingTests(unittest.TestCase):
    def test_actual_inverse_result_can_be_logged_by_unchanged_strict_runner(self):
        tree = ast.parse((ROOT / 'scripts/current-sku-pair-conversion-qualification/cases.py').read_text())
        function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'inverse')
        expression = next(n.value for n in function.body if isinstance(n, ast.Return))
        row = eval(compile(ast.Expression(expression), '<inverse-case-result>', 'eval'), {},
                   dict(made={'conversion_id': 'synthetic-group-id'}, refusal={}, direct={}, blocked_new=[2]))
        logged = dict(group='SYNTHETIC_LOGGER_GROUP', case='INVERSE', **row)
        self.assertEqual(logged['group'], 'SYNTHETIC_LOGGER_GROUP')
        self.assertEqual(logged['conversion_group_id'], 'synthetic-group-id')
        # The old result did reach the original logger with a conflicting key.
        before = dict(row)
        before['group'] = before.pop('conversion_group_id')
        with self.assertRaises(TypeError):
            dict(group='SYNTHETIC_LOGGER_GROUP', case='INVERSE', **before)


if __name__ == '__main__':
    unittest.main()
