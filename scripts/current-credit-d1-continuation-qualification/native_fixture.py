"""Retained Native calls and complete observations. Import performs no SQL."""
from hashlib import sha256
from pathlib import Path
import importlib.util
import json
import re
import sys
import uuid

import psycopg
from psycopg import sql

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
for relative in ('scripts', 'scripts/cp7_customer_credit/consumer',
                 'scripts/cp7_customer_credit/reconciliation/native',
                 'scripts/cp7_customer_credit/native',
                 'scripts/cp7_customer_credit/initial-settlement'):
    path = str(ROOT / relative)
    if path not in sys.path:
        sys.path.insert(0, path)

from cp7_credit_correction_de import cases as d1, composition as product
import native_refund_cases as refunds
from cp7_p21_current_chain_rehearsal_probe import helper

native, basic, fixture, correction = d1.native, d1.basic, d1.fixture, d1.correction
# Preparation uses the owned lawful D1 two-piece fixture. The unchanged
# target-only GL oracle is explicitly delegated to its retained helper.
target_document_ar = fixture.retained._document_ar


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


oracle = load('d1_cont_independent_oracle', HERE / 'oracle.py')


def require_local(cur):
    info = cur.connection.info
    assert info.host in ('localhost', '127.0.0.1') and info.port == 54322, 'D1_CONT_LOCAL_NATIVE_ONLY'
    assert cur.execute('select current_database()').fetchone() == ('cp6_rollback',), 'D1_CONT_DISPOSABLE_ONLY'


def digest(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), default=str).encode()).hexdigest()


def capture(cur):
    """All22, retained _data row-count/hash+sequences, AND raw current rows.

    No field is removed. Only the retained restore census's declared system/
    cron exclusions apply. PostgreSQL JSON text is kept before any parsing.
    """
    native.b.api.admin(cur)
    *_, catalog = product.runtime()
    full = dict(catalog=catalog._catalog_rows(cur), data_and_sequences=catalog._data(cur), raw_rows={})
    assert set(full['catalog']) == set(catalog.QUERIES) and len(full['catalog']) == 22
    with catalog._catalog(cur):
        tables = cur.execute("select n.nspname,c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace "
                             "where c.relkind in('r','p','m')and " + catalog.NAMESPACE + ' order by 1,2').fetchall()
        for name in tables:
            query = sql.SQL("select coalesce(jsonb_agg(to_jsonb(r)order by to_jsonb(r)::text),'[]'::jsonb)from {} r").format(sql.Identifier(*name)).as_string(cur)
            observed = native._raw(cur, query)
            # Keep complete raw PostgreSQL rows; omit only the helper's second,
            # parsed copy of the same JSON, not any table/row/column data.
            full['raw_rows']['.'.join(name)] = dict(raw_json=observed['raw_json'], sha256=observed['sha256'])
    assert set(full['raw_rows']) == {key for key in full['data_and_sequences'] if not key.startswith('sequence:')}
    assert all(table in full['raw_rows'] for table in product.TABLES)
    return full


def retain(prefix, suffix, value):
    assert re.fullmatch('[A-Z0-9_]+', prefix + suffix)
    path = ROOT / 'cp6-proof/t3' / (prefix + '_' + suffix + '.json')
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(value, indent=2, sort_keys=True, default=str) + '\n').encode()
    # A retry or second invocation cannot overwrite an earlier original.
    with path.open('xb') as stream:
        stream.write(raw)
    return dict(path=str(path.relative_to(ROOT)), bytes=len(raw), sha256=sha256(raw).hexdigest())


def prefix(cur, label):
    assert re.fullmatch('[A-Z0-9_]+', label)
    token = 'D1_CONT_' + label + '_' + uuid.uuid4().hex.upper()
    before = capture(cur)
    return token, before, retain(token, 'BEFORE', before)


def error_fact(error):
    detail = dict(type=type(error).__name__, text=str(error))
    if isinstance(error, psycopg.Error):
        detail.update(sqlstate=error.sqlstate, message=error.diag.message_primary,
                      detail=error.diag.message_detail, hint=error.diag.message_hint,
                      context=error.diag.context)
    return detail


