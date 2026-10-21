"""Complete CP7 owning composition, including OW04, without running a probe.

The caller supplies one transaction. Installation never commits, schedules a
job, writes a WhatsApp key, or calls a provider. Release/hosted admission is a
separate decision. The exact predecessor verifiers run before OW04 captures;
afterwards its declared Native deltas use the strict composed verification.
"""
import hashlib
from pathlib import Path

from psycopg import sql

import cp7_analysis_bundle as analysis
import cp7_schedule_bundle as schedule
import cp7_planning_bundle as planning
import cp7_baseline_bundle as baseline
import cp7_supply_bundle as supply
import cp7_f03_bundle as f03
import cp7_alert_bundle as top
import cp7_note_correction_verify as note_correction
import cp7_sales_payment_correction_bundle as payment_correction
import cp7_sales_return_correction_bundle as return_correction
import cp7_sales_chain_bundle as sales_chain
import cp7_p12_nota_probe as payroll
import cp7_p13_finance_probe as finance
import cp7_p09_procurement_probe as p09
from cp7_customer_credit.integration import owning_bundle as credit

ROOT = Path(__file__).resolve().parents[1]
PREDECESSOR_SQL_SHA256 = 'e7701eaada592cfd74a8555cf4cdcb7df8d180448213d3bbf5698c3bfa025127'


def predecessor_extension():
    return '\n'.join((f03.extension(), planning.extension(), baseline.extension(),
        supply.extension(), schedule.extension(), analysis.predecessor.extension(),
        analysis.extension(), top.extension()))


def source_manifest():
    # The CP6 harness also has an older writer checkout on sys.path. Accept
    # identical dependency bytes only; never silently qualify that old code.
    dependencies = {}
    for module in (analysis,schedule,planning,baseline,supply,f03,top,note_correction,
                   payment_correction,return_correction,sales_chain,payroll,finance,p09):
        source = Path(module.__file__)
        actual = hashlib.sha256(source.read_bytes()).hexdigest()
        expected = hashlib.sha256((ROOT/'scripts'/source.name).read_bytes()).hexdigest()
        if actual != expected:
            raise ValueError('CP7_FULL_IMPORTED_PREDECESSOR_SOURCE_CHANGED: '+source.name)
        dependencies[source.name] = actual
    predecessor_sha = hashlib.sha256((f03.procurement.bundle()+'\n'+predecessor_extension()).encode()).hexdigest()
    if predecessor_sha != PREDECESSOR_SQL_SHA256:
        raise ValueError('CP7_FULL_PREDECESSOR_SQL_SOURCE_CHANGED')
    return dict(installer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        predecessor_sql_sha256=predecessor_sha,dependencies=dependencies,
        credit_sources=credit.source_files(native_empty=True))


def _verify_families(cur, *, customer_credit):
    analysis.verify(cur)
    payroll.verify(cur, True, True, True, True, True)
    finance.verify(cur, customer_credit=customer_credit)
    f03.journal.verify(cur)
    f03.misc.verify(cur)
    f03.installment.verify(cur)
    f03.transaction_source.verify(cur)
    f03.misc_correction.verify(cur)
    payment_correction.verify(cur)
    sales_chain.verify(cur)
    f03.cutting_correction.verify(cur)
    return top.verify(cur)


def verify_predecessor(cur):
    result = _verify_families(cur, customer_credit=False)
    note_correction.verify(cur)
    return_correction.verify(cur)
    return dict(stage='FULL_CP7_PREDECESSOR_BEFORE_OW04', alerts=result)


