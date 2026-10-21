"""Atomic OW04 composition for the closed disposable Native qualification.

This is the integrating writer, not a permissive proposal runner. It first
verifies the installed predecessor; records its complete accepted captures;
then composes actual source, accounting, Native, and reader implementations.
The caller owns the transaction and must roll back every failure.
"""
from __future__ import annotations

from copy import deepcopy
from contextlib import contextmanager
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import re
import sys
from psycopg.pq import TransactionStatus

ROOT = Path(__file__).resolve().parents[1]
REPO = Path(__file__).resolve().parents[3]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def digest(value):
    return sha256(value.encode()).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), default=str)


SQL_FILES = (
    'kernel/kernel.sql', 'ordinal-wrapper/wrapper.sql',
    'ledger/01_immutable_facts.proposal.sql', 'ledger/02_uuid_poster.proposal.sql',
    'source/NO_JOURNAL_SCHEMA_DIFF.proposal.sql', 'source/source.sql',
    'source/member-proof.sql', 'source/absence-proof.sql',
    'readers/01_current_reader_capability.proposal.sql',
    'readers/02_materialized_profile.proposal.sql',
    'reconciliation/01_source_operation_facts.sql',
    'admission/01_typed_context_and_preclaim.proposal.sql',
    'admission/02_owning_wrapper.proposal.sql', 'refund/01_initial_refund.proposal.sql',
    'coordinator/01_coordinator_facts.sql', 'coordinator/02_hpp_book.sql',
    'coordinator/02_initial_projection.sql',
    'coordinator/03_native_initial_callbacks.sql',
    'coordinator/03_opening_return_hpp.sql',
    'coordinator/03_opening_hpp_diagnostics.sql',
    'coordinator/04_register_and_materialize.sql', 'coordinator/05_factual_profile.sql',
    'coordinator/06_finish_and_closed_routes.sql',
    'coordinator/07_capabilities_and_quote.sql', 'coordinator/08_outer_wrapper.sql',
    'coordinator/09_public_facades.sql',
    'reconciliation/02_reconciliation_inputs.sql',
    'reconciliation/03_source_requests.sql',
    'reconciliation/03_native_inverse_proof.sql',
    'reconciliation/04_source_binding.sql',
    'reconciliation/05_source_adjustments.sql',
    'reconciliation/06_source_coordinator.sql',
    'reconciliation/07_source_closure.sql',
)
NEW_SCHEMAS = ('cp7_credit', 'ow04_ordinal_wrapper', 'ow04_source_proposal', 'ow04_pure_kernel')
NEW_ROLES = ('cp7_credit_write', 'cp7_credit_visible_read')
NEW_ERP = (
    'erp._cp7_receivable_credit_adjustment(uuid)',
    'erp._cp7_current_credit_adjustment_visible(uuid)',
    'erp._cp7_current_credit_adjustment(uuid)',
)
NEW_PUBLIC = (
    'public.erp_cp7_settle_sales_return_v1(jsonb,uuid,text)',
    'public.erp_cp7_get_sales_return_settlement_quote_v1(jsonb)',
)
NEW_SALES = (
    'cp7_sales.execute_preclaimed_credit_return(uuid,jsonb,text)',
    'cp7_sales.preclaim_credit_return(uuid,jsonb,text)',
)
PRIVATE_FUNCTION_OWNERS = {
    'cp7_credit.return_settlement_command(jsonb,uuid,text)': 'cp7_credit_write',
    'cp7_credit._has_ambient_plan_apply_scope()': 'cp7_plan_writer',
    'cp7_credit.lock_payment_correction_links(uuid[])': 'cp7_sales_write',
}
PAYMENT_LINK_LOCK_SQL = """create function cp7_credit.lock_payment_correction_links(p_payments uuid[])returns void
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $lock_links$
begin
 perform 1 from cp7_payment_correction.links where original_id=any(p_payments)
  or replacement_id=any(p_payments)order by original_id for share;
end $lock_links$;
grant create on schema cp7_credit to cp7_sales_write;
alter function cp7_credit.lock_payment_correction_links(uuid[])owner to cp7_sales_write;
revoke create on schema cp7_credit from cp7_sales_write;
revoke all on function cp7_credit.lock_payment_correction_links(uuid[])from public,anon,authenticated,service_role,cp7_capture,cp7_sales_read;
grant execute on function cp7_credit.lock_payment_correction_links(uuid[])to postgres;
"""


