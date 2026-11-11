from pathlib import Path
from unittest.mock import patch
import importlib.util
import signal
import time
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('actual_browser_deadline_controls', HERE / 'browser_deadline.py')
deadline = importlib.util.module_from_spec(spec); spec.loader.exec_module(deadline)


class BrowserDeadlineControls(unittest.TestCase):
    def test_source_and_operation_have_separate_preserved_budgets(self):
        original = signal.getsignal(signal.SIGALRM)
        for phase, seconds in (('SOURCE', 360), ('OPERATION', 120)):
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
        self.assertIn('SOURCE_ADMISSION_TIMEOUT_MS=360000,NATIVE_OPERATION_TIMEOUT_MS=120000,FIXTURE_CLEANUP_TIMEOUT_MS=5000', text)
        self.assertIn('timeout:SOURCE_ADMISSION_TIMEOUT_MS+NATIVE_OPERATION_TIMEOUT_MS+FIXTURE_CLEANUP_TIMEOUT_MS', text)
        source = (HERE / 'browser_fixture.py').read_text()
        self.assertIn("with deadline.phase('SOURCE'):", source)
        self.assertIn("with binding.arguments(values), deadline.phase('OPERATION'):", source)


    def test_real_source_expiry_refuses_and_disarms_without_changing_operation_budget(self):
        previous = signal.getsignal(signal.SIGALRM)
        with patch.object(deadline, 'SOURCE_SECONDS', 0.02):
            with self.assertRaisesRegex(TimeoutError, 'SOURCE_DEADLINE_EXCEEDED'):
                with deadline.phase('SOURCE'):
                    time.sleep(0.25)
        self.assertEqual(signal.getitimer(signal.ITIMER_REAL), (0.0, 0.0))
        self.assertIs(signal.getsignal(signal.SIGALRM), previous)
        self.assertEqual(deadline.OPERATION_SECONDS, 120)

    def test_generated_browser_uses_the_same_policy_and_parent_cleanup_margin(self):
        spec = importlib.util.spec_from_file_location('tested_browser_deadline_generator', HERE / 'browser_prepare.py')
        prepare = importlib.util.module_from_spec(spec); spec.loader.exec_module(prepare)
        text, proof = prepare.derive()
        self.assertEqual(text, (HERE / 'browser.mjs').read_text())
        self.assertEqual(proof['cold_source_budget_seconds'], deadline.SOURCE_SECONDS)
        self.assertEqual(proof['unchanged_Native_operation_budget_seconds'], 120)
        self.assertIn('maxBuffer:128*1024*1024,timeout:SOURCE_ADMISSION_TIMEOUT_MS+FIXTURE_CLEANUP_TIMEOUT_MS}', text)
        with patch.object(prepare.deadline, 'SOURCE_SECONDS', 17):
            derived, changed = prepare.derive()
        self.assertIn('SOURCE_ADMISSION_TIMEOUT_MS=17000,NATIVE_OPERATION_TIMEOUT_MS=120000', derived)
        self.assertEqual(changed['cold_source_budget_seconds'], 17)
        self.assertTrue(changed['complete_original_recovered'])

    def test_cold_source_entry_has_its_own_deadline_before_erp_or_network(self):
        spec = importlib.util.spec_from_file_location('tested_cold_source_deadline_entry', HERE / 'browser_source.py')
        source = importlib.util.module_from_spec(spec); spec.loader.exec_module(source)
        from contextlib import contextmanager
        @contextmanager
        def slow_source():
            time.sleep(0.25)
            self.fail('Expired source reached fixture binding')
            yield
        with patch.object(source.binding.entry, 'actual_inputs'), patch.object(source.binding, 'scope', slow_source), \
                patch.object(source.deadline, 'SOURCE_SECONDS', 0.02):
            with self.assertRaisesRegex(TimeoutError, 'SOURCE_DEADLINE_EXCEEDED'):
                source.check()
        self.assertEqual(signal.getitimer(signal.ITIMER_REAL), (0.0, 0.0))


if __name__ == '__main__': unittest.main()
