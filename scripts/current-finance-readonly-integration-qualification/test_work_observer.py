from datetime import datetime, timezone
from types import SimpleNamespace
from zoneinfo import ZoneInfo
import unittest
from psycopg.pq import TransactionStatus
import work_observer


class Cursor:
    def __init__(self, zone):
        self.zone = zone
        self.connection = SimpleNamespace(info=SimpleNamespace(transaction_status=TransactionStatus.INTRANS))
        self.commands = []

    def execute(self, sql, args=()):
        self.commands.append((sql, args))
        if sql == "select current_setting('TimeZone')":
            self.answer = self.zone
        elif sql == "select set_config('TimeZone','UTC',true)":
            self.zone = self.answer = 'UTC'
        elif sql == "select set_config('TimeZone',%s,true)":
            self.zone = self.answer = args[0]
        else:
            raise AssertionError('UNEXPECTED_OBSERVER_OPERATION:' + sql)
        return self

    def fetchone(self):
        return (self.answer,)


class ExactWorkObserver(unittest.TestCase):
    def test_same_instant_across_transaction_zones_keeps_strict_json_equality(self):
        instant = datetime(2026, 10, 27, 12, 36, 0, 123456, tzinfo=timezone.utc)
        cur = Cursor('Asia/Jakarta')
        def reader():
            return dict(job_id='same-job', created_at=instant.astimezone(ZoneInfo(cur.zone)).isoformat(), payload={'amount':'900.00'})
        old_first = reader()
        cur.zone = 'UTC'
        self.assertNotEqual(old_first['created_at'], reader()['created_at'])
        cur.zone = 'Asia/Jakarta'
        observed = {}
        first = work_observer.read(cur, reader, observed)
        self.assertEqual(cur.zone, 'Asia/Jakarta')
        cur.zone = 'UTC'
        second = work_observer.read(cur, reader, observed)
        self.assertEqual(first, second)
        self.assertEqual([x['caller_timezone'] for x in observed['work_reads']], ['Asia/Jakarta', 'UTC'])
        self.assertEqual(first['payload'], {'amount':'900.00'})

    def test_changed_identity_and_timestamp_are_not_rewritten(self):
        cur = Cursor('Asia/Jakarta')
        work = dict(job_id='different-job', created_at='2026-10-27T12:36:00.123457+00:00')
        self.assertIs(work_observer.read(cur, lambda: work, {}), work)
        self.assertEqual(cur.zone, 'Asia/Jakarta')

    def test_reader_failure_restores_zone_and_cannot_appear_successful(self):
        cur = Cursor('Asia/Jakarta')
        observed = {}
        def failed():
            raise ValueError('ACTUAL_READ_FAILED')
        with self.assertRaisesRegex(ValueError, 'ACTUAL_READ_FAILED'):
            work_observer.read(cur, failed, observed)
        self.assertEqual(cur.zone, 'Asia/Jakarta')
        self.assertEqual(observed, {})

    def test_aborted_transaction_does_not_mask_original_error(self):
        cur = Cursor('Asia/Jakarta')
        def failed():
            cur.connection.info.transaction_status = TransactionStatus.INERROR
            raise ValueError('ACTUAL_DATABASE_ERROR')
        with self.assertRaisesRegex(ValueError, 'ACTUAL_DATABASE_ERROR'):
            work_observer.read(cur, failed, {})
        self.assertEqual(len(cur.commands), 1)

    def test_changed_identity_between_reads_is_refused(self):
        cur = Cursor('Asia/Jakarta')
        values = iter([dict(job_id='one', created_at='2026-10-27T12:00:00+00:00'),
                       dict(job_id='two', created_at='2026-10-27T12:00:00+00:00')])
        with self.assertRaisesRegex(AssertionError, 'WORK_CHANGED_DURING'):
            work_observer.read(cur, lambda: next(values), {})
        self.assertEqual(cur.zone, 'Asia/Jakarta')


if __name__ == '__main__':
    unittest.main()
