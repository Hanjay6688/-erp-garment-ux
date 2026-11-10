"""Complete observation protocol models; no SQL connection or ERP execution."""
from pathlib import Path
import importlib.util
import unittest

spec = importlib.util.spec_from_file_location('current_economic_observer_control', Path(__file__).with_name('browser_observer.py'))
observer = importlib.util.module_from_spec(spec);spec.loader.exec_module(observer)


class ObserverControls(unittest.TestCase):
    def test_complete_original_fields_survive_with_two_pools_and_actual_session_observation(self):
        original = dict(census=dict(all22='complete opaque original'), members=[dict(full='member')], untouched=['all raw rows'])
        calls = []
        class Cursor:
            def execute(self, query, args):
                calls.append((query, args));self.product = args[0] if args else None;return self
            def fetchone(self):
                return (dict(actual_protocol_product=self.product) if self.product else
                        dict(advisory_locks=0, advisory_lock_keys=[], other_sessions=[]),)
        fixture = dict(source='SOURCE', target='TARGET', location='LOCATION')
        def retained(cur, actual_fixture, label):
            self.assertEqual(label, 'MODEL');self.assertIs(actual_fixture, fixture);return original
        result = observer.observe(retained, Cursor(), fixture, 'MODEL')
        self.assertEqual(set(result), set(original) | {'current_economic_pools', 'current_session_leaks'})
        self.assertTrue(all(result[key] is value for key, value in original.items()))
        self.assertNotIn('current_economic_pools', original)
        self.assertEqual(calls, [("select cp7_sku_conversion.pool_quote_v2(%s,%s,'GRADE_A')", (product, 'LOCATION'))
                                 for product in ('SOURCE', 'TARGET')] + [(observer.SESSION_SQL, ())])
        self.assertEqual(result['current_session_leaks'], dict(advisory_locks=0, advisory_lock_keys=[], other_sessions=[]))

    def test_conflicting_original_field_refuses_before_any_added_read(self):
        class NoCursor:
            def execute(self, *args):raise AssertionError('A conflicting Original must survive')
        with self.assertRaisesRegex(ValueError, 'MUST_NOT_REPLACE_ORIGINAL_FIELDS'):
            observer.observe(lambda *_: dict(current_economic_pools={'first': 'original'}), NoCursor(), {}, 'MODEL')

    def test_original_failure_is_preserved_before_any_added_observation(self):
        error = RuntimeError('EXPLICIT_ORIGINAL_MODEL_FAILURE')
        def retained(*args):raise error
        with self.assertRaises(RuntimeError) as caught:
            observer.observe(retained, object(), {}, 'MODEL')
        self.assertIs(caught.exception, error)


if __name__ == '__main__':unittest.main()
