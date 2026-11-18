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
import sys
from uuid import uuid4

import psycopg

from .g04_source import PRODUCT, TREE, confirm_source, require


CREDIT_HISTORY = tuple('cp7_credit.' + name for name in (
    'return_families', 'return_family_members', 'cohorts', 'recognition_plans', 'recognition_components',
    'component_parts', 'component_journals', 'consumption_events', 'financial_materializations',
    'financial_materialization_objects', 'source_operation_materializations_v1', 'source_operation_completions_v1',
))
TABLES = ('erp.sales_headers', 'erp.sales_payments', 'erp.sales_returns', 'erp.fg_stock_movements',
          'erp.hpp_versions', 'erp.journal_entries', 'erp.journal_lines', 'erp.account_daily_balances',
          'erp.audit_logs', 'cp7_sales.requests', 'cp7_sales_chain.requests', 'cp7_sales_chain.history',
          'cp7_credit.source_mutation_scope') + CREDIT_HISTORY


def boundary_digest(cur, tables=TABLES):
    from psycopg import sql

    rows = {}
    for table in tables:
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


def native_case(cur, day, observations, evidence):
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
    refusals = {}
    evidence['refusals'] = refusals

    def close_child_transaction():
        # Emulate each RPC's commit-time checks while retaining fixture rollback.
        cur.execute('set constraints all immediate')
        cur.execute('set constraints all deferred')

    def reject(label, operation, message):
        before = boundary_digest(cur)
        cur.execute('savepoint expected_refusal')
        try:
            operation()
            raise ValueError('CP7_AUD_G04_EXPECTED_REFUSAL_' + label.upper())
        except psycopg.Error as error:
            cur.execute('rollback to savepoint expected_refusal')
            unchanged = boundary_digest(cur) == before
            refusals[label] = dict(sqlstate=error.sqlstate, message=error.diag.message_primary, unchanged=unchanged)
            require((error.sqlstate, error.diag.message_primary) == ('P0001', message),
                    'CP7_AUD_G04_UNEXPECTED_REFUSAL_' + label.upper())
            require(unchanged, 'CP7_AUD_G04_REFUSAL_CHANGED_STATE_' + label.upper())
        finally:
            cur.execute('rollback to savepoint expected_refusal')
            cur.execute('release savepoint expected_refusal')

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
                (stock, receivable, cash, hpp), 'CP7_AUD_G04_UNEXPECTED_STOCK_AR_BANK_OR_COGS_' + label.upper())
        if expected_status is not None:
            require(status == expected_status, 'CP7_AUD_G04_UNEXPECTED_DOCUMENT_STATUS_' + label.upper())
        return actual

    snapshot('initial', 10, None, 0, 0)
    p = drafts.payload(f, '3', '20', '0')
    drafts.create(cur, f, p)
    evidence['sale_id'] = f['sale']
    snapshot('draft_3', 7, None, 0, 0, 'DRAFT')
    update, version = drafts.edit_payload(cur, f, p)
    update['items'][0]['qty_pcs'] = '4'
    cmd.command(cur, 'EDIT', update, version)
    snapshot('draft_4', 6, None, 0, 0, 'DRAFT')
    post, version = cmd.review(cur, f)
    cmd.command(cur, 'POST', post, version)
    posted = snapshot('posted', 6, 80, 0, 40, 'POSTED')
    require(posted['ledger'] == dict(AR_CUSTOMER=80, SALES_REVENUE=-80, FG_INVENTORY=-40,
                                    COGS=40, BANK=0, CREDIT=0), 'CP7_AUD_G04_POST_JOURNAL')

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
    require(quote['read_only'] and boundary_digest(cur) == before_quote, 'CP7_AUD_G04_QUOTE_MUTATED_BUSINESS_ROWS')
    require(quote['readiness']['state'] == 'READY', 'CP7_AUD_G04_REFUND_QUOTE_NOT_READY')
    combined = initial._settle(cur, initial._envelope(query, quote), uuid4())
    require(combined['return_status'] == 'POSTED' and combined['refund_event_id'], 'CP7_AUD_G04_LINKED_REFUND_REQUIRED')
    close_child_transaction()
    snapshot('returned_2_refunded_30', 8, 0, 40, 20)
    reject('active_children', lambda: returns.reverse_sale(cur, f), 'CP7_CREDIT_SALE_REVERSE_CHILDREN_NOT_CLOSED')
    reject('active_refund', lambda: returns.inverse(cur, f, combined['return_id']),
           'CP7_CREDIT_SOURCE_CONSUMERS_REQUIRE_UNDO')

    undo = dict(action='UNDO', cohort_id=None, target_sale_id=None, cash_account_id=None,
                restores_event_id=combined['refund_event_id'], amount=None,
                physical_at=(sale_at + timedelta(minutes=4)).isoformat(),
                reason='AUD-G04 reverse the original synthetic cash refund', reference=None)
    result = credit.command(cur, credit.review(cur, undo), uuid4())
    require(Decimal(result['amount']) == -30, 'CP7_AUD_G04_REFUND_INVERSE_AMOUNT')
    close_child_transaction()
    returns.inverse(cur, f, combined['return_id'])
    close_child_transaction()
    payments.inverse(cur, f, payment['payment_id'])
    close_child_transaction()
    before = snapshot('refund_return_payment_reversed', 6, 80, 0, 40, 'POSTED')
    require(before['ledger'] == posted['ledger'], 'CP7_AUD_G04_CHILD_INVERSES_DID_NOT_RESTORE_JOURNAL')
    p, version = chain.payload(cur, f)
    chain_source = chain.workspace(cur, f)['source']
    require(not (chain_source['payments'] or chain_source['returns'] or chain_source['pending_children']),
            'CP7_AUD_G04_ACTIVE_OR_PENDING_CHILDREN')
    require(cur.execute('select exists(select 1 from cp7_credit.return_families where family_root_sale_id=%s)',
                        (f['sale'],)).fetchone() == (True,), 'CP7_AUD_G04_CREDIT_SOURCE_NOT_REGISTERED')
    pre = boundary_digest(cur)
    historic = boundary_digest(cur, CREDIT_HISTORY)
    original_facts = chain.facts(cur, f)
    direct_payload, direct_version = cmd.review(cur, f)

    def attempt(label, call):
        cur.execute('savepoint g04_terminal')
        try:
            request = uuid4()
            response = call(request)
            cur.execute('set constraints all immediate')
            snapshot(label + '_accepted', 10, None, 0, 0, 'REVERSED')
            require(cmd.accounts(cur) == initial_accounts, 'CP7_AUD_G04_FINAL_INVERSE_JOURNAL_NOT_NEUTRAL')
            require(boundary_digest(cur, CREDIT_HISTORY) == historic and chain.facts(cur, f) == original_facts,
                    'CP7_AUD_G04_ORIGINAL_FACTS_CHANGED')
            require(cur.execute('''select count(*) from erp.journal_entries j
                join erp.journal_entries inverse on inverse.reversal_of_id=j.id
                where j.source_type='SALE' and j.source_id=%s and j.status='REVERSED'
                    and inverse.source_type='JOURNAL_REVERSAL' and inverse.status='POSTED' ''',
                (f['sale'],)).fetchone() == (1,), 'CP7_AUD_G04_EXACT_INVOICE_INVERSE_REQUIRED')
            require(cur.execute('''select count(*) from erp.audit_logs where entity_type='sales_headers'
                and entity_id=%s and action='REVERSE' and nullif(btrim(change_reason),'') is not null''',
                (f['sale'],)).fetchone() == (1,), 'CP7_AUD_G04_EXACT_INVOICE_AUDIT_REQUIRED')
            after = boundary_digest(cur)
            require(call(request) == response and boundary_digest(cur) == after, 'CP7_AUD_G04_REPLAY_CHANGED_STATE')
            return dict(outcome='REVERSED', response=response, immutable_history=True, one_journal_inverse=True,
                        one_audit_entry=True, exact_request_replay=True, final_ledger_neutral=True)
        except (psycopg.Error, ValueError) as error:
            cur.execute('rollback to savepoint g04_terminal')
            chain.b.api.admin(cur)
            after = snapshot(label + '_rejected', 6, 80, 0, 40, 'POSTED')
            require(after == before and boundary_digest(cur) == pre, 'CP7_AUD_G04_TERMINAL_REFUSAL_CHANGED_STATE')
            if isinstance(error, psycopg.Error):
                return dict(outcome='REFUSED', sqlstate=error.sqlstate, message=error.diag.message_primary)
            return dict(outcome='INCOMPLETE', message=str(error))
        finally:
            cur.execute('rollback to savepoint g04_terminal')
            cur.execute('release savepoint g04_terminal')
            chain.b.api.admin(cur)

    direct = attempt('direct', lambda key: cmd.command(cur, 'SALE_REVERSE', direct_payload, direct_version, key))
    evidence['direct'] = direct
    compound = attempt('chain', lambda key: chain.reverse(cur, p, version, key))
    evidence.update(chain=compound, available_children=0,
                    both_routes_reversed=all(item['outcome'] == 'REVERSED' for item in (direct, compound)))

    cur.execute('savepoint pending_child')
    try:
        cur.execute("set local timezone='UTC'")
        cur.execute('''insert into erp.sales_payments(sale_id,payment_number,payment_date,amount,cash_account_id,payment_method)
                    values(%s,%s,%s,1,%s,'CASH')''', (f['sale'], 'G04-PENDING-' + uuid4().hex[:10], sale_at, f['bank']))
        pending, pending_version = chain.payload(cur, f)
        # The open-invoice financial reader refuses a new unbound draft in this
        # historical profile. Use the current token from the chain workspace
        # so this control sends the direct command to the server.
        pending_direct = dict(direct_payload, review_token=pending['review_token'])
        reject('pending_direct', lambda: cmd.command(cur, 'SALE_REVERSE', pending_direct, pending_version),
               'CP7_CREDIT_SALE_REVERSE_CHILDREN_NOT_CLOSED')
        reject('pending_chain', lambda: chain.reverse(cur, pending, pending_version), 'CP7_SALES_CHAIN_PENDING_CHILD')
    finally:
        cur.execute('rollback to savepoint pending_child')
        cur.execute('release savepoint pending_child')
    require(boundary_digest(cur) == pre, 'CP7_AUD_G04_PENDING_CONTROL_CHANGED_STATE')


def exercise(conn, cur, day, *, product, lifecycle, state, retain):
    """Call after the existing P21 verified installation and before its restore."""
    confirm_source(product)
    info = conn.info
    require(cur.connection is conn and not conn.autocommit and info.host in ('127.0.0.1', 'localhost')
            and info.dbname == 'cp6_rollback' and info.transaction_status.name == 'IDLE',
            'CP7_AUD_G04_REQUIRES_P21_DISPOSABLE_CLONE')
    lifecycle.verify(cur, state)
    conn.rollback()
    observations = []
    record = dict(case='AUD-G04', product=PRODUCT, tree=TREE, production_go=False, observations=observations, result={})
    try:
        cur.execute("set local timezone='Asia/Jakarta'")
        baseline = boundary_digest(cur)
        with fixture_sources(product):
            native_case(cur, day, observations, record['result'])
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
