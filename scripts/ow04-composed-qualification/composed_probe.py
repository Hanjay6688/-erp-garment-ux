"""Current complete composed owner: 86 retained business oracles + 4 guards.

No legacy case module/declaration is rewritten. Its 86 business cases run on
the current installation. The same original used-rollback ID now calls the
actual complete composed owner, with the same settlement and refusal oracle.
Three additional cases prove APPLY/REFUND use and real metadata tampering.
"""
from hashlib import sha256
from contextlib import contextmanager
from pathlib import Path
import json
import subprocess
import sys
import traceback
import uuid

if sys.argv[1:]:
    raise SystemExit('Composed owner qualification accepts no arguments')
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path[:0] = [str(REPO/'scripts'), str(REPO/'scripts/cp7_customer_credit/consumer')]
sys.argv.extend(['--signed-source','--credit-dependencies','--native-fractional-hpp'])
import cp7_full_ow04_probe as previous
import cp7_consumer_owning_install as product
import native_basic_cases as basic
import native_refund_cases as refund
import psycopg
from cp7_catalog_state import exact_public_catalog
from cp6_t3_aligned_install import advisors, advisor_delta

core, native, package, p09 = previous.core, previous.native, previous.package, previous.p09
EXTRA_IDS = ('OW04_COMPOSED_APPLY_USE_ROLLBACK_REFUSED',
    'OW04_COMPOSED_REFUND_USE_ROLLBACK_REFUSED',
    'OW04_COMPOSED_REAL_CATALOG_DRIFT_REFUSED')
IDS = previous.IDS + EXTRA_IDS
LABEL = 'CP7_OW04_COMPOSED_CURRENT_NATIVE90'
OUT = product.ROOT/'cp6-proof/t3'/f'{LABEL}.json'
DECLARATION = HERE/'EXPECTED.json'
STATE = None


def declared():
    value = json.loads(DECLARATION.read_bytes())
    assert value['expected_count'] == len(IDS) == 90
    assert tuple(value['required_case_ids']) == IDS
    for path, expected in value['unchanged_retained_case_sources'].items():
        assert sha256((REPO/path).read_bytes()).hexdigest() == expected, path
    assert value['old_native87_declaration_sha256'] == sha256(previous.DECLARATION_BYTES).hexdigest()
    source = json.loads((HERE/'SOURCE.json').read_bytes())
    assert source['base_candidate'] == 'da6a5454dba94d102a0c5c1214d7d427da7079dd'
    for path, expected in source['files'].items():
        assert sha256((REPO/path).read_bytes()).hexdigest() == expected, ('COMPOSED_QUALIFIER_SOURCE_CHANGED',path)
    changes = subprocess.check_output(['git','-C',str(REPO),'diff','--name-only',
        source['base_candidate'],'HEAD','--','scripts','src','supabase','tests',
        '.github/workflows/cp7-ow04-composed.yml'],text=True).splitlines()
    assert set(changes) <= set(source['files'])|{'scripts/ow04-composed-qualification/SOURCE.json'}, changes
    assert not subprocess.check_output(['git','-C',str(REPO),'status','--porcelain','--',
        'scripts/cp7_consumer_owning_install.py','scripts/ow04-composed-qualification',
        '.github/workflows/cp7-ow04-composed.yml'],text=True).strip()
    return value


def verify(cur):
    if STATE is None:
        raise ValueError('CP7_COMPOSED_QUALIFICATION_INSTALLATION_REQUIRED')
    return product.verify(cur, STATE)


def held_state(cur):
    return dict(rows=product.base.private_rows(cur),
        boundary=package.boundary.snapshot(cur), functions=p09.functions(cur),
        catalog=product.catalog._catalog_rows(cur))


@contextmanager
def product_catalog(cur):
    """Temporarily undo ONLY Native runner's declared test-only ERP grant.

    The installed product never receives it. Complete administrative catalog
    verification must see the actual installed schema privileges, rather than
    pretending that the retained Native runner's setup grant is a product pin.
    Every outer case observation still includes the same restored test grant.
    """
    basic.native.b.api.admin(cur)
    with product.catalog._catalog(cur):
        actual = dict(cur.execute(product.catalog.QUERIES['schemas']).fetchall())['erp']
    expected = STATE['installed_catalog']['schemas']['erp']
    if actual == expected:
        yield
        return
    extra = ['authenticated','postgres','USAGE',False]
    assert expected[0] == actual[0] == 'postgres'
    assert extra not in expected[1]
    assert sorted(actual[1]) == sorted(expected[1]+[extra]), 'NATIVE_TEST_SCHEMA_DELTA_NOT_EXACT_DECLARED_USAGE'
    cur.execute('revoke usage on schema erp from authenticated')
    try:
        yield
    finally:
        cur.execute('grant usage on schema erp to authenticated')


