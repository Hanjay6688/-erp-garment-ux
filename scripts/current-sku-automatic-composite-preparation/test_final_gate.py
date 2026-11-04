"""Explicit packet protocol models only; no actual Root or ERP execution."""
from copy import deepcopy
from pathlib import Path
from types import FunctionType
import ast
import importlib.util
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('automatic_gate_control_subject', HERE / 'final_gate.py')
subject = importlib.util.module_from_spec(spec)
spec.loader.exec_module(subject)


def retained_model():
    path = subject.ROOT / 'scripts/current-sku-money-composite-preparation/test_execution.py'
    text = path.read_text()
    namespace = dict(deepcopy=deepcopy, gate_support=subject.money_gate, final=subject)
    for name in ('modeled_preflight', 'modeled_packet'):
        code = subject.runtime.report_io.function_code(text, str(path) + '::explicit-protocol-model', name)
        namespace[name] = FunctionType(code, namespace, name)
    return namespace['modeled_packet']()


def model25():
    p, docs, ids = retained_model()
    original = docs[subject.NATIVE]
    template = deepcopy(next(iter(original['cases'].values())))
    ids += ['EXPLICIT_MODEL_CASE_' + str(i) for i in range(19, 25)]
    original.update(planned_case_ids=ids, counts={'PASS': 25}, final={name: 'PASS' for name in ids},
                    cases={name: deepcopy(template) for name in ids})
    main = docs[subject.MAIN]
    part = main['committed'][subject.component.CASE]
    part.update(actual_Native_cases=25, native=deepcopy(original))
    declaration = dict(explicit_source_protocol_model_only=True)
    automatic = dict(status='PASS', errors=[], retained_money19=docs[subject.PREFLIGHT],
                     automatic_functions={name: True for name in subject.prerequisites.FUNCTIONS},
                     automatic_actors={name: dict(role='OWNER', database_role=['authenticated', 'authenticated'],
                        permissions={key: True for key in subject.prerequisites.ACTOR_PERMISSIONS[name]},
                        functions={key: True for key in signatures}) for name, signatures in subject.prerequisites.ACTOR_FUNCTIONS.items()},
                     natural_callers=dict(upstream=dict(status='NATIVE_AUTOMATIC_CALLER_APIS_BOUND_NOT_EXECUTED', calls=6,
                         original_AFUI_physical_constructor=True, actual_ERP_cases=0),
                         invoices=dict(original_invoice_helper_shapes=4, actual_ERP_cases=0)),
                     all_prerequisites_checked_before_first_case=True, source=declaration,
                     all22_rows_and_all_sequences_unchanged=True, actual_ERP_cases=0, production_go=False)
    part['native_prerequisites'] = deepcopy(automatic)
    docs[subject.PREFLIGHT] = automatic
    main.update(actual_Native_cases=25, actual_business_cases=25,
                qualification_scope='CURRENT_PARENT_SKU_MONEY_AUTOMATIC_NATIVE25_ONLY',
                source_declaration=dict(complete_combined_sources=deepcopy(declaration)))
    return p, docs, ids