def _payment_link_metadata(cur):
    row = cur.execute("select pg_get_userbyid(relowner),relrowsecurity,relforcerowsecurity,relacl::text[]"
        "from pg_class where oid='cp7_payment_correction.links'::regclass").fetchone()
    if row is None or row[:3]!=('cp7_sales_write',True,False):
        raise ValueError('OW04_PAYMENT_LINK_LOCK_OWNER_OR_VISIBILITY_CHANGED')
    return row
PRIVATE_TABLE_OWNERS = {
    'cp7_credit.return_requests': 'cp7_credit_write',
    'cp7_credit.return_command_scope': 'cp7_credit_write',
}


def _finalize_private_owners(cur):
    """Only the four fresh, uncommitted schemas; never ERP/predecessor grants."""
    for schema in NEW_SCHEMAS:
        cur.execute('alter schema ' + schema + ' owner to postgres')
    tables = cur.execute("select n.nspname||'.'||c.relname,c.relrowsecurity "
        "from pg_class c join pg_namespace n on n.oid=c.relnamespace "
        "where n.nspname=any(%s::text[])and c.relkind in('r','p') order by 1", (list(NEW_SCHEMAS),)).fetchall()
    for identity, rls in tables:
        cur.execute('alter table ' + identity + ' owner to ' + PRIVATE_TABLE_OWNERS.get(identity,'postgres'))
        if rls and not cur.execute('select exists(select 1 from pg_policy where polrelid=%s::regclass)',(identity,)).fetchone()[0]:
            # Explicit false is the same default denial as RLS/no policies.
            cur.execute('create policy ow04_deny_direct on ' + identity + ' for all to public using(false)with check(false)')
    for (identity,) in cur.execute("select p.oid::regprocedure::text from pg_proc p join pg_namespace n on n.oid=p.pronamespace "
            "where n.nspname=any(%s::text[])order by 1",(list(NEW_SCHEMAS),)).fetchall():
        cur.execute('alter function ' + identity + ' owner to ' + PRIVATE_FUNCTION_OWNERS.get(identity,'postgres'))
    cur.execute('alter domain cp7_credit.cent_amount owner to postgres')
    # The postgres-owned seal/materialize/finish helpers read these two new
    # outer-owned facts and update only the server-maintained scope fields.
    cur.execute('grant select on cp7_credit.return_requests,cp7_credit.return_command_scope to postgres')
    cur.execute('grant update(stage,source_lock_sha256,projection_sha256,credit_account_snapshot,cash_account_snapshot,'
        'return_id,family_id,family_ordinal,actual_manifest_sha256)on cp7_credit.return_command_scope to postgres')


