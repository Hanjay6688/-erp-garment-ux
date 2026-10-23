"""OW-04b slice B step 2 local check: the counted delta B1-B8, B11 side by side with the predecessor definitions.

python3 scripts/cp7_credit_multi/local_check_delta.py 'host=127.0.0.1 port=55480 user=postgres dbname=postgres'

1. Rebuilds the installed predecessor text of the five replaced functions from the repo sources in install order:
   quote = coordinator/02 + followups detail; Native return guard and completion = native-empty overlays;
   registration admission = coordinator/04; initial reasons = followups.sql. All compile with check_function_bodies on.
2. Applies native_delta.patch (step 2 functions; the B9 profile loop has local_check_profile.py): each anchor/marker once; reverting every substitution gives the predecessor back; a
   second application and a missing marker refuse; no refusal text is added or removed. Patched texts compile.
3. Calls predecessor and patched definitions on the same stub rows (savepoints):
   - initial reasons: identical except that PRIOR_CREDIT_RETURN is no longer named (it no longer blocks);
   - quote family check: a credit-only invoice now passes it (and stops at the next retained check), an invoice with
     incoming credit is still refused with the same message;
   - Native return guard: identical value without an earlier cohort and for ORDINARY returns; minus the earlier
     recognized credit with one;
   - registration admission: identical without an earlier cohort (pass and refusal); a cohort of an earlier family goes
     to assert_prior_families_reconciled_v1 with the exact arguments instead of refusing; another cohort of the same or
     a later family still refuses CP7_CREDIT_INITIAL_CAUSAL_SCOPE_INVALID.
   The quote totals (B3-B5) and the completion (B8) are checked as text and by evaluating their new expressions:
   prior_recognized_v1 is exactly 0 without an earlier cohort, so every value is the retained one.
Stubs only stand in for objects these paths read first. The database is dropped at the end.
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
from cp7_credit_followups import native_delta as followups_delta  # noqa: E402
from cp7_credit_multi import native_delta  # noqa: E402

CREDIT = REPO / 'scripts/cp7_customer_credit'
STEP2 = tuple(sig for sig in native_delta.SIGNATURES if sig != native_delta.PROFILE)
DB = 'ow04bb_local_delta'
STUBS = r"""
do $roles$declare r text;begin
 foreach r in array array['cp7_capture','cp7_sales_read','cp7_sales_write','cp7_credit_write','anon','authenticated','service_role']loop
  if not exists(select 1 from pg_roles where rolname=r)then execute format('create role %I nologin',r);end if;
 end loop;
end $roles$;
create schema erp;create schema auth;create schema cp7_credit;create schema cp7_sales;create schema ow04_source_proposal;
create schema cp7_note;create schema cp7_sales_return_correction;create schema local_fixture;
create table local_fixture.source(src jsonb);
create table local_fixture.calls(args jsonb);
create table erp.sales_headers(id uuid primary key,status text,row_version integer);
create table erp.sales_returns(id uuid primary key,sale_id uuid,status text);
create table erp.sales_return_items(id uuid primary key,return_id uuid);
create table cp7_sales_return_correction.links(id uuid primary key,sale_id uuid);
create table cp7_note.revisions(root_sale_id uuid,previous_sale_id uuid,replacement_sale_id uuid);
create table cp7_credit.return_families(id uuid primary key,family_root_sale_id uuid,family_ordinal bigint);
create table cp7_credit.return_family_members(family_id uuid,return_id uuid primary key);
create table cp7_credit.cohorts(id uuid primary key,family_id uuid,source_sale_id uuid);
create table cp7_credit.recognition_plans(id uuid primary key,cohort_id uuid,plan_kind text,before_events jsonb,kernel_result jsonb,added_events jsonb);
create table cp7_credit.recognition_components(id uuid primary key,plan_id uuid,ordinal integer);
create table cp7_credit.component_parts(id uuid primary key,component_id uuid,amount numeric);
create table cp7_credit.component_journals(part_id uuid primary key,journal_id uuid);
create table cp7_credit.consumption_events(id uuid primary key,event_kind text,target_sale_id uuid);
create table cp7_credit.initial_return_work(operation_id uuid,plan_id uuid,return_id uuid,source_sale_id uuid,family_ordinal bigint,origin text,
 projection jsonb,projected_kernel jsonb,settlement jsonb,credit_account_snapshot jsonb,phase text);
