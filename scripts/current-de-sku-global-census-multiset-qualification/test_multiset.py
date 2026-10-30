"""Mutation controls only; doubles and local models confer no ERP credit."""
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch
import importlib.util
import json
import sys
import unittest
import yaml

HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]
HELPER = ROOT / 'scripts/current-global-actual-writer-census-qualification'
sys.path.insert(0, str(HELPER))
import test_census as controls


def load(name, file):
    spec = importlib.util.spec_from_file_location(name, HERE / file)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module


m = load('multiset_codec_controls', 'multiset.py')
d = load('multiset_derivation_controls', 'derive.py')
a = load('multiset_admission_controls', 'admission.py')
w = load('multiset_workflow_controls', 'workflow.py')
compiler = load('multiset_compiler_controls', 'compile_modules.py')
c = compiler.capture(); integration = compiler.integration()
IDENTITY = ('cp6_rollback', 'postgres', 'on', '', 'UTC', '170005')


def inputs():
    catalog = controls.fixture(); old = controls.supplemental_fixture(catalog)
    raw = {name: [[key, value] for key, value in rows.items()] for name, rows in old['groups'].items()}
    raw['dependencies'] = [['1255:300:0:2615:100:0:n', ['pg_proc', '300', 0, 'pg_namespace', '100', 0, 'n', 'function erp.writer()', 'schema erp']]]
    raw['dependencies'].append(deepcopy(raw['dependencies'][0]))
    return catalog, raw


class Cursor:
    def __init__(self, raw, fail=None):
        self.raw = raw; self.fail = fail; self.sql = []
        self.connection = SimpleNamespace(info=SimpleNamespace(host='127.0.0.1', port=54322))
    def execute(self, sql, params=None):
        self.sql.append(sql)
        self.name = next((name for name, query in c.QUERIES.items() if query == sql), None)
        if self.fail is not None and self.name == self.fail:
            error = RuntimeError('unsupported privilege remains an error'); error.sqlstate = '0A000'; raise error
        return self
    def fetchone(self): return IDENTITY
    def fetchall(self): return deepcopy(self.raw[self.name])


def captured(directory, mutation=None):
    catalog, raw = inputs()
    if mutation: mutation(raw)
    supplement = c.capture(Cursor(raw), catalog, raw_directory=directory, progress=lambda _: None)
    return catalog, raw, supplement


class BagControls(unittest.TestCase):
    def test_full_identical_dependencies_and_multiplicity_are_preserved(self):
        _, raw = inputs(); bag = m.encode_group('dependencies', raw['dependencies'])
        self.assertEqual(bag['occurrence_count'], 2); self.assertEqual(bag['distinct_identity_count'], 1)
        self.assertEqual(list(bag['identity_multiplicities'].values()), [2])
        self.assertEqual(m.values(bag), [pair[1] for pair in raw['dependencies']])

    def test_same_identity_different_raw_values_are_not_last_row_wins(self):
        _, raw = inputs(); raw['dependencies'][1][1][7] = 'different raw descriptive field'
        bag = m.encode_group('dependencies', raw['dependencies'])
        self.assertEqual(bag['rows'], raw['dependencies']); self.assertNotEqual(*m.values(bag))

    def test_view_relation_dependencies_preserve_every_eight_field_row(self):
        row = ['900:200:1:n', ['erp.view', '_RETURN', '1', 'O', True, 'erp.lots', 1, 'n']]
        bag = m.encode_group('view_relation_dependencies', [row, deepcopy(row)])
        self.assertEqual(len(m.values(bag)), 2); self.assertEqual(len(m.values(bag)[0]), 8)

    def test_other_seventeen_groups_still_reject_duplicate_identities(self):
        self.assertEqual(len(set(c.QUERIES) - set(m.BAG_GROUPS)), 17)
        for name in set(c.QUERIES) - set(m.BAG_GROUPS):
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, 'DUPLICATE_SUPPLEMENT_IDENTITY'):
                m.encode_group(name, [['same', False], ['same', True]])

    def test_count_boolean_and_inconsistent_multiplicity_refused(self):
        _, raw = inputs(); original = m.encode_group('dependencies', raw['dependencies'])
        for key, value in [('occurrence_count', True), ('distinct_identity_count', True), ('occurrence_count', 1)]:
            bad = deepcopy(original); bad[key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError): m.values(bad)
        for value in (True, 1, 0, 3):
            bad = deepcopy(original); bad['identity_multiplicities'][raw['dependencies'][0][0]] = value
            with self.subTest(value=value), self.assertRaises(ValueError): m.values(bad)

    def test_row_count_field_abi_and_identity_mismatch_refused(self):
        _, raw = inputs()
        for change in (lambda pair: pair[1].pop(), lambda pair: pair[1].__setitem__(2, False),
                       lambda pair: pair.__setitem__(0, 'function-only'), lambda pair: pair[1].__setitem__(4, '999')):
            bad = deepcopy(raw['dependencies']); change(bad[0])
            with self.assertRaises(ValueError): m.encode_group('dependencies', bad)

    def test_bag_digest_and_extra_fields_refused(self):
        _, raw = inputs(); bag = m.encode_group('dependencies', raw['dependencies'])
        for key, value in [('raw_pairs_sha256', '0' * 64), ('omitted', 0), ('group', 'unknown')]:
            bad = deepcopy(bag); bad[key] = value
            with self.assertRaises(ValueError): m.values(bad)