def _private_inventory(cur):
    schemas = cur.execute("select nspname,pg_get_userbyid(nspowner),nspacl::text[]from pg_namespace "
        "where nspname=any(%s::text[])order by 1",(list(NEW_SCHEMAS),)).fetchall()
    domains = cur.execute("select t.oid::regtype::text,pg_get_userbyid(t.typowner),t.typacl::text[],t.typbasetype::regtype::text,"
        "t.typnotnull,t.typtypmod,(select jsonb_agg(jsonb_build_array(c.conname,c.convalidated,pg_get_constraintdef(c.oid,false))order by c.conname)"
        "from pg_constraint c where c.contypid=t.oid)from pg_type t join pg_namespace n on n.oid=t.typnamespace "
        "where n.nspname=any(%s::text[])and t.typtype='d'order by 1",(list(NEW_SCHEMAS),)).fetchall()
    functions = cur.execute("select p.oid::regprocedure::text,pg_get_userbyid(p.proowner),p.prosecdef,p.provolatile::text,"
        "p.proconfig,p.proacl::text[],encode(pg_catalog.sha256(convert_to(pg_get_functiondef(p.oid),'UTF8')),'hex') "
        "from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname=any(%s::text[])order by 1",
        (list(NEW_SCHEMAS),)).fetchall()
    tables = cur.execute("select n.nspname||'.'||c.relname,pg_get_userbyid(c.relowner),c.relacl::text[],c.relrowsecurity,c.relforcerowsecurity,"
        "(select jsonb_agg(jsonb_build_array(a.attname,a.attacl)order by a.attnum)from pg_attribute a where a.attrelid=c.oid and a.attnum>0 and not a.attisdropped),"
        "(select jsonb_agg(jsonb_build_array(p.polname,p.polcmd,p.polroles,p.polpermissive,pg_get_expr(p.polqual,p.polrelid),pg_get_expr(p.polwithcheck,p.polrelid))order by p.polname)from pg_policy p where p.polrelid=c.oid) "
        "from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname=any(%s::text[])and c.relkind in('r','p')order by 1",
        (list(NEW_SCHEMAS),)).fetchall()
    for identity,owner,*_ in functions:
        if owner != PRIVATE_FUNCTION_OWNERS.get(identity,'postgres'):
            raise ValueError('OW04_PRIVATE_FUNCTION_OWNER_CHANGED: '+identity)
    for identity,owner,*_ in tables:
        if owner != PRIVATE_TABLE_OWNERS.get(identity,'postgres'):
            raise ValueError('OW04_PRIVATE_TABLE_OWNER_CHANGED: '+identity)
    if len(schemas)!=len(NEW_SCHEMAS)or any(x[1]!='postgres'for x in schemas):
        raise ValueError('OW04_PRIVATE_SCHEMA_OWNER_CHANGED')
    if len(domains)!=1 or domains[0][0]!='cp7_credit.cent_amount'or domains[0][1]!='postgres':
        raise ValueError('OW04_PRIVATE_DOMAIN_OWNER_CHANGED')
    if not set(PRIVATE_FUNCTION_OWNERS)<=set(x[0]for x in functions)or not set(PRIVATE_TABLE_OWNERS)<=set(x[0]for x in tables):
        raise ValueError('OW04_PRIVATE_CAPABILITY_OBJECT_MISSING')
    with _postgres_reader(cur):
        for table in PRIVATE_TABLE_OWNERS:
            row = cur.execute("select has_table_privilege('postgres',%s,'SELECT'),row_security_active(%s::regclass)",
                (table,table)).fetchone()
            if row!=(True,False):raise ValueError('OW04_PRIVATE_OUTER_SCOPE_VISIBILITY_CHANGED')
    return {'schemas':schemas,'domains':domains,'functions':functions,'tables':tables}


def source_files(native_empty=False):
    names = SQL_FILES + ('integration/source_command_transform.py',
                         'integration/source_triggers/trigger_guard.py',
                         'integration/source_triggers/capture.sql',
                         'integration/source_triggers/SOURCE_PINS.json',
                         'integration/source_triggers/build_source_pins.py',
                         'integration/typed_context_inventory.py',
                         'integration/derive_plan.py',)
    if native_empty:
        names += ('native-empty/01_native_empty_facts.sql','native-empty/02_native_empty_callbacks.sql',
                  'native-empty/04_exact_overlays.sql','native-empty/OVERLAY_MANIFEST.json',
                  'native-empty/SOURCE_PINS.json','native-empty/EXPECTED.json',
                  'native-empty/cp7_ow04_native_empty_cases.py','integration/native_empty_bundle.py')
    return {name: digest((ROOT / name).read_text()) for name in names}


def _actual_sql(name):
    text = (ROOT / name).read_text()
    # A marker is removed only as part of this complete closed composition,
    # never to execute a fragment with missing guards. Other DO blocks remain.
    marker = re.compile(r'do \$not_an_installer\$\s*begin\s*raise exception\s+\'[^\']+\';\s*end \$not_an_installer\$;', re.I)
    count = text.lower().count('do $not_an_installer$')
    if count > 1 or (count and len(marker.findall(text)) != 1):
        raise ValueError('OW04_UNDECLARED_FRAGMENT_BARRIER: ' + name)
    return marker.sub('-- Atomic complete owning composition below.', text)


