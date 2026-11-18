"""AUD-G04 probe for a provisioned, disposable P21 clone.

The caller supplies the current P21 owning lifecycle and committed install
state. This case never installs a product, invents an install receipt, or
commits fixture transactions. The surrounding harness performs full restore.
"""

from contextlib import contextmanager
from datetime import datetime, timedelta
from decimal import Decimal
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
from uuid import uuid4

import psycopg


PRODUCT = '9ee09e9562978e8a501da2a9d36defd9ea30bfcf'
TREE = '747313f22979077f2b149b6e90bf24374e9bb869'
REFUSAL = 'CP7_CREDIT_REGISTERED_SOURCE_MUTATION_REQUIRES_BOUND_RECONCILIATION'
TABLES = ('erp.sales_headers', 'erp.sales_payments', 'erp.sales_returns',
          'erp.fg_stock_movements', 'erp.hpp_versions', 'erp.journal_entries',
          'erp.journal_lines', 'erp.account_daily_balances', 'cp7_credit.return_families',
          'cp7_credit.consumption_events', 'cp7_sales.requests')


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def confirm_source(product):
    def git(*args):
        return subprocess.check_output(('git', '-C', str(product), *args), text=True).strip()

    require((git('rev-parse', 'HEAD'), git('rev-parse', 'HEAD^{tree}')) == (PRODUCT, TREE),
            'AUD_G04_UNEXPECTED_PRODUCT_PIN')
    require(not git('status', '--porcelain', '--untracked-files=no'), 'AUD_G04_PRODUCT_TRACKED_DRIFT')


def boundary_digest(cur):
    from psycopg import sql

    rows = {}
    for table in TABLES:
        schema, name = table.split('.')
        query = sql.SQL("select count(*), encode(sha256(convert_to(coalesce("
                        "jsonb_agg(to_jsonb(x) order by to_jsonb(x)::text),'[]')::text,"
                        "'UTF8')),'hex') from {} x").format(sql.Identifier(schema, name))
        rows[table] = list(cur.execute(query).fetchone())
    return rows


@contextmanager
def fixture_sources(product):
    product = Path(product).resolve()
    scripts = product / 'scripts'
    credit = scripts / 'cp7_customer_credit'
    folders = ('native', 'initial-settlement', 'reconciliation/native', 'consumer', 'readers', 'hpp-fractional')
    previous = Path.cwd()
    previous_search = sys.path[:]
    try:
        os.chdir(product)
        sys.path[:0] = [str(scripts), *(str(credit / folder) for folder in folders)]
        yield
    finally:
        sys.path[:] = previous_search
        os.chdir(previous)


