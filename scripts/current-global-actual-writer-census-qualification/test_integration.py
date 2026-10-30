"""No-database controls for the exact successor integration candidate."""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import json
import unittest
from psycopg.pq import TransactionStatus
import census
import integration
import runner_patch
from test_census import fixture, supplemental_fixture


def snapshot():
    catalog = fixture()
    # Include a sequence to make omission/type/residue controls meaningful.
    catalog['relations']['erp.sequence_v1'] = ['owner', 'S', 'p', False, False, False, 'n', None, True, None, None, None, []]
    catalog['sequences']['erp.sequence_v1'] = ['bigint', '1', '1', '999', '1', '1', False]
    return dict(catalog=catalog, data_and_sequences={
        'erp.lots': [0, sha256(b'[]').hexdigest()],
        'erp.history': [0, sha256(b'[]').hexdigest()],
        'sequence:erp.sequence_v1': ['1', False]})


def simple_snapshot():
    catalog = fixture()
    return dict(catalog=catalog, data_and_sequences={
        'erp.lots': [0, sha256(b'[]').hexdigest()],
        'erp.history': [0, sha256(b'[]').hexdigest()]})


def case(directory):
    before = simple_snapshot()
    supplement = supplemental_fixture(before['catalog'])
    state = dict(after=before['catalog'], preuse_data_and_sequences=before['data_and_sequences'])
    return dict(read_before=before, read_after=deepcopy(before),
        global_writer_supplemental_reference=integration.persist_original(directory, supplement, before['catalog']),
        global_writer_supplemental_noeffect=integration.finish(before, before, supplement, state),
        global_writer_read_transaction=dict(contract=integration.CONTRACT,
            identity=['cp6_rollback', 'postgres', 'on', 'read committed', '', 'UTC'],
            first_statement_read_only=True, isolation='read committed', transaction_writes=False,
            runtime_entry=None, actual_Native_credit=0, production_go=False, independent_acceptance=False))


