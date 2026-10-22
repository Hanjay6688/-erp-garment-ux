"""OW-04b local check on a throwaway PostgreSQL (never hosted; never the Native/Supabase harness).

python3 scripts/cp7_credit_followups/local_check.py 'host=127.0.0.1 port=55480 user=postgres dbname=postgres'

1. Rebuilds the installed predecessor text of the three replaced functions from the repo sources in install order
   (coordinator/02 and 05, native-empty/04 overlay, then the two payment-correction edits, whose literal strings must
   still be in payment_correction/transform.py), installs them on stub objects and reads pg_get_functiondef back.
2. Applies native_delta.patched to that real catalog text: every anchor/marker exactly once, a second application and a
   doubled body refuse.
3. Installs followups.sql and the patched definitions with check_function_bodies on, then CALLS each patched function on
   stub rows up to its retained refusal: same SQLSTATE and message as the predecessor, plus the expected DETAIL; the
   predecessor gives no detail. The pure readers are checked for every reason, combinations and the fallback.
The database it creates is dropped at the end. Stubs only stand in for objects the refusal path reads first.
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
from cp7_credit_followups import native_delta  # noqa: E402

CREDIT = REPO / 'scripts/cp7_customer_credit'
DB = 'ow04b_local_check'
PAYMENT_ENTER = ('begin\n', "begin\n if cp7_credit.payment_native_enter_v1(p_action,p_source)then return;end if;\n")
PAYMENT_BASE_REMOVED = ("\n  or exists(select 1 from cp7_payment_correction.links l join erp.sales_payments p0 on p0.id in"
                        "(l.original_id,l.replacement_id)where p0.sale_id=p_sale)")
PAYMENT_BASE_ANCHOR = "  raise exception 'CP7_CREDIT_SOURCE_CORRECTION_ADAPTER_UNIMPLEMENTED';end if;"
PAYMENT_BASE_ADDED = "\n perform cp7_credit.payment_link_source_check_v1(p_sale);"

STUBS = r"""
do $roles$declare r text;begin
 foreach r in array array['cp7_capture','cp7_sales_read','cp7_sales_write','cp7_credit_write','cp7_credit_visible_read',
  'anon','authenticated','service_role']loop
  if not exists(select 1 from pg_roles where rolname=r)then execute format('create role %I nologin',r);end if;
 end loop;
