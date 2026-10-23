"""OW-04b slice B step 3 local check: the per-cohort profile loop (B9) side by side with the installed predecessor.

python3 scripts/cp7_credit_multi/local_check_profile.py 'host=127.0.0.1 port=55480 user=postgres dbname=postgres'

1. Rebuilds the installed cp7_credit._consumer_root_source_profile_v1 from the repo sources exactly as
   consumer/composition.py derives it (coordinator/05 assert_current_source_plan_profile with its three consumer edits,
   renamed), over the retained collectors, pure kernel and ordinal wrapper. Applies native_delta.patch for B9: each
   anchor once; the only refusal-text change is the declared one; it compiles.
2. With settled credit returns built from the retained kernel on journal-shaped rows (invoice 1000 paid 1000; return
   200 at D2; second return 100 at D3), calls predecessor and patched profile on the same rows:
   - no return / one return: identical outcome, accepted, and identical refusal for every one-family mismatch;
   - two reconciled returns: the predecessor refuses CP7_CREDIT_MULTI_COHORT_RECONCILIATION_UNIMPLEMENTED, the
     patched profile accepts (I = 300 = whole excess F);
   - a mismatch in either family refuses with the exact retained code.
Stubs only stand in for tables, two hashing helpers, the Native base check and consumer data (no consumers here).
"""
from pathlib import Path
import hashlib
import json
import re
import sys
import uuid

import psycopg

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / 'scripts'))
from cp7_credit_multi import native_delta, local_check as step1  # noqa: E402

CREDIT = REPO / 'scripts/cp7_customer_credit'
DB = 'ow04bb_local_profile'
PROFILE = native_delta.PROFILE
CONSUMER_EDITS = (
    ("\n  or exists(select 1 from cp7_credit.consumption_events where event_kind='APPLY'and target_sale_id=p_sale)", '\n '),
    ("if(p_actual->>'I')::numeric<>0 or(p_actual->>'U')::numeric<>0 then", "if(p_actual->>'I')::numeric<>0 then"))
CONSUMER_START = ' -- Current materialized inspector already proves all actual signed part/J'
CONSUMER_END = " select coalesce(jsonb_agg(jsonb_build_object('id',consumer.id::text"
CONSUMER_LOOP = """ -- Every consumer has its actual immutable operation and exact named inverse.
 for ce in select *from cp7_credit.consumption_events where cohort_id=ch.id order by id loop
  perform cp7_credit.consumer_event_data_v1(ce.id);
 end loop;
"""
EXTRA = r"""
alter table cp7_credit.cohorts add column source_return_id uuid,add column initial_plan_id uuid;
drop table cp7_credit.recognition_plans;drop table cp7_credit.recognition_components;
create table cp7_credit.recognition_plans(id uuid primary key,cohort_id uuid,plan_kind text,before_events jsonb,kernel_result jsonb,net_amount numeric);
create table cp7_credit.recognition_components(id uuid primary key,plan_id uuid,ordinal integer,kernel_component jsonb);
create table cp7_credit.initial_return_materializations(cohort_id uuid,plan_id uuid,source_snapshot jsonb,actual_kernel jsonb,projection jsonb);
create table cp7_credit.source_operation_materializations_v1(sale_id uuid);
create table cp7_credit.initial_refund_operations(id uuid primary key);
alter table cp7_credit.consumption_events add column event_kind text,add column target_sale_id uuid;
create function cp7_credit.assert_simple_native_base_v1(uuid)returns void language sql as $$select$$;
create function cp7_credit.consumer_event_data_v1(uuid)returns jsonb language sql as $$select '{}'::jsonb$$;
create function cp7_credit.assert_reconciled_source_profile_v1(uuid,jsonb)returns void language sql as $$select$$;
"""


def predecessor_text(cur):
    """coordinator/05 assert_current_source_plan_profile + the consumer edits, renamed, as consumer/composition.py does."""
    consumer = (CREDIT / 'consumer/composition.py').read_text()
    for literal in ("'FUNCTION cp7_credit.assert_current_source_plan_profile(',\n        'FUNCTION cp7_credit._consumer_root_source_profile_v1('",
                    CONSUMER_START.strip(), "consumer.id::text", 'perform cp7_credit.consumer_event_data_v1(ce.id);'):
        assert literal in consumer, ('LOCAL_CONSUMER_COMPOSITION_CHANGED', literal[:60])
    cur.execute(step1.statement('coordinator/05_factual_profile.sql', 'cp7_credit.assert_current_source_plan_profile'))
    text = cur.execute("select pg_get_functiondef('cp7_credit.assert_current_source_plan_profile(uuid,uuid,uuid,jsonb)'::regprocedure)").fetchone()[0]
    for old, new in CONSUMER_EDITS:
        assert text.count(old) == 1, old
        text = text.replace(old, new, 1)
    start = text.index(CONSUMER_START)
    end = text.index(CONSUMER_END, start)
    text = text[:start] + CONSUMER_LOOP + text[end:]
    assert text.count('FUNCTION cp7_credit.assert_current_source_plan_profile(') == 1
    return text.replace('FUNCTION cp7_credit.assert_current_source_plan_profile(', 'FUNCTION cp7_credit._consumer_root_source_profile_v1(', 1)