def refuse_used(cur):
    before = held_state(cur)
    assert before['rows'] != STATE['seeded_private_rows'], 'COMPOSED_GUARD_REQUIRES_REAL_USE'
    with product_catalog(cur):
        try:
            product.rollback_preuse(cur, STATE)
        except ValueError as error:
            assert str(error) == product.USED_ERROR, str(error)
        else:
            raise AssertionError('COMPOSED_USED_INSTALLATION_WAS_REMOVED')
        verify(cur)
    assert held_state(cur) == before, 'COMPOSED_ROLLBACK_REFUSAL_CHANGED_ANY_STATE'
    cur.execute('set constraints all immediate')
    return dict(rollback_refused=True, all_private_rows_native_boundary_and_catalog_unchanged=True,
        refusal_before_any_uninstall=True, current_composed_verifier_pass=True)


def legacy_used_guard(cur, today):
    # Same actual settlement fixture/outcome and canonical refusal as the
    # original87 guard. Only the owning installer is the composed product.
    initial = core.initial
    source = initial.native
    gold = initial.expected()['cases'][0]
    with source.isolated(cur):
        fixture = source.prepared(cur, today, gold['paid'], gold['profile'])
        master = initial._credit_master(cur)
        query = initial._input(fixture, gold, master)
        quote = source.call_quote(cur, query)
        initial._assert_quote(cur, quote, query, fixture, gold, master)
        envelope = initial._envelope(query, quote)
        request = uuid.uuid4()
        outcome = initial._settle(cur, envelope, request)
        initial._assert_outcome(outcome, request, envelope, quote, gold['mode'])
        source.b.api.admin(cur)
        assert not cur.execute('select exists(select 1 from cp7_credit.consumer_operations_v1)').fetchone()[0]
        proof = refuse_used(cur)
        return dict(status='PASS', actual_settlement_request=str(request),
            native_settlement=outcome, native_executed=True,
            base_used_consumer_unused=True, production_go=False, **proof)


def consumer_used_guard(cur, today, action):
    with basic.native.isolated(cur):
        pair = basic.fixture.prepare(cur, today)
        operation, _, request = (basic.apply(cur, pair, '80.00') if action == 'APPLY'
            else refund.refund(cur, pair, '80.00'))
        actual = basic.fixture.profiles(cur, pair)
        gold = (basic.GOLD if action == 'APPLY' else refund.GOLD)['cases'][0]['expected']
        assert actual == gold, (actual, gold)
        basic.native.b.api.admin(cur)
        proof = refuse_used(cur)
        return dict(status='PASS', action=action, actual_request=str(request),
            actual_outcome=operation, expected=gold, observed=actual,
            actual_financial_command_executed=True, production_go=False, **proof)


def catalog_drift_guard(cur):
    with basic.native.isolated(cur):
        basic.native.b.api.admin(cur)
        before = held_state(cur)
        # A real new private function must be refused even though it has no
        # financial rows. This is DDL in an isolated test, never a saved pin.
        cur.execute('savepoint composed_catalog_drift')
        cur.execute("create function cp7_credit._qualification_unreviewed() returns int language sql as $$select 1$$")
        try:
            verify(cur)
        except ValueError as error:
            message = str(error)
            assert message.startswith('OW04_CONSUMER_COMPOSITION_SOURCE_OR_FUNCTION_CATALOG_CHANGED'), message
        else:
            raise AssertionError('COMPOSED_UNREVIEWED_FUNCTION_WAS_ADMITTED')
        finally:
            cur.execute('rollback to savepoint composed_catalog_drift')
            cur.execute('release savepoint composed_catalog_drift')
        assert held_state(cur) == before
        with product_catalog(cur):
            verify(cur)
        return dict(status='PASS', actual_unreviewed_function_refused=True,
            complete_restoration=True, production_go=False)


def reapply_current_overlays(cur):
    # Retain the legacy-order counterexample's real old-helper generation.
    # Its reapply callback must restore THIS generation, including exact
    # source-derived consumer callbacks, rather than leave stale functions.
    cur.execute(product.base.credit._actual_sql('native-empty/04_exact_overlays.sql'), prepare=False)
    for capture in STATE['consumer']['installed'].values():
        cur.execute(capture['definition'], prepare=False)
    cur.execute(STATE['consumer']['runtime_after']['definition'], prepare=False)
    with product_catalog(cur):
        verify(cur)


def cases(cur, today):
    retained = core.initial.cases(cur,today)+core.retained_returns.cases(cur,today) \
        +core.retained_reads.cases(cur,today)+core.retained_e01.cases(cur,today)
    helpers = [row['definition'] for row in STATE['predecessor']['credit']['native_empty']['before_helpers'].values()]
    retained += core.empty_cases.cases(cur,today,before_helpers=helpers,reapply_overlay=reapply_current_overlays)
    retained += core.fractional_hpp.cases(cur,today)+core.signed_source.cases(cur,today) \
        +core.signed_zero.cases(cur,today)
    retained += [(previous.USED_GUARD_ID, lambda:legacy_used_guard(cur,today))]
    retained += previous.dependency_cases.cases(cur,today)+previous.native_fractional.cases(cur,today)
    assert tuple(name for name,_ in retained) == previous.IDS
    retained += [(EXTRA_IDS[0],lambda:consumer_used_guard(cur,today,'APPLY')),
        (EXTRA_IDS[1],lambda:consumer_used_guard(cur,today,'REFUND')),
        (EXTRA_IDS[2],lambda:catalog_drift_guard(cur))]
    assert tuple(name for name,_ in retained) == IDS
    return retained


