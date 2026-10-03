"""Financial test windows derived from real Native physical timestamps.

Fixtures can straddle midnight in the ERP timezone. Their transaction dates
must remain unchanged; report deltas must include every dated event being
compared. This changes only the oracle query, never a financial writer.
"""
from datetime import date, datetime
from zoneinfo import ZoneInfo

ERP_ZONE = ZoneInfo('Asia/Jakarta')


def window(day, now, *physical):
    day = date.fromisoformat(str(day))
    clock = datetime.fromisoformat(str(now).replace('Z', '+00:00'))
    assert clock.tzinfo is not None, 'NATIVE_FIXTURE_CLOCK_REQUIRES_OFFSET'
    end = clock.astimezone(ERP_ZONE).date()
    days = [day]
    for value in physical:
        at = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        assert at.tzinfo is not None, 'NATIVE_FIXTURE_PHYSICAL_REQUIRES_OFFSET'
        assert at <= clock, 'NATIVE_FIXTURE_EVENT_IS_IN_THE_FUTURE'
        days.append(at.astimezone(ERP_ZONE).date())
    assert day <= end, 'NATIVE_FIXTURE_DAY_IS_IN_THE_FUTURE'
    return {'from': str(min(days)), 'to': str(end), 'as_of': str(end)}


def native_window(cur, day, *physical):
    now = cur.execute('select clock_timestamp()').fetchone()[0]
    return window(day, now, *physical)
