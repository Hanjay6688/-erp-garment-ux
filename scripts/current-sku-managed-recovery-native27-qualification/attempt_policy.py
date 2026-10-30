"""Bound this qualification to one attempt and a real, unchanged WIB day.

The inherited auditor's date guard still marks a rollover INCOMPLETE. Only its
automatic whole-group retry is suppressed for this qualification. No financial
callback, clock, result or restoration operation is changed.
"""
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import json
import sys

JOB_BUDGET_SECONDS = 210 * 60
WIB = ZoneInfo('Asia/Jakarta')


def require_window(now=None):
    now = datetime.now(timezone.utc) if now is None else now
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError('SKU27_AWARE_REAL_CLOCK_REQUIRED')
    local = now.astimezone(WIB)
    midnight = (local + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    remaining = (midnight - local).total_seconds()
    if remaining <= JOB_BUDGET_SECONDS:
        raise ValueError('SKU27_INSUFFICIENT_WIB_DAY_WINDOW_BEFORE_RUNTIME')
    return dict(business_day=local.date().isoformat(), seconds_to_midnight=remaining,
                required_seconds=JOB_BUDGET_SECONDS, automatic_group_retry=False,
                product_clock_changed=False)


@contextmanager
def single_attempt(business_day):
    """Keep the first complete report, including failures; restore the caller."""
    original = business_day.with_retry

    def once(group, run_once, rows_of, keep_first=None):
        first = run_once()
        rolled = sorted(k for k, row in (rows_of(first) or {}).items()
                        if row.get('business_day_rollover'))
        if rolled:
            print(json.dumps(dict(group=group, business_day_rollover='KEPT_FIRST_RESULT',
                                  rolled_cases=rolled, automatic_group_retry=False)), flush=True)
            business_day.annotate('KEPT_FIRST_RESULT', group, rolled)
        return first

    business_day.with_retry = once
    try:
        yield
    finally:
        business_day.with_retry = original


if __name__ == '__main__':
    if sys.argv[1:] != ['--require-window']:
        raise ValueError('SKU27_DECLARED_CLOCK_CHECK_ONLY')
    print(json.dumps(require_window(), sort_keys=True))
