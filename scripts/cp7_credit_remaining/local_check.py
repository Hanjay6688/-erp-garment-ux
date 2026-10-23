"""OW-04b slice A local check on a throwaway PostgreSQL (never hosted; never the Native/Supabase harness).

python3 scripts/cp7_credit_remaining/local_check.py 'host=127.0.0.1 port=55480 user=postgres dbname=postgres'

1. Rebuilds the installed predecessor text of the two replaced functions from the repo sources in install order:
   native_source_enter = native-empty overlay + payment-correction entry + cp7_credit_followups detail;
   source_request_enter_v1 = reconciliation/03 + consumer all-undone adapter + payment-correction branch (both edits read
   from their transform sources, which must still contain them).
2. Applies native_delta.patched: every anchor/marker exactly once; a second application and a missing marker refuse.
3. Calls both definitions (predecessor, then patched) on stub rows. Every case that stays refused gives the identical
   SQLSTATE, message and detail. Only an ordinary payment (or its inverse) on an invoice whose sole credit participation
   is incoming APPLY passes, and then the hook records the retained before-proof calls (simple Native base and zero
   excess on all date pairs) and the existing scope flag that makes native_source_complete repeat them afterwards.
Stubs only stand in for objects these paths read. The database is dropped at the end.
"""
from pathlib import Path
import json
import re
import sys
import uuid

import psycopg

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / 'scripts'))
from cp7_credit_followups import local_check as prev, native_delta as followups_delta  # noqa: E402
from cp7_credit_remaining import native_delta  # noqa: E402

CREDIT = REPO / 'scripts/cp7_customer_credit'
DB = 'ow04ba_local_check'
PAYMENTS = 'create table erp.sales_payments(id uuid primary key,sale_id uuid,status text);'
STUBS = prev.STUBS.replace(PAYMENTS, 'create table erp.sales_payments(id uuid primary key,sale_id uuid,status text,'
                           'cash_account_id uuid,payment_method text,replaces_payment_id uuid);') + r"""
create table erp.initial_import_prepayment_payments(payment_id uuid);
create table cp7_credit.source_mutation_scope(backend_pid integer,transaction_id bigint,actor uuid,action text,source_id uuid,
 sale_id uuid,authority_snapshot jsonb,had_families boolean);
create table cp7_credit.payment_source_context_v1(backend_pid integer,transaction_id bigint,operation_id uuid,phase text);
create table local_fixture.calls(name text,sale uuid);
create function auth.jwt()returns jsonb language sql as $$select '{}'::jsonb$$;
create function cp7_credit.assert_simple_native_base_v1(p uuid)returns void language sql as $$insert into local_fixture.calls values('SIMPLE_NATIVE_BASE',p)$$;
create function cp7_credit.initial_base_events_v1(p uuid)returns jsonb language sql as $$select jsonb_build_array(p::text)$$;
create function cp7_credit.assert_zero_excess_v1(e jsonb)returns void language sql as $$insert into local_fixture.calls values('ZERO_EXCESS_ALL_DATE_PAIRS',(e->>0)::uuid)$$;
"""
assert STUBS.count('cash_account_id uuid,payment_method text') == 1
CONSUMER_START = " select coalesce(jsonb_agg(jsonb_build_object('event_id',e.id,'cohort_id',e.cohort_id,'event_kind',e.event_kind,"
CONSUMER_MARKER = "raise exception 'CP7_CREDIT_SOURCE_CONSUMERS_REQUIRE_UNDO'using detail=blocked::text;end if;"


def request_predecessor(cur):
    """reconciliation/03 + the consumer adapter edit + the payment-correction branch, as their transforms derive them."""
    consumer = (CREDIT / 'consumer/source_history_transform.py').read_text()
    for literal in ("('cp7_credit.source_request_enter_v1(text,jsonb,uuid,text)', 'sale')", CONSUMER_START[1:60],
                    "result[identity] = original[:start] + '\\n perform cp7_credit.consumer_source_undone_v1(' + root + ');' + original[end:]"):
        assert literal in consumer, ('LOCAL_CONSUMER_TRANSFORM_CHANGED', literal)
    payment = (CREDIT / 'payment_correction/transform.py').read_text()
    found = re.findall(r"sig = 'cp7_credit\.source_request_enter_v1\(text,jsonb,uuid,text\)'\n    result\[sig\] = once\(result\[sig\], "
                       r"'begin\\n', \"\"\"(.*?)\"\"\"\)", payment, re.S)
    assert len(found) == 1, ('LOCAL_PAYMENT_REQUEST_EDIT', len(found))
    cur.execute(prev.statement('reconciliation/03_source_requests.sql', 'cp7_credit.source_request_enter_v1'))
    text = prev.definition(cur, native_delta.REQUEST)
    start = text.index(CONSUMER_START)
    end = text.index(CONSUMER_MARKER, start) + len(CONSUMER_MARKER)
    text = text[:start] + '\n perform cp7_credit.consumer_source_undone_v1(sale);' + text[end:]
    text = prev.once(text, 'begin\n', found[0], 'payment-request')
    cur.execute(text)
    return prev.definition(cur, native_delta.REQUEST)


