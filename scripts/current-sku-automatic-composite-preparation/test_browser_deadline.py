from pathlib import Path
from unittest.mock import patch
import importlib.util
import signal
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('actual_browser_deadline_controls', HERE / 'browser_deadline.py')
deadline = importlib.util.module_from_spec(spec); spec.loader.exec_module(deadline)


class BrowserDeadlineControls(unittest.TestCase):
    def test_source_and_operation_have_separate_preserved_budgets(self):
        original = signal.getsignal(signal.SIGALRM)
        for phase, seconds in (('SOURCE', 180), ('OPERATION', 120)):
            with patch.object(signal, 'setitimer') as timer:
                with deadline.phase(phase):
                    timer.assert_called_once_with(signal.ITIMER_REAL, seconds)
                self.assertEqual(timer.call_args.args, (signal.ITIMER_REAL, 0))
            self.assertIs(signal.getsignal(signal.SIGALRM), original)

    def test_timeout_remains_failure_and_restores_handler(self):
        original = signal.getsignal(signal.SIGALRM)
        with patch.object(signal, 'setitimer') as timer:
            with self.assertRaisesRegex(TimeoutError, 'OPERATION_DEADLINE_EXCEEDED'):
                with deadline.phase('OPERATION'):
                    signal.getsignal(signal.SIGALRM)(signal.SIGALRM, None)
            self.assertEqual(timer.call_args.args, (signal.ITIMER_REAL, 0))
        self.assertIs(signal.getsignal(signal.SIGALRM), original)

    def test_unknown_phase_and_existing_timer_are_refused(self):
        with self.assertRaisesRegex(ValueError, 'FIXED_BROWSER_DEADLINE_PHASE'):
            with deadline.phase('OTHER'): pass
        with patch.object(signal, 'getitimer', return_value=(10.0, 0.0)):
            with self.assertRaisesRegex(ValueError, 'PREEXISTING_DEADLINE'):
                with deadline.phase('SOURCE'): pass

    def test_node_total_does_not_replace_python_operation_limit(self):
        text = (HERE / 'browser.mjs').read_text()
        self.assertIn('SOURCE_ADMISSION_TIMEOUT_MS=180000,NATIVE_OPERATION_TIMEOUT_MS=120000,FIXTURE_CLEANUP_TIMEOUT_MS=5000', text)
        self.assertIn('timeout:SOURCE_ADMISSION_TIMEOUT_MS+NATIVE_OPERATION_TIMEOUT_MS+FIXTURE_CLEANUP_TIMEOUT_MS', text)
        source = (HERE / 'browser_fixture.py').read_text()
        self.assertIn("with deadline.phase('SOURCE'):", source)
        self.assertIn("with binding.arguments(values), deadline.phase('OPERATION'):", source)


if __name__ == '__main__': unittest.main()
