"""Actual-original replay and fail-closed cumulative consumer controls."""
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch
import base64
import copy
import json
import unittest

import cumulative_runtime as current
import cumulative_fetch as fetch
import money_binding


class CumulativeRuntimeControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = (current.HERE / 'MANDOR17_PARENT_ROOT_ACTUAL_INTAKE.json').read_bytes()
        cls.money = (current.ROOT / 'scripts/current-sku-money-composite-preparation/SKU_MONEY_PREPARED_SOURCE_INTAKE.json').read_bytes()
        cls.plan = (current.HERE / 'PREPARED_NATIVE25_PLAN.json').read_bytes()
        cls.observed = (current.HERE / current.OBSERVATION).read_bytes()
        cls.archives = (current.HERE / current.ORIGINALS).read_bytes()
        cls.decision = current.prepare(cls.root, cls.observed, cls.archives, cls.money, cls.plan)

    def test_actual_originals_replay_all_17_without_promoting_failed_run(self):
        value = current.review_files(self.root, self.money, self.plan)
        self.assertEqual(value, self.decision)
        self.assertEqual(len({row['case_id'] for row in value['cases']}), 17)
        self.assertEqual(value['original_run']['conclusion'], 'failure')
        self.assertEqual(value['paired_browser_run']['conclusion'], 'success')
        self.assertFalse(value['source_only_root_alone_can_admit_runtime'])
        self.assertFalse(value['independent_acceptance'])
        self.assertEqual(value['actual_SKU_cases'], 0)

    def test_original_root_graph_and_archive_substitution_refuse(self):
        for index in range(5):
            raw = [self.root, self.observed, self.archives, self.money, self.plan]
            if index == 0:
                value = json.loads(raw[index]);value['cumulative_evidence']['original_run']['conclusion'] = 'success'
                raw[index] = current.parent.canonical(value)
            elif index == 2:
                value = json.loads(raw[index]);name = next(iter(value))
                value[name] = base64.b64encode(base64.b64decode(value[name]) + b'changed').decode()
                raw[index] = json.dumps(value).encode()
            elif index == 4:
                # A changed plan changes the explicit five-gate binding and
                # cannot reproduce the already recorded decision.
                altered = current.prepare(*raw[:4], self.plan + b' ')
                self.assertNotEqual(altered, self.decision)
                continue
            else:
                raw[index] += b' '
            with self.subTest(input=index), self.assertRaises(ValueError):
                current.prepare(*raw)

    def test_source_root_and_partial_gates_cannot_admit_any_source_read(self):
        gates = money_binding.admission
        for name in (None, *gates.GATES):
            with self.subTest(gate=name), ExitStack() as stack:
                if name:
                    stack.enter_context(patch.object(gates, name, self.decision['bindings'][name]))
                stack.enter_context(patch.object(current, 'regular', side_effect=AssertionError('read before admission')))
                with self.assertRaisesRegex(ValueError, 'FULL_NATIVE_LIFECYCLE_PENDING'):
                    current.validate_actual(gates, self.root, self.money, self.plan)

    def test_complete_explicit_binding_keeps_exact_observed_money_source(self):
        with patch.multiple(money_binding.admission, **self.decision['bindings']):
            bridge, proof = money_binding.bind(self.root, self.money, self.plan)
            observed = json.loads(self.observed)
            self.assertEqual(proof['private_bound_source'], observed['private_money_binding']['private_bound_source'])
            self.assertEqual(proof['retained_closed_source'], observed['private_money_binding']['retained_closed_source'])
            self.assertEqual(proof['owning_cumulative_qualification_decision']['mode'], 'CUMULATIVE_15_PLUS_2')
            self.assertEqual(bridge.admission.PARENT_HEAD, self.decision['backend_source']['head'])

    def test_missing_decision_cannot_be_replaced_with_the_source_root(self):
        read = current.regular
        def substitute(path):
            return self.root if path.name == current.DECISION else read(path)
        with patch.multiple(money_binding.admission, **self.decision['bindings']), patch.object(current, 'regular', substitute):
            with self.assertRaisesRegex(ValueError, 'EXPLICIT_QUALIFICATION_DECISION'):
                current.validate_actual(money_binding.admission, self.root, self.money, self.plan)

    def test_wrong_graph_binding_refuses_even_with_four_other_values_present(self):
        changed = copy.deepcopy(self.decision['bindings'])
        changed['CURRENT_MONEY_GRAPH_PIN']['sha256'] = '0' * 64
        with patch.multiple(money_binding.admission, **changed):
            with self.assertRaisesRegex(ValueError, 'ALL_FIVE_ACTUAL_BINDINGS'):
                current.validate_actual(money_binding.admission, self.root, self.money, self.plan)

    def test_fetch_inventory_uses_three_raw_originals_and_exact_archive_reader(self):
        value = fetch.inventory(current, self.archives)
        self.assertEqual(set(value), {13708219308, 13713240322, 13712124308, 13741144096})
        self.assertEqual(value[13741144096]['run'], 42770344036)
        for row in value.values():
            self.assertEqual(current.parent.pin(row['raw']), row['pin'])


if __name__ == '__main__':
    unittest.main()