def _predecessor_approval(cur, assembly, verify, functions):
    receipt = {'raw_probe_verify': verify(cur), 'function_inventory': functions(cur),
               'classification': 'VERIFIED_PREDECESSOR_BEFORE_OW04_CAPTURE'}
    rows = [assembly._capture(cur, identity) for identity in assembly.REQUIRED]
    manifest = {
        'contract_version': 'ow04.native-approved.v1',
        'baseline_verification': {
            'phase': 'VERIFIED_PREDECESSOR', 'verifiers': ['probe.verify', 'p09.functions'],
            'receipt_sha256': digest(canonical(receipt)),
        },
        'functions': [assembly._fingerprint(row) for row in rows],
        'helper_sources': assembly._helper_rows(cur),
        'legacy_verifier_sources': {name: digest((REPO / name).read_text()) for name in assembly.LEGACY_FILES},
        'absent_targets': [assembly.BOUND],
    }
    assembly._approval(manifest)
    return manifest, receipt


def _view_capture(cur):
    row = cur.execute("select pg_get_viewdef(c.oid,true),pg_get_userbyid(c.relowner),c.relacl::text[],c.reloptions "
        "from pg_class c where c.oid='erp.v_customer_receivables'::regclass").fetchone()
    return {'definition': row[0], 'owner': row[1], 'acl': row[2], 'options': row[3]}


def _opening_trigger_capture(cur):
    """Bind the real unchanged trigger attachment, not only its function."""
    rows = cur.execute("select t.oid::text,n.nspname,c.relname,t.tgname,t.tgenabled::text,t.tgtype::integer,"
        "t.tgisinternal,t.tgnargs,t.tgconstraint::text,t.tgdeferrable,t.tginitdeferred,"
        "pg_get_expr(t.tgqual,t.tgrelid),encode(t.tgargs,'hex'),"
        "array(select a.attname::text from pg_attribute a where a.attrelid=t.tgrelid and a.attnum=any(t.tgattr)order by a.attnum),"
        "pg_get_triggerdef(t.oid,false),pg_get_userbyid(c.relowner) "
        "from pg_trigger t join pg_class c on c.oid=t.tgrelid join pg_namespace n on n.oid=c.relnamespace "
        "where t.tgfoid='erp.sync_opening_hpp_after_return_status()'::regprocedure order by t.oid").fetchall()
    if len(rows) != 1:
        raise ValueError('OW04_OPENING_RETURN_TRIGGER_ATTACHMENT_SET_CHANGED')
    row = rows[0]
    expected = ('erp','sales_returns','trg_sync_opening_hpp_after_return_status','O',17,
        False,0,'0',False,False,None,'',['status'],
        'CREATE TRIGGER trg_sync_opening_hpp_after_return_status AFTER UPDATE OF status ON erp.sales_returns '
        'FOR EACH ROW EXECUTE FUNCTION erp.sync_opening_hpp_after_return_status()', 'postgres')
    if row[1:] != expected:
        raise ValueError('OW04_OPENING_RETURN_TRIGGER_ATTACHMENT_CHANGED')
    return row


def _opening_pending_capture(cur):
    return cur.execute("select c.relname,pg_get_userbyid(c.relowner),c.relrowsecurity,c.relforcerowsecurity,"
        "(select jsonb_agg(jsonb_build_array(k.conname,k.contype,k.condeferrable,k.condeferred,k.convalidated,"
        "pg_get_constraintdef(k.oid,false))order by k.conname)from pg_constraint k where k.conrelid=c.oid),"
        "(select jsonb_agg(jsonb_build_array(t.tgname,t.tgenabled,pg_get_triggerdef(t.oid,false))order by t.tgname)"
        "from pg_trigger t where t.tgrelid=c.oid and not t.tgisinternal)from pg_class c "
        "where c.oid='cp7_credit.opening_return_hpp_work_v1'::regclass").fetchone()


