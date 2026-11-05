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
    part.update(actual_Native_cases=25, native=deepcopy(original), actual_Auth_browser=True,
                actual_browser_cases=2, actual_business_cases=27, real_Auth_browser_claim=True,
                qualification_scope='NATIVE25_AND_CURRENT_BROWSER2')
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
    main.update(actual_Native_cases=25, actual_business_cases=27, actual_browser_cases=2, real_Auth_browser_claim=True,
                qualification_scope='CURRENT_PARENT_SKU_MONEY_AUTOMATIC_NATIVE25_BROWSER2_ONLY',
                source_declaration=dict(complete_combined_sources=deepcopy(declaration)))
    browser = subject.browser_gate
    actual = dict(status='RUN_COMPLETE', planned_case_ids=list(browser.IDS), counts={'PASS': 2},
        cases={}, database_remaining=0, cleanup_failures=[], session_leaks=[], real_auth=True,
        jwt_signed_by_runtime=False, test_only_usage_grant=False,
        auth_counts=dict(before=[1, 2, 3, 4], after=[1, 2, 3, 4], restored=True),
        cleanup=dict(cleanup_failures=[], rest_remaining=False), host_exit=0, host_status='RUN_COMPLETE',
        console_errors=0, auth_cleanup_failures=[],
        script_sha256=subject.admission.pin(browser.module('browser_model_source', browser.HERE / 'browser_prepare.py').derive()[0].encode())['sha256'])
    for index, name in enumerate(browser.IDS):
        actual['cases'][name] = dict(status='PASS', actual_Auth_form_normal_full_App=True, actual_public_PostgREST=True,
            role='ADMIN' if index else 'OWNER', viewport=390 if index else 1440, screenshots=['EXPLICIT_MODEL_PNG'],
            visible_text_contrast=['EXPLICIT_PROTOCOL_MODEL_ONLY'], current_observations=['EXPLICIT_PROTOCOL_MODEL_ONLY'],
            session_leaks=dict(advisory_locks=0, advisory_lock_keys=[], other_sessions=[]),
            actual_UI_refusal_zero_all22_rows_sequences_effect=True, actual_UI_whole_group_inverse_from_other_member=True,
            Native_financial_accounts_restored=True, no_horizontal_page_overflow_at_feature_checkpoints=True,
            unexpected_console_errors=0, full_manual_group_accessory_recovery_claim=False,
            expected_returns_first_child_limitation_not_closed=True, outer_full_backup_Auth_restore_still_required=True,
            production_go=False, independent_acceptance=False, console_evidence=dict(unexpected_errors=[], page_errors=[]),
            post=dict(one_complete_group_two_Native_parts_physical_value='60.06', moving_average_value='68.07',
                source_available=5, source_reserved=1, target_physical=8, actual_double_click_one_new_group=True,
                actual_lost_committed_reply_same_UUID_after_reload=not bool(index),
                all_read_after_replay_rows_sequences_catalog_unchanged=not bool(index)),
            source_pins=dict(entire_current_source_admission=dict(
                status='COMPLETE_CURRENT_PRODUCT_SOURCE_ADMITTED_NOT_BROWSER_OR_FINANCIAL_ACCEPTANCE',
                qualification_commit='explicit-model-head', source_projected=False, database_calls=0, real_case_success_not_implied=True,
                actual_ERP_cases=0, actual_Auth_HTTP_cases=0, actual_browser_cases=0,
                complete_current_source_admission=deepcopy(main['source_declaration']),
                source_database_network_guard=dict(attempts=[], network_nonGit_attempts=[]))))
    docs[subject.BROWSER] = actual
    part['current_browser_gate'] = browser.typed()[0](actual, browser.IDS, mode='BROWSER')
    part['current_browser_copy_authority'] = dict(source=browser.copy_source(), actual_copy_admissions=[dict(
        all22_groups_equal_original_install=True, product_state_modified=False, Native_or_schema_or_RPC_permissions_changed=False)])
    part['current_browser_journey_derivation'] = browser.module('browser_model_derivation', browser.HERE / 'browser_prepare.py').derive()[1]
    return p, docs, ids