def native_case(cur, day, observations):
    import cp7_sales_chain_cases as chain
    import cp7_sales_draft_cases as drafts
    import cp7_ow04_initial_settlement_cases as initial
    import native_basic_cases as credit

    cmd, source, returns, payments = chain.cmd, chain.source, chain.returns, chain.payments
    f = drafts.fixture(cur, day, 10)
    f['destination'] = f['location']
    f['bank'] = str(source.bc.bank_account(cur, 'G04-' + uuid4().hex[:8]))
    liability = initial._credit_master(cur)
    codes = {k: cmd.mapping(cur, k) for k in ('AR_CUSTOMER', 'SALES_REVENUE', 'FG_INVENTORY', 'COGS')}
    codes['BANK'] = payments.bank_account(cur, f)
    codes['CREDIT'] = liability['id']
    initial_accounts = cmd.accounts(cur)

    def snapshot(label, stock, receivable, cash, hpp, expected_status=None):
        chain.b.api.admin(cur)
        status = None
        open_balance = None
        if 'sale' in f:
            detail = source.read(cur, f)['detail']
            status = detail['status']
            balance = detail['financial']['open_balance']
            open_balance = Decimal(balance) if balance is not None else None
        ledger_delta = cmd.delta(initial_accounts, cmd.accounts(cur))
        actual = dict(stock=cmd.available(cur, f), open_balance=open_balance, status=status,
                      ledger={code: ledger_delta.get(account, 0) for code, account in codes.items()},
                      all_ledger_deltas=ledger_delta)
        observations.append(dict(step=label, actual=actual))
        require((actual['stock'], open_balance, actual['ledger']['BANK'], actual['ledger']['COGS']) ==
                (stock, receivable, cash, hpp), 'AUD_G04_UNEXPECTED_STOCK_AR_BANK_OR_COGS_' + label.upper())
        if expected_status is not None:
            require(status == expected_status, 'AUD_G04_UNEXPECTED_DOCUMENT_STATUS_' + label.upper())
        return actual

    snapshot('initial', 10, None, 0, 0)
    p = drafts.payload(f, '3', '20', '0')
    drafts.create(cur, f, p)
    snapshot('draft_3', 7, None, 0, 0, 'DRAFT')
    update, version = drafts.edit_payload(cur, f, p)
    update['items'][0]['qty_pcs'] = '4'
    cmd.command(cur, 'EDIT', update, version)
    snapshot('draft_4', 6, None, 0, 0, 'DRAFT')
    post, version = cmd.review(cur, f)
    cmd.command(cur, 'POST', post, version)
    posted = snapshot('posted', 6, 80, 0, 40, 'POSTED')
    require(posted['ledger'] == dict(AR_CUSTOMER=80, SALES_REVENUE=-80, FG_INVENTORY=-40,
                                    COGS=40, BANK=0, CREDIT=0), 'AUD_G04_POST_JOURNAL')

    sale_at = datetime.fromisoformat(f['sale_at'])
    payment_payload, version = payments.payment_payload(cur, f, '70.00')
    payment_payload['payment_date'] = (sale_at + timedelta(minutes=1)).isoformat()
    payment = cmd.command(cur, 'PAYMENT', payment_payload, version)
    snapshot('paid_70', 6, 10, 70, 40, 'PARTIAL_PAID')

    f['allocations'] = returns.read(cur, f)['page']['rows']
    return_payload, version = returns.payload(cur, f, qty='2', refund='40.00')
    return_payload['physical_at'] = (sale_at + timedelta(minutes=2)).isoformat()
    query = dict(sale_id=f['sale'], expected_version=version, review_token=return_payload['review_token'],
                 return_payload={k: return_payload[k] for k in ('return_number', 'physical_at', 'notes', 'items', 'change_reason')},
                 settlement=dict(mode='REFUND', credit_account_id=liability['id'], cash_account_id=f['bank'],
                                 refund_physical_at=(sale_at + timedelta(minutes=3)).isoformat(),
                                 reference='AUD-G04 synthetic cash refund'))
    before_quote = boundary_digest(cur)
    quote = initial.native.call_quote(cur, query)
    require(quote['read_only'] and boundary_digest(cur) == before_quote, 'AUD_G04_QUOTE_MUTATED_BUSINESS_ROWS')
    require(quote['readiness']['state'] == 'READY', 'AUD_G04_REFUND_QUOTE_NOT_READY')
    combined = initial._settle(cur, initial._envelope(query, quote), uuid4())
    require(combined['return_status'] == 'POSTED' and combined['refund_event_id'], 'AUD_G04_LINKED_REFUND_REQUIRED')
    snapshot('returned_2_refunded_30', 8, 0, 40, 20)

    undo = dict(action='UNDO', cohort_id=None, target_sale_id=None, cash_account_id=None,
                restores_event_id=combined['refund_event_id'], amount=None,
                physical_at=(sale_at + timedelta(minutes=4)).isoformat(),
                reason='AUD-G04 reverse the original synthetic cash refund', reference=None)
    result = credit.command(cur, credit.review(cur, undo), uuid4())
    require(Decimal(result['amount']) == -30, 'AUD_G04_REFUND_INVERSE_AMOUNT')
    returns.inverse(cur, f, combined['return_id'])
    payments.inverse(cur, f, payment['payment_id'])
    before = snapshot('refund_return_payment_reversed', 6, 80, 0, 40, 'POSTED')
    require(before['ledger'] == posted['ledger'], 'AUD_G04_CHILD_INVERSES_DID_NOT_RESTORE_JOURNAL')
    p, version = chain.payload(cur, f)
    chain_source = chain.workspace(cur, f)['source']
    require(not (chain_source['payments'] or chain_source['returns'] or chain_source['pending_children']),
            'AUD_G04_ACTIVE_OR_PENDING_CHILDREN')
    require(cur.execute('select exists(select 1 from cp7_credit.return_families where family_root_sale_id=%s)',
                        (f['sale'],)).fetchone() == (True,), 'AUD_G04_CREDIT_SOURCE_NOT_REGISTERED')
    pre = boundary_digest(cur)

    def attempt(label, call):
        cur.execute('savepoint g04_terminal')
        try:
            response = call()
            cur.execute('set constraints all immediate')
            snapshot(label + '_accepted', 10, None, 0, 0, 'REVERSED')
            require(cmd.accounts(cur) == initial_accounts, 'AUD_G04_FINAL_INVERSE_JOURNAL_NOT_NEUTRAL')
            return dict(outcome='REVERSED', response=response)
        except psycopg.Error as error:
            if (error.sqlstate, error.diag.message_primary) != ('P0001', REFUSAL):
                raise
            # The known business refusal must leave both money and stock intact.
            cur.execute('rollback to savepoint g04_terminal')
            chain.b.api.admin(cur)
            after = snapshot(label + '_refused', 6, 80, 0, 40, 'POSTED')
            require(after == before and boundary_digest(cur) == pre, 'AUD_G04_TERMINAL_REFUSAL_CHANGED_STATE')
            return dict(outcome='REFUSED', sqlstate=error.sqlstate, message=error.diag.message_primary)
        finally:
            cur.execute('rollback to savepoint g04_terminal')
            cur.execute('release savepoint g04_terminal')
            chain.b.api.admin(cur)

    direct = attempt('direct', lambda: returns.reverse_sale(cur, f))
    compound = attempt('chain', lambda: chain.reverse(cur, p, version))
    return dict(sale_id=f['sale'], direct=direct, chain=compound, available_children=0,
                guard_reproduced=all(item.get('message') == REFUSAL and item.get('sqlstate') == 'P0001'
                                     for item in (direct, compound)),
                both_routes_reversed=all(item['outcome'] == 'REVERSED' for item in (direct, compound)))