@contextmanager
def _postgres_reader(cur):
    """Measure visibility as the actual private guard owner, not installer."""
    previous = cur.execute("select current_setting('role')").fetchone()[0]
    cur.execute('set local role postgres')
    try:
        yield
    finally:
        # A database exception requires the caller's atomic rollback. Do not
        # replace that first error with another statement in an aborted tx.
        if cur.connection.info.transaction_status != TransactionStatus.INERROR:
            cur.execute("select set_config('role',%s,true)", (previous,))


def _source_trigger_capture(cur, guard):
    previous=cur.execute('show search_path').fetchone()[0]
    cur.execute("select set_config('search_path','',true)")
    try:
        with _postgres_reader(cur):
            return guard.capture(cur)
    finally:
        if cur.connection.info.transaction_status != TransactionStatus.INERROR:
            cur.execute("select set_config('search_path',%s,true)",(previous,))


def _source_trigger_install_phase(cur, state, guard, manifest, phase):
    before=state['source_triggers']
    actual=_source_trigger_capture(cur,guard)
    guard.expected_transition(before['installed'],actual,manifest,before['phase'],phase)
    # PostgreSQL computes its own jsonb canonical hash. Python's JSON encoding
    # is not PostgreSQL's text codec. Keep the full checked capture in state,
    # while the callable guard stores its exact digest instead of 450KB SQL.
    expected_sha=cur.execute('select cp7_credit.pg_jsonb_sha256(%s::jsonb)',(canonical(actual),)).fetchone()[0]
    runtime=guard.render_runtime_guard(actual,manifest,phase,expected_sha)
    cur.execute(runtime,prepare=False)
    before.update(installed=actual,phase=phase,runtime_definition_sha256=digest(runtime),runtime_capture_sha256_pg=expected_sha,
        proof=guard.validate_source(actual,manifest,phase))


