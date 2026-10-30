"""Negative oracle controls using labelled row doubles, never Native credit."""
from copy import deepcopy
from pathlib import Path
import importlib.util
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('s03_history_under_test', HERE / 'pool_history.py')
h = importlib.util.module_from_spec(spec); spec.loader.exec_module(h)


def rows():
    pool = dict(id='pool', status='ACTIVE', row_version=2, post_journal_entry_id='post',
                source_manifest={'source': 'unchanged'}, source_manifest_sha256='frozen-hash',
                cancellation_journal_entry_id=None, cancellation_reason=None, cancelled_by=None, cancelled_at=None)
    line = dict(id='line1', journal_entry_id='post', account_id='WIP', customer_id=None,
                vendor_id=None, contractor_id='mandor', po_id='po', product_id=None,
                debit=1000.03, credit=0, description='Original source')
    opposite = dict(line, id='line2', account_id='OFFSET', debit=0, credit=1000.03)
    active = dict(pool=pool, sources=[{'id': 'source', 'amount': 1000.03}],
                  allocations=[{'id': 'allocation-row', 'amount': 1000.03}], links=[{'id': 'link'}],
                  choice_allocation=[{'id': 'allocation'}],
                  journal=dict(id='post', status='POSTED', source_type='ATTENDANCE_HPP_POOL', source_id='pool'),
                  lines=[line, opposite])
    current = deepcopy(active)
    current['pool'].update(status='CANCELLED', row_version=3, cancellation_journal_entry_id='inverse',
                           cancellation_reason='Owner checked', cancelled_by='actor', cancelled_at='2026-10-30T08:00:00+00:00')
    current['journal']['status'] = 'REVERSED'
    cancellation = dict(journals=[dict(id='inverse', source_type='JOURNAL_REVERSAL', source_id='post',
        reversal_of_id='post', status='POSTED', economic_date='2026-10-30', transaction_date='2026-10-30')],
        lines=[dict(r, id='inverse-' + r['id'], journal_entry_id='inverse', debit=r['credit'],
                    credit=r['debit'], description='Reversal: ' + r['description']) for r in active['lines']],
        choice_reversals=[dict(id='undo', allocation_id='allocation', journal_id='inverse',
                              app_user='actor', reason='Owner checked')],
        expected_economic_date='2026-10-30', expected_book_date='2026-10-30')
    return active, current, cancellation


class RowsOnlyDouble:
    def __init__(self, state, cancellation):
        self.state, self.cancellation, self.native_calls = state, cancellation, 0

    def native(self, cur, sql, params):
        assert sql == "select erp.validate_attendance_hpp_pool_v1(%s)->>'validation'"
        self.native_calls += 1
        return 'PASS'  # Labelled source double; not actual Native validation.

    def one(self, cur, sql, params):
        assert sql.startswith('select '), sql
        tables = {'erp.attendance_hpp_pool_sources': 'sources', 'erp.attendance_hpp_pool_allocations': 'allocations',
                  'erp.attendance_hpp_journal_line_links': 'links', 'cp7_attendance_choice.allocations_v1 r': 'choice_allocation'}
        for table, key in tables.items():
            if table in sql:
                return deepcopy(self.state[key])
        if 'allocation_reversals_v1' in sql:
            return deepcopy(self.cancellation['choice_reversals'])
        if 'reversal_of_id=%s' in sql:
            return deepcopy(self.cancellation['journals'])
        if 'journal_lines' in sql:
            return deepcopy(self.state['lines'] if params[0] == 'post' else self.cancellation['lines'])
        if 'journal_entries' in sql:
            return deepcopy(self.state['journal'])
        if "at time zone 'Asia/Jakarta'" in sql:
            return self.cancellation['expected_economic_date']
        if 'resolve_accounting_transaction_date' in sql:
            return self.cancellation['expected_book_date']
        raise AssertionError(sql)