create table cp7_credit.return_native_scope(backend_pid integer,transaction_id bigint,return_id uuid,native_refund numeric,native_net_after numeric,
 guard_effective_paid numeric,completed boolean);
create function auth.uid()returns uuid language sql as $$select null::uuid$$;
create table cp7_sales.command_context(backend_pid integer,transaction_id bigint,actor uuid,sale_id uuid,action text);
create table cp7_sales.requests(actor uuid,request_id uuid,action text,payload jsonb,expected_version text,response jsonb);
create function cp7_sales.review_token(uuid)returns text language sql as $$select 'stub'$$;
create function cp7_sales.validate_return(jsonb,boolean)returns void language sql as $$select$$;
create function cp7_credit.return_command_access(text)returns jsonb language sql as $$select '{"stub":true}'::jsonb$$;
create function cp7_credit.initial_choice_v1(jsonb)returns jsonb language sql as $$select '{}'::jsonb$$;
create function ow04_source_proposal.locked_source_family(uuid)returns jsonb language sql as $$select src from local_fixture.source$$;
create function ow04_source_proposal.verify_return_member_v1(uuid)returns jsonb language sql as $$select '{"member_kind":"ORIGINAL"}'::jsonb$$;
create function cp7_credit.native_empty_owns_return_v1(uuid)returns boolean language sql as $$select false$$;
create function cp7_credit.native_empty_guard_v1(uuid,numeric,numeric,numeric)returns numeric language sql as $$select null::numeric$$;
create function cp7_credit.native_empty_complete_v1(uuid,numeric,numeric)returns numeric language sql as $$select null::numeric$$;
create function cp7_credit.is_unchanged_native_return_v1(uuid)returns boolean language sql as $$select false$$;
create function cp7_credit.assert_return_owner_context(uuid)returns void language sql as $$select$$;
create function cp7_credit.assert_owner_context(uuid)returns void language sql as $$select$$;
create function cp7_credit.actual_own_return_events_v1(p uuid)returns jsonb language sql as $$select '[]'::jsonb$$;
"""


def statement(path, name, replace=False):
    text = (CREDIT / path).read_text()
    head = 'create or replace function ' if replace else 'create function '
    found = re.findall(re.escape(head + name) + r'\(.*?\$\$;', text, re.S)
    assert len(found) == 1, ('LOCAL_SOURCE_STATEMENT_NOT_UNIQUE', path, name, len(found))
    return found[0]


def definition(cur, sig):
    return cur.execute('select pg_get_functiondef(%s::regprocedure)', (sig,)).fetchone()[0]


def outcome(cur, sql, args=()):
    cur.execute('savepoint local_call')
    try:
        value = cur.execute(sql, args).fetchone()[0]
    except psycopg.Error as error:
        cur.execute('rollback to savepoint local_call')
        return dict(sqlstate=error.sqlstate, message=error.diag.message_primary, detail=error.diag.message_detail or '')
    calls = cur.execute('select coalesce(jsonb_agg(args),\'[]\')from local_fixture.calls').fetchone()[0]
    cur.execute('rollback to savepoint local_call')
    return dict(ok=True, value=value, calls=calls)


def side_by_side(cur, originals, patched, sql, args=()):
    for sig in STEP2:
        cur.execute(originals[sig])
    before = outcome(cur, sql, args)
    for sig in STEP2:
        cur.execute(patched[sig])
    after = outcome(cur, sql, args)
    return before, after


def main(dsn):
    report = {}
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
            cur.execute((CREDIT / 'kernel/kernel.sql').read_text())
            cur.execute(statement('coordinator/01_coordinator_facts.sql', 'cp7_credit.assert_zero_excess_v1'))
            cur.execute((REPO / 'scripts/cp7_credit_followups/followups.sql').read_text())
            # 1. Predecessor text in install order.
            cur.execute(statement('coordinator/02_initial_projection.sql', 'cp7_credit.build_initial_return_for_draft_v1'))
            build = definition(cur, native_delta.BUILD)
            cur.execute(build.replace(followups_delta.anchor(followups_delta.BUILD), followups_delta.replacement(followups_delta.BUILD), 1))
            cur.execute(statement('native-empty/04_exact_overlays.sql', 'cp7_credit.native_return_guard', True).replace('create or replace', 'create', 1))
            cur.execute(statement('native-empty/04_exact_overlays.sql', 'cp7_credit.native_return_complete', True).replace('create or replace', 'create', 1))
            cur.execute(statement('coordinator/04_register_and_materialize.sql', 'cp7_credit.assert_source_admission'))
            originals = {sig: definition(cur, sig) for sig in STEP2}
            assert followups_delta.replacement(followups_delta.BUILD) in originals[native_delta.BUILD]
            # 2. Counted delta.
            patched = {sig: native_delta.patch(sig, originals[sig]) for sig in STEP2}
            for sig in STEP2:
                # Rebuild the predecessor from the patched text: put each replacement back at its exact position.
                back, text = patched[sig], originals[sig]
                # Anchors are in text order, so restoring them front to back keeps every later position.
                for label, old, new in native_delta.SUBSTITUTIONS[sig]:
                    assert text.count(old) == 1 and (new == '' or back.count(new) == 1), (sig, label)
                    at = originals[sig].index(old)
                    assert back[at:at + len(new)] == new, (sig, label)
                    back = back[:at] + old + back[at + len(new):]
                    forward = text.index(old)
                    text = text[:forward] + new + text[forward + len(old):]
                assert text == patched[sig], ('LOCAL_FORWARD_DIFFERS', sig)
                assert back == originals[sig], ('LOCAL_REVERSE_DIFFERS', sig)
            refused = []
            for label, bad in (('twice', patched),
                               ('missing', {sig: text.replace(native_delta.PREDECESSOR_MARKERS[sig][0], '') for sig, text in originals.items()})):
                errors = set()
                for sig in STEP2:
                    try:
                        native_delta.patch(sig, bad[sig])
                    except ValueError as error:
                        errors.add(str(error).split(':')[0])
                if errors:
                    refused.append((label, sorted(errors)))
            assert [label for label, _ in refused] == ['twice', 'missing'], refused
            cur.execute((HERE / 'multi.sql').read_text())
            for sig in STEP2:
                cur.execute(patched[sig])
                assert definition(cur, sig) == patched[sig], ('LOCAL_INSTALLED_TEXT_DIFFERS', sig)
            report['delta'] = dict(substitutions={sig: [label for label, _, _ in native_delta.SUBSTITUTIONS[sig]] for sig in STEP2},
                                   exactly_once=True, reverse_restores_predecessor=True, refused=refused, compiled=True)
            # 3. Side by side on stub rows.
            sale, target, both = (str(uuid.uuid4()) for _ in range(3))
            for s in (sale, target, both):
                cur.execute("insert into erp.sales_headers values(%s,'PAID',7)", (s,))
            fam = {}
            for s in (sale, both):
                fam[s] = str(uuid.uuid4())
                cur.execute('insert into cp7_credit.return_families values(%s,%s,1)', (fam[s], s))
                cur.execute('insert into cp7_credit.cohorts values(%s,%s,%s)', (str(uuid.uuid4()), fam[s], s))
            for s in (target, both):
                cur.execute("insert into cp7_credit.consumption_events values(%s,'APPLY',%s)", (str(uuid.uuid4()), s))
            cur.execute("insert into local_fixture.source values('{\"source_status\":\"BASE_COLLECTED\",\"family\":{\"note_revisions\":[]}}')")
            reasons = 'select cp7_credit_followups.initial_family_reasons_v1(%s,(select src from local_fixture.source))'
            quote = "select cp7_credit.build_initial_return_for_draft_v1(%s::jsonb,'1','{}'::jsonb,null)::text"
            seen = {}
            for name, s in (('credit_only', sale), ('incoming_credit', target), ('both', both)):
                seen['reasons_' + name] = side_by_side(cur, originals, patched, reasons, (s,))
                seen['quote_' + name] = side_by_side(cur, originals, patched, quote, (json.dumps(dict(sale_id=s)),))
            det = lambda o: json.loads(o['value'])['reasons'] if o.get('ok') else json.loads(o['detail'])['reasons']
            assert det(seen['reasons_credit_only'][0]) == ['PRIOR_CREDIT_RETURN'] and det(seen['reasons_credit_only'][1]) == ['UNCLASSIFIED']
            assert det(seen['reasons_incoming_credit'][0]) == det(seen['reasons_incoming_credit'][1]) == ['CREDIT_APPLIED_TO_INVOICE']
            assert det(seen['reasons_both'][0]) == ['PRIOR_CREDIT_RETURN', 'CREDIT_APPLIED_TO_INVOICE'] and det(seen['reasons_both'][1]) == ['CREDIT_APPLIED_TO_INVOICE']
            family = 'CP7_CREDIT_INITIAL_SOURCE_FAMILY_UNSUPPORTED'
            old, new = seen['quote_credit_only']
            assert old['message'] == family and new['message'] == 'CP7_SALES_REVIEW_CHANGED', (old, new)  # passes B1, next retained check
            old, new = seen['quote_incoming_credit']
            assert old == new and old['message'] == family, (old, new)
            old, new = seen['quote_both']
            assert (old['sqlstate'], old['message']) == (new['sqlstate'], new['message']) == ('P0001', family)
            assert det(old) == ['PRIOR_CREDIT_RETURN', 'CREDIT_APPLIED_TO_INVOICE'] and det(new) == ['CREDIT_APPLIED_TO_INVOICE']
            # Native return guard and registration admission.
            work = lambda s, origin, fo: (str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4()), s, fo, origin,
                json.dumps(dict(return_amount='100', net_after='600', raw_paid='1000')), json.dumps(dict(has_recognition_effect=True, net_current_k='100')),
                json.dumps(dict(mode='CREDIT')), json.dumps(dict(account='x')), 'ENTERED')
            clean = str(uuid.uuid4())
            cur.execute("insert into erp.sales_headers values(%s,'PAID',7)", (clean,))
            rows = {}
            for label, s, origin, fo in (('no_cohort', clean, 'REVIEWED_SETTLEMENT', 1), ('earlier_cohort', sale, 'REVIEWED_SETTLEMENT', 2),
                                         ('ordinary', sale, 'ORDINARY', 2)):
                rows[label] = work(s, origin, fo)
                cur.execute('insert into cp7_credit.initial_return_work values(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)', rows[label])
            part = str(uuid.uuid4());plan0 = str(uuid.uuid4());comp = str(uuid.uuid4())
            cohort_of_sale = cur.execute('select id from cp7_credit.cohorts where source_sale_id=%s', (sale,)).fetchone()[0]
            cur.execute("insert into cp7_credit.recognition_plans values(%s,%s,'INITIAL','[]','{}','[]')", (plan0, cohort_of_sale))
            cur.execute('insert into cp7_credit.recognition_components values(%s,%s,1)', (comp, plan0))
            cur.execute('insert into cp7_credit.component_parts values(%s,%s,200)', (part, comp))
            cur.execute('insert into cp7_credit.component_journals values(%s,%s)', (part, str(uuid.uuid4())))
            guard = 'select cp7_credit.native_return_guard(%s,100,600,1000)'
            g = {label: side_by_side(cur, originals, patched, guard, (rows[label][2],)) for label in rows}
            assert g['no_cohort'][0] == g['no_cohort'][1] and g['no_cohort'][0]['value'] == 900, g['no_cohort']
            assert g['ordinary'][0] == g['ordinary'][1] and g['ordinary'][0]['value'] == 1000, g['ordinary']
            assert g['earlier_cohort'][0]['value'] == 900 and g['earlier_cohort'][1]['value'] == 700, g['earlier_cohort']
            seen['guard'] = g
            # Admission: a plan for each work row (own cohort), zero-excess vectors from the real kernel.
            ok_events = json.dumps([dict(id='journal:a', kind='NET', amount='1000.00', economic_date='2026-10-01', transaction_date='2026-10-01', source_sha256='0' * 64),
                                    dict(id='journal:b', kind='FUNDING', amount='900.00', economic_date='2026-10-01', transaction_date='2026-10-01', source_sha256='1' * 64)])
            over_events = json.dumps([dict(id='journal:a', kind='NET', amount='1000.00', economic_date='2026-10-01', transaction_date='2026-10-01', source_sha256='0' * 64),
                                      dict(id='journal:b', kind='FUNDING', amount='1100.00', economic_date='2026-10-01', transaction_date='2026-10-01', source_sha256='1' * 64)])
            admission = 'select cp7_credit.assert_source_admission(%s)::text'
            a = {}
            for label, s, events in (('no_cohort_ok', clean, ok_events), ('no_cohort_over', clean, over_events), ('earlier_cohort', sale, ok_events)):
                op, plan, ret = (str(uuid.uuid4()) for _ in range(3))
                own_family, own_cohort = str(uuid.uuid4()), str(uuid.uuid4())
                ordinal = 1 if s == clean else 2
                cur.execute('savepoint admission_case')
                cur.execute('insert into cp7_credit.return_families values(%s,%s,%s)', (own_family, s, ordinal))
                cur.execute('insert into cp7_credit.return_family_members values(%s,%s)', (own_family, ret))
                cur.execute('insert into cp7_credit.cohorts values(%s,%s,%s)', (own_cohort, own_family, s))
                cur.execute("insert into cp7_credit.recognition_plans values(%s,%s,'INITIAL',%s::jsonb,'{\"net_current_k\":\"100\"}','[]')", (plan, own_cohort, events))
                cur.execute('insert into cp7_credit.initial_return_work values(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)',
                            (op, plan, ret, s, ordinal, 'REVIEWED_SETTLEMENT', json.dumps(dict(return_amount='100')), '{}', '{}', '{}', 'ENTERED'))
                if label == 'earlier_cohort':
                    # Record the call instead of running the collectors (proved in local_check.py).
                    stub = ("create or replace function cp7_credit_multi.assert_prior_families_reconciled_v1(p_sale uuid,p_before_events jsonb,p_own_return uuid default null)"
                            "returns void language sql as $$insert into local_fixture.calls values(jsonb_build_array(p_sale,p_before_events,p_own_return))$$")
                    real = definition(cur, 'cp7_credit_multi.assert_prior_families_reconciled_v1(uuid,jsonb,uuid)')
                    cur.execute(stub)
                    a[label] = side_by_side(cur, originals, patched, admission, (plan,))
                    later = str(uuid.uuid4())
                    cur.execute('insert into cp7_credit.return_families values(%s,%s,3)', (later, s))
                    cur.execute('insert into cp7_credit.cohorts values(%s,%s,%s)', (str(uuid.uuid4()), later, s))
                    a['later_cohort'] = side_by_side(cur, originals, patched, admission, (plan,))
                    cur.execute(real)
                else:
                    a[label] = side_by_side(cur, originals, patched, admission, (plan,))
                cur.execute('rollback to savepoint admission_case')
                a.setdefault('rows', {})[label] = dict(plan=plan, sale=s, own_return=ret)
            causal = 'CP7_CREDIT_INITIAL_CAUSAL_SCOPE_INVALID'
            assert a['no_cohort_ok'][0] == a['no_cohort_ok'][1] and a['no_cohort_ok'][0].get('ok'), a['no_cohort_ok']
            assert a['no_cohort_over'][0] == a['no_cohort_over'][1] and a['no_cohort_over'][0]['message'] == 'CP7_CREDIT_HISTORICAL_BASE_OVERFUNDING'
            old, new = a['earlier_cohort']
            row = a['rows']['earlier_cohort']
            assert old['message'] == causal and new.get('ok') and new['calls'] == [[row['sale'], json.loads(ok_events), row['own_return']]], (old, new)
            old, new = a['later_cohort']
            assert old['message'] == new['message'] == causal, (old, new)
            seen['admission'] = {k: v for k, v in a.items() if k != 'rows'}
            # B3-B5, B8: with no earlier cohort every new expression is the retained value.
            zero = cur.execute('select cp7_credit_multi.prior_recognized_v1(%s),cp7_credit_multi.prior_recognized_v1(%s,1),'
                               "cp7_credit.cent_text(cp7_credit_multi.prior_recognized_v1(%s)),cp7_credit_multi.prior_recognized_v1(%s),"
                               'cp7_credit_multi.prior_recognized_v1(%s,1),cp7_credit_multi.prior_recognized_v1(%s,2)',
                               (clean, clean, clean, sale, sale, sale)).fetchone()
            assert list(zero) == [0, 0, '0.00', 200, 0, 200], zero
            seen['prior_recognized'] = dict(no_cohort=0, no_cohort_text='0.00', earlier_family_200=200, before_family_1=0, before_family_2=200)
            report['side_by_side'] = seen
            conn.rollback()
    finally:
        with psycopg.connect(dsn, autocommit=True) as admin:
            admin.execute('drop database if exists ' + DB)
    report['status'] = 'LOCAL_PASS'
    report['scope'] = 'LOCAL_PG_STUBS_NOT_NATIVE_NOT_SUPABASE'
    print(json.dumps(report, indent=1, default=str))


if __name__ == '__main__':
    main(sys.argv[1])
