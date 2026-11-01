"""Local source and connection-lifecycle models only, zero ERP case credit."""
from pathlib import Path
from types import SimpleNamespace,ModuleType
from unittest.mock import patch
import importlib.util
import subprocess
import sys
import unittest

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('permanent_metadata_control',HERE/'system_metadata.py')
metadata=importlib.util.module_from_spec(spec);spec.loader.exec_module(metadata)


class MetadataControls(unittest.TestCase):
    def test_all_eleven_files_are_exact_published_originals(self):
        collector,binding=metadata.source()
        self.assertEqual(binding['byte_exact_original_files'],11)
        self.assertEqual(len(collector.queries()),27)
        for path in(HERE/'metadata').iterdir():
            if path.is_file():
                raw=subprocess.check_output(['/usr/bin/git','-C',str(HERE.parents[1]),'show',
                    metadata.SOURCE_COMMIT+':'+metadata.SOURCE_PREFIX+path.name])
                self.assertEqual(path.read_bytes(),raw)

    def test_pending_parent_stops_before_client_import_or_source_loading(self):
        with patch.object(metadata,'source',side_effect=AssertionError('TOO_EARLY')):
            with self.assertRaisesRegex(ValueError,'TERMINAL_JOIN37_INTAKE_PENDING'):
                metadata.capture_pair('postgresql://postgres@127.0.0.1:54322/cp6_rollback',b'')

    def test_foreign_host_port_database_or_fragment_refused(self):
        for url in('postgresql://postgres@remote.invalid:54322/cp6_rollback',
                    'postgresql://postgres@127.0.0.1:5432/cp6_rollback',
                    'postgresql://postgres@127.0.0.1:54322/postgres',
                    'postgresql://postgres@127.0.0.1:54322/cp6_rollback#anything'):
            with self.subTest(url=url),self.assertRaisesRegex(ValueError,'EXACT_LOCAL_CANDIDATE_URI'):
                metadata.local_urls(url)

    def test_readonly_repeatable_read_precedes_query_and_no_commit_even_on_failure(self):
        events=[]
        class Error(Exception):pass
        class Connection:
            def cursor(self):return self
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def execute(self,sql):
                self.assert_configured();events.append(sql)
            def assert_configured(self):
                if self.read_only is not True or self.isolation_level!='RR':raise AssertionError('NOT_READONLY_RR')
            def rollback(self):events.append('ROLLBACK')
            def close(self):events.append('CLOSE')
            def commit(self):raise AssertionError('UNEXPECTED_COMMIT')
        client=SimpleNamespace(Error=Error,IsolationLevel=SimpleNamespace(REPEATABLE_READ='RR'),connect=lambda url:Connection())
        def capture(cur):cur.assert_configured();events.append('CAPTURE');return {'control':True}
        value=metadata.one(client,'control',capture)
        self.assertEqual(value,{'control':True})
        self.assertEqual(events,['set local search_path=pg_catalog','CAPTURE','ROLLBACK','CLOSE'])
        events.clear()
        def fail(cur):raise RuntimeError('original')
        with self.assertRaisesRegex(RuntimeError,'original'):metadata.one(client,'control',fail)
        self.assertEqual(events,['set local search_path=pg_catalog','ROLLBACK','CLOSE'])

    def test_SQL_unavailability_is_explicit_and_never_writer_credit(self):
        class Error(Exception):sqlstate='42501'
        client=ModuleType('psycopg');client.Error=Error
        required=SimpleNamespace(qualified_receipt=lambda raw:{'head':'LABELLED_MODEL_PARENT'})
        collector=SimpleNamespace(capture=object(),capture_scheduler=object())
        with patch.object(metadata,'load',return_value=required),patch.object(metadata,'source',return_value=(collector,{})),\
             patch.object(metadata,'one',side_effect=Error()),patch.dict(sys.modules,{'psycopg':client}):
            value=metadata.capture_pair('postgresql://postgres@127.0.0.1:54322/cp6_rollback',b'LABELLED_MODEL')
        self.assertIs(value['all_metadata_captured'],False)
        self.assertIs(value['writer_closure'],False)
        self.assertEqual(value['actual_Native_case_credit'],0)
        self.assertTrue(all(v['status']=='READONLY_METADATA_UNAVAILABLE'for v in value['snapshots'].values()))


if __name__=='__main__':unittest.main()
