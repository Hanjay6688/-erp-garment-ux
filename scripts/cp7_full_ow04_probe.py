"""Qualify the actual complete owning installer on disposable Native copies.

Retain all frozen63 OW04 cases, add one real-used-installation rollback
refusal, and prove pre-use removal restores CP6 before the measured suite.
No providers, scheduled jobs, hosted writes, or release admission.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import traceback
import uuid

import psycopg
import cp7_ow04_probe as core
# CP6 preparation inserts its frozen writer directory on sys.path. Select
# this candidate's new product installer/dependencies explicitly afterwards.
sys.path.insert(0,str(Path(__file__).resolve().parent))
import cp7_full_owning_install as full
import cp7_restore_state as restore_state
from cp7_catalog_state import exact_public_catalog
from cp6_t3_aligned_install import advisors, advisor_delta

assert core.SIGNED_SOURCE, 'FULL_INSTALL_QUALIFIER_REQUIRES_EXPLICIT_SIGNED_SOURCE'
DEPENDENCIES = '--credit-dependencies' in sys.argv[1:]
NATIVE_FRACTIONAL = '--native-fractional-hpp' in sys.argv[1:]
assert not NATIVE_FRACTIONAL or DEPENDENCIES, 'NATIVE_FRACTIONAL_RETAINS_ALL_NATIVE73_CASES'
if DEPENDENCIES:
    from cp7_customer_credit.readers import cp7_ow04_credit_dependency_cases as dependency_cases
if NATIVE_FRACTIONAL:
    import cp7_ow04_native_fractional_cases as native_fractional
LABEL = 'CP7_FULL_OW04_NATIVE_FRACTIONAL' if NATIVE_FRACTIONAL else 'CP7_FULL_OW04_DEPENDENCIES_NATIVE' if DEPENDENCIES else 'CP7_FULL_OW04_NATIVE'
OUT = full.ROOT/'cp6-proof/t3'/f'{LABEL}.json'
DECLARATION_PATH = full.ROOT/'docs/cp7/d17-14/ow04'/('DIRECT_NATIVE_FRACTIONAL_QUALIFICATION.json' if NATIVE_FRACTIONAL else 'CREDIT_DEPENDENCY_NATIVE_QUALIFICATION.json' if DEPENDENCIES else 'FULL_INSTALL_QUALIFICATION.json')
DECLARATION_BYTES = DECLARATION_PATH.read_bytes()
DECLARATION = json.loads(DECLARATION_BYTES)
USED_GUARD_ID = 'OW04_FULL_USED_INSTALL_ROLLBACK_REFUSED'
IDS = core.IDS+(USED_GUARD_ID,)+(dependency_cases.IDS if DEPENDENCIES else ())+(native_fractional.IDS if NATIVE_FRACTIONAL else ())
assert DECLARATION['expected_count'] == len(IDS) == (87 if NATIVE_FRACTIONAL else 73 if DEPENDENCIES else 64)
assert tuple(DECLARATION['required_case_ids']) == IDS
STATE = None
package, native, p09 = core.package, core.native, core.p09


def used_install_guard(cur, today):
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
        before = dict(rows=full.private_rows(cur), functions=p09.functions(cur),
            boundary=package.boundary.snapshot(cur))
        assert before['rows'] != STATE['seeded_private_rows'], 'FULL_GUARD_REAL_USE_REQUIRED'
        try:
            full.rollback_preuse(cur, STATE)
        except ValueError as error:
            assert str(error) == 'CP7_FULL_ROLLBACK_AFTER_USE_REQUIRES_BACKUP_RESTORE', str(error)
        else:
            raise AssertionError('FULL_USED_INSTALLATION_WAS_REMOVED')
        assert before == dict(rows=full.private_rows(cur), functions=p09.functions(cur),
            boundary=package.boundary.snapshot(cur)), 'FULL_ROLLBACK_REFUSAL_CHANGED_STATE'
        cur.execute('set constraints all immediate')
        return dict(status='PASS', actual_settlement_request=str(request),
            native_settlement=outcome, rollback_refused=True,
            all_private_rows_and_catalog_unchanged=True, native_executed=True,
            production_go=False)


def cases(cur, today):
    retained = core.initial.cases(cur,today)+core.retained_returns.cases(cur,today) \
        +core.retained_reads.cases(cur,today)+core.retained_e01.cases(cur,today)
    helpers = [row['definition'] for row in STATE['credit']['native_empty']['before_helpers'].values()]
    retained += core.empty_cases.cases(cur,today,before_helpers=helpers,
        reapply_overlay=lambda cursor:cursor.execute(
            full.credit._actual_sql('native-empty/04_exact_overlays.sql'),prepare=False))
    retained += core.fractional_hpp.cases(cur,today)+core.signed_source.cases(cur,today) \
        +core.signed_zero.cases(cur,today)
    result = retained+[(USED_GUARD_ID,lambda:used_install_guard(cur,today))]
    if DEPENDENCIES:
        result += dependency_cases.cases(cur,today)
    if NATIVE_FRACTIONAL:
        result += native_fractional.cases(cur,today)
    assert tuple(name for name,_ in result) == IDS, 'FULL_PREDECLARED_CASE_SET_CHANGED'
    return result


def verify(cur):
    if STATE is None:
        raise ValueError('FULL_INSTALLATION_STATE_REQUIRED')
    return full.verify(cur, STATE)



def qualification_sources():
    paths=[Path(__file__).resolve()]
    if DEPENDENCIES:
        paths.append(Path(dependency_cases.__file__).resolve())
    if NATIVE_FRACTIONAL:
        paths.extend([Path(native_fractional.__file__).resolve(),Path(native_fractional.__file__).with_name('NATIVE_EXPECTED.json').resolve()])
    return {str(path.relative_to(full.ROOT.resolve())):hashlib.sha256(path.read_bytes()).hexdigest()
            for path in paths}

def run():
    global STATE
    report = dict(label=LABEL,status='INCOMPLETE',expected_case_count=len(IDS),
        required_case_ids=list(IDS),predeclared_case_sha256=hashlib.sha256(DECLARATION_BYTES).hexdigest(),
        candidate_commit=subprocess.check_output(['git','-C',str(full.ROOT),'rev-parse','HEAD'],text=True).strip(),
        source_manifest=full.source_manifest(),production_go=False,feature_complete=False,
        independent_acceptance=False,qualification_only=True,hosted=False,
        scope='FULL_OWNING_INSTALL_PREUSE_RESTORE_NATIVE87_RETAINED73_AND_DIRECT_NATIVE_FRACTIONAL14' if NATIVE_FRACTIONAL else 'FULL_OWNING_INSTALL_PREUSE_RESTORE_NATIVE63_AND_USED_ROLLBACK_GUARD',
        retained_native_declaration_sha256=hashlib.sha256(core.DECLARATION_BYTES).hexdigest(),
        qualification_source_sha256=qualification_sources())
    installed = False
    try:
        with psycopg.connect(package.boundary.ADMIN) as conn, conn.cursor() as cur:
            p09.wip.policy.bf.verified(cur)
            before = restore_state.capture(cur,package.boundary.snapshot,core.predecessor.public_state,p09.functions)
            conn.rollback()
            STATE = full.install(cur)
            full.rollback_preuse(cur,STATE)
            restored = {}
            assert restore_state.prove(cur,before,package.boundary.snapshot,
                core.predecessor.public_state,p09.functions,restored), ('FULL_PREUSE_RESTORE_FAILED',restored)
            report['preuse_rollback'] = dict(status='PASS',**restored)
            STATE = full.install(cur)
            report['verified_predecessor_info_manifest'] = core.predecessor_info_manifest(cur)
            report['integrated_installation'] = dict(sources=STATE['sources'],
                predecessor=STATE['predecessor_installation'],credit={key:STATE['credit'][key]
                    for key in ('approval','context_proof','refund_proof','source_sha256')})
            report['installed_verification'] = verify(cur)
            conn.commit()
            installed = True
        report['advisors_with_cp7'] = advisors(package.boundary.PG)
        with exact_public_catalog(native,retain_raw=True) as catalog:
            report['native'] = native.strict_group(LABEL,cases,verify)
        report['native_public_catalog_comparison'] = catalog
    except Exception as error:
        report.update(error=str(error),traceback=traceback.format_exc())
    finally:
        if installed:
            try:
                with psycopg.connect(package.boundary.ADMIN) as conn, conn.cursor() as cur:
                    # Native strict_group rolls each case back, so this clone
                    # has never been used; ordinary pre-use admission applies.
                    full.rollback_preuse(cur,STATE)
                    conn.commit()
                    report['cp6_restored'] = restore_state.prove(cur,before,package.boundary.snapshot,
                        core.predecessor.public_state,p09.functions,report)
                    conn.rollback()
                    p09.wip.policy.bf.verified(cur)
                    conn.rollback()
                report['advisor_delta'] = advisor_delta(advisors(package.boundary.PG),report['advisors_with_cp7'])
                report['advisor_disposition'] = core.advisor_disposition(
                    report['advisor_delta'],report['verified_predecessor_info_manifest'])
                report['advisor_gate'] = report['advisor_disposition']['gate']
            except Exception as error:
                report.update(restore_error=str(error),restore_traceback=traceback.format_exc(),
                    cp6_restored=False,advisor_gate=False)
        group = report.get('native',{})
        report['observed_case_count'] = sum(group.get('counts',{}).values())
        report['required_case_ids_pass'] = set(group.get('cases',{})) == set(IDS)
        if not report.get('error') and report.get('cp6_restored') and report.get('advisor_gate') \
                and report.get('preuse_rollback',{}).get('status') == 'PASS' \
                and group.get('counts') == {'PASS':len(IDS)} and report['required_case_ids_pass'] \
                and group.get('database_remaining',0) == 0:
            report['status'] = 'PASS'
        OUT.parent.mkdir(parents=True,exist_ok=True)
        OUT.write_text(json.dumps(report,indent=2,default=str)+'\n')
        print(json.dumps({key:report.get(key) for key in ('label','status','expected_case_count',
            'observed_case_count','cp6_restored','advisor_gate','error','restore_error')},default=str),flush=True)
    return dict(status=report['status'],production_go=False,independent_acceptance=False,feature_complete=False)


if __name__ == '__main__':
    if sys.argv[1:] not in (['--signed-source'],['--signed-source','--credit-dependencies'],['--signed-source','--credit-dependencies','--native-fractional-hpp']):
        raise SystemExit('Only --signed-source with optional --credit-dependencies and --native-fractional-hpp is supported')
    package._writer_runtime = lambda browser_mode=False:run()
    package.run('install')