def run():
    global STATE
    declaration = declared()
    report = dict(label=LABEL,status='INCOMPLETE',expected_case_count=90,
        required_case_ids=list(IDS), candidate_commit=subprocess.check_output(
            ['git','-C',str(REPO),'rev-parse','HEAD'],text=True).strip(),
        declaration_sha256=sha256(DECLARATION.read_bytes()).hexdigest(),
        unchanged_retained_case_sources=declaration['unchanged_retained_case_sources'],
        composed_sources=product.sources(), scope='CURRENT_COMPOSED_NATIVE86_PLUS_MATCHING_USED_GUARD_AND_THREE_NEW_GUARDS',
        legacy_case_modules_modified=False, legacy_verifier_projected=False,
        original_used_guard_owning_installer_adapted=True,
        legacy_upgrade_reapply_callback_restores_current_overlays=True,
        Native_runner_test_erp_usage_removed_for_real_product_catalog_checks=True,
        product_erp_schema_usage_grant_added=False,
        production_go=False,formal_CP7C_started=False,feature_complete=False,
        independent_acceptance=False,qualification_only=True,hosted=False)
    installed = False
    try:
        with psycopg.connect(package.boundary.ADMIN) as conn, conn.cursor() as cur:
            p09.wip.policy.bf.verified(cur)
            before = previous.restore_state.capture(cur,package.boundary.snapshot,core.predecessor.public_state,p09.functions)
            conn.rollback()
            STATE = product.install(cur)
            report['first_install_verification'] = verify(cur)
            report['preuse_rollback'] = product.rollback_preuse(cur,STATE)
            restored = {}
            assert previous.restore_state.prove(cur,before,package.boundary.snapshot,
                core.predecessor.public_state,p09.functions,restored), restored
            report['first_preuse_exact_restore'] = restored
            STATE = product.install(cur)
            report['installed_verification'] = verify(cur)
            report['verified_predecessor_info_manifest'] = core.predecessor_info_manifest(cur)
            conn.commit()
            installed = True
        report['advisors_with_cp7'] = advisors(package.boundary.PG)
        with exact_public_catalog(native,retain_raw=True) as comparison:
            report['native'] = native.strict_group(LABEL,cases,verify)
        report['native_public_catalog_comparison'] = comparison
    except Exception as error:
        report.update(error=str(error),traceback=traceback.format_exc())
    finally:
        if installed:
            try:
                with psycopg.connect(package.boundary.ADMIN) as conn, conn.cursor() as cur:
                    report['complete_composed_preuse_removal'] = product.rollback_preuse(cur,STATE)
                    conn.commit()
                    report['cp6_restored'] = previous.restore_state.prove(cur,before,
                        package.boundary.snapshot,core.predecessor.public_state,p09.functions,report)
                    conn.rollback()
                    p09.wip.policy.bf.verified(cur)
                    conn.rollback()
                report['advisor_delta'] = advisor_delta(advisors(package.boundary.PG),report['advisors_with_cp7'])
                report['advisor_disposition'] = core.advisor_disposition(report['advisor_delta'],report['verified_predecessor_info_manifest'])
                report['advisor_gate'] = report['advisor_disposition']['gate']
            except Exception as error:
                report.update(restore_error=str(error),restore_traceback=traceback.format_exc(),cp6_restored=False,advisor_gate=False)
        group = report.get('native',{})
        report['observed_case_count'] = sum(group.get('counts',{}).values())
        report['required_case_ids_pass'] = set(group.get('cases',{})) == set(IDS)
        if not report.get('error') and report.get('cp6_restored') and report.get('advisor_gate') \
            and report['required_case_ids_pass'] and group.get('status') == 'PASS' \
            and group.get('counts') == {'PASS':90} and group.get('database_remaining',0) == 0:
            report['status'] = 'PASS'
        OUT.parent.mkdir(parents=True,exist_ok=True)
        OUT.write_text(json.dumps(report,indent=2,default=str)+'\n')
        print(json.dumps({key:report.get(key) for key in ('label','status','expected_case_count',
            'observed_case_count','cp6_restored','advisor_gate','error','restore_error')},default=str),flush=True)
    return dict(status=report['status'],production_go=False,feature_complete=False,independent_acceptance=False)


if __name__ == '__main__':
    declared()
    package._writer_runtime = lambda browser_mode=False:run()
    package.run('install')