def main(dsn):
    report = {}
    with psycopg.connect(dsn, autocommit=True) as admin:
        admin.execute('drop database if exists ' + DB)
        admin.execute('create database ' + DB)
    try:
        with psycopg.connect(re.sub(r'dbname=\S+', 'dbname=' + DB, dsn)) as conn, conn.cursor() as cur:
            cur.execute("set check_function_bodies=on;set search_path=''")
            cur.execute(step1.STUBS)
            cur.execute(EXTRA)
            ledger = 'ledger/01_immutable_facts.proposal.sql'
            cur.execute(step1.statement(ledger, 'cp7_credit.pg_jsonb_sha256'))
            cur.execute(re.findall(r'create domain cp7_credit\.cent_amount as numeric.*?\);', (CREDIT / ledger).read_text(), re.S)[0])
            cur.execute(step1.statement(ledger, 'cp7_credit.cent_text'))
            cur.execute((CREDIT / 'kernel/kernel.sql').read_text())
            cur.execute((CREDIT / 'ordinal-wrapper/wrapper.sql').read_text())
            for path, name in (('coordinator/01_coordinator_facts.sql', 'cp7_credit.initial_base_events_v1'),
                               ('coordinator/01_coordinator_facts.sql', 'cp7_credit.initial_preserved_source_v1'),
                               ('coordinator/01_coordinator_facts.sql', 'cp7_credit.assert_zero_excess_v1'),
                               ('coordinator/05_factual_profile.sql', 'cp7_credit.initial_ordinal_input_v1'),
                               ('coordinator/04_register_and_materialize.sql', 'cp7_credit.actual_own_return_events_v1'),
                               ('coordinator/02_initial_projection.sql', 'cp7_credit.component_movements_v1')):
                cur.execute(step1.statement(path, name))
            cur.execute((HERE / 'multi.sql').read_text())
            original = predecessor_text(cur)
            cur.execute(original)
            original = cur.execute('select pg_get_functiondef(%s::regprocedure)', (PROFILE,)).fetchone()[0]
            patched = native_delta.patch(PROFILE, original)
            for label, old, new in native_delta.SUBSTITUTIONS[PROFILE]:
                assert original.count(old) == 1 and patched.count(new) == 1, label
            refused = []
            for label, bad in (('twice', patched), ('missing', original.replace(native_delta.PREDECESSOR_MARKERS[PROFILE][0], ''))):
                try:
                    native_delta.patch(PROFILE, bad)
                except ValueError as error:
                    refused.append((label, str(error).split(':')[0]))
            assert [label for label, _ in refused] == ['twice', 'missing'], refused
            cur.execute(patched)
            assert cur.execute('select pg_get_functiondef(%s::regprocedure)', (PROFILE,)).fetchone()[0] == patched
            report['delta'] = dict(substitutions=[label for label, _, _ in native_delta.SUBSTITUTIONS[PROFILE]], exactly_once=True,
                                   refused=refused, compiled=True, refusal_delta=native_delta.REFUSAL_DELTA[PROFILE])

            def run(sql_args):
                """The same call through the predecessor, then the patched definition."""
                out = []
                for text in (original, patched):
                    cur.execute(text)
                    out.append(step1.outcome(cur, 'select cp7_credit._consumer_root_source_profile_v1(%s,%s,%s,%s::jsonb)::text', sql_args))
                cur.execute(patched)
                return out

            ar, cash, revenue = (str(uuid.uuid4()) for _ in range(3))
            cur.execute("insert into erp.accounting_account_mappings values('AR_CUSTOMER',%s)", (ar,))
            customer, sale, item = (str(uuid.uuid4()) for _ in range(3))
            cur.execute('insert into erp.customers values(%s,%s)', (customer, 'Pelanggan'))
            cur.execute("insert into erp.sales_headers values(%s,%s,'S-1','PAID',3,now())", (sale, customer))
            cur.execute('insert into erp.sales_items values(%s,%s,1000)', (item, sale))

            def journal(kind, source, day, ar_debit, ar_credit):
                j = str(uuid.uuid4())
                cur.execute("insert into erp.journal_entries values(%s,%s,%s,null,%s,%s,'POSTED')", (j, kind, source, day, day))
                cur.execute('insert into erp.journal_lines(journal_entry_id,account_id,debit,credit)values(%s,%s,%s,%s),(%s,%s,%s,%s)',
                            (j, ar, ar_debit, ar_credit, j, cash if kind == 'SALES_PAYMENT' else revenue, ar_credit, ar_debit))
            journal('SALE', sale, '2026-10-01', 1000, 0)
            payment = str(uuid.uuid4())
            cur.execute("insert into erp.sales_payments values(%s,%s,1000,'POSTED')", (payment, sale))
            cur.execute('insert into erp.sales_payment_posting_facts values(%s,%s)', (payment, sale))
            journal('SALES_PAYMENT', payment, '2026-10-01', 0, 1000)
            q = lambda sql, *args: cur.execute('select ' + sql, args).fetchone()[0]
            actual = lambda i: json.dumps(dict(sale_id=sale, root_sale_id=sale, current_leaf_id=sale, I=i, U='0.00'))
            call = lambda i: (sale, sale, sale, actual(i))
            report['no_return'] = run(call('0.00'))
            assert report['no_return'][0] == report['no_return'][1] and report['no_return'][0].get('ok'), report['no_return']

            def settle(amount, day, ordinal):
                """A posted return, its family and an INITIAL cohort exactly as the retained kernel plans it."""
                r, family, cohort, plan = (str(uuid.uuid4()) for _ in range(4))
                cur.execute("insert into erp.sales_returns values(%s,%s,'POSTED')", (r, sale))
                cur.execute('insert into erp.sales_return_items values(%s,%s,%s)', (str(uuid.uuid4()), r, amount))
                journal('SALES_RETURN', r, day, 0, amount)
                cur.execute('insert into cp7_credit.return_families values(%s,%s,%s,%s,%s)', (family, sale, ordinal, r, hashlib.sha256(family.encode()).hexdigest()))
                cur.execute('insert into cp7_credit.return_family_members values(%s,%s)', (family, r))
                before = q('cp7_credit.initial_base_events_v1(%s,%s)', sale, r)
                fresh = q('ow04_pure_kernel.recognition_plan_v1(%s::jsonb,cp7_credit.actual_own_return_events_v1(%s))', json.dumps(before), r)
                preserved = q('cp7_credit.initial_preserved_source_v1(%s,%s)', sale, r)
                cur.execute('insert into cp7_credit.cohorts values(%s,%s,%s,%s,%s)', (cohort, family, sale, r, plan))
                cur.execute("insert into cp7_credit.recognition_plans values(%s,%s,'INITIAL',%s,%s,%s)",
                            (plan, cohort, json.dumps(before), json.dumps(fresh), fresh['net_current_k']))
                for n, component in enumerate(fresh['components'], 1):
                    cid, part = str(uuid.uuid4()), str(uuid.uuid4())
                    cur.execute('insert into cp7_credit.recognition_components values(%s,%s,%s,%s)', (cid, plan, n, json.dumps(component)))
                    cur.execute('insert into cp7_credit.component_parts values(%s,%s,%s)', (part, cid, component['amount']))
                    cur.execute('insert into cp7_credit.component_journals values(%s,%s,%s,%s)',
                                (part, str(uuid.uuid4()), component['economic_date'], component['transaction_date']))
                cur.execute('insert into cp7_credit.initial_return_materializations values(%s,%s,%s,%s,%s)',
                            (cohort, plan, json.dumps(dict(preserved_source=preserved)), json.dumps(fresh), json.dumps(dict(return_amount=str(amount)))))
                return dict(r=r, family=family, cohort=cohort, plan=plan, k=fresh['net_current_k'])
            one = settle(200, '2026-10-02', 1)
            assert one['k'] == '200.00', one

            def tamper(sql, args, label, expected_pair):
                """One mismatch inside a savepoint; returns both outcomes."""
                cur.execute('savepoint tamper')
                cur.execute(sql, args)
                out = run(call(expected_pair[0]))
                cur.execute('rollback to savepoint tamper')
                return out
            single = dict(accepted=run(call('200.00')),
                          wrong_invoice_I=run(call('150.00')),
                          snapshot=tamper("update cp7_credit.initial_return_materializations set source_snapshot=jsonb_set(source_snapshot,'{preserved_source,ar_mapping}','null')where cohort_id=%s",
                                          (one['cohort'],), 'snapshot', ('200.00',)),
                          retained_part=tamper('update cp7_credit.component_parts set amount=amount-1 where component_id in(select id from cp7_credit.recognition_components where plan_id=%s)',
                                               (one['plan'],), 'part', ('200.00',)))
            for name, (old, new) in single.items():
                assert old == new, (name, old, new)
            assert single['accepted'][0].get('ok')
            assert single['wrong_invoice_I'][0]['message'] == 'CP7_CREDIT_CURRENT_RECOGNITION_TARGET_UNRECONCILED'
            assert single['snapshot'][0]['message'] == 'CP7_CREDIT_RECOGNIZED_SOURCE_MUTATION_UNIMPLEMENTED'
            assert single['retained_part'][0]['message'] == 'CP7_CREDIT_CURRENT_ORDINAL_RECONCILIATION_REQUIRED'
            report['one_return_identical'] = {k: v[0] for k, v in single.items()}

            two = settle(100, '2026-10-03', 2)
            assert two['k'] == '100.00', two
            multi = dict(accepted=run(call('300.00')),
                         wrong_invoice_I=run(call('250.00')),
                         family1_snapshot=tamper("update cp7_credit.initial_return_materializations set source_snapshot=jsonb_set(source_snapshot,'{preserved_source,ar_mapping}','null')where cohort_id=%s",
                                                 (one['cohort'],), 'f1', ('300.00',)),
                         family2_snapshot=tamper("update cp7_credit.initial_return_materializations set source_snapshot=jsonb_set(source_snapshot,'{preserved_source,ar_mapping}','null')where cohort_id=%s",
                                                 (two['cohort'],), 'f2', ('300.00',)),
                         family2_before_events=tamper("update cp7_credit.recognition_plans set before_events=before_events-0 where id=%s",
                                                      (two['plan'],), 'f2b', ('300.00',)),
                         family2_component=tamper("update cp7_credit.recognition_components set kernel_component=jsonb_set(kernel_component,'{amount}','\"99.00\"')where plan_id=%s",
                                                  (two['plan'],), 'f2c', ('300.00',)),
                         family1_retained_part=tamper('update cp7_credit.component_parts set amount=amount-1 where component_id in(select id from cp7_credit.recognition_components where plan_id=%s)',
                                                      (one['plan'],), 'f1p', ('300.00',)))
            expected = dict(
                accepted=dict(ok=True, value=''),
                wrong_invoice_I='CP7_CREDIT_CURRENT_RECOGNITION_TARGET_UNRECONCILED',
                family1_snapshot='CP7_CREDIT_RECOGNIZED_SOURCE_MUTATION_UNIMPLEMENTED',
                family2_snapshot='CP7_CREDIT_RECOGNIZED_SOURCE_MUTATION_UNIMPLEMENTED',
                family2_before_events='CP7_CREDIT_RECOGNIZED_SOURCE_MUTATION_UNIMPLEMENTED',
                family2_component='CP7_CREDIT_CURRENT_RECOGNITION_TARGET_UNRECONCILED',
                family1_retained_part='CP7_CREDIT_CURRENT_ORDINAL_RECONCILIATION_REQUIRED')
            for name, (old, new) in multi.items():
                if name in ('accepted', 'wrong_invoice_I', 'family1_snapshot', 'family2_snapshot', 'family2_before_events', 'family2_component'):
                    assert old['message'] == 'CP7_CREDIT_MULTI_COHORT_RECONCILIATION_UNIMPLEMENTED', (name, old)
                want = expected[name]
                if isinstance(want, dict):
                    assert {k: new.get(k) for k in want} == want, (name, new)
                else:
                    assert (new.get('sqlstate'), new.get('message')) == ('P0001', want), (name, new)
            report['two_returns'] = {k: dict(predecessor=v[0], patched=v[1]) for k, v in multi.items()}
            conn.rollback()
    finally:
        with psycopg.connect(dsn, autocommit=True) as admin:
            admin.execute('drop database if exists ' + DB)
    report['status'] = 'LOCAL_PASS'
    report['scope'] = 'LOCAL_PG_STUBS_NOT_NATIVE_NOT_SUPABASE'
    print(json.dumps(report, indent=1, default=str))


if __name__ == '__main__':
    main(sys.argv[1])