def install(cur, predecessor_verify, predecessor_functions, *, native_empty=False):
    """Execute in caller's SINGLE transaction; no commit and no partial mode."""
    for schema in NEW_SCHEMAS:
        if cur.execute('select to_regnamespace(%s)is not null',(schema,)).fetchone()[0]:
            raise ValueError('OW04_NEW_SCHEMA_ALREADY_EXISTS: '+schema)
    assembly = load('ow04_integrated_native_plan', ROOT / 'integration/derive_plan.py')
    readers = load('ow04_integrated_reader_plan', ROOT / 'readers/03_reader_transforms.py')
    refunds = load('ow04_integrated_refund_plan', ROOT / 'refund/02_native_refund_transform.py')
    approval, receipt = _predecessor_approval(cur, assembly, predecessor_verify, predecessor_functions)
    trigger_guard=load('ow04_integrated_source_trigger_guard',ROOT/'integration/source_triggers/trigger_guard.py')
    trigger_manifest=trigger_guard.declarations(REPO)
    trigger_before=_source_trigger_capture(cur,trigger_guard)
    trigger_guard.validate_source(trigger_before,trigger_manifest,'VERIFIED_PREDECESSOR')
    payment_link_before = _payment_link_metadata(cur)
    opening_trigger_before = _opening_trigger_capture(cur)
    opening_diagnostic_before = assembly._capture(cur, 'erp.sync_opening_lot_hpp_to_gl(uuid,date)')
    captures = assembly.capture_verified(cur, approval, REPO)
    plan = assembly.derive_plan(captures, approval)
    reader_before = {sig: assembly._capture(cur, sig) for sig in readers.TRANSFORMS}
    reader_targets = {}
    for sig, before in reader_before.items():
        definition, proof = readers.derive(before, assembly._fingerprint(before))
        reader_targets[sig] = {'definition': definition, 'proof': proof}
    view_before = _view_capture(cur)
    if view_before['owner'] != 'postgres' or 'security_invoker=true' not in (view_before['options'] or []):
        raise ValueError('OW04_NATIVE_RECEIVABLE_VIEW_METADATA_CHANGED')
    view_after = readers.receivables_view(view_before['definition'])
    # The Native admission dispatch is not the complete set of private scopes.
    # Keep its exact proof, then capture the closed source-backed typed census
    # across every namespace, including correction and transaction-only scopes.
    guard = load('ow04_integrated_internal_guard', REPO / 'scripts/cp7_internal_guard_bundle.py')
    guard.verify(cur)
    guard_body = cur.execute("select prosrc from pg_proc where oid='erp.require_internal()'::regprocedure").fetchone()[0]
    unpatched, probe = guard.unpatched(guard_body)
    context_names = guard.contexts(unpatched)
    contexts = load('ow04_integrated_context_inventory', ROOT / 'integration/typed_context_inventory.py')
    with _postgres_reader(cur):
        census = contexts.capture(cur, REPO, context_names)
    refusal_guards = contexts.render_guards(census)
    context_proof = {'guard_body_sha256':digest(guard_body),'probe_sha256':digest(probe),
                     'typed_census':census}
    # Refund is a second exact private copy from the SAME approved actual
    # Native poster. Its source UUID and journal pair are operation-bound.
    poster = next(row for row in captures['functions'] if row['identity'] == assembly.POSTER)
    cap = refunds.native.Capture(**{**poster, 'acl': tuple(poster['acl'] or ()), 'config': tuple(poster['config'] or ())})
    approved = refunds.native.Approved(**{**{k: v for k, v in assembly._fingerprint(poster).items() if k != 'body_sha256'},
        'acl':tuple(poster['acl'] or ()), 'config':tuple(poster['config'] or ())})
    refund_sql, refund_proof = refunds.derive_initial_refund_post(cap, approved)
    expected_sources = source_files(native_empty=native_empty)
    for name in SQL_FILES:
        if digest((ROOT / name).read_text()) != expected_sources[name]:
            raise ValueError('OW04_SOURCE_CHANGED_DURING_COMPOSITION')
        if name == 'coordinator/07_capabilities_and_quote.sql':
            cur.execute(contexts.plan_reader_sql(), prepare=False)
            cur.execute(PAYMENT_LINK_LOCK_SQL, prepare=False)
            cur.execute(refusal_guards['no_ambient'], prepare=False)
            cur.execute(refusal_guards['only_own_return'], prepare=False)
            cur.execute(refusal_guards['only_own_source'], prepare=False)
        cur.execute(_actual_sql(name), prepare=False)
    cur.execute("create function cp7_credit.return_causal_book_floor(p_return uuid)returns date "
        "language sql volatile security definer set search_path=''as $$ "
        "select ow04_source_proposal.return_causal_book_floor(p_return)$$;", prepare=False)
    cur.execute(assembly.render_install_sql(plan, approval), prepare=False)
    cur.execute(refund_sql, prepare=False)
    cur.execute(readers.HISTORY_HELPER_SQL, prepare=False)
    for target in reader_targets.values():
        cur.execute(target['definition'], prepare=False)
    cur.execute('create or replace view erp.v_customer_receivables with(security_invoker=true)as ' + view_after, prepare=False)
    # PostgreSQL deparses equivalent arithmetic with normalized parentheses.
    # Capture immediately under this transaction's DDL lock after executing
    # the exact checked transform; retain the derived SQL separately. This is
    # a canonical text receipt, not permission to accept another expression.
    view_installed = _view_capture(cur)
    if any(view_installed[key] != view_before[key] for key in ('owner','acl','options')):
        raise ValueError('OW04_INSTALLED_VIEW_METADATA_CHANGED')
    _finalize_private_owners(cur)
    for schema in NEW_SCHEMAS:
        cur.execute('revoke all on schema ' + schema + ' from public,anon,authenticated,service_role,cp7_capture')
        cur.execute('revoke all on all functions in schema ' + schema + ' from public,anon,authenticated,service_role,cp7_capture')
    state = dict(approval=approval, baseline_receipt=receipt, captures=captures, plan=plan,
        reader_before=reader_before, reader_targets=reader_targets, view_before=view_before,
        view_after=view_installed['definition'], view_derived=view_after,
        view_canonical_sha256=digest(view_installed['definition']),
        context_proof=context_proof, refund_proof=refund_proof,
        source_sha256=expected_sources,native_empty_requested=native_empty)
    state['payment_link_before'] = payment_link_before
    state['opening_trigger_before'] = opening_trigger_before
    state['opening_diagnostic_before'] = opening_diagnostic_before
    state['opening_pending_inventory'] = _opening_pending_capture(cur)
    state['source_triggers']=dict(before=trigger_before,installed=trigger_before,phase='VERIFIED_PREDECESSOR')
    _source_trigger_install_phase(cur,state,trigger_guard,trigger_manifest,'OW04_COMPOSED')
    state['private_inventory'] = _private_inventory(cur)
    verify(cur, state)
    if native_empty:
        # Never connect a partial overlay to an unverified Native/copy/reader
        # installation. The complete base verification above precedes its DDL.
        empty = load('ow04_integrated_native_empty', ROOT / 'integration/native_empty_bundle.py')
        state['native_empty'] = empty.install(cur, _actual_sql)
        _finalize_private_owners(cur)
        for schema in NEW_SCHEMAS:
            cur.execute('revoke all on all functions in schema ' + schema + ' from public,anon,authenticated,service_role,cp7_capture')
        _source_trigger_install_phase(cur,state,trigger_guard,trigger_manifest,'OW04_COMPOSED_NATIVE_EMPTY')
        state['private_inventory'] = _private_inventory(cur)
        verify(cur, state)
    return state