class Native25GateProtocol(unittest.TestCase):
    def test_count_metadata_routes_recover_the_entire_unchanged_parent_gate(self):
        raw = subject.RETAINED.read_bytes()
        text, proof = subject.derive(raw)
        self.assertTrue(proof['retained_source_recovered_exactly'])
        self.assertEqual(proof['metadata_expression_routes'], 6)
        self.assertTrue(proof['Auth_race_browser_counts_still_zero'])
        old = {node.name: node for node in ast.parse(raw).body if isinstance(node, ast.FunctionDef)}
        new = {node.name: node for node in ast.parse(text).body if isinstance(node, ast.FunctionDef)}
        self.assertEqual(set(old), set(new))
        self.assertEqual({name for name in old if ast.dump(old[name]) != ast.dump(new[name])}, {'validate'})
        with self.assertRaisesRegex(ValueError, 'EXACT_RETAINED_COMPLETE_GATE_SOURCE'):
            subject.derive(raw + b'\n')

    def test_explicit_native25_protocol_model_preserves_zero_Auth_race_and_browser_credit(self):
        p, docs, ids = model25()
        result = subject.validate(p, docs, 'explicit-model-head', ids)
        self.assertEqual(result['actual_Native_cases'], 25)
        self.assertEqual((result['actual_Auth_HTTP_cases'], result['actual_two_session_races'], result['actual_browser_cases']), (0, 0, 0))
        self.assertTrue(result['package_all_five'])
        self.assertFalse(result['production_go'])
        self.assertFalse(docs[subject.MAIN]['full_combined_final_qualification'])
        p, old, ids = retained_model()
        with self.assertRaises((ValueError, KeyError)):
            subject.validate(p, old, 'explicit-model-head', ids)

    def test_changed_case_counts_boundaries_authority_and_supervision_are_refused(self):
        p, original, ids = model25()
        mutations = [
            (subject.MAIN, 'actual_Native_cases', 19), (subject.MAIN, 'actual_Auth_HTTP_cases', 2),
            (subject.MAIN, 'actual_browser_cases', 2), (subject.MAIN, 'actual_two_session_races', 2),
            (subject.MAIN, 'full_combined_final_qualification', True), (subject.MAIN, 'production_go', True),
            (subject.MAIN, 'baseline_full22_all_rows_all_sequences_equal', False),
            (subject.MAIN, 'restore_raw_public_equal', False), (subject.MAIN, 'baseline_advisors_equal', False),
            (subject.MAIN, 'advisor_gate', False), (subject.MAIN, 'used_guard_refused_before_DDL', False),
            (subject.NATIVE, 'counts', {'PASS': 24}), (subject.NATIVE, 'complete_boundary_restored', False),
            (subject.SUPERVISION, 'external_signal', 'SIGTERM'), (subject.SUPERVISION, 'worker_exit', -9),
            (subject.SUPERVISION, 'deadline_reached', True), (subject.SUPERVISION, 'process_group_empty', False),
            (subject.SUPERVISION, 'process_tree_empty', False), (subject.SUPERVISION, 'work_budget_seconds', 120),
        ]
        for filename, key, value in mutations:
            docs = deepcopy(original)
            docs[filename][key] = value
            with self.subTest(filename=filename, key=key), self.assertRaises((ValueError, KeyError)):
                subject.validate(p, docs, 'explicit-model-head', ids)
        for name in ids:
            docs = deepcopy(original)
            docs[subject.NATIVE]['cases'][name]['session_leaks']['other_sessions'] = ['unexpected']
            docs[subject.MAIN]['committed'][subject.component.CASE]['native'] = deepcopy(docs[subject.NATIVE])
            with self.subTest(case=name), self.assertRaises((ValueError, KeyError)):
                subject.validate(p, docs, 'explicit-model-head', ids)

    def test_batch_preflight_cannot_omit_an_actor_function_permission_or_natural_caller(self):
        p, original, ids = model25()
        mutations = [
            lambda d: d.update(all22_rows_and_all_sequences_unchanged=False),
            lambda d: d.update(all_prerequisites_checked_before_first_case=False),
            lambda d: d['automatic_actors'].pop('upstream_completion_owner'),
            lambda d: d['automatic_actors']['supplier_invoice_owner'].update(role='USER'),
            lambda d: d['automatic_actors']['supplier_invoice_owner'].update(database_role=['postgres', 'postgres']),
            lambda d: d['natural_callers']['invoices'].update(original_invoice_helper_shapes=3),
            lambda d: d['natural_callers']['upstream'].update(original_AFUI_physical_constructor=False),
            lambda d: d['source'].update(unbound_extra_source=True),
        ]
        for signature in subject.prerequisites.FUNCTIONS:
            mutations.append(lambda d, signature=signature: d['automatic_functions'].pop(signature))
        for name, permissions in subject.prerequisites.ACTOR_PERMISSIONS.items():
            for permission in permissions:
                mutations.append(lambda d, name=name, permission=permission: d['automatic_actors'][name]['permissions'].update({permission: False}))
        for index, mutate in enumerate(mutations):
            docs = deepcopy(original)
            mutate(docs[subject.PREFLIGHT])
            docs[subject.MAIN]['committed'][subject.component.CASE]['native_prerequisites'] = deepcopy(docs[subject.PREFLIGHT])
            with self.subTest(counterexample=index), self.assertRaises((ValueError, KeyError)):
                subject.validate(p, docs, 'explicit-model-head', ids)

    def test_owning_acceptance_refuses_closed_Root_before_reading_any_original(self):
        class NoInspection:
            def __getattribute__(self, name):
                raise AssertionError('Closed Root gate inspected an Original path')
        with self.assertRaisesRegex(ValueError, 'FULL_NATIVE_LIFECYCLE_PENDING'):
            subject.gate(NoInspection(), NoInspection())


if __name__ == '__main__':
    unittest.main()
