"""OW-04b slice C step 1 local check: incoming_applied_v1 equals U wherever the retained checks read it.

python3 scripts/cp7_credit_incoming/local_check.py 'host=127.0.0.1 port=55480 user=postgres dbname=postgres'

Every place that reads U today is located in the repo sources by its exact text (each found exactly once):
1. erp._cp7_current_credit_adjustment (readers/01): `select coalesce(sum(e.amount),0)into u ... event_kind='APPLY'and
   e.target_sale_id=p_sale` - the statement is extracted and executed as written;
2. the materialized profile reader (readers/02) adds e.amount to v_u for `e.event_kind='APPLY'and e.target_sale_id=p_sale`
   while looping the consumption events of every cohort in the upstream root closure (`ce.event_kind='APPLY'and
   ce.target_sale_id=any(sales)`), evaluated here with that same closure rule and predicate;
3. consumer_incoming_funding_v1 (consumer/05, installed unchanged): the sum of its FUNDING event amounts;
4. the consumer fixture's U (cp7_ow04_consumer_fixture.py), the query string executed as written.
On stub rows (two credit sources, applies, a named undo, a refund, an apply into another invoice, an invoice without
credit) all four equal incoming_applied_v1 for every invoice. Stubs only stand in for tables and hashing helpers.
"""
from pathlib import Path
import json
import re
import sys
import uuid

import psycopg

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
CREDIT = REPO / 'scripts/cp7_customer_credit'
DB = 'ow04bc_local_check'
STUBS = r"""
do $roles$declare r text;begin
 foreach r in array array['cp7_capture','cp7_sales_read','cp7_sales_write','cp7_credit_write','anon','authenticated','service_role']loop
  if not exists(select 1 from pg_roles where rolname=r)then execute format('create role %I nologin',r);end if;
 end loop;
end $roles$;
create schema erp;create schema cp7_credit;create schema ow04_source_proposal;
create table cp7_credit.return_families(id uuid primary key,family_root_sale_id uuid);
create table cp7_credit.cohorts(id uuid primary key,family_id uuid);
create table cp7_credit.consumption_events(id uuid primary key,cohort_id uuid,event_kind text check(event_kind in('APPLY','REFUND')),
 amount numeric check(amount<>0),economic_date date,transaction_date date,target_sale_id uuid,restores_event_id uuid unique,journal_id uuid unique);
create function cp7_credit.consumer_event_data_v1(p uuid)returns jsonb language sql as $$select jsonb_build_object('other_account_id',gen_random_uuid())$$;
create function ow04_source_proposal.sha(p jsonb)returns text language sql immutable as $$select encode(sha256(convert_to(p::text,'UTF8')),'hex')$$;
create function ow04_source_proposal.financial_journal_payload(p uuid,a uuid)returns jsonb language sql as $$select jsonb_build_object('journal',p)$$;
"""


def statement(path, name):
    text = (CREDIT / path).read_text()
    found = re.findall(r'create (?:or replace )?function ' + re.escape(name) + r'\(.*?\$\$;', text, re.S)
    assert len(found) == 1, ('LOCAL_SOURCE_STATEMENT_NOT_UNIQUE', path, name, len(found))
    return found[0]


def exactly_once(path, text):
    source = (REPO / path).read_text()
    assert source.count(text) == 1, ('LOCAL_U_READER_TEXT_CHANGED', path, source.count(text))
    return text