def enter_predecessor(cur):
    cur.execute(prev.statement('native-empty/04_exact_overlays.sql', 'cp7_credit.native_source_enter'))
    text = prev.once(prev.definition(cur, native_delta.ENTER), *prev.PAYMENT_ENTER, 'enter')
    sig = followups_delta.ENTER
    text = prev.once(text, followups_delta.anchor(sig), followups_delta.replacement(sig), 'followups-detail')
    cur.execute(text)
    return prev.definition(cur, native_delta.ENTER)


def outcome(cur, sql, args):
    """One call, rolled back: its refusal, or its success plus what the hook wrote and called."""
    cur.execute('savepoint local_call')
    try:
        cur.execute(sql, args)
    except psycopg.Error as error:
        cur.execute('rollback to savepoint local_call')
        return dict(sqlstate=error.sqlstate, message=error.diag.message_primary, detail=error.diag.message_detail or '')
    scope = cur.execute('select action,source_id::text,sale_id::text,had_families from cp7_credit.source_mutation_scope').fetchall()
    calls = cur.execute('select name,sale::text from local_fixture.calls order by name').fetchall()
    cur.execute('rollback to savepoint local_call')
    return dict(ok=True, scope=[list(row) for row in scope], calls=[list(row) for row in calls])


def main(dsn):
    report = {}
    with psycopg.connect(dsn, autocommit=True) as admin:
        admin.execute('drop database if exists ' + DB)
        admin.execute('create database ' + DB)
    try:
        with psycopg.connect(re.sub(r'dbname=\S+', 'dbname=' + DB, dsn)) as conn, conn.cursor() as cur:
            cur.execute("set check_function_bodies=on;set search_path=''")
            cur.execute(STUBS)
            cur.execute((REPO / 'scripts/cp7_credit_followups/followups.sql').read_text())
            originals = {native_delta.ENTER: enter_predecessor(cur), native_delta.REQUEST: request_predecessor(cur)}
            patched = native_delta.patched(originals)
            refused = []
            for label, bad in (('twice', patched),
                               ('missing', {sig: text.replace(native_delta.PREDECESSOR_MARKERS[sig][0], '') for sig, text in originals.items()})):
                try:
                    native_delta.patched(bad)
                except ValueError as error:
                    refused.append((label, str(error).split(':')[0]))
            assert [label for label, _ in refused] == ['twice', 'missing'], refused
            for sig in native_delta.SIGNATURES:
                for old, new in native_delta.SUBSTITUTIONS[sig]:
                    assert originals[sig].count(old) == 1 and patched[sig].count(new) == 1, sig
            report['anchors'] = dict(exactly_once=True, refused=refused)
            # Stub rows. T: incoming APPLY only. ADV: APPLY + an opening advance. FAM: APPLY + its own return family.
            # S: credit source with a cohort. Each has one ordinary DRAFT payment and one POSTED payment.
            ids = {name: str(uuid.uuid4()) for name in ('T', 'ADV', 'FAM', 'S')}
            pay = {}
            for name, sale in ids.items():
                cur.execute("insert into erp.sales_headers values(%s,'PARTIAL_PAID')", (sale,))
                pay[name] = (str(uuid.uuid4()), str(uuid.uuid4()))
                cur.execute("insert into erp.sales_payments values(%s,%s,'DRAFT',%s,'BANK_TRANSFER',null),(%s,%s,'POSTED',%s,'BANK_TRANSFER',null)",
                            (pay[name][0], sale, str(uuid.uuid4()), pay[name][1], sale, str(uuid.uuid4())))
                if name != 'S':
                    cur.execute("insert into cp7_credit.consumption_events values(%s,'APPLY',%s)", (str(uuid.uuid4()), sale))
            cur.execute("insert into erp.sales_payments values(%s,%s,'POSTED',null,'OPENING_ADVANCE',null)", (str(uuid.uuid4()), ids['ADV']))
            for name in ('FAM', 'S'):
                family = str(uuid.uuid4())
                cur.execute('insert into cp7_credit.return_families values(%s,%s)', (family, ids[name]))
                if name == 'S':
                    cur.execute('insert into cp7_credit.cohorts values(%s,%s,%s)', (str(uuid.uuid4()), family, ids[name]))
            enter = "select cp7_credit.native_source_enter(%s,%s)"
            request = "select cp7_credit.source_request_enter_v1(%s,%s::jsonb,%s,'1')"
            calls = dict(
                pay_T=(enter, ('PAYMENT', pay['T'][0])), reverse_T=(enter, ('PAYMENT_REVERSE', pay['T'][1])),
                pay_ADV=(enter, ('PAYMENT', pay['ADV'][0])), pay_FAM=(enter, ('PAYMENT', pay['FAM'][0])),
                pay_S=(enter, ('PAYMENT', pay['S'][0])),
                request_reverse_T=(request, ('PAYMENT_REVERSE', json.dumps(dict(sale_id=ids['T'], payment_id=pay['T'][1])), str(uuid.uuid4()))),
                request_draft_T=(request, ('PAYMENT_REVERSE', json.dumps(dict(sale_id=ids['T'], payment_id=pay['T'][0])), str(uuid.uuid4()))),
                request_malformed_T=(request, ('PAYMENT_REVERSE', json.dumps(dict(sale_id=ids['T'], payment_id='not-a-uuid')), str(uuid.uuid4()))),
                request_return_T=(request, ('RETURN_REVERSE', json.dumps(dict(sale_id=ids['T'], return_id=str(uuid.uuid4()))), str(uuid.uuid4()))),
                request_reverse_ADV=(request, ('PAYMENT_REVERSE', json.dumps(dict(sale_id=ids['ADV'], payment_id=pay['ADV'][1])), str(uuid.uuid4()))),
                request_reverse_S=(request, ('PAYMENT_REVERSE', json.dumps(dict(sale_id=ids['S'], payment_id=pay['S'][1])), str(uuid.uuid4()))),
            )
            before = {name: outcome(cur, sql, args) for name, (sql, args) in calls.items()}
            cur.execute((HERE / 'remaining.sql').read_text())
            for sig in native_delta.SIGNATURES:
                cur.execute(patched[sig])
                assert prev.definition(cur, sig) == patched[sig], ('LOCAL_INSTALLED_TEXT_DIFFERS', sig)
            after = {name: outcome(cur, sql, args) for name, (sql, args) in calls.items()}
            admitted = {'pay_T', 'reverse_T', 'request_reverse_T'}
            for name in calls:
                if name in admitted:
                    assert before[name].get('ok') is None, (name, before[name])
                    continue
                assert after[name] == before[name], (name, before[name], after[name])
            registered = 'CP7_CREDIT_REGISTERED_SOURCE_MUTATION_REQUIRES_BOUND_RECONCILIATION'
            for name in ('pay_T', 'reverse_T', 'pay_ADV', 'pay_FAM', 'pay_S'):
                assert before[name]['message'] == registered, (name, before[name])
            for name, action, payment in (('pay_T', 'PAYMENT', pay['T'][0]), ('reverse_T', 'PAYMENT_REVERSE', pay['T'][1])):
                assert after[name] == dict(ok=True, scope=[[action, payment, ids['T'], True]],
                                           calls=[['SIMPLE_NATIVE_BASE', ids['T']], ['ZERO_EXCESS_ALL_DATE_PAIRS', ids['T']]]), (name, after[name])
            assert before['request_reverse_T']['sqlstate'] == '42501' and after['request_reverse_T'] == dict(ok=True, scope=[], calls=[]), (
                before['request_reverse_T'], after['request_reverse_T'])
            report['predecessor'] = before
            report['patched'] = after
            for role in ('anon', 'authenticated', 'service_role', 'cp7_capture', 'cp7_sales_read', 'cp7_sales_write', 'cp7_credit_write'):
                for sig in ('cp7_credit_remaining.payment_admitted_v1(text,uuid,uuid)', 'cp7_credit_remaining.request_admitted_v1(text,jsonb,uuid)'):
                    assert not cur.execute("select has_function_privilege(%s,%s,'EXECUTE')", (role, sig)).fetchone()[0], (role, sig)
                assert not cur.execute("select has_schema_privilege(%s,'cp7_credit_remaining','USAGE')", (role,)).fetchone()[0], role
            conn.rollback()
    finally:
        with psycopg.connect(dsn, autocommit=True) as admin:
            admin.execute('drop database if exists ' + DB)
    report['status'] = 'LOCAL_PASS'
    report['scope'] = 'LOCAL_PG_STUBS_NOT_NATIVE_NOT_SUPABASE'
    print(json.dumps(report, indent=1))


if __name__ == '__main__':
    main(sys.argv[1])
