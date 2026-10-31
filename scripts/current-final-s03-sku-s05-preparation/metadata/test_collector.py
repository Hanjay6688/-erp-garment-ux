"""Administrative preconditions only; labelled cursor models, zero Native SQL."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import importlib.util
import unittest

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('system_metadata_collector_control',HERE/'collector.py')
collector=importlib.util.module_from_spec(spec);spec.loader.exec_module(collector)


class Cursor:
    def __init__(self,*,autocommit=False,host='127.0.0.1',port=54322,path='pg_catalog',before=None,after=None):
        self.connection=SimpleNamespace(autocommit=autocommit,info=SimpleNamespace(host=host,port=port))
        self.path=path;self.calls=[]
        self.before=before or('cp6_rollback','postgres','postgres','on','repeatable read','170005','control','7:9:','pg_catalog')
        self.after=after or self.before[:5]+self.before[7:]
    def execute(self,sql):
        self.calls.append(sql)
        if sql=="select pg_catalog.current_setting('search_path')":self.value=(self.path,)
        elif 'server_version_num'in sql:self.value=self.before
        elif 'pg_current_snapshot'in sql:self.value=self.after
        elif 'to_regclass'in sql:self.value=(False,)
        else:self.value=([],)
        return self
    def fetchone(self):return self.value


class AdministrativeGuards(unittest.TestCase):
    def test_autocommit_refused_before_even_loading_query_bundle(self):
        cur=Cursor(autocommit=True)
        with patch.object(collector,'queries',side_effect=AssertionError('TOO_EARLY')):
            with self.assertRaisesRegex(ValueError,'ONE_EXISTING_READONLY_TRANSACTION'):collector.capture(cur)
        self.assertEqual(cur.calls,[])

    def test_foreign_host_or_port_refused_before_SQL(self):
        for change in (dict(host='remote.example.invalid'),dict(port=5432)):
            cur=Cursor(**change)
            with self.subTest(change=change),patch.object(collector,'queries',return_value={}):
                with self.assertRaisesRegex(ValueError,'LOCAL_DISPOSABLE_ONLY'):collector.capture(cur)
            self.assertEqual(cur.calls,[])

    def test_untrusted_search_path_refused_before_metadata(self):
        for path in ('public','"$user", public','pg_catalog, public',''):
            cur=Cursor(path=path)
            with self.subTest(path=path),patch.object(collector,'queries',return_value={}):
                with self.assertRaisesRegex(ValueError,'SEARCH_PATH_PG_CATALOG'):collector.capture(cur)
            self.assertEqual(len(cur.calls),1)

    def test_database_authority_readonly_and_isolation_must_all_match(self):
        correct=Cursor().before
        for index,value in [(0,'postgres'),(1,'authenticated'),(2,'authenticated'),(3,'off'),(4,'read committed')]:
            before=list(correct);before[index]=value;cur=Cursor(before=tuple(before))
            with self.subTest(index=index),patch.object(collector,'queries',return_value={}):
                with self.assertRaisesRegex(ValueError,'READONLY_REPEATABLE_ADMINISTRATIVE_SNAPSHOT'):collector.capture(cur)

    def test_changed_snapshot_or_search_path_is_refused(self):
        for change in [(5,'9:10:'),(6,'public')]:
            after=list(Cursor().after);after[change[0]]=change[1];cur=Cursor(after=tuple(after))
            with self.subTest(change=change),patch.object(collector,'queries',return_value={'control':'select control'}):
                with self.assertRaisesRegex(ValueError,'SNAPSHOT_OR_AUTHORITY_CHANGED'):collector.capture(cur)

    def test_success_keeps_zero_case_credit_and_closure_open(self):
        with patch.object(collector,'queries',return_value={'control':'select control','cron_jobs':'select cron-control'}):
            value=collector.capture(Cursor())
        self.assertEqual(value['Native_cases'],0)
        self.assertIs(value['writer_closure'],False)
        self.assertIs(value['permission_closure'],False)
        self.assertEqual(value['groups']['cron_jobs']['status'],'RELATION_ABSENT')
        self.assertEqual(value['search_path'],'pg_catalog')


if __name__=='__main__':unittest.main()
