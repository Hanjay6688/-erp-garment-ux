"""Read unchanged work JSON in UTC, restoring the caller's transaction setting."""
from psycopg.pq import TransactionStatus
from datetime import datetime


def read(cur, reader, observed):
    prior = cur.execute("select current_setting('TimeZone')").fetchone()[0]
    try:
        raw = reader()
        entry = dict(caller_timezone=prior, raw_job_id=raw['job_id'],
                     raw_created_at=raw['created_at'])
        observed.setdefault('work_reads', []).append(entry)
        actual = cur.execute("select set_config('TimeZone','UTC',true)").fetchone()[0]
        if actual != 'UTC':
            raise AssertionError('CHOICE_WORK_OBSERVER_UTC_NOT_SET')
        work = reader()
        after = cur.execute("select current_setting('TimeZone')").fetchone()[0]
        entry.update(observed_timezone=after, job_id=work['job_id'], created_at=work['created_at'])
        if after != 'UTC':
            raise AssertionError('CHOICE_WORK_READER_CHANGED_OBSERVER_ZONE')
        if work['job_id'] != raw['job_id'] or datetime.fromisoformat(work['created_at']) != datetime.fromisoformat(raw['created_at']):
            raise AssertionError('CHOICE_WORK_CHANGED_DURING_OBSERVATION')
        return work
    finally:
        if cur.connection.info.transaction_status != TransactionStatus.INERROR:
            restored = cur.execute("select set_config('TimeZone',%s,true)", (prior,)).fetchone()[0]
            if restored != prior:
                raise AssertionError('CHOICE_WORK_OBSERVER_CALLER_ZONE_NOT_RESTORED')