class Native25GateProtocol(unittest.TestCase):
    def test_count_metadata_routes_recover_the_entire_unchanged_parent_gate(self):
        raw = subject.RETAINED.read_bytes()
        text, proof = subject.derive(raw)
        self.assertTrue(proof['retained_source_recovered_exactly'])
        self.assertEqual(proof['metadata_expression_routes'], 11)
        self.assertTrue(proof['Auth_HTTP_and_race_counts_still_zero'])
        old = {node.name: node for node in ast.parse(raw).body if isinstance(node, ast.FunctionDef)}
        new = {node.name: node for node in ast.parse(text).body if isinstance(node, ast.FunctionDef)}
        self.assertEqual(set(old), set(new))
        self.assertEqual({name for name in old if ast.dump(old[name]) != ast.dump(new[name])}, {'validate'})
        with self.assertRaisesRegex(ValueError, 'EXACT_RETAINED_COMPLETE_GATE_SOURCE'):
            subject.derive(raw + b'\n')

    def test_explicit_native25_browser2_protocol_requires_fresh_browser_and_zero_HTTP_or_race_credit(self):
        p, docs, ids = model25()
        result = subject.validate(p, docs, 'explicit-model-head', ids)
        self.assertEqual(result['actual_Native_cases'], 25)
        self.assertEqual((result['actual_Auth_HTTP_cases'], result['actual_two_session_races'], result['actual_browser_cases']), (0, 0, 2))
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
            (subject.MAIN, 'actual_browser_cases', 0), (subject.MAIN, 'actual_two_session_races', 2),
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

    def test_browser_cleanup_complete_source_and_real_current_cases_cannot_be_omitted(self):
        p, original, ids = model25()
        def row(d):return d[subject.BROWSER]['cases'][subject.browser_gate.IDS[0]]
        def part(d):return d[subject.MAIN]['committed'][subject.component.CASE]
        mutations = [
            lambda d: d.pop(subject.BROWSER),
            lambda d: d[subject.BROWSER].update(real_auth=False),
            lambda d: d[subject.BROWSER].update(jwt_signed_by_runtime=True),
            lambda d: d[subject.BROWSER].update(test_only_usage_grant=True),
            lambda d: d[subject.BROWSER].update(database_remaining=1),
            lambda d: d[subject.BROWSER]['auth_counts'].update(restored=False),
            lambda d: d[subject.BROWSER]['auth_counts'].update(after=[1, 2, 3, 5]),
            lambda d: d[subject.BROWSER]['cleanup'].update(rest_remaining=True),
            lambda d: d[subject.BROWSER].update(script_sha256='0' * 64),
            lambda d: row(d).update(actual_Auth_form_normal_full_App=False),
            lambda d: row(d).update(actual_public_PostgREST=False),
            lambda d: row(d).update(current_observations=[]),
            lambda d: row(d)['session_leaks'].update(other_sessions=['UNEXPECTED']),
            lambda d: row(d)['post'].update(moving_average_value='60.06'),
            lambda d: row(d)['source_pins']['entire_current_source_admission'].update(qualification_commit='OLDER_HEAD'),
            lambda d: row(d)['source_pins']['entire_current_source_admission'].update(complete_current_source_admission={}),
            lambda d: part(d)['current_browser_copy_authority']['actual_copy_admissions'].append({}),
            lambda d: part(d)['current_browser_copy_authority']['actual_copy_admissions'][0].update(product_state_modified=True),
            lambda d: part(d)['current_browser_copy_authority']['source'].update(product_or_schema_or_RPC_grants_added=True),
        ]
        for index, mutate in enumerate(mutations):
            docs = deepcopy(original);mutate(docs)
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
