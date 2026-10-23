"""OW-04b slice C step 2 local check: the counted delta C1-C7, C12 side by side with the slice B definitions.

python3 scripts/cp7_credit_incoming/local_check_delta.py 'host=127.0.0.1 port=55480 user=postgres dbname=postgres'

1. Rebuilds the slice B definitions exactly as the slice B checks do (repo sources in install order, then the slice B
   delta), applies this delta: every anchor once, forward and reverse exact, a second application and a missing slice B
   marker refuse, no refusal text changes, everything compiles.
2. Side by side on stub rows, slice B definitions then slice C definitions:
   - no credit applied to the invoice (U = 0): every outcome identical (reasons, quote family check, Native return guard
     reviewed and ordinary, registration admission, opening-HPP owner);
   - credit applied: the return reasons no longer name it, the quote passes the family check, the guard and the
     opening-HPP owner add U, the registration admission reaches the prior-family check;
   - C3b, ordinary return (no settlement choice): P > net-after keeps the retained Native paid exception (P11) exactly;
     a recognition effect keeps CP7_CREDIT_EXPLICIT_RECOGNITION_REVIEW_REQUIRED exactly; otherwise P + U;
   - the profile U check (C6): with U = 0 identical; U equal to the credit applied passes where slice B refused; a wrong U
     refuses CP7_CREDIT_CURRENT_RECOGNITION_TARGET_UNRECONCILED;
   - C8: the native-empty direct-route refusal is not in this delta and its frozen text is unchanged.
Stubs only stand in for objects these paths read first. The databases are dropped at the end.
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
from cp7_credit_multi import native_delta as b, local_check_delta as bcheck, local_check_profile as bprofile, local_check as step1  # noqa: E402
from cp7_credit_incoming import native_delta as c  # noqa: E402

CREDIT = REPO / 'scripts/cp7_customer_credit'
DB = 'ow04bc_local_delta'
SIX = bcheck.STEP2
EXTRA = ("create function cp7_credit.consumer_incoming_funding_v1(p uuid)returns jsonb language sql as $$select '[]'::jsonb$$;\n"
         "alter table cp7_credit.consumption_events add column amount numeric;\n")


def slice_b_definitions(cur):
    """The slice B text of the six non-profile functions, built as the slice B local check builds it."""
    cur.execute(bcheck.statement('coordinator/02_initial_projection.sql', 'cp7_credit.build_initial_return_for_draft_v1'))
    build = bcheck.definition(cur, b.BUILD)
    cur.execute(build.replace(followups_delta.anchor(followups_delta.BUILD), followups_delta.replacement(followups_delta.BUILD), 1))
    cur.execute(bcheck.statement('native-empty/04_exact_overlays.sql', 'cp7_credit.native_return_guard', True).replace('create or replace', 'create', 1))
    cur.execute(bcheck.statement('native-empty/04_exact_overlays.sql', 'cp7_credit.native_return_complete', True).replace('create or replace', 'create', 1))
    cur.execute(bcheck.statement('coordinator/04_register_and_materialize.sql', 'cp7_credit.assert_source_admission'))
    cur.execute(bcheck.statement('coordinator/03_opening_return_hpp.sql', 'cp7_credit.opening_return_hpp_owner_v1'))
    before_b = {sig: bcheck.definition(cur, sig) for sig in SIX}
    return {sig: b.patch(sig, before_b[sig]) for sig in SIX}


def native_delta_text_contains(text, expression):
    return text.count(expression) == 1


def delta_checks(originals, patched, sigs):
    for sig in sigs:
        back, text = patched[sig], originals[sig]
        for label, old, new in sorted(c.SUBSTITUTIONS[sig], key=lambda s: originals[sig].index(s[1])):
            assert text.count(old) == 1 and (new == '' or back.count(new) == 1), (sig, label)
            at = originals[sig].index(old)
            assert back[at:at + len(new)] == new, (sig, label)
            back = back[:at] + old + back[at + len(new):]
            forward = text.index(old)
            text = text[:forward] + new + text[forward + len(old):]
        assert text == patched[sig] and back == originals[sig], ('LOCAL_DELTA_NOT_EXACT', sig)
    # A second application and a missing slice B marker must both refuse, for every function.
    refused = {}
    for label, bad in (('twice', patched), ('missing_marker', {sig: originals[sig].replace(c.PREDECESSOR_MARKERS[sig][0], '') for sig in sigs})):
        for sig in sigs:
            try:
                c.patch(sig, bad[sig])
            except ValueError as error:
                refused.setdefault(sig, []).append((label, str(error).split(':')[0]))
    assert all(len(refused.get(sig, [])) == 2 for sig in sigs), refused
    return sorted({code for pairs in refused.values() for _, code in pairs})


def main(dsn):
    report = {}
    frozen_c8 = (CREDIT / 'native-empty/02_native_empty_callbacks.sql').read_text()
    c8 = "  or exists(select 1 from cp7_credit.consumption_events where event_kind='APPLY'and target_sale_id=p_sale)then\n  raise exception 'CP7_NATIVE_EMPTY_RECOGNIZED_OR_CORRECTED_SOURCE_UNIMPLEMENTED';end if;"
    assert frozen_c8.count(c8) == 1 and 'cp7_credit.assert_native_empty_supported_v1(uuid)' not in c.SIGNATURES
    report['C8_native_empty_direct_route'] = 'UNCHANGED_REFUSAL_NOT_IN_DELTA'
    for name in (DB, DB + '_profile'):
        with psycopg.connect(dsn, autocommit=True) as admin:
            admin.execute('drop database if exists ' + name)
            admin.execute('create database ' + name)
    try:
        with psycopg.connect(re.sub(r'dbname=\S+', 'dbname=' + DB, dsn)) as conn, conn.cursor() as cur:
            cur.execute("set check_function_bodies=on;set search_path=''")
            cur.execute(bcheck.STUBS)
            cur.execute(EXTRA)
            ledger = (CREDIT / 'ledger/01_immutable_facts.proposal.sql').read_text()
            cur.execute(re.findall(r'create domain cp7_credit\.cent_amount as numeric.*?\);', ledger, re.S)[0])
            cur.execute(bcheck.statement('ledger/01_immutable_facts.proposal.sql', 'cp7_credit.cent_text'))
            cur.execute((CREDIT / 'kernel/kernel.sql').read_text())
            cur.execute(bcheck.statement('coordinator/01_coordinator_facts.sql', 'cp7_credit.assert_zero_excess_v1'))
            cur.execute((REPO / 'scripts/cp7_credit_followups/followups.sql').read_text())
            cur.execute((REPO / 'scripts/cp7_credit_multi/multi.sql').read_text())
            originals = slice_b_definitions(cur)
            for sig in SIX:
                cur.execute(originals[sig])
            cur.execute((HERE / 'incoming.sql').read_text())
            patched = {sig: c.patch(sig, originals[sig]) for sig in SIX}
            refused = delta_checks(originals, patched, SIX)
            for sig in SIX:
                cur.execute(patched[sig])
                assert bcheck.definition(cur, sig) == patched[sig], sig
            report['delta'] = dict(substitutions={sig: [label for label, _, _ in c.SUBSTITUTIONS[sig]] for sig in SIX}, exactly_once=True,
                                   forward_and_reverse_exact=True, refused=refused, compiled=True)
            sbs = lambda sql, args: bcheck.side_by_side(cur, originals, patched, sql, args)
            clean, target, revised = (str(uuid.uuid4()) for _ in range(3))
            for s in (clean, target, revised):
                cur.execute("insert into erp.sales_headers values(%s,'PAID',7)", (s,))
            source, fam = str(uuid.uuid4()), str(uuid.uuid4())
            cur.execute("insert into erp.sales_headers values(%s,'PAID',7)", (source,))
            cur.execute('insert into cp7_credit.return_families values(%s,%s,1)', (fam, source))
            source_cohort = str(uuid.uuid4())
            cur.execute('insert into cp7_credit.cohorts values(%s,%s,%s)', (source_cohort, fam, source))

            def apply(to, amount):
                cur.execute("insert into cp7_credit.consumption_events values(%s,'APPLY',%s,%s)", (str(uuid.uuid4()), to, amount))
            apply(target, 80)
            u = lambda s: cur.execute('select cp7_credit_incoming.incoming_applied_v1(%s)', (s,)).fetchone()[0]
            assert (u(clean), u(target)) == (0, 80), (u(clean), u(target))
            seen = {}
            src = '{"source_status":"BASE_COLLECTED","family":{"note_revisions":%s}}'
            reasons = 'select cp7_credit_followups.initial_family_reasons_v1(%s,(select src from local_fixture.source))'
            quote = "select cp7_credit.build_initial_return_for_draft_v1(%s::jsonb,'1','{}'::jsonb,null)::text"
            for label, s, revisions in (('clean', clean, '[]'), ('credit_applied', target, '[]'), ('note_revised', revised, '[{"r":1}]')):
                cur.execute('delete from local_fixture.source');cur.execute('insert into local_fixture.source values(%s::jsonb)', (src % revisions,))
                seen['reasons_' + label] = sbs(reasons, (s,))
                seen['quote_' + label] = sbs(quote, (json.dumps(dict(sale_id=s)),))
            det = lambda o: json.loads(o['value'])['reasons'] if o.get('ok') else json.loads(o['detail'])['reasons']
            family = 'CP7_CREDIT_INITIAL_SOURCE_FAMILY_UNSUPPORTED'
            assert seen['reasons_clean'][0] == seen['reasons_clean'][1] and det(seen['reasons_clean'][0]) == ['UNCLASSIFIED']
            assert det(seen['reasons_credit_applied'][0]) == ['CREDIT_APPLIED_TO_INVOICE'] and det(seen['reasons_credit_applied'][1]) == ['UNCLASSIFIED']
            assert seen['reasons_note_revised'][0] == seen['reasons_note_revised'][1] and det(seen['reasons_note_revised'][0]) == ['NOTE_REVISED']
            assert seen['quote_clean'][0] == seen['quote_clean'][1] and seen['quote_clean'][0]['message'] == 'CP7_SALES_REVIEW_CHANGED'
            assert seen['quote_credit_applied'][0]['message'] == family and seen['quote_credit_applied'][1]['message'] == 'CP7_SALES_REVIEW_CHANGED'
            assert seen['quote_note_revised'][0] == seen['quote_note_revised'][1] and seen['quote_note_revised'][0]['message'] == family
            # Native return guard (reviewed and ordinary) and the opening-HPP owner.
            guard = 'select cp7_credit.native_return_guard(%s,100,%s,%s)'
            g = {}
            for label, s, origin, raw, net_after, effect in (
                    ('reviewed_no_credit', clean, 'REVIEWED_SETTLEMENT', 1000, 600, True), ('reviewed_credit_applied', target, 'REVIEWED_SETTLEMENT', 1000, 600, True),
                    ('ordinary_no_credit', clean, 'ORDINARY', 500, 600, False), ('ordinary_credit_applied', target, 'ORDINARY', 500, 600, False),
                    ('ordinary_P11_paid_exceeds', target, 'ORDINARY', 1000, 600, False), ('ordinary_recognition_effect', target, 'ORDINARY', 500, 600, True)):
                ret = str(uuid.uuid4())
                cur.execute('savepoint guard_case')
                cur.execute('insert into cp7_credit.initial_return_work(operation_id,plan_id,return_id,source_sale_id,family_ordinal,origin,projection,projected_kernel,'
                            "settlement,credit_account_snapshot,phase)values(%s,null,%s,%s,1,%s,%s,%s,'{\"mode\":\"CREDIT\"}','{\"a\":1}','ENTERED')",
                            (str(uuid.uuid4()), ret, s, origin, json.dumps(dict(return_amount='100', net_after=str(net_after), raw_paid=str(raw))),
                             json.dumps(dict(has_recognition_effect=effect, net_current_k='100' if effect else '0'))))
                g[label] = sbs(guard, (ret, net_after, raw))
                cur.execute('rollback to savepoint guard_case')
            same = lambda pair: pair[0] == pair[1]
            assert same(g['reviewed_no_credit']) and g['reviewed_no_credit'][0]['value'] == 900
            assert g['reviewed_credit_applied'][0]['value'] == 900 and g['reviewed_credit_applied'][1]['value'] == 980
            assert same(g['ordinary_no_credit']) and g['ordinary_no_credit'][0]['value'] == 500
            assert g['ordinary_credit_applied'][0]['value'] == 500 and g['ordinary_credit_applied'][1]['value'] == 580
            assert same(g['ordinary_P11_paid_exceeds']) and g['ordinary_P11_paid_exceeds'][0]['value'] == 1000  # Native's own paid exception follows
            assert same(g['ordinary_recognition_effect']) and g['ordinary_recognition_effect'][0]['message'] == 'CP7_CREDIT_EXPLICIT_RECOGNITION_REVIEW_REQUIRED'
            seen['guard'] = g
            owner = 'select cp7_credit.opening_return_hpp_owner_v1(%s)::text'
            o = {}
            for label, s, origin, guard_value in (('reviewed_no_credit', clean, 'REVIEWED_SETTLEMENT', 900), ('ordinary_no_credit', clean, 'ORDINARY', 1000),
                                                  ('reviewed_credit_applied', target, 'REVIEWED_SETTLEMENT', 980), ('ordinary_credit_applied', target, 'ORDINARY', 1080),
                                                  ('credit_applied_wrong_value', target, 'REVIEWED_SETTLEMENT', 850)):
                cur.execute('savepoint owner_case')
                ret, actor, request, customer = (str(uuid.uuid4()) for _ in range(4))
                cur.execute("insert into erp.sales_returns(id,sale_id,status,customer_id)values(%s,%s,'POSTED',%s)", (ret, s, customer))
                cur.execute("""insert into cp7_credit.initial_return_work(operation_id,plan_id,return_id,source_sale_id,family_ordinal,origin,projection,
                    projected_kernel,settlement,credit_account_snapshot,phase,backend_pid,transaction_id,actor,request_id,source_lock_sha256,projection_sha256)
                    values(%s,null,%s,%s,null,%s,%s,%s,'{}','{}','ENTERED',pg_backend_pid(),txid_current(),%s,%s,'lock','projection')""",
                    (str(uuid.uuid4()), ret, s, origin, json.dumps(dict(return_amount='100', net_after='600', raw_paid='1000')),
                     json.dumps(dict(has_recognition_effect=True, net_current_k='100')), actor, request))
                cur.execute("""insert into cp7_credit.return_native_scope(backend_pid,transaction_id,return_id,native_refund,native_net_after,guard_effective_paid,
                    completed,actor,request_id,source_sale_id,customer_id,origin,source_lock_sha256,projection_sha256)
                    values(pg_backend_pid(),txid_current(),%s,100,600,%s,false,%s,%s,%s,%s,%s,'lock','projection')""",
                    (ret, guard_value, actor, request, s, customer, origin))
                o[label] = sbs(owner, (ret,))
                cur.execute('rollback to savepoint owner_case')
            guarded = 'CP7_CREDIT_OPENING_HPP_GUARDED_OWNER_REQUIRED'
            assert same(o['reviewed_no_credit']) and o['reviewed_no_credit'][0].get('ok')
            assert same(o['ordinary_no_credit']) and o['ordinary_no_credit'][0].get('ok')
            assert o['reviewed_credit_applied'][0]['message'] == guarded and o['reviewed_credit_applied'][1].get('ok')
            assert o['ordinary_credit_applied'][0]['message'] == guarded and o['ordinary_credit_applied'][1].get('ok')
            assert o['credit_applied_wrong_value'][0]['message'] == o['credit_applied_wrong_value'][1]['message'] == guarded
            seen['opening_hpp_owner'] = o
            # Registration admission: incoming credit no longer refuses by itself; no credit applied stays identical.
            ok_events = json.dumps([dict(id='journal:a', kind='NET', amount='1000.00', economic_date='2026-10-01', transaction_date='2026-10-01', source_sha256='0' * 64),
                                    dict(id='journal:b', kind='FUNDING', amount='900.00', economic_date='2026-10-01', transaction_date='2026-10-01', source_sha256='1' * 64)])
            admission = 'select cp7_credit.assert_source_admission(%s)::text'
            a = {}
            for label, s in (('no_credit', clean), ('credit_applied', target)):
                cur.execute('savepoint admission_case')
                plan, ret, own_family, own_cohort = (str(uuid.uuid4()) for _ in range(4))
                cur.execute('insert into cp7_credit.return_families values(%s,%s,1)', (own_family, s))
                cur.execute('insert into cp7_credit.return_family_members values(%s,%s)', (own_family, ret))
                cur.execute('insert into cp7_credit.cohorts values(%s,%s,%s)', (own_cohort, own_family, s))
                cur.execute("insert into cp7_credit.recognition_plans values(%s,%s,'INITIAL',%s::jsonb,'{\"net_current_k\":\"100\"}','[]')", (plan, own_cohort, ok_events))
                cur.execute('insert into cp7_credit.initial_return_work(operation_id,plan_id,return_id,source_sale_id,family_ordinal,origin,projection,projected_kernel,'
                            "settlement,credit_account_snapshot,phase)values(%s,%s,%s,%s,1,'REVIEWED_SETTLEMENT',%s,'{}','{}','{}','ENTERED')",
                            (str(uuid.uuid4()), plan, ret, s, json.dumps(dict(return_amount='100'))))
                a[label] = sbs(admission, (plan,))
                cur.execute('rollback to savepoint admission_case')
            assert same(a['no_credit']) and a['no_credit'][0].get('ok'), a['no_credit']
            assert a['credit_applied'][0]['message'] == 'CP7_CREDIT_INITIAL_CAUSAL_SCOPE_INVALID' and a['credit_applied'][1].get('ok'), a['credit_applied']
            seen['admission'] = a
            # C13: the quote's source-vector completeness, old expression (Native events only) vs new (plus the proven
            # incoming FUNDING events). Without incoming credit both agree; with it only the new one accepts the exact
            # vector, and a vector missing the incoming event is still refused.
            cur.execute(bcheck.statement('coordinator/01_coordinator_facts.sql', 'cp7_credit.initial_event_semantics_v1'))
            ev = lambda i, kind, amount, day: dict(id='journal:' + i, kind=kind, amount=amount, economic_date=day, transaction_date=day, source_sha256='0' * 64)
            native_events = [ev('a', 'NET', '500.00', '2026-10-01'), ev('b', 'FUNDING', '420.00', '2026-10-03')]
            incoming = [ev('c', 'FUNDING', '80.00', '2026-10-02')]
            distinct = lambda x, y: cur.execute('select cp7_credit.initial_event_semantics_v1(%s::jsonb)is distinct from cp7_credit.initial_event_semantics_v1(%s::jsonb)',
                                                (json.dumps(x), json.dumps(y))).fetchone()[0]
            c13 = dict(no_credit_old=distinct(native_events, native_events), no_credit_new=distinct(native_events, native_events + []),
                       credit_old=distinct(native_events + incoming, native_events), credit_new=distinct(native_events + incoming, native_events + incoming),
                       missing_incoming_new=distinct(native_events, native_events + incoming))
            assert c13 == dict(no_credit_old=False, no_credit_new=False, credit_old=True, credit_new=False, missing_incoming_new=True), c13
            seen['quote_source_vector_C13_refuses'] = c13
            # C14: the stored recognition hash equals the retained readers' manifest (sorted, no consumption objects);
            # without consumption objects it is the slice B hash.
            cur.execute(bcheck.statement('ledger/01_immutable_facts.proposal.sql', 'cp7_credit.pg_jsonb_sha256'))
            fact = lambda kind, i: dict(object_kind=kind, object_id=i, fact_sha256='0' * 64)
            ids = sorted(str(uuid.uuid4()) for _ in range(4))
            profile_plain = [fact('COHORT', ids[0]), fact('FAMILY', ids[1]), fact('PART', ids[2])]
            profile_with_apply = [fact('COHORT', ids[0]), fact('CONSUMPTION', ids[3]), fact('FAMILY', ids[1]), fact('PART', ids[2])]
            readers = "select cp7_credit.pg_jsonb_sha256(coalesce((select jsonb_agg(x order by x->>'object_kind'collate\"C\",x->>'object_id'collate\"C\")from jsonb_array_elements(%s::jsonb)x where x->>'object_kind'<>'CONSUMPTION'),'[]'))"
            old_store = 'select cp7_credit.pg_jsonb_sha256(%s::jsonb)'
            new_store = ("select cp7_credit.pg_jsonb_sha256((select coalesce(jsonb_agg(x order by x->>'object_kind'collate\"C\",x->>'object_id'collate\"C\"),'[]')"
                         "from jsonb_array_elements(%s::jsonb)x where x->>'object_kind'<>'CONSUMPTION'))")
            h = lambda sql, v: cur.execute(sql, (json.dumps(v),)).fetchone()[0]
            c14 = dict(plain_old_equals_new=h(old_store, profile_plain) == h(new_store, profile_plain),
                       plain_readers_match=h(readers, profile_plain) == h(new_store, profile_plain),
                       with_apply_old_matches_readers=h(old_store, profile_with_apply) == h(readers, profile_with_apply),
                       with_apply_new_matches_readers=h(new_store, profile_with_apply) == h(readers, profile_with_apply))
            assert c14 == dict(plain_old_equals_new=True, plain_readers_match=True, with_apply_old_matches_readers=False,
                               with_apply_new_matches_readers=True), c14
            assert native_delta_text_contains(patched[c.COMPLETE], new_store.split('select ', 1)[1].replace('%s::jsonb', "a->'actual_objects'"))
            seen['refund_recognition_manifest_C14'] = c14
            report['side_by_side'] = seen
            conn.rollback()
        report['profile_C6'] = profile_check(re.sub(r'dbname=\S+', 'dbname=' + DB + '_profile', dsn))
    finally:
        for name in (DB, DB + '_profile'):
            with psycopg.connect(dsn, autocommit=True) as admin:
                admin.execute('drop database if exists ' + name)
    report['status'] = 'LOCAL_PASS'
    report['scope'] = 'LOCAL_PG_STUBS_NOT_NATIVE_NOT_SUPABASE'
    print(json.dumps(report, indent=1, default=str))


def profile_check(dsn):
    """C6 on the slice B profile loop: one settled return, then credit applied to that invoice from another source."""
    import hashlib
    with psycopg.connect(dsn) as conn, conn.cursor() as cur:
        cur.execute("set check_function_bodies=on;set search_path=''")
        cur.execute(step1.STUBS)
        cur.execute(bprofile.EXTRA)
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
        cur.execute((REPO / 'scripts/cp7_credit_multi/multi.sql').read_text())
        cur.execute((HERE / 'incoming.sql').read_text())
        cur.execute(bprofile.predecessor_text(cur))
        before_b = cur.execute('select pg_get_functiondef(%s::regprocedure)', (b.PROFILE,)).fetchone()[0]
        original = b.patch(b.PROFILE, before_b)
        cur.execute(original)
        original = cur.execute('select pg_get_functiondef(%s::regprocedure)', (b.PROFILE,)).fetchone()[0]
        patched = c.patch(c.PROFILE, original)
        refused = delta_checks({c.PROFILE: original}, {c.PROFILE: patched}, (c.PROFILE,))
        cur.execute(patched)
        ar, cash, revenue, customer, sale, item = (str(uuid.uuid4()) for _ in range(6))
        cur.execute("insert into erp.accounting_account_mappings values('AR_CUSTOMER',%s)", (ar,))
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
        r, family, cohort, plan = (str(uuid.uuid4()) for _ in range(4))
        cur.execute("insert into erp.sales_returns values(%s,%s,'POSTED')", (r, sale))
        cur.execute('insert into erp.sales_return_items values(%s,%s,200)', (str(uuid.uuid4()), r))
        journal('SALES_RETURN', r, '2026-10-02', 0, 200)
        cur.execute('insert into cp7_credit.return_families values(%s,%s,1,%s,%s)', (family, sale, r, hashlib.sha256(family.encode()).hexdigest()))
        cur.execute('insert into cp7_credit.return_family_members values(%s,%s)', (family, r))
        before = q('cp7_credit.initial_base_events_v1(%s,%s)', sale, r)
        fresh = q('ow04_pure_kernel.recognition_plan_v1(%s::jsonb,cp7_credit.actual_own_return_events_v1(%s))', json.dumps(before), r)
        preserved = q('cp7_credit.initial_preserved_source_v1(%s,%s)', sale, r)
        cur.execute('insert into cp7_credit.cohorts values(%s,%s,%s,%s,%s)', (cohort, family, sale, r, plan))
        cur.execute("insert into cp7_credit.recognition_plans values(%s,%s,'INITIAL',%s,%s,%s)", (plan, cohort, json.dumps(before), json.dumps(fresh), fresh['net_current_k']))
        for n, component in enumerate(fresh['components'], 1):
            cid, part = str(uuid.uuid4()), str(uuid.uuid4())
            cur.execute('insert into cp7_credit.recognition_components values(%s,%s,%s,%s)', (cid, plan, n, json.dumps(component)))
            cur.execute('insert into cp7_credit.component_parts values(%s,%s,%s)', (part, cid, component['amount']))
            cur.execute('insert into cp7_credit.component_journals values(%s,%s,%s,%s)', (part, str(uuid.uuid4()), component['economic_date'], component['transaction_date']))
        cur.execute('insert into cp7_credit.initial_return_materializations values(%s,%s,%s,%s,%s)',
                    (cohort, plan, json.dumps(dict(preserved_source=preserved)), json.dumps(fresh), json.dumps(dict(return_amount='200'))))
        call = lambda u_text: (sale, sale, sale, json.dumps(dict(sale_id=sale, root_sale_id=sale, current_leaf_id=sale, I='200.00', U=u_text)))

        def run(args):
            out = []
            for text in (original, patched):
                cur.execute(text)
                out.append(step1.outcome(cur, 'select cp7_credit._consumer_root_source_profile_v1(%s,%s,%s,%s::jsonb)::text', args))
            cur.execute(patched)
            return out
        result = dict(no_credit=run(call('0.00')))
        # Credit applied to this invoice from another cohort (the incoming event itself is proven by the consumer root wrapper).
        other = str(uuid.uuid4())
        cur.execute('insert into cp7_credit.cohorts values(%s,%s,%s,null,null)', (other, str(uuid.uuid4()), str(uuid.uuid4())))
        cur.execute("insert into cp7_credit.consumption_events(id,cohort_id,amount,economic_date,transaction_date,source_sha256,event_kind,target_sale_id)"
                    "values(%s,%s,80,'2026-10-03','2026-10-03',%s,'APPLY',%s)", (str(uuid.uuid4()), other, '2' * 64, sale))
        result.update(credit_applied=run(call('80.00')), credit_applied_wrong_U=run(call('70.00')))
        unreconciled = 'CP7_CREDIT_CURRENT_RECOGNITION_TARGET_UNRECONCILED'
        assert result['no_credit'][0] == result['no_credit'][1] and result['no_credit'][0].get('ok'), result['no_credit']
        assert result['credit_applied'][0]['message'] == unreconciled and result['credit_applied'][1].get('ok'), result['credit_applied']
        assert result['credit_applied_wrong_U'][0]['message'] == result['credit_applied_wrong_U'][1]['message'] == unreconciled
        conn.rollback()
        return {k: dict(slice_b=v[0], slice_c=v[1]) for k, v in result.items()}


if __name__ == '__main__':
    main(sys.argv[1])