class CancelledHistoryControls(unittest.TestCase):
    def test_prior_pool_disappearance_and_duplicate_observation_refuse(self):
        active, _, _ = rows()
        history = {'pool': {'active': active, 'cancelled': None}}
        h.require_observed(history, [active['pool']])
        for observed in ([], [active['pool'], active['pool']]):
            with self.assertRaisesRegex(ValueError, 'EVERY_PRIOR_POOL_PRESENT_EXACTLY_ONCE'):
                h.require_observed(history, observed)

    def test_known_historical_pool_cannot_change_to_draft_or_voided(self):
        active, _, _ = rows()
        history = {'pool': {'active': active, 'cancelled': None}}
        for status in ('DRAFT', 'VOIDED'):
            with self.assertRaisesRegex(ValueError, 'ACTIVE_OR_CANCELLED_REQUIRED'):
                h.observe(None, object(), dict(active['pool'], status=status), history)

    def test_full_cancelled_lineage_and_inverse_pass_without_current_eligibility(self):
        active, current, cancellation = rows()
        self.assertFalse(h.checked_cancelled(active, current, cancellation)['current_allocation_eligibility_claim'])

    def test_missing_active_authority_refuses_before_any_read(self):
        _, current, _ = rows()
        with self.assertRaisesRegex(ValueError, 'CANCELLED_WITHOUT_PRE_CANCEL_ACTIVE_AUTHORITY'):
            h.observe(None, object(), current['pool'], {})

    def test_actual_active_route_is_required_and_first_authority_is_never_replaced(self):
        active, _, cancellation = rows(); f = RowsOnlyDouble(active, cancellation); history = {}
        h.observe(None, f, active['pool'], history)
        self.assertEqual(f.native_calls, 1)
        f.state = deepcopy(active); f.state['sources'][0]['amount'] = 999
        with self.assertRaisesRegex(ValueError, 'NATIVE_VALIDATED_ACTIVE_AUTHORITY_CHANGED'):
            h.observe(None, f, f.state['pool'], history)
        self.assertEqual(history['pool']['active'], active)

    def test_cancelled_history_survives_later_decision_reverse_and_other_pool_cancellation(self):
        active, current, cancellation = rows(); f = RowsOnlyDouble(active, cancellation); history = {}
        h.observe(None, f, active['pool'], history); f.state = current
        first = h.observe(None, f, current['pool'], history)
        # Current decision and current PO HPP are intentionally not historical authority.
        f.current_decision = None; f.current_HPP_after_another_pool_cancel = 'different'
        self.assertEqual(h.observe(None, f, current['pool'], history), first)
        self.assertEqual(f.native_calls, 1)

    def test_all_immutable_sources_allocations_links_manifest_and_original_lines_refuse_changes(self):
        for field in ('sources', 'allocations', 'links', 'choice_allocation', 'lines', 'manifest', 'hash', 'header'):
            with self.subTest(field=field):
                active, current, cancellation = rows()
                if field in h.IMMUTABLE: current[field][0]['unexpected'] = 'changed'
                elif field == 'manifest': current['pool']['source_manifest'] = {'changed': True}
                elif field == 'hash': current['pool']['source_manifest_sha256'] = 'changed'
                else: current['journal']['source_id'] = 'other'
                with self.assertRaises(ValueError): h.checked_cancelled(active, current, cancellation)

    def test_symmetric_rewrite_of_original_and_inverse_is_not_accepted(self):
        active, current, cancellation = rows()
        current['lines'][0]['debit'] = 999
        cancellation['lines'][0]['credit'] = 999
        with self.assertRaisesRegex(ValueError, 'IMMUTABLE_LINES_CHANGED'):
            h.checked_cancelled(active, current, cancellation)

    def test_inverse_amount_dimensions_identity_dates_duplicate_and_ownership_refuse(self):
        for field in ('amount', 'dimension', 'link', 'economic', 'book', 'duplicate', 'owner', 'reason', 'version', 'line_id'):
            with self.subTest(field=field):
                active, current, c = rows()
                if field == 'amount': c['lines'][0]['credit'] = 999
                elif field == 'dimension': c['lines'][0]['po_id'] = 'other'
                elif field == 'link': c['journals'][0]['reversal_of_id'] = 'other'
                elif field == 'economic': c['journals'][0]['economic_date'] = '2026-10-23'
                elif field == 'book': c['journals'][0]['transaction_date'] = '2026-10-23'
                elif field == 'duplicate': c['journals'].append(deepcopy(c['journals'][0]))
                elif field == 'owner': c['choice_reversals'][0]['app_user'] = 'other'
                elif field == 'reason': c['choice_reversals'][0]['reason'] = 'other'
                elif field == 'version': current['pool']['row_version'] += 1
                else: c['lines'][0]['id'] = active['lines'][0]['id']
                with self.assertRaises(ValueError): h.checked_cancelled(active, current, c)

    def test_subsequent_cancel_metadata_rewrite_is_rejected(self):
        active, current, cancellation = rows(); f = RowsOnlyDouble(active, cancellation); history = {}
        h.observe(None, f, active['pool'], history); f.state = current
        h.observe(None, f, current['pool'], history)
        f.state['pool']['cancellation_reason'] = 'rewritten'
        f.cancellation['choice_reversals'][0]['reason'] = 'rewritten'
        with self.assertRaisesRegex(ValueError, 'CANCELLED_HISTORY_CHANGED_AFTER_FIRST_VALIDATION'):
            h.observe(None, f, current['pool'], history)


if __name__ == '__main__':
    unittest.main(verbosity=2)