def exercise(conn, cur, day, *, product, lifecycle, state, retain):
    """Call after the existing P21 verified installation and before its restore."""
    confirm_source(product)
    info = conn.info
    require(cur.connection is conn and not conn.autocommit and info.host in ('127.0.0.1', 'localhost')
            and info.dbname == 'cp6_rollback' and info.transaction_status.name == 'IDLE',
            'AUD_G04_REQUIRES_P21_DISPOSABLE_CLONE')
    lifecycle.verify(cur, state)
    conn.rollback()
    observations = []
    record = dict(case='AUD-G04', product=PRODUCT, tree=TREE, production_go=False, observations=observations)
    try:
        cur.execute("set local timezone='Asia/Jakarta'")
        baseline = boundary_digest(cur)
        with fixture_sources(product):
            record['result'] = native_case(cur, day, observations)
        record['status'] = 'OBSERVED'
    except Exception as error:
        record['status'] = 'INCOMPLETE'
        record['first_failure'] = str(error).splitlines()[0][:360]
        raise
    finally:
        conn.rollback()
        if 'baseline' in locals():
            cur.execute("set local timezone='Asia/Jakarta'")
            record['business_rows_rolled_back'] = boundary_digest(cur) == baseline
        conn.rollback()
        record['probe_sha256'] = sha256(Path(__file__).read_bytes()).hexdigest()
        retain(record)
    return record