class IntegrationControls(unittest.TestCase):
    def test_full_table_and_sequence_snapshot_positive_control(self):
        result = integration.complete_snapshot(snapshot())
        self.assertEqual((result['table_count'], result['sequence_count']), (2, 1))

    def test_missing_sequence_refused(self):
        value = snapshot(); del value['data_and_sequences']['sequence:erp.sequence_v1']
        with self.assertRaisesRegex(ValueError, 'ALL_TABLES_AND_ALL_SEQUENCES'):
            integration.complete_snapshot(value)

    def test_missing_table_refused(self):
        value = snapshot(); del value['data_and_sequences']['erp.history']
        with self.assertRaisesRegex(ValueError, 'ALL_TABLES_AND_ALL_SEQUENCES'):
            integration.complete_snapshot(value)

    def test_unknown_extra_sequence_refused(self):
        value = snapshot(); value['data_and_sequences']['sequence:erp.unknown'] = ['1', False]
        with self.assertRaisesRegex(ValueError, 'ALL_TABLES_AND_ALL_SEQUENCES'):
            integration.complete_snapshot(value)

    def test_sequence_is_called_requires_exact_bool(self):
        value = snapshot(); value['data_and_sequences']['sequence:erp.sequence_v1'][1] = 0
        with self.assertRaisesRegex(ValueError, 'ALL_SEQUENCE_STATE_ABI'):
            integration.complete_snapshot(value)

    def test_table_count_bool_not_integer_zero(self):
        value = snapshot(); value['data_and_sequences']['erp.history'][0] = False
        with self.assertRaisesRegex(ValueError, 'TABLE_FINGERPRINT_ABI'):
            integration.complete_snapshot(value)

    def test_preuse_comparison_rejects_a_changed_sequence(self):
        before = snapshot(); state = dict(after=before['catalog'], preuse_data_and_sequences=deepcopy(before['data_and_sequences']))
        state['preuse_data_and_sequences']['sequence:erp.sequence_v1'] = ['2', True]
        with self.assertRaisesRegex(ValueError, 'INSTALLED_COMMITTED_PREUSE_STATE_CHANGED'):
            integration.require_current_preuse(before, state)

    def test_full_noeffect_comparison_rejects_changed_table(self):
        before = simple_snapshot(); after = deepcopy(before); after['data_and_sequences']['erp.lots'][0] = 1
        state = dict(after=before['catalog'], preuse_data_and_sequences=before['data_and_sequences'])
        with self.assertRaisesRegex(ValueError, 'READ_CHANGED_CATALOGUE_ROWS_OR_SEQUENCES'):
            integration.finish(before, after, supplemental_fixture(before['catalog']), state)

    def test_first_transaction_statement_precedes_any_select(self):
        conn = SimpleNamespace(autocommit=False, info=SimpleNamespace(host='127.0.0.1', port=54322,
                                                                     transaction_status=TransactionStatus.IDLE))
        calls = []
        class Cursor:
            connection = conn
            def execute(self, query): calls.append(query); return self
            def fetchone(self): return ('cp6_rollback', 'postgres', 'on', 'read committed', '', 'UTC')
        result = integration.begin_readonly(conn, Cursor())
        self.assertEqual(calls[0], 'SET TRANSACTION ISOLATION LEVEL READ COMMITTED READ ONLY')
        self.assertEqual(len(calls), 4)
        self.assertEqual(result['isolation'], 'read committed')

    def test_active_installer_transaction_refused_before_sql(self):
        conn = SimpleNamespace(autocommit=False, info=SimpleNamespace(host='127.0.0.1', port=54322,
                                                                     transaction_status=TransactionStatus.INTRANS))
        with self.assertRaisesRegex(ValueError, 'FRESH_NONAUTOCOMMIT'):
            integration.begin_readonly(conn, SimpleNamespace(connection=conn))

    def test_autocommit_connection_refused_before_sql(self):
        conn = SimpleNamespace(autocommit=True, info=SimpleNamespace(host='127.0.0.1', port=54322,
                                                                    transaction_status=TransactionStatus.IDLE))
        with self.assertRaisesRegex(ValueError, 'FRESH_NONAUTOCOMMIT'):
            integration.begin_readonly(conn, SimpleNamespace(connection=conn))

    def test_repeatable_read_identity_refused(self):
        conn = SimpleNamespace(autocommit=False, info=SimpleNamespace(host='127.0.0.1', port=54322,
                                                                     transaction_status=TransactionStatus.IDLE))
        class Cursor:
            connection = conn
            def execute(self, query): return self
            def fetchone(self): return ('cp6_rollback', 'postgres', 'on', 'repeatable read', '', 'UTC')
        with self.assertRaisesRegex(ValueError, 'TRANSACTION_SETTINGS_CHANGED'):
            integration.begin_readonly(conn, Cursor())

    def test_separate_original_roundtrip_and_parent_gate_obligation(self):
        with TemporaryDirectory() as directory:
            value = case(directory)
            self.assertNotIn('global_writer_supplemental_capture', value)
            self.assertTrue(integration.validate_case(value, directory)['parent_outer_all5_gate_required'])
            self.assertFalse(value['global_writer_supplemental_noeffect']['outer_restoration_verified'])

    def test_original_cannot_overwrite_first_evidence(self):
        with TemporaryDirectory() as directory:
            value = case(directory); path = Path(directory) / integration.ORIGINAL; prior = path.read_bytes()
            with self.assertRaises(FileExistsError): case(directory)
            self.assertEqual(path.read_bytes(), prior)

    def test_modified_original_raw_bytes_refused(self):
        with TemporaryDirectory() as directory:
            value = case(directory); path = Path(directory) / integration.ORIGINAL
            path.write_bytes(path.read_bytes() + b' ')
            with self.assertRaisesRegex(ValueError, 'ORIGINAL_RAW_BYTES_CHANGED'):
                integration.validate_case(value, directory)

    def test_original_reference_cannot_select_another_filename(self):
        with TemporaryDirectory() as directory:
            value = case(directory); value['global_writer_supplemental_reference']['name'] = '../other.json'
            with self.assertRaisesRegex(ValueError, 'EXACT_ORIGINAL_REFERENCE'):
                integration.validate_case(value, directory)

    def test_noeffect_proof_bool_credit_refused(self):
        with TemporaryDirectory() as directory:
            value = case(directory); value['global_writer_supplemental_noeffect']['actual_Native_credit'] = False
            with self.assertRaisesRegex(ValueError, 'FULL_READ_BRACKET_PROOF_CHANGED'):
                integration.validate_case(value, directory)

    def test_case_settings_bool_credit_refused(self):
        with TemporaryDirectory() as directory:
            value = case(directory); value['global_writer_read_transaction']['actual_Native_credit'] = False
            with self.assertRaisesRegex(ValueError, 'READ_ONLY_READ_COMMITTED_REQUIRED'):
                integration.validate_case(value, directory)

    def test_derived_runner_uses_existing_snapshots_and_rollback(self):
        text, proof = runner_patch.derive('runner')
        self.assertEqual(proof['counted_changes'], 3)
        self.assertLess(text.index('begin_readonly(conn,cur)'), text.index("cur.execute('select current_database()')"))
        self.assertEqual(text.count('catalog._data(cur)'), 2)
        self.assertEqual(text.count('conn.rollback()'), 1)
        self.assertEqual(text.count('persist_original('), 1)
        self.assertNotIn('conn.commit()', text)
        self.assertFalse(proof['metadata_launch_prepared'])

    def test_derived_gate_retains_outer_all5_and_custom_output_directory(self):
        text, proof = runner_patch.derive('gate')
        self.assertEqual(proof['counted_changes'], 3)
        for text_anchor in ('DE_SKU_COMPLETE_ALL5_REQUIRED', 'DE_SKU_COMPLETE_OUTER_REQUIRED', 'DE_SKU_AUTH_RESIDUE', 'original_directory=args.directory'):
            self.assertIn(text_anchor, text)
        self.assertIn('validate_case(case,original_directory', text)

    def test_different_parent_source_bytes_refused(self):
        for kind, filename in (('runner', runner_patch.RUNNER), ('gate', runner_patch.GATE)):
            raw = (runner_patch.ROOT / filename).read_bytes() + b'\n'
            with self.subTest(kind=kind), self.assertRaisesRegex(ValueError, 'EXACT_PARENT_DERIVATIVE_SOURCE'):
                runner_patch.derive(kind, raw)


if __name__ == '__main__':
    unittest.main()
