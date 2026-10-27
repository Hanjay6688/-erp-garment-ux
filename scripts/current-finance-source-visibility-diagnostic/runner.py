"""Prepared Native source-visibility case; never a runtime PASS without execution.

The posting starts in a child transaction before the report snapshot, then
commits after journal/line chunks. Counts of the later book/cash families stay
constant. This probes a boundary the accepted post-snapshot kasbon race did not.
The outer qualification must install the exact readonly composition and restore
its full preinstall database dump after this committed fixture.
"""
from pathlib import Path
import importlib.util
import json
import psycopg

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('retained_fresh_finance_race',
    ROOT / 'scripts/current-finance-reader-source-race-qualification/runner.py')
race = importlib.util.module_from_spec(spec)
spec.loader.exec_module(race)
finance = race.capture
CASE = 'FINANCE_PREEXISTING_CHILD_TRANSACTION_COMMITS_AFTER_JOURNAL_SCAN'


def family_counts(cur, as_of):
    return dict(zip(finance.FAMILIES, cur.execute('''select
      (select count(*) from erp.journal_entries where transaction_date<=%s),
      (select count(*) from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id where j.transaction_date<=%s),
      (select count(*) from erp.account_daily_balances where balance_date<=%s),
      (select count(*) from erp.cash_accounts)''', (as_of, as_of, as_of)).fetchone()))


def exercise(conn, cur, database, url, report):
    declaration = json.loads(Path(__file__).with_name('PREPARED_SOURCES.json').read_bytes())
    assert declaration['allow_database_execution'] is True, 'PREPARED_SOURCE_VISIBILITY_EXECUTION_NOT_ADMITTED'
    assert conn.info.host in ('localhost', '127.0.0.1') and conn.info.port == 54322
    assert cur.execute('select current_database()').fetchone() == ('cp6_rollback',)
    report.update(case_id=CASE, status='INCOMPLETE', diagnostic_only=True,
                  actual_cron_claim=False, production_go=False, manual_committed_steps=0,
                  previous_accepted_post_snapshot_race_remains_valid=True)
    race.bounded(cur)
    granted, _ = database._foundation(cur)
    today = cur.execute("select(statement_timestamp()at time zone'Asia/Jakarta')::date").fetchone()[0]
    seed = race.base.setup(cur, today)
    cid = finance.start(cur, finance.query(today))
    dates = race.capture_row(cur, cid)['dates']
    before_signature, before_counts = finance.independent_signature(cur, dates['as_of'])
    old_journals = [str(row[0]) for row in cur.execute('select id from erp.journal_entries').fetchall()]
    if granted:
        cur.execute('revoke usage on schema erp from authenticated')
    conn.commit()
    report.update(capture_id=str(cid), dates=dates, before_counts=before_counts,
                  before_signature=before_signature)
    with psycopg.connect(url) as holder, holder.cursor() as h:
        race.bounded(h)
        parent_xid = int(h.execute('select pg_current_xact_id()::text').fetchone()[0])
        assert parent_xid < 2**32, 'DISPOSABLE_CASE_REQUIRES_FIRST_XID_EPOCH'
        holder_pid = h.execute('select pg_backend_pid()').fetchone()[0]
        h.execute('savepoint d17_preexisting_native_posting')
        grant = not h.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]
        if grant:
            h.execute('grant usage on schema erp to authenticated')
        posted = finance.c17.kasbon_give(h, seed['contractor'], seed['bank'], '900.00', seed['day'])
        report['native_kasbon'] = posted['advance']
        finance.b.api.admin(h)
        if grant:
            h.execute('revoke usage on schema erp from authenticated')
        children = h.execute('select id::text,xmin::text from erp.journal_entries where not(id=any(%s::uuid[])) order by id',
                             (old_journals,)).fetchall()
        assert children and all(int(xid) > parent_xid for _, xid in children), 'NATIVE_CHILD_XID_NOT_OBSERVED'
        after_in_holder = family_counts(h, dates['as_of'])
        assert after_in_holder['journal'] > before_counts['journal']
        assert after_in_holder['line'] > before_counts['line']
        assert all(after_in_holder[k] == before_counts[k] for k in ('book', 'cash')), 'RACE_REQUIRES_CONSTANT_LATER_FAMILY_COUNTS'
        h.execute('release savepoint d17_preexisting_native_posting')
        first, stored, observed = race.fresh_step(url, cid)
        report['manual_committed_steps'] += 1
        report['report_step'] = observed
        assert first['state'] == 'RUNNING' and first['units_done'] == 1
        snapshot = stored['report_snapshot']
        assert snapshot is not None, 'FRESH_REPORT_SNAPSHOT_REQUIRED_FOR_CHILD_XID_CASE'
        plan = stored['plan']
        assert plan['journal']['chunks'] == plan['line']['chunks'] == 1, 'SMALL_RACE_REQUIRES_ONE_CHUNK_PER_EARLY_FAMILY'
        visibility = []
        for journal, xid in children:
            visible = h.execute('select pg_visible_in_snapshot(%s::xid8,%s::pg_snapshot)', (xid, snapshot)).fetchone()[0]
            visibility.append(dict(journal_id=journal, child_xid=xid, visible=visible))
        parent_visible = h.execute('select pg_visible_in_snapshot(%s::xid8,%s::pg_snapshot)',
                                   (str(parent_xid), snapshot)).fetchone()[0]
        assert parent_visible is False, 'PREEXISTING_PARENT_NOT_IN_REPORT_SNAPSHOT'
        report.update(holder_pid=holder_pid, parent_xid=str(parent_xid), parent_visible=parent_visible,
                      child_visibility=visibility, report_snapshot=snapshot,
                      child_posting_precedes_report_snapshot=True,
                      observed_source_counts_in_uncommitted_holder=after_in_holder,
                      source_commit_after_journal_and_line_chunks=False)
        early = []
        for expected_done in (2, 3):
            state, row, observation = race.fresh_step(url, cid)
            report['manual_committed_steps'] += 1
            early.append(observation)
            assert state['state'] == 'RUNNING' and state['units_done'] == expected_done, state
            assert row['report_snapshot'] == snapshot
        report['early_chunks_before_source_commit'] = early
        holder.commit()
        report['source_commit_after_journal_and_line_chunks'] = True
    state, row, trail = race.finish(url, cid, report, 'later_chunks_after_source_commit')
    race.bounded(cur)
    current_signature, current_counts = finance.independent_signature(cur, dates['as_of'])
    assert current_counts == after_in_holder
    report.update(final_state=state, stored_signature=row['book_signature'],
                  current_signature=current_signature, current_counts=current_counts,
                  signature_matches_before=row['book_signature'] == before_signature,
                  signature_matches_after=row['book_signature'] == current_signature,
                  child_transaction_closed=True)
    if state['state'] == 'READY':
        result = finance.call(cur, 'select cp7_finance_capture.result(%s)', (cid,))
        report.update(unsafe_ready_observed=True, result_escaped=True,
                      mixed_signature_confirmed=result['book_signature'] not in (before_signature, current_signature))
        conn.rollback()
        raise AssertionError('PREEXISTING_CHILD_TRANSACTION_MUST_NOT_SEAL_MIXED_BOOK')
    assert state['state'] == 'FAILED' and state['failure_code'] == 'CP7_FINANCE_CAPTURE_SOURCE_CHANGED', state
    assert row['source_hash'] is row['book_signature'] is None
    conn.rollback()
    report.update(status='PASS', unsafe_ready_observed=False, result_escaped=False,
                  changed_source_refused_before_seal=True)