def _install_predecessor(cur):
    originals, installation = p09.install(cur)
    before = p09.functions(cur)
    internal = cur.execute("select pg_get_functiondef('erp.require_internal()'::regprocedure)").fetchone()[0]
    originals['erp.require_owner_admin()'] = cur.execute(
        "select pg_get_functiondef('erp.require_owner_admin()'::regprocedure)").fetchone()[0]
    f03.note_report.capture(cur, originals)
    cur.execute(predecessor_extension(), prepare=False)
    after = p09.functions(cur)
    path = cur.execute('show search_path').fetchone()[0]
    cur.execute("select set_config('search_path','',true)")
    grants = {}
    try:
        for principal, signatures in top.GRANTS.items():
            for signature in signatures:
                key = str(cur.execute('select %s::regprocedure::text', (signature,)).fetchone()[0])
                grants.setdefault(key, set()).add((principal, 'EXECUTE', False))
    finally:
        cur.execute("select set_config('search_path',%s,true)", (path,))
    expected = f03.note_report.expected_definitions(
        internal, originals, f03.patched_internal, f03.settlement.patched_owner)
    for signature, old in before.items():
        new = after[signature]
        wanted = hashlib.md5(expected[signature].encode()).hexdigest() if signature in expected else old['definition']
        assert new['definition'] == wanted and new['owner'] == old['owner'], (
            'CP7_FULL_UNDECLARED_PREDECESSOR_CHANGE', signature)
        assert {tuple(x) for x in new['acl'] or []} == {
            tuple(x) for x in old['acl'] or []} | grants.get(signature, set()), (
            'CP7_FULL_UNDECLARED_PREDECESSOR_ACL_DELTA', signature)
    for signature, definition in expected.items():
        assert cur.execute('select pg_get_functiondef(%s::regprocedure)', (signature,)).fetchone()[0] == definition, (
            'CP7_FULL_EXACT_ADMISSION_DELTA', signature)
    f03.dated_guard.verify(cur)
    f03.rework.verify(cur)
    f03.hpp_policy.verify(cur)
    f03.kasbon.verify(cur)
    f03.pickup.verify(cur)
    f03.rate_revision.verify(cur)
    p09.INSTALLED_FUNCTIONS = after
    return originals, installation


def private_rows(cur):
    """Exact pre-use drop guard, including OW04 schemas outside cp7_*.

    Compare row hashes as well as counts: replacing a seeded row is use too.
    This administrative check never runs in an ordinary product save.
    """
    tables = cur.execute("select n.nspname,c.relname from pg_class c "
        "join pg_namespace n on n.oid=c.relnamespace where c.relkind in('r','p') "
        "and (left(n.nspname,4)='cp7_' or n.nspname=any(%s::text[])) order by 1,2",
        (list(credit.NEW_SCHEMAS),)).fetchall()
    result = {}
    for schema, table in tables:
        result[schema+'.'+table] = cur.execute(sql.SQL(
            "select count(*),encode(pg_catalog.sha256(convert_to("
            "coalesce(jsonb_agg(to_jsonb(r)order by to_jsonb(r)::text),'[]'::jsonb)::text,'UTF8')),'hex') "
            "from {} r").format(sql.Identifier(schema, table))).fetchone()
    return result


def install(cur):
    """Install every family and the complete OW04 owner in ONE transaction."""
    sources = source_manifest()
    originals, installation = _install_predecessor(cur)
    state = dict(originals=originals, predecessor_installation=installation,
        sources=sources, credit=credit.install(cur, verify_predecessor, p09.functions, native_empty=True))
    p09.INSTALLED_FUNCTIONS = p09.functions(cur)
    state['seeded_private_rows'] = private_rows(cur)
    verify(cur, state)
    return state


def verify(cur, state):
    if source_manifest() != state['sources']:
        raise ValueError('CP7_FULL_COMPOSITION_SOURCE_CHANGED')
    exact = credit.verify(cur, state['credit'])
    families = _verify_families(cur, customer_credit=True)
    # Both original note/return correction verifiers execute inside credit's
    # exact live-target + immutable-baseline composition, never get skipped.
    return dict(stage='FULL_CP7_WITH_OW04', credit=exact, alerts=families,
        production_go=False, feature_complete=False, independent_acceptance=False)


def rollback_preuse(cur, state):
    """Refuse a used installation before executing any destructive DDL."""
    verify(cur, state)
    if private_rows(cur) != state['seeded_private_rows']:
        raise ValueError('CP7_FULL_ROLLBACK_AFTER_USE_REQUIRES_BACKUP_RESTORE')
    credit.uninstall(cur, state['credit'])
    for definition in state['originals'].values():
        cur.execute(definition, prepare=False)
    for role in top.ROLES:
        cur.execute('drop owned by '+role+' cascade;drop role '+role, prepare=False)
