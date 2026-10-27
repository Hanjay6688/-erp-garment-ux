"""Timing must neither alter an operation nor swallow its original failure."""
import contextlib
import io
import json
import unittest
from unittest.mock import patch
from phase_timing import measured


class PhaseTiming(unittest.TestCase):
    def test_completion_preserves_return_and_actual_order(self):
        trail, output, calls = [], io.StringIO(), []
        sentinel = object()
        def work(value, *, named):
            self.assertEqual(trail[0]['state'], 'RUNNING')
            self.assertEqual((value, named), (3, 4))
            calls.append('executed')
            return sentinel
        with contextlib.redirect_stdout(output):
            self.assertIs(measured(trail, 'INSTALL', work, 3, named=4), sentinel)
        rows = [json.loads(line) for line in output.getvalue().splitlines()]
        self.assertEqual(calls, ['executed'])
        self.assertEqual([row['state'] for row in rows], ['RUNNING', 'COMPLETED'])
        self.assertGreaterEqual(trail[0]['elapsed_ms'], 0)
        self.assertFalse(any('percent' in key or 'overall' in key for row in rows for key in row))

    def test_failure_is_same_exception_and_cleanup_remains_possible(self):
        trail, output, calls = [], io.StringIO(), []
        error = RuntimeError('original refusal')
        def fail():
            raise error
        with contextlib.redirect_stdout(output):
            with self.assertRaises(RuntimeError) as observed:
                try:
                    measured(trail, 'CASE', fail)
                finally:
                    calls.append('cleanup')
        self.assertIs(observed.exception, error)
        self.assertEqual(calls, ['cleanup'])
        self.assertEqual(trail[0]['state'], 'FAILED')
        self.assertEqual(json.loads(output.getvalue().splitlines()[-1])['error_type'], 'RuntimeError')

    def test_interrupt_is_recorded_then_propagated(self):
        trail = []
        def stop():
            raise KeyboardInterrupt()
        with contextlib.redirect_stdout(io.StringIO()), self.assertRaises(KeyboardInterrupt):
            measured(trail, 'SOURCE_ADMISSION', stop)
        self.assertEqual(trail[0]['state'], 'FAILED')

    def test_log_sink_failure_does_not_replace_business_failure(self):
        trail = []
        original = ValueError('original business refusal')
        def fail():
            raise original
        with patch('builtins.print', side_effect=OSError('log unavailable')):
            with self.assertRaises(ValueError) as observed:
                measured(trail, 'CASE', fail)
        self.assertIs(observed.exception, original)
        self.assertEqual(trail[0]['state'], 'FAILED')

    def test_log_sink_failure_does_not_skip_the_operation(self):
        calls, trail = [], []
        with patch('builtins.print', side_effect=OSError('log unavailable')):
            self.assertEqual(measured(trail, 'RESTORE', lambda: calls.append('restored') or 7), 7)
        self.assertEqual(calls, ['restored'])
        self.assertEqual(trail[0]['state'], 'COMPLETED')


if __name__ == '__main__':
    unittest.main()
