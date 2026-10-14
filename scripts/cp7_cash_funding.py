"""Owner capital into a disposable fixture bank (owner D14-3: cash/bank may never go negative).

Fixture banks are created empty (cp6_bc_probe.bank_account / fixture). Since the dated cash guard
(cp7_guard.guard_cash_line) a payment out of an empty bank is refused, as the owner decided, so the
first CI run on 597d6778 refused the old fixtures' supplier payments (CP7_CASH_NEGATIVE, logs kept).
A fixture that pays out therefore first records owner capital into that bank through the accepted
native journal (Dr bank / Cr OPENING_EQUITY), dated on or before its first payment. The guard is not
changed or bypassed; the empty-bank refusal itself is proven by its own cases.
"""
from decimal import Decimal as D

LABEL = 'CP7_FIXTURE_BANK_CAPITAL'


def coa(cur, cash_account_id):
    return str(cur.execute('select coa_account_id from erp.cash_accounts where id=%s', (cash_account_id,)).fetchone()[0])


def open_day(cur):
    """The earliest business date still open for posting (the day after closed_through)."""
    return cur.execute("select closed_through+1 from erp.accounting_period_control where singleton_id=1").fetchone()[0]


def fund(cur, cash_account_id, amount, day, label=LABEL):
    """Post owner capital `amount` into the bank on economic date `day`; returns the journal id."""
    import cp7_finance_analysis_cases as journals
    value = str(D(str(amount)))
    assert D(value) > 0, ('CP7_FIXTURE_CAPITAL_NOT_POSITIVE', value)
    return journals.journal(cur, day, [dict(account_id=coa(cur, cash_account_id), debit=value),
                                       dict(mapping_key='OPENING_EQUITY', credit=value)], label)
