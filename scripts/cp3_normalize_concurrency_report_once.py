#!/usr/bin/env python3
from pathlib import Path

PATH = Path('scripts/cp3_concurrency_harness.py')
OLD = '''        issues = one(conn, "select coalesce(sum(issue_count),0) from erp.run_v2614_attendance_hpp_integrity_checks()")
        conn.commit()
    if journals != 1 or issues != 0: raise AssertionError(f"idempotency/integrity mismatch journals={journals} issues={issues}")
'''
NEW = '''        issues = one(conn, "select coalesce(sum(issue_count),0) from erp.run_v2614_attendance_hpp_integrity_checks()")
        conn.commit()
    issues = int(issues)
    if journals != 1 or issues != 0: raise AssertionError(f"idempotency/integrity mismatch journals={journals} issues={issues}")
'''


def main() -> None:
    text = PATH.read_text()
    if text.count(OLD) != 1:
        raise SystemExit('integrity report normalization anchor is missing or ambiguous')
    text = text.replace(OLD, NEW, 1)
    if text.count('issues = int(issues)') != 1:
        raise SystemExit('integrity issue count was not normalized exactly once')
    for assertion in (
        'assert_exactly_one(results, "sewing capacity race")',
        'assert_exactly_one(results, "overlapping range race")',
        'assert_exactly_one(results, "post versus cancel race")',
        'same-key same-payload should both succeed',
    ):
        if assertion not in text:
            raise SystemExit(f'concurrency assertion changed unexpectedly: {assertion}')
    PATH.write_text(text)


if __name__ == '__main__':
    main()
