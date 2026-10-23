"""OW-04b slice B step 1 local check on a throwaway PostgreSQL (never hosted; never the Native/Supabase harness).

python3 scripts/cp7_credit_multi/local_check.py 'host=127.0.0.1 port=55480 user=postgres dbname=postgres'

Installs the retained, unchanged OW04 collectors from the repo sources (initial_base_events_v1,
initial_preserved_source_v1, assert_zero_excess_v1, initial_ordinal_input_v1, the pure kernel and the ordinal wrapper,
cent helpers) over stub tables, then multi.sql, and proves on real journal-shaped rows:
1. One return family: family_before_events_v1 / family_preserved_source_v1 equal today's
   initial_base_events_v1(sale, own return) / initial_preserved_source_v1(sale, own return), byte for byte; with no
   later family they equal the collectors without exclusion.
2. assert_prior_families_reconciled_v1 behaves exactly like today's assert_zero_excess_v1 whenever no EARLIER family
   has a cohort (quote of a first return; registration of the only family): same pass, same refusal.
3. Two families with cohorts (the new branch): reconciled earlier family passes with excess = recognized credit; an
   unreconciled earlier family, an incomplete before-vector and an unrecognized later family refuse.
Stubs only stand in for tables and two hashing helpers these collectors read. The database is dropped at the end.
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
CREDIT = REPO / 'scripts/cp7_customer_credit'
DB = 'ow04bb_local_check'

STUBS = r"""
do $roles$declare r text;begin
 foreach r in array array['cp7_capture','cp7_sales_read','cp7_sales_write','cp7_credit_write','anon','authenticated','service_role']loop
  if not exists(select 1 from pg_roles where rolname=r)then execute format('create role %I nologin',r);end if;
 end loop;
end $roles$;
create schema erp;create schema cp7_credit;create schema cp7_note;create schema ow04_source_proposal;
create table erp.customers(id uuid primary key,customer_name text);
create table erp.sales_headers(id uuid primary key,customer_id uuid,sale_number text,status text,row_version integer,updated_at timestamptz);
create table erp.sales_items(id uuid primary key,sale_id uuid,line_total numeric);
create table erp.sale_stock_allocations(id uuid primary key,sale_item_id uuid);
create table erp.sales_payments(id uuid primary key,sale_id uuid,amount numeric,status text);
create table erp.initial_import_prepayment_payments(payment_id uuid);
create table erp.sales_payment_posting_facts(payment_id uuid,sale_id uuid);
create table erp.sales_payment_reversal_facts(payment_id uuid);
create table erp.sales_returns(id uuid primary key,sale_id uuid,status text);
create table erp.sales_return_items(id uuid primary key,return_id uuid,refund_amount numeric);
create table erp.journal_entries(id uuid primary key,source_type text,source_id uuid,reversal_of_id uuid,economic_date date,transaction_date date,status text);
create table erp.journal_lines(id uuid primary key default gen_random_uuid(),journal_entry_id uuid,account_id uuid,debit numeric,credit numeric);
create table erp.accounting_account_mappings(mapping_key text primary key,account_id uuid);
create table cp7_note.revisions(root_sale_id uuid,previous_sale_id uuid,replacement_sale_id uuid);
create table cp7_credit.return_families(id uuid primary key,family_root_sale_id uuid,family_ordinal bigint,first_return_id uuid,source_sha256 text);
create table cp7_credit.return_family_members(family_id uuid,return_id uuid primary key);
create table cp7_credit.cohorts(id uuid primary key,family_id uuid,source_sale_id uuid);
create table cp7_credit.recognition_plans(id uuid primary key,cohort_id uuid);
create table cp7_credit.recognition_components(id uuid primary key,plan_id uuid);
create table cp7_credit.component_parts(id uuid primary key,component_id uuid,amount numeric);
create table cp7_credit.component_journals(part_id uuid primary key,journal_id uuid,economic_date date,transaction_date date);
create table cp7_credit.initial_return_work(backend_pid integer,transaction_id bigint,actor uuid,request_id uuid,plan_id uuid,source_sale_id uuid,phase text);
create table cp7_credit.execution_context(backend_pid integer,transaction_id bigint,actor uuid,request_id uuid,plan_id uuid);
create table cp7_credit.consumption_events(id uuid primary key,cohort_id uuid,amount numeric,economic_date date,transaction_date date,source_sha256 text);
create function ow04_source_proposal.sha(p jsonb)returns text language sql immutable as $$select encode(sha256(convert_to(p::text,'UTF8')),'hex')$$;
create function ow04_source_proposal.financial_journal_payload(p_journal uuid,p_ar uuid)returns jsonb language sql stable as $$
 select jsonb_build_object('journal',to_jsonb(j),'ar',p_ar)from erp.journal_entries j where j.id=p_journal$$;
