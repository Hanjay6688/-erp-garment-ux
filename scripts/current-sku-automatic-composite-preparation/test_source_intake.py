"""Closed source-intake controls; no actual Mandor Root or ERP execution."""
from pathlib import Path
from unittest.mock import patch
import importlib.util
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('automatic_graph_intake_control', HERE / 'source_intake.py')
intake = importlib.util.module_from_spec(spec)
spec.loader.exec_module(intake)


class SourceIntakeControls(unittest.TestCase):
    def test_all_five_financial_gates_must_remain_closed_before_any_input_read(self):
        gates = intake.entry.admission
        for name in gates.GATES:
            with self.subTest(name=name), patch.object(gates, name, 'EXPLICIT_CONTROL_ONLY'), \
                    patch.object(Path, 'is_file', side_effect=AssertionError('Input inspected')):
                with self.assertRaisesRegex(ValueError, 'REQUIRES_ALL_FIVE_FINANCIAL_GATES_CLOSED'):
                    intake.inputs(dict(bytes=1, sha256='0' * 64))

    def test_exact_reviewed_parent_pin_precedes_any_input_inspection(self):
        for expected in (None, {}, dict(bytes=0, sha256='0' * 64), dict(bytes=True, sha256='0' * 64),
                         dict(bytes=1, sha256='unreviewed'), dict(bytes=1, sha256='0' * 64, extra=True)):
            with self.subTest(expected=expected), patch.object(Path, 'is_file', side_effect=AssertionError('Input inspected')):
                with self.assertRaisesRegex(ValueError, 'EXACT_REVIEWED_ACTUAL_PARENT_PIN_REQUIRED'):
                    intake.inputs(expected)

    def test_no_genuine_parent_original_refuses_before_frozen_or_ERP_inspection(self):
        with patch.object(Path, 'is_file', return_value=False), \
                patch.object(intake.entry, 'frozen', side_effect=AssertionError('Frozen source inspected')), \
                patch.object(intake.entry, 'load', side_effect=AssertionError('Runtime inspected')):
            with self.assertRaisesRegex(ValueError, 'GENUINE_REGULAR_INPUT_ORIGINAL_REQUIRED'):
                intake.observe(dict(bytes=1, sha256='0' * 64))

    def test_shared_private_bridge_calls_validator_before_loading_any_retained_source(self):
        binding = intake.entry.money_binding
        def refused():
            raise ValueError('EXPLICIT_SOURCE_VALIDATOR_REFUSED')
        with patch.object(binding, 'load', side_effect=AssertionError('Retained source inspected')):
            with self.assertRaisesRegex(ValueError, 'EXPLICIT_SOURCE_VALIDATOR_REFUSED'):
                binding._private_bridge(object(), object(), refused)
            with self.assertRaisesRegex(ValueError, 'FULL_NATIVE_LIFECYCLE_PENDING'):
                binding.bind(object(), object(), object())


if __name__ == '__main__':
    unittest.main()