def verify(cur, state):
    if source_files(native_empty=state['native_empty_requested'])!=state['source_sha256']:
        raise ValueError('OW04_QUALIFIED_SOURCE_FILES_CHANGED')
    assembly = load('ow04_integrated_native_plan', ROOT / 'integration/derive_plan.py')
    proof = assembly.verify_installed(cur, state['plan'], state['approval'])
    legacy = assembly.verify_legacy_composed(cur, state['plan'], state['approval'], REPO)
    contexts = load('ow04_integrated_context_inventory', ROOT / 'integration/typed_context_inventory.py')
    with _postgres_reader(cur):
        context_verification = contexts.verify(cur, REPO, state['context_proof']['typed_census'])
    trigger_guard=load('ow04_verify_source_trigger_guard',ROOT/'integration/source_triggers/trigger_guard.py')
    trigger_manifest=trigger_guard.declarations(REPO)
    trigger_proof=trigger_guard.verify_unchanged(_source_trigger_capture(cur,trigger_guard),
        state['source_triggers']['installed'],trigger_manifest,state['source_triggers']['phase'])
    private_inventory = _private_inventory(cur)
    if private_inventory != state['private_inventory']:
        raise ValueError('OW04_PRIVATE_FUNCTION_TABLE_OR_ACL_CHANGED')
    if _payment_link_metadata(cur)!=state['payment_link_before']:
        raise ValueError('OW04_PREDECESSOR_PAYMENT_LINK_ACL_CHANGED')
    if _opening_trigger_capture(cur) != state['opening_trigger_before']:
        raise ValueError('OW04_OPENING_RETURN_TRIGGER_ATTACHMENT_CHANGED')
    if assembly._capture(cur, 'erp.sync_opening_lot_hpp_to_gl(uuid,date)') != state['opening_diagnostic_before']:
        raise ValueError('OW04_OPENING_HPP_ORIGINAL_DIAGNOSTIC_CHANGED')
    if _opening_pending_capture(cur) != state['opening_pending_inventory']:
        raise ValueError('OW04_OPENING_HPP_PENDING_CLOSURE_CHANGED')
    for sig, target in state['reader_targets'].items():
        actual = assembly._capture(cur, sig)
        expected = state['reader_before'][sig]
        if actual['definition'] != target['definition'] or any(actual[key] != expected[key] for key in
                ('owner', 'acl', 'security_definer', 'volatility', 'config')):
            raise ValueError('OW04_INSTALLED_READER_OR_METADATA_CHANGED: ' + sig)
    view = _view_capture(cur)
    if view['definition'] != state['view_after'] or any(view[key] != state['view_before'][key] for key in ('owner','acl','options')):
        raise ValueError('OW04_INSTALLED_VIEW_OR_METADATA_CHANGED')
    for role in ('anon','authenticated','service_role','cp7_capture'):
        for schema in NEW_SCHEMAS:
            if cur.execute('select has_schema_privilege(%s,%s,\'USAGE\')', (role,schema)).fetchone()[0]:
                raise ValueError('OW04_PRIVATE_SCHEMA_EXPOSED')
    for sig, owner in zip(NEW_PUBLIC, ('cp7_credit_write','cp7_sales_read')):
        row = cur.execute("select pg_get_userbyid(proowner),prosecdef,provolatile::text,proconfig "
            "from pg_proc where oid=%s::regprocedure", (sig,)).fetchone()
        if row != (owner,True,'v',['search_path=""','TimeZone=UTC']):
            raise ValueError('OW04_PUBLIC_FACADE_METADATA_CHANGED')
        if not cur.execute("select has_function_privilege('authenticated',%s,'EXECUTE')", (sig,)).fetchone()[0]:
            raise ValueError('OW04_PUBLIC_FACADE_MISSING')
        for role in ('anon','service_role','cp7_capture'):
            if cur.execute("select has_function_privilege(%s,%s,'EXECUTE')", (role,sig)).fetchone()[0]:
                raise ValueError('OW04_PUBLIC_FACADE_EXPOSED')
    empty_proof = None
    if 'native_empty' in state:
        empty = load('ow04_integrated_native_empty_verify', ROOT / 'integration/native_empty_bundle.py')
        empty_proof = empty.verify(cur,state['native_empty'])
    return {'classification':'INTERNAL_WRITER_NATIVE_CANDIDATE_VERIFICATION','native':proof,
            'legacy_composition':legacy,'context_inventory':context_verification,
            'private_inventory_sha256':digest(canonical(private_inventory)),
            'native_empty':empty_proof,'source_triggers':trigger_proof,'production_go':False}