create function cp7_credit.materialized_journal_payload(p uuid)returns jsonb language sql stable as $$
 select jsonb_build_object('journal',to_jsonb(j),'lines',(select jsonb_agg(to_jsonb(l)order by l.id)from erp.journal_lines l where l.journal_entry_id=j.id))
 from erp.journal_entries j where j.id=p$$;
"""


def statement(path, name):
    text = (CREDIT / path).read_text()
    found = re.findall(r'create (?:or replace )?function ' + re.escape(name) + r'\(.*?\$\$;', text, re.S)
    assert len(found) == 1, ('LOCAL_SOURCE_STATEMENT_NOT_UNIQUE', path, name, len(found))
    return found[0]


def outcome(cur, sql, args=()):
    cur.execute('savepoint local_call')
    try:
        value = cur.execute(sql, args).fetchone()[0]
    except psycopg.Error as error:
        cur.execute('rollback to savepoint local_call')
        return dict(sqlstate=error.sqlstate, message=error.diag.message_primary)
    cur.execute('release savepoint local_call')
    return dict(ok=True, value=value)


def one(cur, sql, args=()):
    return cur.execute(sql, args).fetchone()[0]


def main(dsn):
    report = {}
    with psycopg.connect(dsn, autocommit=True) as admin:
        admin.execute('drop database if exists ' + DB)
        admin.execute('create database ' + DB)
    try:
        with psycopg.connect(re.sub(r'dbname=\S+', 'dbname=' + DB, dsn)) as conn, conn.cursor() as cur:
            cur.execute("set check_function_bodies=on;set search_path=''")
            cur.execute(STUBS)
            ledger = 'ledger/01_immutable_facts.proposal.sql'
            cur.execute(statement(ledger, 'cp7_credit.pg_jsonb_sha256'))
            domain = re.findall(r'create domain cp7_credit\.cent_amount as numeric.*?\);', (CREDIT / ledger).read_text(), re.S)
            assert len(domain) == 1
            cur.execute(domain[0])
            cur.execute(statement(ledger, 'cp7_credit.cent_text'))
            cur.execute((CREDIT / 'kernel/kernel.sql').read_text())
            cur.execute((CREDIT / 'ordinal-wrapper/wrapper.sql').read_text())
            for path, name in (('coordinator/01_coordinator_facts.sql', 'cp7_credit.initial_base_events_v1'),
                               ('coordinator/01_coordinator_facts.sql', 'cp7_credit.initial_preserved_source_v1'),
                               ('coordinator/01_coordinator_facts.sql', 'cp7_credit.assert_zero_excess_v1'),
                               ('coordinator/05_factual_profile.sql', 'cp7_credit.initial_ordinal_input_v1')):
                cur.execute(statement(path, name))
            cur.execute((HERE / 'multi.sql').read_text())
            # Real journal-shaped rows: invoice 1000 paid 1000 (D1); return r1 200 (D2); later return r2 100 (D3).
            ar, cash, revenue = (str(uuid.uuid4()) for _ in range(3))
            cur.execute("insert into erp.accounting_account_mappings values('AR_CUSTOMER',%s)", (ar,))
            customer, sale, item = (str(uuid.uuid4()) for _ in range(3))
            cur.execute('insert into erp.customers values(%s,%s)', (customer, 'Pelanggan'))
            cur.execute("insert into erp.sales_headers values(%s,%s,'S-1','PAID',3,now())", (sale, customer))
            cur.execute('insert into erp.sales_items values(%s,%s,1000)', (item, sale))
            cur.execute('insert into erp.sale_stock_allocations values(%s,%s)', (str(uuid.uuid4()), item))

            def journal(kind, source, day, ar_debit, ar_credit, reversal_of=None):
                j = str(uuid.uuid4())
                cur.execute("insert into erp.journal_entries values(%s,%s,%s,%s,%s,%s,'POSTED')", (j, kind, source, reversal_of, day, day))
                cur.execute('insert into erp.journal_lines(journal_entry_id,account_id,debit,credit)values(%s,%s,%s,%s),(%s,%s,%s,%s)',
                            (j, ar, ar_debit, ar_credit, j, cash if kind == 'SALES_PAYMENT' else revenue, ar_credit, ar_debit))
                return j
            journal('SALE', sale, '2026-10-01', 1000, 0)
            payment = str(uuid.uuid4())
            cur.execute("insert into erp.sales_payments values(%s,%s,1000,'POSTED')", (payment, sale))
            cur.execute('insert into erp.sales_payment_posting_facts values(%s,%s)', (payment, sale))
            journal('SALES_PAYMENT', payment, '2026-10-01', 0, 1000)

            def ret(amount, day, ordinal):
                r = str(uuid.uuid4())
                cur.execute("insert into erp.sales_returns values(%s,%s,'POSTED')", (r, sale))
                cur.execute('insert into erp.sales_return_items values(%s,%s,%s)', (str(uuid.uuid4()), r, amount))
                j = journal('SALES_RETURN', r, day, 0, amount)
                family = str(uuid.uuid4())
                cur.execute('insert into cp7_credit.return_families values(%s,%s,%s,%s,%s)',
                            (family, sale, ordinal, r, hashlib.sha256(family.encode()).hexdigest()))
                cur.execute('insert into cp7_credit.return_family_members values(%s,%s)', (family, r))
                return r, j, family
            r1, j1, f1 = ret(200, '2026-10-02', 1)
            draft = str(uuid.uuid4())
            cur.execute("insert into erp.sales_returns values(%s,%s,'DRAFT')", (draft, sale))
            q = lambda name, *args: one(cur, 'select ' + name + '(' + ','.join(['%s'] * len(args)) + ')', args)
            # 1. One family: byte-identical to today's collectors.
            same = dict(
                before_events=q('cp7_credit_multi.family_before_events_v1', sale, 1) == q('cp7_credit.initial_base_events_v1', sale, r1),
                preserved_source=q('cp7_credit_multi.family_preserved_source_v1', sale, 1) == q('cp7_credit.initial_preserved_source_v1', sale, r1),
                no_later_family_events=q('cp7_credit_multi.family_before_events_v1', sale, 2) == q('cp7_credit.initial_base_events_v1', sale),
                no_later_family_preserved=q('cp7_credit_multi.family_preserved_source_v1', sale, 2) == q('cp7_credit.initial_preserved_source_v1', sale))
            assert all(same.values()), same
            text_same = one(cur, 'select cp7_credit_multi.family_preserved_source_v1(%s,1)::text=cp7_credit.initial_preserved_source_v1(%s,%s)::text', (sale, sale, r1))
            assert text_same is True
            report['one_family_identical'] = dict(same, jsonb_text_identical=True,
                                                  events=len(q('cp7_credit_multi.family_before_events_v1', sale, 1)))
            # Same identity with inverse descendants: a reversed second payment, and an inverse child of r1's journal
            # (which must leave together with r1).
            cur.execute('savepoint descendants')
            payment2 = str(uuid.uuid4())
            cur.execute("insert into erp.sales_payments values(%s,%s,50,'REVERSED')", (payment2, sale))
            jp2 = journal('SALES_PAYMENT', payment2, '2026-10-01', 0, 50)
            journal('JOURNAL_REVERSAL', jp2, '2026-10-04', 50, 0, jp2)
            journal('JOURNAL_REVERSAL', j1, '2026-10-05', 200, 0, j1)
            deep = dict(
                before_events=q('cp7_credit_multi.family_before_events_v1', sale, 1) == q('cp7_credit.initial_base_events_v1', sale, r1),
                preserved_source=q('cp7_credit_multi.family_preserved_source_v1', sale, 1) == q('cp7_credit.initial_preserved_source_v1', sale, r1),
                no_later_family_events=q('cp7_credit_multi.family_before_events_v1', sale, 2) == q('cp7_credit.initial_base_events_v1', sale))
            assert all(deep.values()), deep
            counts = (len(q('cp7_credit_multi.family_before_events_v1', sale, 1)), len(q('cp7_credit.initial_base_events_v1', sale)))
            assert counts == (4, 6), counts  # sale, payment 1, payment 2 and its inverse; plus r1 and its inverse child
            cur.execute('rollback to savepoint descendants')
            report['one_family_identical_with_inverse_descendants'] = dict(deep, events_family1_vs_all=list(counts))
            # 2. No earlier cohort: exactly assert_zero_excess_v1 (pass and refusal), at quote time and at registration.
            vectors = dict(zero_excess=q('cp7_credit.initial_base_events_v1', sale, r1), overfunded=q('cp7_credit.initial_base_events_v1', sale))
            compared = {}
            for label, own in (('quote_first_return', None), ('quote_own_draft', draft), ('registration_only_family', r1)):
                for vector, events in vectors.items():
                    today = outcome(cur, 'select cp7_credit.assert_zero_excess_v1(%s::jsonb)::text', (json.dumps(events),))
                    new = outcome(cur, 'select cp7_credit_multi.assert_prior_families_reconciled_v1(%s,%s::jsonb,%s)::text', (sale, json.dumps(events), own))
                    assert new == today, (label, vector, today, new)
                    compared[label + ':' + vector] = today
            assert compared['quote_first_return:overfunded'] == dict(sqlstate='P0001', message='CP7_CREDIT_HISTORICAL_BASE_OVERFUNDING')
            assert compared['quote_first_return:zero_excess'].get('ok') is True
            cohort1 = str(uuid.uuid4())
            cur.execute('insert into cp7_credit.cohorts values(%s,%s,%s)', (cohort1, f1, sale))
            for vector, events in vectors.items():  # its own cohort is not an EARLIER cohort
                today = outcome(cur, 'select cp7_credit.assert_zero_excess_v1(%s::jsonb)::text', (json.dumps(events),))
                assert outcome(cur, 'select cp7_credit_multi.assert_prior_families_reconciled_v1(%s,%s::jsonb,%s)::text',
                               (sale, json.dumps(events), r1)) == today
                compared['registration_own_cohort:' + vector] = today
            report['no_earlier_cohort_same_as_assert_zero_excess'] = compared

            # 3. The new branch: family 1 recognized 200 at (D2,D2); return r2 100 at D3 is family 2.
            def recognize(cohort, amount, day):
                plan, component, part = (str(uuid.uuid4()) for _ in range(3))
                cur.execute('insert into cp7_credit.recognition_plans values(%s,%s)', (plan, cohort))
                cur.execute('insert into cp7_credit.recognition_components values(%s,%s)', (component, plan))
                cur.execute('insert into cp7_credit.component_parts values(%s,%s,%s)', (part, component, amount))
                cur.execute('insert into cp7_credit.component_journals values(%s,%s,%s,%s)', (part, str(uuid.uuid4()), day, day))
                return part
            part1 = recognize(cohort1, 200, '2026-10-02')
            r2, j2, f2 = ret(100, '2026-10-03', 2)
            multi = 'select cp7_credit_multi.assert_prior_families_reconciled_v1(%s,%s::jsonb,%s)::text'
            before2 = q('cp7_credit.initial_base_events_v1', sale, r2)
            assert q('cp7_credit_multi.family_before_events_v1', sale, 2) == before2
            only_base = q('cp7_credit_multi.family_before_events_v1', sale, 1)
            assert sorted(e['kind'] for e in only_base) == ['FUNDING', 'NET'], only_base  # the sale and its payment only
            branch = dict(
                registration_second_reconciled=outcome(cur, multi, (sale, json.dumps(before2), r2)),
                registration_second_incomplete=outcome(cur, multi, (sale, json.dumps(only_base), r2)))
            cur.execute('update cp7_credit.component_parts set amount=150 where id=%s', (part1,))
            branch['registration_second_prior_unreconciled'] = outcome(cur, multi, (sale, json.dumps(before2), r2))
            cur.execute('update cp7_credit.component_parts set amount=200 where id=%s', (part1,))
            before3 = q('cp7_credit.initial_base_events_v1', sale)
            branch['quote_third_family2_not_recognized'] = outcome(cur, multi, (sale, json.dumps(before3), None))
            cohort2 = str(uuid.uuid4())
            cur.execute('insert into cp7_credit.cohorts values(%s,%s,%s)', (cohort2, f2, sale))
            recognize(cohort2, 100, '2026-10-03')
            branch['quote_third_both_recognized'] = outcome(cur, multi, (sale, json.dumps(before3), None))
            expected = dict(
                registration_second_reconciled=dict(ok=True, value=''),
                registration_second_incomplete=dict(sqlstate='P0001', message='CP7_CREDIT_MULTI_BEFORE_EVENTS_NOT_EXACT'),
                registration_second_prior_unreconciled=dict(sqlstate='P0001', message='CP7_CREDIT_MULTI_PRIOR_FAMILY_UNRECONCILED'),
                quote_third_family2_not_recognized=dict(sqlstate='P0001', message='CP7_CREDIT_MULTI_PRIOR_FAMILY_UNRECONCILED'),
                quote_third_both_recognized=dict(ok=True, value=''))
            assert branch == expected, branch
            report['earlier_cohort_branch'] = branch
            for role in ('anon', 'authenticated', 'service_role', 'cp7_capture', 'cp7_sales_read', 'cp7_sales_write', 'cp7_credit_write'):
                assert not one(cur, "select has_schema_privilege(%s,'cp7_credit_multi','USAGE')", (role,)), role
                for sig in ('later_family_returns_v1(uuid,bigint)', 'family_before_events_v1(uuid,bigint)',
                            'family_preserved_source_v1(uuid,bigint)', 'prior_recognized_v1(uuid,bigint)',
                            'assert_prior_families_reconciled_v1(uuid,jsonb,uuid)'):
                    assert not one(cur, "select has_function_privilege(%s,%s,'EXECUTE')", (role, 'cp7_credit_multi.' + sig)), (role, sig)
            conn.rollback()
    finally:
        with psycopg.connect(dsn, autocommit=True) as admin:
            admin.execute('drop database if exists ' + DB)
    report['status'] = 'LOCAL_PASS'
    report['scope'] = 'LOCAL_PG_STUBS_NOT_NATIVE_NOT_SUPABASE'
    print(json.dumps(report, indent=1, default=str))


if __name__ == '__main__':
    main(sys.argv[1])
