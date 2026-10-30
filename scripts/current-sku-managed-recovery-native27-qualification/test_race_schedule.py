"""Threaded protocol doubles; these tests confer zero Native/race credit."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import importlib.util
import json
import unittest

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('sku27_schedule_controls',HERE/'race_schedule.py')
s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s)
State=s.psycopg.pq.TransactionStatus
POCKET=json.loads((HERE/'RACE_CONTRACT.json').read_bytes())['actual_pocket_function_row19']


class DatabaseError(Exception):
    def __init__(self,message,sqlstate='P0001'):
        self.sqlstate=sqlstate;self.diag=SimpleNamespace(message_primary=message)


class Database:
    def __init__(self,commit,*,first='POCKET_PERIOD_BUSY: fixture',drift=False,metadata=False):
        self.release=commit;self.first=first;self.drift=drift;self.metadata=metadata
        self.pid=100;self.holder=None;self.calls=0;self.value=0;self.noeffects=0;self.events=[]

    def connect(self):
        db=self;db.pid+=1
        class Connection:
            def __init__(self):
                self.pid=db.pid;self.info=SimpleNamespace(host='localhost',port=54322,transaction_status=State.IDLE)
            def __enter__(self):return self
            def __exit__(self,kind,*_):self.rollback()if kind else self.commit()
            def cursor(self):return Cursor(self)
            def commit(self):
                if self is db.holder and self.info.transaction_status==State.INTRANS:
                    db.events.append('holder commit');db.value+=1
                self.info.transaction_status=State.IDLE
            def rollback(self):
                if self is db.holder and self.info.transaction_status==State.INTRANS:db.events.append('holder rollback')
                self.info.transaction_status=State.IDLE
        class Cursor:
            def __init__(self,connection):self.connection=connection;self.result=None
            def __enter__(self):return self
            def __exit__(self,*_):pass
            def execute(self,sql):
                self.connection.info.transaction_status=State.INTRANS
                if sql=='select current_database()':self.result=('cp6_auditor_race',)
                elif sql=='select pg_backend_pid()':self.result=(self.connection.pid,)
                elif sql.startswith('set local lock_timeout='):self.result=None
                else:raise AssertionError(sql)
                return self
            def fetchone(self):return self.result
        return Connection()

    def first_op(self,cursor):
        self.holder=cursor.connection;self.events.append('holder operation');return {'first':'held'}

    def second_op(self,cursor):
        self.calls+=1
        if self.calls==1:
            assert self.holder.info.transaction_status==State.INTRANS
            self.events.append('busy attempt')
            if self.drift:self.value+=1
            if self.first is None:return {'unexpected':'early success'}
            raise DatabaseError(self.first)
        assert self.holder.info.transaction_status==State.IDLE
        self.events.append('retry')
        if self.release:raise DatabaseError('STALE_VERSION: fixture')
        self.value+=1;return {'fresh':'committed'}

    def capture(self,cursor):
        row=deepcopy(POCKET)
        if self.metadata:row[0]+='changed'
        return dict(catalog={'functions':{'erp.pocket_period_lock_v1()':row}},data_and_sequences={'test':self.value})

    def unchanged(self,cursor,before,label):
        assert before==self.capture(cursor),'FULL_CENSUS_CHANGED'
        self.noeffects+=1
        return dict(all22_and_all_current_rows_sequences_unchanged=True,before_sha256='double',after_sha256='double',dropped_fields=[])


class Schedule(unittest.TestCase):
    def run_double(self,db):
        with patch.object(s.psycopg,'Error',DatabaseError):
            return s.run(db,db.first_op,db.second_op,db.release,same_uuid=False,native_fixture=db)

    def test_commit_busy_noeffect_release_stale_retry_noeffect(self):
        db=Database(True);_,proof,outcome=self.run_double(db)
        self.assertEqual(db.events,['holder operation','busy attempt','holder commit','retry'])
        self.assertEqual(db.noeffects,2);self.assertEqual(db.value,1)
        self.assertFalse(outcome['ok']);s.require_contention(proof,False)

    def test_abort_busy_noeffect_release_same_request_recovers(self):
        db=Database(False);_,proof,outcome=self.run_double(db)
        self.assertEqual(db.events,['holder operation','busy attempt','holder rollback','retry'])
        self.assertEqual(db.noeffects,1);self.assertEqual(db.value,1)
        self.assertTrue(outcome['ok']);s.require_contention(proof,False)

    def test_wrong_refusal_and_early_success_do_not_trigger_retry(self):
        for first in ('permission denied','STALE_VERSION: premature',None):
            with self.subTest(first=first):
                db=Database(True,first=first)
                with self.assertRaisesRegex(AssertionError,'EXACT_POCKET_BUSY'):self.run_double(db)
                self.assertEqual(db.calls,1);self.assertIn('holder rollback',db.events)

    def test_busy_drift_refuses_and_rolls_back_holder_before_retry(self):
        db=Database(True,drift=True)
        with self.assertRaisesRegex(AssertionError,'FULL_CENSUS_CHANGED'):self.run_double(db)
        self.assertEqual(db.calls,1);self.assertIn('holder rollback',db.events)

    def test_actual_lock_metadata_cannot_drift(self):
        db=Database(True,metadata=True)
        with self.assertRaisesRegex(AssertionError,'ACTUAL_POCKET_TRY_LOCK_CONTRACT_CHANGED'):self.run_double(db)
        self.assertEqual(db.calls,0)

    def test_same_uuid_retains_original_real_blocking_protocol(self):
        expected=('held',{'kind':'BLOCKED','holder_blocks_worker':True},{'ok':True})
        seen=[]
        tools=SimpleNamespace(two_sessions=lambda *args:(seen.append(args)or expected))
        self.assertIs(s.run(tools,'first','second',True,same_uuid=True,native_fixture=None),expected)
        self.assertEqual(seen,[('first','second',True)])
        s.require_contention(expected[1],True)
        with self.assertRaises(AssertionError):s.require_contention({'kind':'NO_CONTENTION'},True)

    def test_fail_fast_proof_requires_every_noeffect_and_release_field(self):
        db=Database(False);_,proof,_=self.run_double(db)
        for key in ('distinct_actual_backend_pids','holder_in_transaction_at_refusal','retry_only_after_holder_release'):
            bad=deepcopy(proof);bad[key]=False
            with self.subTest(key=key),self.assertRaises(AssertionError):s.require_contention(bad,False)
        for key,value in (('dropped_fields',['sequence']),('after_sha256','different'),('all22_and_all_current_rows_sequences_unchanged',False)):
            bad=deepcopy(proof);bad['complete_busy_no_effect'][key]=value
            with self.subTest(key=key),self.assertRaises(AssertionError):s.require_contention(bad,False)
        with self.assertRaises(AssertionError):s.require_busy(dict(ok=False,sqlstate='55P03',message='POCKET_PERIOD_BUSY: wrong SQLSTATE'))


if __name__=='__main__':unittest.main()