def uninstall(cur, state):
    # Restore live pre-OW04 definitions BEFORE removing any new dependency.
    for item in state['plan']['entries']:
        if item['action'] == 'REPLACE': cur.execute(item['old']['definition'], prepare=False)
    for item in state['reader_before'].values(): cur.execute(item['definition'], prepare=False)
    cur.execute('create or replace view erp.v_customer_receivables with(security_invoker=true)as ' + state['view_before']['definition'], prepare=False)
    for sig in NEW_PUBLIC + NEW_ERP + NEW_SALES:
        cur.execute('drop function if exists ' + sig + ' cascade')
    for schema in NEW_SCHEMAS: cur.execute('drop schema ' + schema + ' cascade')
    for role in NEW_ROLES: cur.execute('drop owned by ' + role + ' cascade;drop role ' + role, prepare=False)
    trigger_guard=load('ow04_uninstall_source_trigger_guard',ROOT/'integration/source_triggers/trigger_guard.py')
    trigger_manifest=trigger_guard.declarations(REPO)
    restored_triggers=_source_trigger_capture(cur,trigger_guard)
    trigger_guard.expected_transition(state['source_triggers']['installed'],restored_triggers,trigger_manifest,
        state['source_triggers']['phase'],'VERIFIED_PREDECESSOR')
    trigger_guard.verify_unchanged(restored_triggers,state['source_triggers']['before'],trigger_manifest,'VERIFIED_PREDECESSOR')
    for schema in NEW_SCHEMAS:
        if cur.execute('select to_regnamespace(%s)is not null', (schema,)).fetchone()[0]:
            raise ValueError('OW04_UNINSTALL_SCHEMA_REMAINS')
    if _opening_trigger_capture(cur) != state['opening_trigger_before']:
        raise ValueError('OW04_UNINSTALL_OPENING_RETURN_TRIGGER_CHANGED')
    assembly = load('ow04_uninstalled_native_capture', ROOT / 'integration/derive_plan.py')
    if assembly._capture(cur, 'erp.sync_opening_lot_hpp_to_gl(uuid,date)') != state['opening_diagnostic_before']:
        raise ValueError('OW04_UNINSTALL_OPENING_HPP_DIAGNOSTIC_CHANGED')
    for sig in NEW_PUBLIC + NEW_ERP + NEW_SALES:
        if cur.execute('select to_regprocedure(%s)is not null', (sig,)).fetchone()[0]:
            raise ValueError('OW04_UNINSTALL_FUNCTION_REMAINS')