class RawAndConsumerControls(unittest.TestCase):
    def test_offline_consumer_requires_original_and_preserves_unknown_closure(self):
        analyzer = compiler.census()
        with TemporaryDirectory() as directory:
            catalog, _, supplement = captured(directory)
            with self.assertRaisesRegex(ValueError, 'ANALYSIS_RAW_ORIGINAL_REQUIRED'):
                analyzer.analyze(catalog, expected_contexts=['erp.history'], roots=controls.ROOTS, supplement=supplement)
            value = analyzer.analyze(catalog, expected_contexts=['erp.history'], roots=controls.ROOTS,
                supplement=supplement, original_directory=directory)
            self.assertEqual(value['supplemental_capture'], supplement)
            self.assertFalse(value['writer_or_phantom_lock_closed']); self.assertIsNone(value['runtime_entry'])
            self.assertEqual(value['permission_closure'], 'UNKNOWN')

    def test_capture_retains_raw_and_all19_query_groups_before_validated_projection(self):
        with TemporaryDirectory() as directory:
            catalog, raw, supplement = captured(directory)
            value = m.require_projection(directory, supplement, catalog, c.QUERIES)
            self.assertEqual(value['raw_groups'], raw); self.assertEqual(value['captured_groups'], list(c.QUERIES))
            self.assertEqual(supplement['groups']['dependencies']['occurrence_count'], 2)
            self.assertFalse(c.validate(supplement, catalog)['writer_or_phantom_lock_closed'])

    def test_unique_group_failure_keeps_all_raw_pairs_before_refusal(self):
        with TemporaryDirectory() as directory:
            catalog, raw = inputs(); raw['roles'].append(deepcopy(raw['roles'][0]))
            with self.assertRaisesRegex(ValueError, 'DUPLICATE_SUPPLEMENT_IDENTITY:roles'):
                c.capture(Cursor(raw), catalog, raw_directory=directory, progress=lambda _: None)
            value = m.document((Path(directory) / m.RAW_NAME).read_bytes())
            self.assertEqual(value['raw_groups'], raw); self.assertEqual(len(value['captured_groups']), 19)

    def test_malformed_row_failure_retains_the_original_row(self):
        with TemporaryDirectory() as directory:
            catalog, raw = inputs(); raw['dependencies'][0][1].pop()
            with self.assertRaisesRegex(ValueError, 'ROW_ABI'):
                c.capture(Cursor(raw), catalog, raw_directory=directory, progress=lambda _: None)
            self.assertEqual(m.document((Path(directory) / m.RAW_NAME).read_bytes())['raw_groups'], raw)

    def test_unsupported_query_retains_prefix_and_never_substitutes_false(self):
        for phase in ('schemas', 'effective_function_privileges', 'dependencies'):
            with self.subTest(phase=phase), TemporaryDirectory() as directory:
                catalog, raw = inputs(); cursor = Cursor(raw, fail=phase)
                with self.assertRaisesRegex(RuntimeError, 'unsupported privilege'):
                    c.capture(cursor, catalog, raw_directory=directory, progress=lambda _: None)
                value = m.document((Path(directory) / m.RAW_NAME).read_bytes())
                m.validate_raw(value, c.QUERIES, catalog)
                self.assertEqual(value['captured_groups'], list(c.QUERIES)[:list(c.QUERIES).index(phase)])
                self.assertEqual(value['query_failure'], dict(phase=phase, sqlstate='0A000'))
                self.assertNotIn(phase, value['raw_groups'])

    def test_raw_persist_failure_prevents_success_and_does_not_overwrite(self):
        with TemporaryDirectory() as directory:
            catalog, raw, supplement = captured(directory); path = Path(directory) / m.RAW_NAME; before = path.read_bytes()
            with self.assertRaises(FileExistsError): c.capture(Cursor(raw), catalog, raw_directory=directory, progress=lambda _: None)
            self.assertEqual(path.read_bytes(), before)

    def test_separate_raw_and_supplement_originals_both_required_and_exact(self):
        with TemporaryDirectory() as directory:
            catalog, _, supplement = captured(directory)
            reference = integration.persist_original(directory, supplement, catalog)
            observed, _ = integration.read_original(directory, reference, catalog)
            self.assertEqual(observed, supplement)
            raw = Path(directory) / m.RAW_NAME; raw.unlink()
            with self.assertRaisesRegex(ValueError, 'RAW_ORIGINAL_REQUIRED'):
                integration.read_original(directory, reference, catalog)

    def test_removing_one_dependency_occurrence_is_detected_against_raw(self):
        with TemporaryDirectory() as directory:
            catalog, _, supplement = captured(directory)
            supplement['groups']['dependencies'] = m.encode_group('dependencies', supplement['groups']['dependencies']['rows'][:1])
            c.validate(supplement, catalog)  # Shape alone is deliberately insufficient.
            with self.assertRaisesRegex(ValueError, 'NOT_LOSSLESS'): integration.persist_original(directory, supplement, catalog)

    def test_changing_raw_description_without_raw_original_is_detected(self):
        with TemporaryDirectory() as directory:
            catalog, _, supplement = captured(directory)
            rows = supplement['groups']['dependencies']['rows']; rows[0][1][7] = 'mutated description'
            supplement['groups']['dependencies'] = m.encode_group('dependencies', rows)
            with self.assertRaisesRegex(ValueError, 'NOT_LOSSLESS'): integration.persist_original(directory, supplement, catalog)

    def test_complete_raw_is_not_claimed_after_partial_query_prefix(self):
        catalog, raw = inputs()
        with TemporaryDirectory() as directory:
            ref = m.persist_raw(directory, catalog, IDENTITY,
                {key: sorted(catalog[key]) for key in ('schemas','relations','functions')}, {}, c.QUERIES,
                failure=dict(phase='schemas', sqlstate='0A000'))
            with self.assertRaisesRegex(ValueError, 'PARTIAL_RAW_CANNOT_QUALIFY'):
                m.require_projection(directory, dict(raw_capture_reference=ref), catalog, c.QUERIES)

    def test_raw_reference_byte_digest_and_name_mutations_rejected(self):
        with TemporaryDirectory() as directory:
            catalog, _, supplement = captured(directory)
            for key, value in [('bytes', True), ('sha256', '0'*64), ('name', '../other.json')]:
                ref = deepcopy(supplement['raw_capture_reference']); ref[key] = value
                with self.subTest(key=key), self.assertRaises(ValueError): m.read_raw(directory, ref, c.QUERIES, catalog)

    def test_source_query_hash_scope_and_identity_mutations_rejected(self):
        with TemporaryDirectory() as directory:
            catalog, _, supplement = captured(directory)
            value = m.read_raw(directory, supplement['raw_capture_reference'], c.QUERIES, catalog)
            changes = (lambda v: v['query_sha256'].__setitem__('dependencies', '0'*64),
                lambda v: v['params']['relations'].pop(), lambda v: v['identity'].__setitem__(2, 'off'),
                lambda v: v.__setitem__('actual_Native_credit', False), lambda v: v.__setitem__('transaction_writes', 0),
                lambda v: v.__setitem__('independent_acceptance', 0))
            for change in changes:
                bad = deepcopy(value); change(bad)
                with self.assertRaises(ValueError): m.validate_raw(bad, c.QUERIES, catalog)

    def test_capture_caller_flags_and_unknown_empty_dependencies_remain_closed(self):
        with TemporaryDirectory() as directory:
            catalog, _, supplement = captured(directory)
            for key, value in [('actual_Native_credit', False), ('independent_acceptance', 0), ('transaction_writes', 0),
                ('caller_outer_restoration_required', 1), ('caller_full_catalogue_data_sequence_bracket_required', 1)]:
                bad = deepcopy(supplement); bad[key] = value
                with self.subTest(key=key), self.assertRaises(ValueError): c.validate(bad, catalog)
            bad = deepcopy(supplement); bad['groups']['dependencies'] = m.encode_group('dependencies', [])
            with self.assertRaisesRegex(ValueError, 'UNKNOWN_EMPTY_DEPENDENCIES'): c.validate(bad, catalog)

    def test_progress_never_contains_catalogue_rows(self):
        catalog, raw = inputs(); events = []
        with TemporaryDirectory() as directory: c.capture(Cursor(raw), catalog, raw_directory=directory, progress=events.append)
        self.assertEqual(len(events), 38)
        self.assertTrue(all(set(e) <= {'component','phase','status','rows','sqlstate'} for e in events))

    def test_raw_symlink_and_duplicate_json_members_rejected(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / m.RAW_NAME; path.symlink_to(HERE / 'admission.py')
            with self.assertRaisesRegex(ValueError, 'SYMLINK'): m.regular(directory, m.RAW_NAME)
        for raw in ('{"rows":[],"rows":[]}', '{"v":NaN}'):
            with self.assertRaises(ValueError): m.document(raw)


class SourceAndPhaseControls(unittest.TestCase):
    def test_whole_parent_and_exact_reversible_file_transitions(self):
        proof = a.preflight(require_clean=False)
        self.assertEqual(proof['parent_files'], 13909); self.assertTrue(d.file_transitions()['byte_reversible'])
        self.assertFalse(proof['old_frozen_guards_edited']); self.assertIsNone(proof['runtime_entry'])

    def test_all_nineteen_sql_queries_remain_byte_exact(self):
        self.assertEqual(c.QUERIES, controls.capture.QUERIES); self.assertEqual(len(c.QUERIES), 19)

    def test_engine_outer_restore_and_stream_fence_remain_byte_exact(self):
        new, proof = d.engine(); old, _ = d.parent('engine')
        for start, end in [('    finally:\n        if before is not None and pre_dumped:', "        cases=report['committed']"),
                           ('\ndef run():\n', "\n\nif __name__=='__main__':")]:
            self.assertEqual(new[new.index(start):new.index(end)], old[old.index(start):old.index(end)])
        self.assertTrue(proof['install_preuse_inverse_reinstall_commit_outer_restore_all5_preserved'])

    def test_runner_retains_before_and_settings_even_when_capture_refuses(self):
        text, _ = d.runner()
        self.assertLess(text.index("report['read_before']=before"), text.index('supplemental_capture=census_capture.capture'))
        self.assertLess(text.index("report['global_writer_read_transaction']=read_transaction"), text.index('supplemental_capture=census_capture.capture'))
        self.assertLess(text.index('begin_readonly(conn,cur)'), text.index("cur.execute('select current_database()')"))
        self.assertIn('if before!=after:', text); self.assertIn('census_integration.finish(', text)

    def test_readonly_first_sql_and_empty_path_remain_exact(self):
        conn = SimpleNamespace(autocommit=False, info=SimpleNamespace(host='127.0.0.1', port=54322, transaction_status=integration.TransactionStatus.IDLE))
        calls = []
        class TxCursor:
            connection = conn
            def execute(self, sql): calls.append(sql); return self
            def fetchone(self): return ('cp6_rollback','postgres','on','read committed','','UTC')
        integration.begin_readonly(conn, TxCursor())
        self.assertEqual(calls[:3], ['SET TRANSACTION ISOLATION LEVEL READ COMMITTED READ ONLY',
            "SELECT pg_catalog.set_config('search_path','',true)", "SET LOCAL TimeZone = 'UTC'"])

    def test_parent_source_failure_and_unknown_outputs_refuse_before_old_imports(self):
        with patch.object(a, 'immutable_parent', side_effect=ValueError('parent changed')), patch.object(a, 'load', side_effect=AssertionError('old import')):
            with self.assertRaisesRegex(ValueError, 'parent changed'): a.preflight(require_clean=False)
        with patch.object(a, 'load', side_effect=AssertionError('old output reader imported')):
            with self.assertRaisesRegex(ValueError, 'UNKNOWN_UNTRACKED_SOURCE_BEFORE_IMPORT'): a.outputs({'unknown.py'})

    def test_mode_symlink_and_counted_anchor_mutations_refused(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / 'source.py'; path.write_text('exact'); pin = dict(a.pin(path.read_bytes()), mode='100644')
            path.chmod(0o755)
            with self.assertRaisesRegex(ValueError, 'MODE_CHANGED'): a.checked('source.py', pin, directory)
        for text in ('missing', 'anchor anchor'):
            with self.assertRaisesRegex(ValueError, 'ANCHOR_CHANGED'): d.replace_exact(text, [('anchor','replacement')], 'test')

    def test_full_inherited_gate_all5_and_new_raw_binding_remain_mandatory(self):
        text, _ = d.gate()
        for anchor in ('DE_SKU_COMPLETE_ALL5_REQUIRED','DE_SKU_COMPLETE_OUTER_REQUIRED:',
            'DE_SKU_ACTUAL_CATALOGUE_ROWS_SEQUENCES_CHANGED','DE_SKU_COMPLETE22_CATALOGUE_GROUPS_REQUIRED',
            'DE_SKU_COMPLETE_EFFECTIVE_ROLE_PRIVILEGE_MATRIX_REQUIRED','census_integration.validate_case(case,'):
            self.assertIn(anchor, text)
        self.assertIn('/loader.py', text)

    def test_exact_workflow_preserves_product_checkout_and_all_other_steps(self):
        old = yaml.safe_load((ROOT / w.OLD).read_bytes()); new = yaml.safe_load((ROOT / w.NEW).read_bytes())
        self.assertEqual(new, w.derive(old)); self.assertEqual(len(new['jobs']['p21']['steps']), 72)
        changed = [(before, after) for before, after in zip(old['jobs']['p21']['steps'], new['jobs']['p21']['steps']) if before != after]
        self.assertEqual(len(changed), 8); self.assertEqual(new['permissions'], old['permissions'])
        self.assertEqual(new['jobs']['p21']['steps'][0], old['jobs']['p21']['steps'][0])
        self.assertFalse(new['concurrency']['cancel-in-progress'])
        self.assertEqual(new['jobs']['p21']['steps'][-1]['if'], 'always()')

    def test_raw_original_retention_is_separate_and_never_body_stdout(self):
        retain = load('multiset_retention_controls', 'retain.py')
        with TemporaryDirectory() as directory:
            path = Path(directory) / m.RAW_NAME; raw = b'{"raw":"retained privately"}\n'; path.write_bytes(raw)
            value = retain.retain(directory)
            self.assertEqual(value['files'][m.RAW_NAME], a.pin(raw)); self.assertFalse(value['metadata_or_data_bodies_printed'])
            self.assertTrue(value['missing_required']); self.assertEqual(path.read_bytes(), raw)


if __name__ == '__main__': unittest.main()