def invoke(cur, label, call, *, no_effect=False):
    token, before, first = prefix(cur, label)
    try:
        result = call()
    except Exception as error:
        retain(token, 'FIRST_ERROR', error_fact(error))
        raise
    after = capture(cur)
    evidence = retain(token, 'RESULT', dict(before_original=first, after=after, outcome=result))
    assert before['catalog'] == after['catalog'], ('D1_CONT_COMMAND_CHANGED_CATALOG', evidence)
    if no_effect:
        assert before == after, ('D1_CONT_REPLAY_CHANGED_CURRENT_ROWS_OR_SEQUENCES', evidence)
    return result, dict(before=first, result=evidence, before_sha256=digest(before), after_sha256=digest(after),
                        all22_observed=True, all_current_rows_and_sequences_observed=True,
                        exact_no_effect_checked=no_effect, dropped_fields=[])


def refused(cur, label, call, expected_message):
    token, before, first = prefix(cur, label)
    point = 'd1_cont_' + uuid.uuid4().hex
    cur.execute('savepoint ' + point)
    try:
        result = call()
    except psycopg.Error as error:
        result = error_fact(error)
        # Preserve the original complete error before rollback or assertions.
        original = retain(token, 'FIRST_ERROR', result)
        cur.execute('rollback to savepoint ' + point)
        cur.execute('release savepoint ' + point)
        after = capture(cur)
        evidence = retain(token, 'REFUSAL', dict(before_original=first, after=after, error=result))
        assert result['sqlstate'] == 'P0001' and result['message'] == expected_message, (expected_message, result, evidence)
        assert before == after, ('D1_CONT_REFUSAL_CHANGED_COMPLETE_STATE', evidence)
        return dict(error=result, original=original, before=first, result=evidence,
                    all22_all_rows_and_sequences_unchanged=True, dropped_fields=[])
    except Exception as error:
        retain(token, 'FIRST_ERROR', error_fact(error))
        cur.execute('rollback to savepoint ' + point)
        cur.execute('release savepoint ' + point)
        raise
    else:
        after = capture(cur)
        evidence = retain(token, 'UNEXPECTED_SUCCESS', dict(before_original=first, after=after, outcome=result))
        cur.execute('rollback to savepoint ' + point)
        cur.execute('release savepoint ' + point)
        raise AssertionError(('D1_CONT_EXPECTED_NATIVE_REFUSAL_SUCCEEDED', expected_message, evidence))


def observe(cur, pair, stage):
    gold = oracle.GOLD[stage]
    source = d1.profile(cur, pair, gold['source']['I'], gold['source']['available'])
    native.b.api.admin(cur)
    target = pair['target']
    sale = target['sale']
    gross, paid, returned, incoming = cur.execute("""select
      (select coalesce(sum(line_total),0)from erp.sales_items where sale_id=%s),
      (select coalesce(sum(amount),0)from erp.sales_payments where sale_id=%s and status='POSTED'),
      (select coalesce(sum(i.refund_amount),0)from erp.sales_return_items i join erp.sales_returns r on r.id=i.return_id where r.sale_id=%s and r.status='POSTED'),
      (select coalesce(sum(amount),0)from cp7_credit.consumption_events where event_kind='APPLY'and target_sale_id=%s)""", (sale, sale, sale, sale)).fetchone()
    assert (gross, paid, returned) == (oracle.cents('500.00'), 0, 0), 'D1_CONT_TARGET_FIXTURE_CHANGED'
    # The retained GL oracle is used ONLY on the unchanged target500 invoice.
    # Unlike the source, this target has no correction/restatement of its own.
    assert not cur.execute('select exists(select 1 from cp7_sales_return_correction.links where sale_id=%s)', (sale,)).fetchone()[0]
    ar = target_document_ar(cur, sale, target['customer'], pair['ar']['target'])
    target_truth = {key: format(value, '.2f') for key, value in dict(net=gross-returned, P=paid, U=incoming,
                       I=oracle.cents('0.00'), E=paid+incoming, AR=ar).items()}
    assert ar == gross-returned-paid-incoming
    detail = native.source.read(cur, target)['detail']
    native.b.api.admin(cur)
    assert {key: detail['financial'][key] for key in ('net_total', 'paid_total', 'open_balance')} == dict(
        net_total=target_truth['net'], paid_total=target_truth['E'], open_balance=target_truth['AR'])
    bank = native.payments.bank_account(cur, pair['source']['f'])
    cash = cur.execute('select coalesce(sum(debit-credit),0)from erp.journal_lines where account_id=%s', (bank,)).fetchone()[0]
    actual = dict(source=source, target=target_truth, cash=format(cash, '.2f'))
    assert actual == gold, (stage, actual, gold)
    return actual


