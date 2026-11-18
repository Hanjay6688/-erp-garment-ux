"""One AUD-G04 observation on the verified full P21 installation."""
import importlib
from pathlib import Path
import re
from traceback import extract_tb

from . import g04_invoice as probe, mode
from .g04_catalogue import SALE_CREDIT_SHA, SOURCE_SHA
from .followup import provision, require
from .retained import verify_retained
from .state_probe import write

G04 = 'P21_AUD_G04_TERMINAL'
CHECKS = (G04,)


def exercise(conn, cur, state, report, *, lifecycle, candidate, switch_roll_receipt, checkpoint, auth, package):
    from global_owning import owning, p20_batch
    from .installed import verify_loopback

    require(mode.enabled(), 'P21_G04_EXACT_MODE')
    verify_loopback(conn, cur)
    product = Path(candidate).parent / 'g04-product'
    probe.confirm_source(product)
    day = lifecycle.foundation.day
    output = Path(candidate) / 'cp6-proof/t3/P21_FOLLOWUP_ORIGINALS'
    output.mkdir(mode=0o700, exist_ok=False)
    reused = verify_retained()
    report['p21_followup_retained'] = reused
    write(output / 'retained-originals.json', reused)
    results = report['p21_installed_checks'] = {}
    observations = []
    evidence = dict(case='AUD-G04', product=probe.PRODUCT, product_tree=probe.TREE,
                    installed_p21_base=reused['product'], business_day=str(day),
                    observations=observations, result={}, rpc_auth='SYNTHETIC_NATIVE_FIXTURE',
                    production_go=False)
    baseline = None
    phase = 'P21_AUD_G04_PREPARE'
    try:
        p20_batch.progress(phase, 'STARTED')
        fingerprint = state.global_installation['sealed']['actual_parent_root_receipt']['catalogue_fingerprint']
        require(switch_roll_receipt['source_sha256'] == SOURCE_SHA and switch_roll_receipt['sealed_fingerprint'] == fingerprint
                and switch_roll_receipt['sale_credit']['source_sha256'] == SALE_CREDIT_SHA,
                'CP7_P21_G04_SEALED_FINGERPRINT_REQUIRED')
        write(output / 'switch-roll-install-original.json', switch_roll_receipt)
        scripts = product / 'scripts'
        roots = [scripts, *(scripts / 'cp7_customer_credit' / part for part in
                            ('consumer', 'native', 'initial-settlement', 'reconciliation/native'))]
        with owning.import_paths(*roots):
            prepare = importlib.import_module('global_owning.p20.native').prepare
            auth.begin(conn, cur, package.boundary.ADMIN, package.boundary.PRIMARY_ADMIN,
                       lambda observer: lifecycle.verify(observer, state), report)
            provision(conn, cur, auth)
            prepare(cur)
        with lifecycle.provider.as_role(cur, 'postgres'):
            live = cur.execute('select cp7_global_nonpo_envelope.catalogue_fingerprint_v1()').fetchone()[0]
        require(live == fingerprint, 'CP7_P21_G04_CATALOGUE_DRIFT_BEFORE_TRANSACTIONS')
        evidence['verified_catalogue_sha256'] = live['sha256']
        baseline = probe.boundary_digest(cur)
        p20_batch.progress(phase, 'COMPLETED')
        phase = 'P21_AUD_G04_REVERSE'
        p20_batch.progress(phase, 'STARTED')
        with probe.fixture_sources(product):
            probe.native_case(cur, day, observations, evidence['result'])
        for route in ('direct', 'chain'):
            failure = evidence['result'][route]
            require(failure['outcome'] == 'REVERSED', failure.get('message', 'CP7_P21_G04_INVERSE_INCOMPLETE'))
        evidence['status'] = 'OBSERVED'
        p20_batch.progress(phase, 'COMPLETED')
    except Exception as error:
        evidence['status'] = 'INCOMPLETE'
        evidence['first_failure'] = dict(p20_batch.bounded_failure(error), phase=phase)
        probe_sites = [f'{Path(frame.filename).name}:{frame.lineno}' for frame in extract_tb(error.__traceback__)
                       if Path(frame.filename).name in ('g04_invoice.py', 'g04_followup.py')]
        evidence['first_failure']['locations'].extend(probe_sites[-4:])
        if isinstance(error, KeyError) and len(error.args) == 1 and isinstance(error.args[0], str):
            if re.fullmatch(r'[a-z][a-z_0-9]{0,63}', error.args[0]):
                evidence['first_failure']['missing_key'] = error.args[0]
        report['p21_followup_exception'] = evidence['first_failure']
        write(output / 'first-failure.json', evidence['first_failure'])
        p20_batch.progress(phase, 'FAILED')
    finally:
        conn.rollback()
        if baseline is not None:
            cur.execute("set local timezone='Asia/Jakarta'")
            evidence['business_rows_rolled_back'] = probe.boundary_digest(cur) == baseline
        conn.rollback()
        write(output / 'g04-invoice.json', evidence)
        result = evidence.get('result', {})
        results[G04] = dict(status=evidence.get('status'), product=probe.PRODUCT,
                            result=result, business_rows_rolled_back=evidence.get('business_rows_rolled_back', False),
                            verified_catalogue_sha256=evidence.get('verified_catalogue_sha256'),
                            first_failure=evidence.get('first_failure'))
        checkpoint(G04, results[G04])
    return results


def proven(results):
    if set(results) != {G04}:
        return False
    receipt = results[G04]
    result = receipt.get('result', {})
    return (receipt['status'] == 'OBSERVED' and receipt['business_rows_rolled_back'] is True
            and bool(receipt.get('verified_catalogue_sha256'))
            and result.get('available_children') == 0 and result.get('both_routes_reversed') is True
            and set(result.get('refusals', {})) == {'active_children', 'active_refund', 'pending_direct', 'pending_chain'}
            and all(item.get('unchanged') is True for item in result['refusals'].values())
            and all(result.get(route, {}).get('outcome') == 'REVERSED' and all(
                result[route].get(key) is True for key in ('immutable_history', 'one_journal_inverse',
                    'one_audit_entry', 'exact_request_replay', 'final_ledger_neutral')) for route in ('direct', 'chain')))
