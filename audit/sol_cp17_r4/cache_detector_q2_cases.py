"""Two one-key mutable-cache controls; immutable facts/guards are untouched."""
from datetime import date
from decimal import Decimal
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
PRODUCT = ROOT.parents[2] / 'auditor'
sys.path.insert(0, str(PRODUCT / 'scripts'))
import cp7_cp17_fix_cases as c
from detector_case import detector_rows, counts
from numeric_boundary_q2_cases import record


def cases(cur, today):
    def check(o, sql, args, expected, readback, original):
        o['before'] = detector_rows(cur)
        before = counts(o['before'])
        assert len(before) == 167 and all(v == 0 for v in before.values()), 'SOL_CACHE_BASELINE_NOT_ZERO'
        cur.execute('savepoint sol_cache_counterfixture')
        try:
            c.b.api.admin(cur)
            changed = cur.execute(sql, args).fetchall()
            assert len(changed) == 1, ('SOL_CACHE_ONE_ROW_REQUIRED', len(changed))
            o['changed_cache'] = changed
            o['during'] = detector_rows(cur)
        finally:
            cur.execute('rollback to savepoint sol_cache_counterfixture')
            c.b.api.admin(cur)
            o['after_rollback'] = detector_rows(cur)
        during, after = counts(o['during']), counts(o['after_rollback'])
        assert set(before) == set(during) == set(after), 'SOL_CACHE_DETECTOR_IDENTITIES_CHANGED'
        assert len(before) == len(during) == len(after) == 167, 'SOL_CACHE_ALL_167_ROWS_REQUIRED'
        delta = {k:during[k]-v for k,v in before.items() if during[k] != v}
        assert delta == expected, ('SOL_CACHE_EXACT_ONE_UNIT_EXPECTED', expected, delta)
        assert after == before and readback() == original
        o.update(observed_count_deltas=delta, expected_count_deltas=expected, original_cache=original, full_cache_row_restored=True, all_nine_functions_exported=True, no_fact_guard_trigger_or_grant_change=True)

    def daily(o):
        o['oracle_origin'] = 'SOL_ONE_MUTABLE_EQUITY_CACHE_KEY_EXPECT_DAILY_AND_EQUATION_ONE_UNIT_EACH'
        bank = c.s.cash(cur, '8.00')
        c.b.api.admin(cur)
        o['capital_source'] = cur.execute("select j.id::text,j.source_type,j.transaction_date::text,l.account_id::text,l.debit::text,l.credit::text from erp.journal_entries j join erp.journal_lines l on l.journal_entry_id=j.id join erp.cash_accounts ca on ca.coa_account_id=l.account_id where ca.id=%s and j.source_type='CP7_FIXTURE_BANK_CAPITAL' and j.status='POSTED' order by j.id,l.id", (bank,)).fetchall()
        assert len(o['capital_source']) == 1 and Decimal(o['capital_source'][0][4]) == 8 and Decimal(o['capital_source'][0][5]) == 0
        rows = cur.execute("select distinct a.balance_date,a.account_id::text,a.debit_total::text,a.credit_total::text from erp.account_daily_balances a join erp.chart_accounts ca on ca.id=a.account_id and ca.account_type='EQUITY' where exists(select 1 from erp.journal_lines e join erp.journal_entries j on j.id=e.journal_entry_id where e.account_id=a.account_id and j.transaction_date=a.balance_date and exists(select 1 from erp.journal_lines cash where cash.journal_entry_id=j.id and cash.account_id=(select coa_account_id from erp.cash_accounts where id=%s) and j.source_type='CP7_FIXTURE_BANK_CAPITAL' and j.status='POSTED')) order by a.balance_date,a.account_id::text", (bank,)).fetchall()
        assert len(rows) == 1, ('SOL_CACHE_OWN_CAPITAL_EQUITY_ROW', rows)
        key = tuple(rows[0][:2])
        readback = lambda: cur.execute('select to_jsonb(x) from erp.account_daily_balances x where balance_date=%s and account_id=%s', key).fetchone()[0]
        original = readback()
        o.update(fixture_origin='WRITER_ACCEPTED_OWNER_CAPITAL8_OWN_BANK', bank=bank, source_key=key, original_debit=rows[0][2], original_credit=rows[0][3], target_checks=['run_v268_financial_report_checks:V268_DAILY_BALANCE_LEDGER_MISMATCH','run_v268_financial_report_checks:V268_BALANCE_SHEET_EQUATION'])
        expected = {k:1 for k in o['target_checks']}
        check(o, 'update erp.account_daily_balances set debit_total=debit_total+1 where balance_date=%s and account_id=%s returning debit_total::text,credit_total::text', key, expected, readback, original)

    return [record('SOL_R4_D01_DAILY_EQUITY_CACHE_ONE_KEY', daily)]
