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
    'admission/01_typed_context_and_preclaim.proposal.sql',
    'admission/02_owning_wrapper.proposal.sql', 'refund/01_initial_refund.proposal.sql',
    'coordinator/01_coordinator_facts.sql', 'coordinator/02_initial_projection.sql',
    'coordinator/03_native_initial_callbacks.sql',
    'coordinator/04_register_and_materialize.sql', 'coordinator/05_factual_profile.sql',
    'coordinator/06_finish_and_closed_routes.sql',
    'coordinator/07_capabilities_and_quote.sql', 'coordinator/08_outer_wrapper.sql',
    'coordinator/09_public_facades.sql',
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


def source_files():
    return {name: digest((ROOT / name).read_text()) for name in SQL_FILES}


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


def install(cur, predecessor_verify, predecessor_functions):
    """Execute in caller's SINGLE transaction; no commit and no partial mode."""
    for schema in NEW_SCHEMAS:
        if cur.execute('select to_regnamespace(%s)is not null',(schema,)).fetchone()[0]:
            raise ValueError('OW04_NEW_SCHEMA_ALREADY_EXISTS: '+schema)
    assembly = load('ow04_integrated_native_plan', ROOT / 'integration/derive_plan.py')
    readers = load('ow04_integrated_reader_plan', ROOT / 'readers/03_reader_transforms.py')
    refunds = load('ow04_integrated_refund_plan', ROOT / 'refund/02_native_refund_transform.py')
    approval, receipt = _predecessor_approval(cur, assembly, predecessor_verify, predecessor_functions)
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
    expected_sources = source_files()
    for name in SQL_FILES:
        if digest((ROOT / name).read_text()) != expected_sources[name]:
            raise ValueError('OW04_SOURCE_CHANGED_DURING_COMPOSITION')
        if name == 'coordinator/07_capabilities_and_quote.sql':
            cur.execute(contexts.plan_reader_sql(), prepare=False)
            cur.execute(refusal_guards['no_ambient'], prepare=False)
            cur.execute(refusal_guards['only_own_return'], prepare=False)
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
    for schema in NEW_SCHEMAS:
        cur.execute('revoke all on schema ' + schema + ' from public,anon,authenticated,service_role,cp7_capture')
        cur.execute('revoke all on all functions in schema ' + schema + ' from public,anon,authenticated,service_role,cp7_capture')
    state = dict(approval=approval, baseline_receipt=receipt, captures=captures, plan=plan,
        reader_before=reader_before, reader_targets=reader_targets, view_before=view_before,
        view_after=view_installed['definition'], view_derived=view_after,
        view_canonical_sha256=digest(view_installed['definition']),
        context_proof=context_proof, refund_proof=refund_proof,
        source_sha256=expected_sources)
    verify(cur, state)
    return state


def verify(cur, state):
    assembly = load('ow04_integrated_native_plan', ROOT / 'integration/derive_plan.py')
    proof = assembly.verify_installed(cur, state['plan'], state['approval'])
    legacy = assembly.verify_legacy_composed(cur, state['plan'], state['approval'], REPO)
    contexts = load('ow04_integrated_context_inventory', ROOT / 'integration/typed_context_inventory.py')
    with _postgres_reader(cur):
        context_verification = contexts.verify(cur, REPO, state['context_proof']['typed_census'])
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
    return {'classification':'INTERNAL_WRITER_NATIVE_CANDIDATE_VERIFICATION','native':proof,
            'legacy_composition':legacy,'context_inventory':context_verification,'production_go':False}


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
    for schema in NEW_SCHEMAS:
        if cur.execute('select to_regnamespace(%s)is not null', (schema,)).fetchone()[0]:
            raise ValueError('OW04_UNINSTALL_SCHEMA_REMAINS')
    for sig in NEW_PUBLIC + NEW_ERP + NEW_SALES:
        if cur.execute('select to_regprocedure(%s)is not null', (sig,)).fetchone()[0]:
            raise ValueError('OW04_UNINSTALL_FUNCTION_REMAINS')