def main(dsn):
    report = {}
    adjustment_u = exactly_once('scripts/cp7_customer_credit/readers/01_current_reader_capability.proposal.sql',
        " select coalesce(sum(e.amount),0)into u from cp7_credit.consumption_events e\n  where e.event_kind='APPLY'and e.target_sale_id=p_sale;")
    exactly_once('scripts/cp7_customer_credit/readers/02_materialized_profile.proposal.sql',
        "  if e.event_kind='APPLY'and e.target_sale_id=p_sale then v_u:=v_u+e.amount;end if;")
    exactly_once('scripts/cp7_customer_credit/readers/02_materialized_profile.proposal.sql',
        "    where ce.event_kind='APPLY'and ce.target_sale_id=any(sales))s;")
    exactly_once('scripts/cp7_customer_credit/readers/02_materialized_profile.proposal.sql',
        " for e in select *from cp7_credit.consumption_events where cohort_id=any(cohorts)order by id loop")
    fixture_u = exactly_once('scripts/cp7_customer_credit/consumer/cp7_ow04_consumer_fixture.py',
        "select coalesce(sum(amount),0)from cp7_credit.consumption_events where event_kind='APPLY'and target_sale_id=%s")
    with psycopg.connect(dsn, autocommit=True) as admin:
        admin.execute('drop database if exists ' + DB)
        admin.execute('create database ' + DB)
    try:
        with psycopg.connect(re.sub(r'dbname=\S+', 'dbname=' + DB, dsn)) as conn, conn.cursor() as cur:
            cur.execute("set check_function_bodies=on;set search_path=''")
            cur.execute(STUBS)
            ledger = (CREDIT / 'ledger/01_immutable_facts.proposal.sql').read_text()
            cur.execute(re.findall(r'create domain cp7_credit\.cent_amount as numeric.*?\);', ledger, re.S)[0])
            cur.execute(statement('ledger/01_immutable_facts.proposal.sql', 'cp7_credit.cent_text'))
            cur.execute(statement('consumer/05_event_data.sql', 'cp7_credit.consumer_incoming_funding_v1'))
            cur.execute((HERE / 'incoming.sql').read_text())
            # Two credit sources (S1, S2), targets T (applies 80 + 30, the 30 undone, 25 from S2), V (apply 40), N (none).
            s1, s2, t, v, n = (str(uuid.uuid4()) for _ in range(5))
            cohort = {}
            for s in (s1, s2):
                family, cohort[s] = str(uuid.uuid4()), str(uuid.uuid4())
                cur.execute('insert into cp7_credit.return_families values(%s,%s)', (family, s))
                cur.execute('insert into cp7_credit.cohorts values(%s,%s)', (cohort[s], family))

            def event(source, kind, amount, target=None, restores=None):
                e = str(uuid.uuid4())
                cur.execute('insert into cp7_credit.consumption_events values(%s,%s,%s,%s,%s,%s,%s,%s,%s)',
                            (e, cohort[source], kind, amount, '2026-10-02', '2026-10-02', target, restores, str(uuid.uuid4())))
                return e
            event(s1, 'APPLY', 80, t)
            thirty = event(s1, 'APPLY', 30, t)
            event(s1, 'APPLY', -30, t, thirty)
            event(s2, 'APPLY', 25, t)
            event(s1, 'APPLY', 40, v)
            event(s1, 'REFUND', 50)
            adjustment_sql = 'select ' + adjustment_u.split('select ', 1)[1].replace('into u ', '').replace('p_sale;', '%s')
            results = {}
            for name, sale in (('T', t), ('V', v), ('N', n), ('S1', s1)):
                new = cur.execute('select cp7_credit_incoming.incoming_applied_v1(%s)', (sale,)).fetchone()[0]
                adjustment = cur.execute(adjustment_sql, (sale,)).fetchone()[0]
                funding = cur.execute("select coalesce(sum((x->>'amount')::numeric),0)from jsonb_array_elements(cp7_credit.consumer_incoming_funding_v1(%s))x",
                                      (sale,)).fetchone()[0]
                fixture = cur.execute(fixture_u, (sale,)).fetchone()[0]
                # Materialized profile: cohorts of the upstream root closure, then the v_u predicate.
                roots = {sale}
                while True:
                    reached = {r[0] for r in cur.execute("""select rf.family_root_sale_id::text from cp7_credit.consumption_events ce
                        join cp7_credit.cohorts ch on ch.id=ce.cohort_id join cp7_credit.return_families rf on rf.id=ch.family_id
                        where ce.event_kind='APPLY'and ce.target_sale_id=any(%s::uuid[])""", (list(roots),)).fetchall()}
                    if reached <= roots:
                        break
                    roots |= reached
                profile = cur.execute("""select coalesce(sum(e.amount),0)from cp7_credit.consumption_events e where e.cohort_id in(
                    select c.id from cp7_credit.cohorts c join cp7_credit.return_families f on f.id=c.family_id where f.family_root_sale_id=any(%s::uuid[]))
                    and e.event_kind='APPLY'and e.target_sale_id=%s""", (list(roots), sale)).fetchone()[0]
                assert new == adjustment == funding == fixture == profile, (name, new, adjustment, funding, fixture, profile)
                results[name] = str(new)
            assert results == dict(T='105', V='40', N='0', S1='0'), results
            report['U_equal_at_every_reader'] = results
            for role in ('anon', 'authenticated', 'service_role', 'cp7_capture', 'cp7_sales_read', 'cp7_sales_write', 'cp7_credit_write'):
                assert not cur.execute("select has_function_privilege(%s,'cp7_credit_incoming.incoming_applied_v1(uuid)','EXECUTE')", (role,)).fetchone()[0], role
                assert not cur.execute("select has_schema_privilege(%s,'cp7_credit_incoming','USAGE')", (role,)).fetchone()[0], role
            report['private'] = True
            conn.rollback()
    finally:
        with psycopg.connect(dsn, autocommit=True) as admin:
            admin.execute('drop database if exists ' + DB)
    report['readers_located_once'] = ['erp._cp7_current_credit_adjustment u', 'materialized profile v_u and its closure',
                                      'consumer_incoming_funding_v1', 'consumer fixture U']
    report['status'] = 'LOCAL_PASS'
    report['scope'] = 'LOCAL_PG_STUBS_NOT_NATIVE_NOT_SUPABASE'
    print(json.dumps(report, indent=1, default=str))


if __name__ == '__main__':
    main(sys.argv[1])
