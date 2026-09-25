"""Auditor BB T1 case wrapper on exact writer head 72bf53f.

Keep the writer's original 24-case semantics. Strip only the duplicate `case`
display field from a case result before the unmodified group reporter adds its
canonical ID, and add one independently derived AR opening journal oracle.
This script changes no product, SQL or writer checkout file.
"""
from datetime import date
from decimal import Decimal
from pathlib import Path
import argparse
import sys

sys.path.insert(0, str((Path.cwd().parent / 'auditor' / 'scripts').resolve()))
import cp6_bb_probe as bb


def opening_ar_sign(cur, today: date):
    before = bb.gl(cur)
    start = bb.now(cur)
    fx = bb.financial_fixture(
        cur, today,
        documents=[('CUSTOMER_RECEIVABLE', 'AUD-S01-100-30', '100.00', '30.00')],
        bank='100.00',
    )
    delta = bb.moved(before, bb.gl(cur))
    ar = bb.account(cur, 'AR_CUSTOMER')
    equity = bb.account(cur, 'OPENING_EQUITY')
    bank_id = str(cur.execute('select coa_account_id from erp.cash_accounts where id=%s', (fx['cash'],)).fetchone()[0])
    expected = {ar: '70.00', equity: '-170.00', bank_id: '100.00'}
    observed = {k: str(Decimal(v).quantize(Decimal('0.01'))) for k, v in delta.items()}
    checks = {
        'opening_ar_debit_70': observed.get(ar) == '70.00',
        'opening_equity_credit_170_includes_cash_100': observed.get(equity) == '-170.00',
        'opening_bank_debit_100': observed.get(bank_id) == '100.00',
        'no_extra_journal_accounts': set(observed) == set(expected),
        'no_historical_sale_or_receipt_journal': set(bb.journal_types(cur, start)) <= {'OPENING_BALANCE'},
        'subledger_residual_70': bb.balance_row(cur, fx, 'AUD-S01-100-30')[2] == Decimal('70.00'),
    }
    return bb.verdict(checks, expected=expected, observed=observed,
                      journal_types=bb.journal_types(cur, start),
                      oracle='Master Pulih M:934–938; corrected frozen ALL-S01 errata')


def main(phase: str):
    assert len(bb.PLAN) == 24, ('BB_ORIGINAL_PLAN_COUNT', len(bb.PLAN))
    assert len({k for k, _, _ in bb.PLAN}) == 24, 'BB_ORIGINAL_DUPLICATE_CASE_ID'
    bb.PLAN.append(('AUD:ALL_S01_OPENING_AR_SIGN', 'PASS', opening_ar_sign))
    original = bb.cases

    def visible_case_results(cur, today):
        cases = original(cur, today)
        assert len(cases) == 25 and len({k for k, _ in cases}) == 25

        def without_redundant_case(operation):
            result = operation()
            assert isinstance(result, dict), ('BB_RESULT_NOT_DICT', result)
            result.pop('case', None)  # reporter supplies this ID as its own field
            return result

        return [(key, lambda op=op: without_redundant_case(op)) for key, op in cases]

    bb.cases = visible_case_results
    bb.run(phase)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--phase', choices=('before', 'after'), required=True)
    main(parser.parse_args().phase)