def static_facts(cur, pair):
    native.b.api.admin(cur)
    source, target = pair['source']['f'], pair['target']
    lots = [source['lot'], target['lot']]
    positions = native._raw(cur, "select coalesce(jsonb_agg(to_jsonb(p)order by p.product_id,p.lot_id,p.location_id,p.quality_grade),'[]')from "
                          "(select product_id,lot_id,location_id,quality_grade,physical_qty,reserved_qty,available_qty "
                          "from cp7_fg.positions('',true)where lot_id=any(%s::uuid[]))p", (lots,))
    accounts = native.cmd.accounts(cur)
    return dict(positions=positions,
        hpp=native._array(cur, 'erp.hpp_versions', 'lot_id=any(%s::uuid[])', (lots,)),
        current_hpp=native._raw(cur, "select coalesce(jsonb_agg(to_jsonb(h)order by h.lot_id),'[]')from "
                               "(select lot_id,total_cost,hpp_per_pcs from erp.v_current_hpp where lot_id=any(%s::uuid[]))h", (lots,)),
        allocations=native._array(cur, 'erp.sale_stock_allocations', 'lot_id=any(%s::uuid[])', (lots,)),
        sale=native.note.unchanged_facts(cur, source['sale']), target=native.note.unchanged_facts(cur, target['sale']),
        payment=native.payment_snapshot(cur, source['payment']),
        cost_accounts={name: accounts.get(native.cmd.mapping(cur, name), 0) for name in ('FG_INVENTORY', 'COGS', 'WIP')},
        accounting_period=native._array(cur, 'erp.accounting_period_control', 'true', ()))


def movements(cur, pair):
    native.b.api.admin(cur)
    return native._array(cur, 'erp.fg_stock_movements', 'lot_id=any(%s::uuid[])', ([pair['source']['f']['lot'], pair['target']['lot']],))


def d1_history(cur, requests):
    native.b.api.admin(cur)
    operations = native._array(cur, 'cp7_credit_correction_de.operations_v1', 'request_id=any(%s::uuid[])', (requests,))
    ids = [row['operation_id'] for row in operations['document']]
    assert len(ids) == len(requests)
    plans = native._array(cur, 'cp7_credit_correction_de.plans_v1', 'operation_id=any(%s::uuid[])', (ids,))
    parts = native._array(cur, 'cp7_credit_correction_de.parts_v1', 'operation_id=any(%s::uuid[])', (ids,))
    plan_ids = [row['plan_id'] for row in plans['document']]
    component_ids = 'component_id in(select id from cp7_credit.recognition_components where plan_id=any(%s::uuid[]))'
    return dict(operations=operations, plans=plans, parts=parts,
        journals={row['journal_id']: native.journal(cur, row['journal_id']) for row in parts['document']},
        receipts=native._array(cur, 'cp7_sales_return_correction.requests', 'request_id=any(%s::uuid[])', (requests,)),
        recognition_plans=native._array(cur, 'cp7_credit.recognition_plans', 'id=any(%s::uuid[])', (plan_ids,)),
        recognition_components=native._array(cur, 'cp7_credit.recognition_components', 'plan_id=any(%s::uuid[])', (plan_ids,)),
        component_parts=native._array(cur, 'cp7_credit.component_parts', component_ids, (plan_ids,)),
        component_journals=native._array(cur, 'cp7_credit.component_journals', 'part_id in(select id from cp7_credit.component_parts where '+component_ids+')', (plan_ids,)),
        materializations=native._array(cur, 'cp7_credit.financial_materializations', 'id=any(%s::uuid[])', (ids,)),
        materialization_objects=native._array(cur, 'cp7_credit.financial_materialization_objects', 'materialization_id=any(%s::uuid[])', (ids,)))


def consumer_history(cur, pair):
    native.b.api.admin(cur)
    cohort = pair['initial_result']['credit_id']
    events = native._array(cur, 'cp7_credit.consumption_events', 'cohort_id=%s', (cohort,))
    ids = [row['id'] for row in events['document']]
    requests = [str(row[0]) for row in cur.execute('select request_id from cp7_credit.consumer_operations_v1 where id=any(%s::uuid[])', (ids,))]
    return dict(events=events,
        operations=native._array(cur, 'cp7_credit.consumer_operations_v1', 'id=any(%s::uuid[])', (ids,)),
        completions=native._array(cur, 'cp7_credit.consumer_completions_v1', 'operation_id=any(%s::uuid[])', (ids,)),
        requests=native._array(cur, 'cp7_credit.consumer_requests_v1', 'request_id=any(%s::uuid[])', (requests,)),
        journals={row['journal_id']: native.journal(cur, row['journal_id']) for row in events['document']})
