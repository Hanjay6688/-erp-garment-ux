"""Exercise due staff reminders on the combined product, then restore all fixtures."""

import importlib
from pathlib import Path
from traceback import extract_tb

from . import mode, s06_transport
from .followup import provision
from .g04_invoice import boundary_digest
from .retained import verify_retained
from .s06_source import PRODUCT, TREE, confirm_source, require
from .state_probe import write

S06 = 'P21_CLOSE05_S06'
CHECKS = (S06,)


def exercise(conn, cur, state, report, *, lifecycle, candidate, switch_roll_receipt, checkpoint, auth, package):
    from global_owning import owning, p20_batch
    from .installed import verify_loopback

    require(mode.enabled(), 'CP7_S06_EXACT_MODE_REQUIRED')
    verify_loopback(conn, cur)
    product = Path(candidate).parent / 's06-product'
    confirm_source(product)
    output = Path(candidate) / 'cp6-proof/t3/P21_FOLLOWUP_ORIGINALS'
    output.mkdir(mode=0o700, exist_ok=False)
    reused = verify_retained()
    report['p21_followup_retained'] = reused
    write(output / 'retained-originals.json', reused)
    results = report['p21_installed_checks'] = {}
    evidence = dict(case=S06, product=PRODUCT, product_tree=TREE, result={},
                    rpc_auth='SYNTHETIC_NATIVE_FIXTURE', sender='TRANSACTIONAL_PG_NET_FIXTURE',
                    actual_whatsapp_delivery=False, actual_G04_cases_rerun=0, production_go=False)
    baseline = catalogue = None
    phase = 'P21_S06_PREPARE'
    try:
        p20_batch.progress(phase, 'STARTED')
        fingerprint = state.global_installation['sealed']['actual_parent_root_receipt']['catalogue_fingerprint']
        require(switch_roll_receipt['sealed_fingerprint'] == fingerprint
                and switch_roll_receipt['s06']['product'] == PRODUCT
                and switch_roll_receipt['s06']['changed_function_count'] == 3,
                'CP7_S06_SEALED_INSTALLATION_REQUIRED')
        write(output / 's06-install-original.json', switch_roll_receipt)
        scripts = product / 'scripts'
        with owning.import_paths(scripts):
            cases = importlib.import_module('cp7_s06_reminder_forward_cases')
            require(Path(cases.__file__).resolve() == scripts / 'cp7_s06_reminder_forward_cases.py',
                    'CP7_S06_EXACT_CASE_SOURCE_REQUIRED')
            auth.begin(conn, cur, package.boundary.ADMIN, package.boundary.PRIMARY_ADMIN,
                       lambda observer: lifecycle.verify(observer, state), report)
            provision(conn, cur, auth)
            cur.execute("set local timezone='Asia/Jakarta'; set local lock_timeout='8s'; set local statement_timeout='120s'")
            cur.execute("select set_config('app.change_reason','S06 isolated forwarding fixture',true)")
            with lifecycle.provider.as_role(cur, 'postgres'), lifecycle.provider.metadata_context(cur):
                live = cur.execute('select cp7_global_nonpo_envelope.catalogue_fingerprint_v1()').fetchone()[0]
            require(live == fingerprint, 'CP7_S06_CATALOGUE_DRIFT_BEFORE_TRANSACTIONS')
            catalogue = lifecycle.provider.capture(cur)
            tables = [row[0] for row in cur.execute("""select n.nspname||'.'||c.relname
                from pg_class c join pg_namespace n on n.oid=c.relnamespace
                where (n.nspname='erp' or left(n.nspname,4)='cp7_') and c.relkind in('r','p')
                order by 1""").fetchall()]
            baseline = boundary_digest(cur, tables)
            evidence['verified_catalogue_sha256'] = live['sha256']
            p20_batch.progress(phase, 'COMPLETED')
            phase = 'P21_S06_CASES'
            p20_batch.progress(phase, 'STARTED')
            with lifecycle.provider.as_role(cur, 'supabase_admin'):
                s06_transport.install(cur)
            evidence['result'] = cases.exercise(cur, s06_transport.read_requests,
                                                s06_transport.FAKE_KEY, already_installed=True)
        evidence['status'] = 'OBSERVED'
        p20_batch.progress(phase, 'COMPLETED')
    except Exception as error:
        evidence['status'] = 'INCOMPLETE'
        evidence['first_failure'] = dict(p20_batch.bounded_failure(error), phase=phase)
        sites = [f'{Path(frame.filename).name}:{frame.lineno}' for frame in extract_tb(error.__traceback__)
                 if 's06' in Path(frame.filename).name]
        evidence['first_failure']['locations'].extend(sites[-5:])
        report['p21_followup_exception'] = evidence['first_failure']
        write(output / 'first-failure.json', evidence['first_failure'])
        p20_batch.progress(phase, 'FAILED')
    finally:
        conn.rollback()
        if baseline is not None:
            cur.execute("set local timezone='Asia/Jakarta'")
            evidence['business_rows_rolled_back'] = boundary_digest(cur, list(baseline)) == baseline
            evidence['installed_catalogue_restored'] = lifecycle.provider.capture(cur) == catalogue
        conn.rollback()
        write(output / 's06-reminder.json', evidence)
        results[S06] = evidence
        checkpoint(S06, evidence)
    return results


def proven(results):
    if set(results) != {S06}:
        return False
    receipt = results[S06]
    checks = receipt.get('result', {})
    cases = checks.get('cases', {})
    instant = cases.get('instant', {})
    return (receipt.get('status') == 'OBSERVED' and receipt.get('business_rows_rolled_back') is True
            and receipt.get('installed_catalogue_restored') is True
            and bool(receipt.get('verified_catalogue_sha256'))
            and checks.get('code_and_sender_rows_restored') is True
            and set(cases) == {'instant', 'digest'}
            and all(c.get('status') == 'PASS' and c.get('fake_transport_messages') == 1
                    and c.get('second_tick', {}).get('outcome') == 'IDLE' for c in cases.values())
            and all(instant.get(key) is True for key in ('owner_and_staff_delivered_once', 'future_not_queued',
                    'cancelled_and_rescheduled_not_sent', 'other_staff_cannot_read_or_cancel',
                    'non_owner_cannot_read_wa_settings')))
