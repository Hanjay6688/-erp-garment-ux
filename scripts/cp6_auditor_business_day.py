"""Business-day control of the auditor runtime (Sol retest of 8116800c, 10 Oct 2026: OPEN_TOOLING S3
ATTENTION_WIB_MIDNIGHT_FIXTURE).

Every group of the runtime (savepoint, race, HTTP and browser) reads the WIB date once at setup and plans its cases and
fixtures with it, while the product reads the date per statement (statement_timestamp() at time zone 'Asia/Jakarta').
attention284 on 8116800c (run 37958882487, job 113916327717) ran from 23:33 to 00:08 WIB: its browser cases built
fixtures for 9 Oct while the server already counted 10 Oct (CP7_NOTA_AFTER_PERIOD, '2' !== '1'), and the next attempt on
the same commit passed 286/286. The first failure is kept in docs/cp7/evidence/sol-p20-k4-20261009/.

The control, applied by every mode:
  * the WIB date is read from the database right before and right after each case;
  * a case that starts on another date than the one its group was planned with, or whose date changes while it runs,
    cannot show what it was written to show: its row records the three dates and business_day_rollover=true, and a
    PASS becomes INCOMPLETE (status_before_rollover=PASS). FAIL, COUNTEREXAMPLE and INCOMPLETE are never changed;
  * the group is run once more from a fresh copy (a new setup, a new date, cases and fixtures planned again) only when
    the date change explains every row that did not pass and the group itself finished cleanly. A row failed by a
    runtime check (boundary, public schema, leaked session or lock) or a malformed case result is never explained by a
    date; such a row, any other non-PASS row, a group error, a missing case, a copy left behind or a failed cleanup
    keeps the first result as it is;
  * the first attempt is kept whole in the final report (business_day_first_attempt) and its rows stay in the job log.
No assertion, oracle or product clock is changed; a second change of date in the same run stays INCOMPLETE.
"""
import json

WIB_DAY = "select (statement_timestamp() at time zone 'Asia/Jakarta')::date"


def wib_day(cur):
    return cur.execute(WIB_DAY).fetchone()[0]


def guard(row, planned, before, after):
    """Mark one case row; returns True when the case ran on another WIB date than its group was planned with."""
    row['business_day'] = dict(planned=str(planned), before=str(before), after=str(after))
    if str(planned) == str(before) == str(after):
        return False
    row['business_day_rollover'] = True
    if row.get('status') == 'PASS':
        row['status_before_rollover'] = 'PASS'
        row['status'] = 'INCOMPLETE'
        row.setdefault('error', 'AUDITOR_BUSINESS_DAY_ROLLOVER')
    return True


SCENARIO_ERRORS = ('AUDITOR_CASE_RESULT_NOT_A_DICT', 'AUDITOR_CASE_RESULT_NOT_AN_OBJECT')


def explained(row):
    """A row the change of date accounts for: not a runtime check (boundary, schema, session, lock) and not a malformed
    case result, which a date cannot cause."""
    return bool(row.get('business_day_rollover')) and not row.get('harness_check_failed') \
        and 'status_outside_vocabulary' not in row and row.get('error') not in SCENARIO_ERRORS


def retry_allowed(report, rows):
    """True when a change of WIB date explains every row that did not pass and nothing else went wrong in the group."""
    rows = list((rows or {}).values())
    if report.get('error') or report.get('missing') or report.get('database_remaining') or report.get('cleanup_failures'):
        return False
    if report.get('complete_boundary_restored') is False:
        return False
    if not any(r.get('business_day_rollover') for r in rows):
        return False
    return all(explained(r) for r in rows if r.get('status') != 'PASS')


def with_retry(group, run_once, rows_of, keep_first=None):
    """Run a group; run it once more from a fresh copy when retry_allowed. The first attempt is kept in the result (and
    handed to keep_first, which saves it before the second attempt starts)."""
    first = run_once()
    if not retry_allowed(first, rows_of(first)):
        return first
    rolled = sorted(k for k, r in rows_of(first).items() if r.get('business_day_rollover'))
    print(json.dumps(dict(group=group, business_day_rollover='RERUN_FROM_FRESH_COPY', rolled_cases=rolled,
                          first_attempt_final={k: r.get('status') for k, r in rows_of(first).items()})), flush=True)
    if keep_first:
        keep_first(first)
    second = run_once()
    second['business_day_retried'] = True
    second['business_day_first_attempt'] = first
    return second