end $roles$;
create schema erp;create schema auth;create schema cp7_credit;create schema cp7_sales;create schema ow04_source_proposal;
create schema cp7_note;create schema cp7_sales_return_correction;create schema cp7_payment_correction;create schema local_fixture;
create table local_fixture.source(src jsonb);
create table erp.sales_headers(id uuid primary key,status text);
create table erp.sales_payments(id uuid primary key,sale_id uuid,status text);
create table erp.sales_returns(id uuid primary key,sale_id uuid,status text);
create table erp.sales_payment_posting_facts(payment_id uuid);create table erp.sales_payment_reversal_facts(payment_id uuid);
create table erp.journal_entries(id uuid);
create table cp7_sales.command_context(backend_pid integer,transaction_id bigint,actor uuid,sale_id uuid,action text);
create table cp7_sales.requests(actor uuid,request_id uuid,action text,payload jsonb,expected_version text,response jsonb);
create table cp7_credit.return_families(id uuid primary key,family_root_sale_id uuid);
create table cp7_credit.cohorts(id uuid primary key,family_id uuid,source_sale_id uuid);
create table cp7_credit.consumption_events(id uuid primary key,event_kind text,target_sale_id uuid);
create table cp7_sales_return_correction.links(id uuid primary key,sale_id uuid);
create table cp7_note.revisions(root_sale_id uuid,previous_sale_id uuid,replacement_sale_id uuid);
create table cp7_payment_correction.links(original_id uuid,replacement_id uuid);
create function auth.uid()returns uuid language sql as $$select null::uuid$$;
create function cp7_sales.validate_return(jsonb,boolean)returns void language sql as $$select$$;
create function cp7_sales.command_access(text)returns jsonb language sql as $$select '{"stub":true}'::jsonb$$;
create function cp7_credit.return_command_access(text)returns jsonb language sql as $$select '{"stub":true}'::jsonb$$;
create function cp7_credit.initial_choice_v1(jsonb)returns jsonb language sql as $$select '{}'::jsonb$$;
create function ow04_source_proposal.locked_source_family(uuid)returns jsonb language sql as $$select src from local_fixture.source$$;
create function cp7_credit.payment_native_enter_v1(text,uuid)returns boolean language sql as $$select false$$;
create function cp7_credit.native_empty_is_direct_v1()returns boolean language sql as $$select false$$;
create function cp7_credit.native_empty_source_enter_v1(text,uuid)returns void language sql as $$select$$;
create function cp7_credit.source_operation_owns_v1(text,uuid)returns boolean language sql as $$select false$$;
create function cp7_credit.source_operation_native_enter_v1(text,uuid)returns void language sql as $$select$$;
create function cp7_credit.has_ow04_participation_v1(uuid)returns boolean language sql as $$select true$$;
create function cp7_credit.payment_link_source_check_v1(uuid)returns void language sql as $$select$$;
"""


def statement(path, name):
    text = (CREDIT / path).read_text()
    found = re.findall(r'create (?:or replace )?function ' + re.escape(name) + r'\(.*?\$\$;', text, re.S)
    assert len(found) == 1, ('LOCAL_SOURCE_STATEMENT_NOT_UNIQUE', path, name, len(found))
    return found[0]


def once(text, old, new, label):
    assert text.count(old) == 1, ('LOCAL_PAYMENT_EDIT_ANCHOR', label, text.count(old))
    return text.replace(old, new, 1)


def definition(cur, sig):
    return cur.execute('select pg_get_functiondef(%s::regprocedure)', (sig,)).fetchone()[0]


def refusal(cur, sql, args=()):
    cur.execute('savepoint local_refusal')
    try:
        cur.execute(sql, args)
    except psycopg.Error as error:
        cur.execute('rollback to savepoint local_refusal')
        return dict(sqlstate=error.sqlstate, message=error.diag.message_primary, detail=error.diag.message_detail or '')
    cur.execute('rollback to savepoint local_refusal')
    raise AssertionError('LOCAL_EXPECTED_REFUSAL: ' + sql)


def detail(refusal_kind, action, reasons, blockers=()):
    return dict(contract='cp7.credit-followups.refusal.v1', refusal=refusal_kind, action=action,
                reasons=list(reasons), source_blockers=list(blockers))


def main(dsn):
    transform = (CREDIT / 'payment_correction/transform.py').read_text()
    for literal in ("'begin\\n', 'begin\\n if cp7_credit.'+call+'(p_action,p_source)then return;end if;\\n'",
                    "('cp7_credit.native_source_enter(text,uuid)', 'payment_native_enter_v1')",
                    'or exists(select 1 from cp7_payment_correction.links l join erp.sales_payments p0 on p0.id in(l.original_id,l.replacement_id)where p0.sale_id=p_sale)',
                    "anchor = \"  raise exception 'CP7_CREDIT_SOURCE_CORRECTION_ADAPTER_UNIMPLEMENTED';end if;\"",
                    "anchor+'\\n perform cp7_credit.payment_link_source_check_v1(p_sale);'"):
        assert literal in transform, ('LOCAL_PAYMENT_TRANSFORM_CHANGED', literal)
    report = {}
    with psycopg.connect(dsn, autocommit=True) as admin:
        admin.execute('drop database if exists ' + DB)
        admin.execute('create database ' + DB)
    try:
        with psycopg.connect(re.sub(r'dbname=\S+', 'dbname=' + DB, dsn)) as conn, conn.cursor() as cur:
            cur.execute("set check_function_bodies=on;set search_path=''")
            cur.execute(STUBS)
            # 1. Predecessor text in install order (02/05 coordinator; native-empty overlay; payment-correction edits).
            cur.execute(statement('coordinator/02_initial_projection.sql', 'cp7_credit.build_initial_return_for_draft_v1'))
            cur.execute(statement('coordinator/05_factual_profile.sql', 'cp7_credit.assert_simple_native_base_v1'))
            cur.execute(statement('native-empty/04_exact_overlays.sql', 'cp7_credit.native_source_enter'))
            enter = once(definition(cur, native_delta.ENTER), *PAYMENT_ENTER, 'enter')
            cur.execute(enter)
            base = once(definition(cur, native_delta.BASE), PAYMENT_BASE_REMOVED, '', 'base-link')
            base = once(base, PAYMENT_BASE_ANCHOR, PAYMENT_BASE_ANCHOR + PAYMENT_BASE_ADDED, 'base-check')
            cur.execute(base)
            originals = {sig: definition(cur, sig) for sig in native_delta.SIGNATURES}
            # 2. Counted delta on that catalog text, and its refusals.
            patched = native_delta.patched(originals)
            for sig in native_delta.SIGNATURES:
                assert originals[sig].count(native_delta.anchor(sig)) == 1 and patched[sig].count(native_delta.replacement(sig)) == 1
                assert patched[sig].replace(native_delta.replacement(sig), native_delta.anchor(sig), 1) == originals[sig]
            refused = []
            for label, bad in (('twice', patched),
                               ('doubled', {sig: text + text for sig, text in originals.items()}),
                               ('missing', {sig: text.replace(native_delta.anchor(sig), '') for sig, text in originals.items()})):
                try:
                    native_delta.patched(bad)
                except ValueError as error:
                    refused.append((label, str(error).split(':')[0]))
            assert [label for label, _ in refused] == ['twice', 'doubled', 'missing'], refused
            report['anchors'] = dict(exactly_once=True, refused=refused)
            # 3a. Predecessor refusals on stub rows: message, no detail.
            sale, target, revised, corrected, payment, ret = (str(uuid.uuid4()) for _ in range(6))
            cur.execute('insert into erp.sales_headers values(%s,%s),(%s,%s),(%s,%s),(%s,%s)',
                        (sale, 'PAID', target, 'PARTIAL_PAID', revised, 'PAID', corrected, 'PAID'))
            cur.execute('insert into erp.sales_payments values(%s,%s,%s)', (payment, target, 'DRAFT'))
            cur.execute('insert into erp.sales_returns values(%s,%s,%s)', (ret, sale, 'POSTED'))
            family = str(uuid.uuid4())
            cur.execute('insert into cp7_credit.return_families values(%s,%s)', (family, sale))
            cur.execute('insert into cp7_credit.cohorts values(%s,%s,%s)', (str(uuid.uuid4()), family, sale))
            cur.execute("insert into cp7_credit.consumption_events values(%s,'APPLY',%s)", (str(uuid.uuid4()), target))
            cur.execute('insert into cp7_note.revisions values(%s,%s,%s)', (revised, revised, str(uuid.uuid4())))
            cur.execute('insert into cp7_sales_return_correction.links values(%s,%s)', (str(uuid.uuid4()), corrected))

            def source(status='BASE_COLLECTED', revisions=(), blockers=()):
                cur.execute('delete from local_fixture.source')
                cur.execute('insert into local_fixture.source values(%s::jsonb)', (json.dumps(dict(
                    source_status=status, blockers=[dict(code=code) for code in blockers],
                    family=dict(note_revisions=list(revisions)))),))

            def build(for_sale):
                return refusal(cur, 'select cp7_credit.build_initial_return_for_draft_v1(%s::jsonb,%s,%s::jsonb,null)',
                               (json.dumps(dict(sale_id=for_sale)), '1', json.dumps(dict(mode=None))))

            calls = dict(
                build_prior=(lambda: (source(), build(sale))[1], 'CP7_CREDIT_INITIAL_SOURCE_FAMILY_UNSUPPORTED',
                             detail('INITIAL_SOURCE_FAMILY', None, ['PRIOR_CREDIT_RETURN'])),
                build_applied=(lambda: (source(), build(target))[1], 'CP7_CREDIT_INITIAL_SOURCE_FAMILY_UNSUPPORTED',
                               detail('INITIAL_SOURCE_FAMILY', None, ['CREDIT_APPLIED_TO_INVOICE'])),
                build_revised=(lambda: (source(revisions=[{'revision': 1}]), build(revised))[1],
                               'CP7_CREDIT_INITIAL_SOURCE_FAMILY_UNSUPPORTED', detail('INITIAL_SOURCE_FAMILY', None, ['NOTE_REVISED'])),
                build_corrected=(lambda: (source(), build(corrected))[1], 'CP7_CREDIT_INITIAL_SOURCE_FAMILY_UNSUPPORTED',
                                 detail('INITIAL_SOURCE_FAMILY', None, ['RETURN_CORRECTED'])),
                build_blocked=(lambda: (source('BLOCKED', blockers=['AR_MAPPING_OR_ACCOUNT_CHANGED', 'RESTATEMENT_PRECEDES_ORIGINAL_BOOK']),
                                        build(sale))[1], 'CP7_CREDIT_INITIAL_SOURCE_FAMILY_UNSUPPORTED',
                               detail('INITIAL_SOURCE_FAMILY', None, ['SOURCE_HISTORY_BLOCKED', 'PRIOR_CREDIT_RETURN'],
                                      ['AR_MAPPING_OR_ACCOUNT_CHANGED', 'RESTATEMENT_PRECEDES_ORIGINAL_BOOK'])),
                enter_return=(lambda: refusal(cur, "select cp7_credit.native_source_enter('RETURN_REVERSE',%s)", (ret,)),
                              'CP7_CREDIT_REGISTERED_SOURCE_MUTATION_REQUIRES_BOUND_RECONCILIATION',
                              detail('REGISTERED_SOURCE_MUTATION', 'RETURN_REVERSE', ['PRIOR_CREDIT_RETURN'])),
                enter_payment=(lambda: refusal(cur, "select cp7_credit.native_source_enter('PAYMENT',%s)", (payment,)),
                               'CP7_CREDIT_REGISTERED_SOURCE_MUTATION_REQUIRES_BOUND_RECONCILIATION',
                               detail('REGISTERED_SOURCE_MUTATION', 'PAYMENT', ['CREDIT_APPLIED_TO_INVOICE'])),
                base_revised=(lambda: refusal(cur, 'select cp7_credit.assert_simple_native_base_v1(%s)', (revised,)),
                              'CP7_CREDIT_SOURCE_CORRECTION_ADAPTER_UNIMPLEMENTED', detail('SOURCE_CORRECTION', None, ['NOTE_REVISED'])),
                base_corrected=(lambda: refusal(cur, 'select cp7_credit.assert_simple_native_base_v1(%s)', (corrected,)),
                                'CP7_CREDIT_SOURCE_CORRECTION_ADAPTER_UNIMPLEMENTED', detail('SOURCE_CORRECTION', None, ['RETURN_CORRECTED'])),
            )
            before = {name: call() for name, (call, _, _) in calls.items()}
            for name, (_, message, _) in calls.items():
                assert before[name] == dict(sqlstate='P0001', message=message, detail=''), (name, before[name])
            # 3b. The stage: readers, then patched definitions, compiled with check_function_bodies on.
            cur.execute((HERE / 'followups.sql').read_text())
            for sig in native_delta.SIGNATURES:
                cur.execute(patched[sig])
                assert definition(cur, sig) == patched[sig], ('LOCAL_INSTALLED_TEXT_DIFFERS', sig)
            after = {name: call() for name, (call, _, _) in calls.items()}
            for name, (_, message, wanted) in calls.items():
                got = after[name]
                assert (got['sqlstate'], got['message']) == ('P0001', message), (name, got)
                assert json.loads(got['detail']) == wanted, (name, got)
            report['refusals'] = {name: dict(message=after[name]['message'], detail=json.loads(after[name]['detail']))
                                  for name in calls}
            # 3c. Pure reader edge cases: several reasons together, a non-array revision list, the fallback.
            cur.execute("insert into cp7_credit.consumption_events values(%s,'APPLY',%s)", (str(uuid.uuid4()), sale))
            both = cur.execute('select cp7_credit_followups.source_mutation_reasons_v1(%s,%s)', ('SALE_REVERSE', sale)).fetchone()[0]
            assert json.loads(both) == detail('REGISTERED_SOURCE_MUTATION', 'SALE_REVERSE', ['PRIOR_CREDIT_RETURN', 'CREDIT_APPLIED_TO_INVOICE'])
            odd = cur.execute("select cp7_credit_followups.initial_family_reasons_v1(%s,'{\"source_status\":null,\"family\":{\"note_revisions\":{}}}'::jsonb)",
                              (str(uuid.uuid4()),)).fetchone()[0]
            assert json.loads(odd) == detail('INITIAL_SOURCE_FAMILY', None, ['UNCLASSIFIED'])
            for role in ('anon', 'authenticated', 'service_role', 'cp7_capture', 'cp7_sales_read', 'cp7_sales_write', 'cp7_credit_write'):
                for sig in ('cp7_credit_followups.detail_v1(text,text,jsonb,jsonb)', 'cp7_credit_followups.initial_family_reasons_v1(uuid,jsonb)',
                            'cp7_credit_followups.correction_reasons_v1(uuid)', 'cp7_credit_followups.source_mutation_reasons_v1(text,uuid)'):
                    assert not cur.execute("select has_function_privilege(%s,%s,'EXECUTE')", (role, sig)).fetchone()[0], (role, sig)
                assert not cur.execute("select has_schema_privilege(%s,'cp7_credit_followups','USAGE')", (role,)).fetchone()[0], role
            report['reader_edges'] = dict(two_reasons=json.loads(both), malformed_source=json.loads(odd), private=True)
            conn.rollback()
    finally:
        with psycopg.connect(dsn, autocommit=True) as admin:
            admin.execute('drop database if exists ' + DB)
    report['status'] = 'LOCAL_PASS'
    report['scope'] = 'LOCAL_PG_STUBS_NOT_NATIVE_NOT_SUPABASE'
    print(json.dumps(report, indent=1))


if __name__ == '__main__':
    main(sys.argv[1])
