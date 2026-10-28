from contextlib import contextmanager
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import importlib.util,json,sys,unittest
import psycopg
import stream_data,restoration

HERE=Path(__file__).resolve().parent


class CompleteCanonicalDataFingerprint(unittest.TestCase):
    def test_empty_duplicate_unicode_and_numeric_row_text_keep_exact_old_array_bytes(self):
        for rows in ([],['{"x": null}'],['{"x": "HPP ♞"}','{"x": "HPP ♞"}'],['{"x": 1.2300}','{"x": -4}']):
            expected=('['+', '.join(rows)+']').encode('UTF8')
            self.assertEqual(stream_data.array_fingerprint(iter(rows)),[len(rows),sha256(expected).hexdigest()])

    def test_row_stream_is_closed_even_when_hashing_fails(self):
        events=[]
        class Rows:
            def __iter__(self):yield (None,)
            def close(self):events.append('CLOSE_STREAM')
        class Scan:
            def __enter__(self):return self
            def __exit__(self,*args):events.append('CLOSE_CURSOR')
            def stream(self,query):return Rows()
        connection=SimpleNamespace(cursor=lambda **kwargs:Scan())
        with self.assertRaisesRegex(ValueError,'JSONB_ROW_TEXT_REQUIRED'):
            stream_data.table_fingerprint(SimpleNamespace(connection=connection),('public','large_table'))
        self.assertEqual(events,['CLOSE_STREAM','CLOSE_CURSOR'])

    def test_real_catalog_derivation_keeps_scope_and_sequences_and_restores_callback(self):
        sys.path.insert(0,str(HERE.parents[1]/'scripts'))
        with patch.object(sys,'argv',[__file__]),patch.object(psycopg,'connect',side_effect=AssertionError('NO_DATABASE_ALLOWED')):
            import cp7_ow04_restore_bundle as catalog
            original=catalog._data
            with self.assertRaisesRegex(RuntimeError,'ORIGINAL_FAILURE'):
                with stream_data.bound(catalog)as proof:
                    self.assertIsNot(catalog._data,original)
                    self.assertIs(catalog._data.__globals__['_catalog'],catalog._catalog)
                    self.assertEqual(catalog._data.__globals__['NAMESPACE'],catalog.NAMESPACE)
                    self.assertTrue(proof['namespace_table_selection_authority_GUC_and_all_sequences_unchanged'])
                    raise RuntimeError('ORIGINAL_FAILURE')
            self.assertIs(catalog._data,original)

    def test_pre_restore_fingerprint_error_cannot_skip_the_full_restore(self):
        events=[]
        def observe():events.append('OBSERVE');raise ValueError('FIRST_ARRAY_FAILURE')
        def restore():events.append('COMPLETE_DUMP_RESTORE');return {'restored':True}
        def verify(result):events.append('VERIFY_ALL_ROWS_SEQUENCES_ROLES');return result['restored']
        observed,restored,verified,failure=restoration.always(observe,restore,verify)
        self.assertEqual(events,['OBSERVE','COMPLETE_DUMP_RESTORE','VERIFY_ALL_ROWS_SEQUENCES_ROLES'])
        self.assertIsNone(observed);self.assertTrue(verified);self.assertEqual(str(failure[0]),'FIRST_ARRAY_FAILURE')


if __name__=='__main__':unittest.main()
