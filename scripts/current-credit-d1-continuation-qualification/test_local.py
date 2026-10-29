"""Meaningful local arithmetic, dependency-gate and exact-source controls.

Synthetic group dictionaries test the gate ONLY. They are never actual Native
evidence. All actual callback imports are exercised with connection forbidden.
"""
from copy import deepcopy
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, main
from unittest.mock import patch
import importlib.util
import inspect
import json
import shutil
import sys

import psycopg

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
ORIGINAL_ARGV = sys.argv[:]
sys.dont_write_bytecode = True


def load(name, file):
    spec = importlib.util.spec_from_file_location(name, file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


with patch.object(psycopg, 'connect', side_effect=AssertionError('D1_CONT_IMPORT_ATTEMPTED_DATABASE')):
    business = load('d1_cont_local_import_under_no_database_guard', HERE/'cases.py')

oracle = business.n.oracle


def fake_native13():
    return dict(status='PASS', counts={'PASS': 13}, complete_boundary_restored=True,
                cases={name: dict(status='PASS', full_boundary_restored=True) for name in business.NATIVE13_IDS})


def fake_install():
    *_, catalog = business.n.product.runtime()
    pins = json.loads((HERE/'SOURCE.json').read_bytes())
    # product.sources() intentionally requires retained parent original packages
    # absent in this local no-database test. This synthetic predecessor tests
    # gate structure only; it is never a claim of that package's admission.
    return dict(sources=dict(contract=business.n.product.CONTRACT,
                predecessor=dict(classification='SYNTHETIC_LOCAL_GATE_ONLY'),
                files=pins['D1_runtime_files']), after={key: {} for key in catalog.QUERIES})


def admit(group=None, state=None, digest='a'*64, commit='b'*40):
    with patch.object(business.n.product, 'sources', return_value=fake_install()['sources']):
        return business.admit_native13(group if group is not None else fake_native13(),
            original_report_sha256=digest, qualified_backend_commit=commit,
            installed_state=state if state is not None else fake_install())


class Arithmetic(TestCase):
    def test_literal_states_and_added_capacity(self):
        expected = {
            'INITIAL_200': ('200.00', '200.00', '800.00', '0.00', '500.00', '1000.00'),
            'D1_250': ('250.00', '250.00', '750.00', '0.00', '500.00', '1000.00'),
            'APPLY_220': ('250.00', '30.00', '750.00', '0.00', '280.00', '1000.00'),
            'APPLY_UNDONE': ('250.00', '250.00', '750.00', '0.00', '500.00', '1000.00'),
            'REFUND_230': ('250.00', '20.00', '750.00', '0.00', '500.00', '770.00'),
            'REFUND_UNDONE': ('250.00', '250.00', '750.00', '0.00', '500.00', '1000.00'),
            'SECOND_D1_275': ('275.00', '275.00', '725.00', '0.00', '500.00', '1000.00'),
        }
        self.assertEqual(set(expected), set(oracle.GOLD))
        for stage, values in expected.items():
            row = oracle.GOLD[stage]
            self.assertEqual(tuple(row['source'][key] for key in ('I', 'available', 'net', 'AR')) + (row['target']['AR'], row['cash']), values)
        for channel, amount in (('applications', '220.00'), ('refunds', '230.00')):
            with self.assertRaisesRegex(ValueError, 'UNFUNDED'):
                oracle.profile('200.00', **{channel: (amount,)})

    def test_cash_and_target_channels_cannot_be_swapped_or_netted_together(self):
        self.assertNotEqual(oracle.profile('250.00', applications=('230.00',)), oracle.GOLD['REFUND_230'])
        self.assertNotEqual(oracle.profile('250.00', refunds=('220.00',)), oracle.GOLD['APPLY_220'])
        combined = oracle.profile('250.00', applications=('100.00', '-100.00'), refunds=('230.00',))
        self.assertEqual(combined, oracle.GOLD['REFUND_230'])
        self.assertEqual(oracle.profile('250.01', applications=('220.00',))['source']['available'], '30.01')

    def test_refuses_float_boolean_subcent_nonfinite_and_unfunded_oracle_inputs(self):
        for value in (250.0, True, '250.001', 'NaN', 'Infinity', 'bad'):
            with self.assertRaises(ValueError):
                oracle.cents(value)
        self.assertEqual(oracle.cents(Decimal('0.01')), Decimal('0.01'))
        for arguments in (dict(applications=('250.01',)), dict(refunds=('250.01',)), dict(applications=('-0.01',))):
            with self.assertRaises(ValueError):
                oracle.profile('250.00', **arguments)

    def test_named_signed_history_controls(self):
        original = dict(consumption_event_id='original')
        undo = dict(consumption_event_id='inverse', action='UNDO', restores_event_id='original', amount='-220.00')
        history = dict(events=dict(document=[dict(id='original', event_kind='APPLY', amount='220.00', restores_event_id=None),
                                               dict(id='inverse', event_kind='APPLY', amount='-220.00', restores_event_id='original')]),
                       operations=dict(document=[{}, {}]), completions=dict(document=[{}, {}]))
        business.assert_signed_history(history, original, undo, 'APPLY', '220.00')
        for key, value in (('amount', '-219.99'), ('restores_event_id', 'other')):
            wrong = deepcopy(history)
            wrong['events']['document'][1][key] = value
            with self.assertRaises(AssertionError):
                business.assert_signed_history(wrong, original, undo, 'APPLY', '220.00')
        old = dict(document=[dict(id='old', qty_signed=1)])
        business.old_movements_retained(old, dict(document=[*old['document'], dict(id='inverse'), dict(id='replacement')]), 2)
        with self.assertRaises(AssertionError):
            business.old_movements_retained(old, dict(document=[dict(id='old', qty_signed=2), dict(id='inverse'), dict(id='replacement')]), 2)


class Gate(TestCase):
    def setUp(self):
        business.ADMISSION, business.INSTALLED_STATE = None, None

    def tearDown(self):
        business.ADMISSION, business.INSTALLED_STATE = None, None

    def test_unadmitted_callbacks_refuse_before_any_database_or_fixture(self):
        with self.assertRaisesRegex(AssertionError, 'REQUIRES_PRIOR_ACTUAL_NATIVE13_PASS_ON_OWNING_REPAIRED_STAGE'):
            business.cases(None, None)

    def test_rejects_failure_missing_case_and_incomplete_restoration(self):
        controls = []
        for key, value in (('status', 'FAIL'), ('counts', {'PASS': 12, 'FAIL': 1}),
                           ('complete_boundary_restored', False), ('error', 'original owning install failed')):
            control = fake_native13()
            control[key] = value
            controls.append(control)
        missing = fake_native13()
        del missing['cases'][business.NATIVE13_IDS[0]]
        controls.append(missing)
        failed_case = fake_native13()
        failed_case['cases'][business.NATIVE13_IDS[0]]['full_boundary_restored'] = False
        controls.append(failed_case)
        bad_status = fake_native13()
        bad_status['cases'][business.NATIVE13_IDS[0]]['status'] = 'INCOMPLETE'
        controls.append(bad_status)
        for control in controls:
            with self.assertRaises(AssertionError):
                admit(control)
            self.assertIsNone(business.ADMISSION)

    def test_requires_bound_current_stage_digest_and_qualified_successor(self):
        wrong = fake_install()
        wrong['sources']['files']['proof.sql'] = '0'*64
        with self.assertRaisesRegex(AssertionError, 'EXACT_INSTALLED_STAGE'):
            admit(state=wrong)
        for arguments in (dict(digest=''), dict(commit=''),
                          dict(commit=business.guard.BASE['published_commit']),
                          dict(commit=business.guard.BASE['equivalent_local_commit'])):
            with self.assertRaises(AssertionError):
                admit(**arguments)
        value = admit()  # Synthetic structural gate control, not actual13 evidence.
        self.assertFalse(value['callbacks_actual_execution'])
        self.assertEqual(len(value['exact_native13_ids']), 13)
        failed = fake_native13()
        failed['status'] = 'FAIL'
        with self.assertRaises(AssertionError):
            admit(failed)
        self.assertIsNone(business.ADMISSION, 'failed admission must close a previously opened local control')


class Sources(TestCase):
    def test_retained_call_interfaces_bind_without_database(self):
        n = business.n
        for function, args, kwargs in (
            (n.d1.post, (None, None, '275.00', 'first-return'), {}),
            (n.d1.profile, (None, None, '250.00', '30.00'), {}),
            (n.basic.apply, (None, None, '220.00'), {}),
            (n.refunds.refund, (None, None, '230.00'), {}),
            (n.basic.payload, (None, 'UNDO'), dict(original='named-event')),
            (n.basic.review, (None, None), {}),
            (n.basic.command, (None, None, None), {}),
            (n.correction.correct, (None, None, None, None), {}),
            (n.native.note.unchanged_facts, (None, 'sale'), {}),
            (n.target_document_ar, (None, 'target-sale', 'customer', 'AR-account'), {}),
        ):
            inspect.signature(function).bind(*args, **kwargs)

    def test_exact_current_sources_and_case_ids(self):
        result = business.guard.admitted()
        self.assertEqual(result['case_ids'], list(business.IDS))
        self.assertFalse(result['actual_Native_execution'])
        self.assertEqual(set(business.NATIVE13_IDS), set(business.n.d1.IDS))

    def test_native_source_change_cannot_silently_rebind(self):
        pins = json.loads((HERE/'SOURCE.json').read_bytes())
        with TemporaryDirectory(prefix='d1-cont-source-negative-') as directory:
            root = Path(directory)
            for relative in (*pins['files'], 'scripts/current-credit-d1-continuation-qualification/SOURCE.json'):
                target = root/relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT/relative, target)
            business.guard.admitted(root)
            file = root/'scripts/cp7_customer_credit/consumer/native_basic_cases.py'
            file.write_text(file.read_text()+'\n# Unadmitted source mutation\n')
            with self.assertRaisesRegex(AssertionError, 'D1_CONT_SOURCE_CHANGED'):
                business.guard.admitted(root)


if __name__ == '__main__':
    # Retained Native import helpers append their own runner flags. They are
    # not arguments to this standalone unittest process.
    main(argv=ORIGINAL_ARGV, verbosity=2)
