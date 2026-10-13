"""Run own OID/backup oracles on the unchanged candidate in disposable native CI."""
from pathlib import Path
from urllib.parse import urlparse
import sys, json, traceback
PRODUCT = Path.cwd().parent / 'auditor'
ROOT = Path(__file__).resolve().parent
sys.path[:0] = [str(PRODUCT / 'scripts'), str(ROOT)]
import psycopg
import cp7_p21_full_rehearsal_probe as composition
import cp6_auditor_modes as modes
import cp6_t3_package_run as package
import backup_cases
OUT = PRODUCT / 'cp6-proof/t3/ASTRA_XC2_BACKUP.json'


def run():
    report = dict(status='INCOMPLETE', product_sha='0b7049d9203bac52b47a4c89f3e0d75646067a8f',
                  production_go=False, expected_cases=11, evidence_origin='INDEPENDENT_NATIVE_CASE',
                  oracle_origin='ASTRA_CONTRACT', fixture_origin='ASTRA_SYNTHETIC_DATABASES')
    installed = False
    try:
        for url in (package.boundary.ADMIN, package.boundary.PRIMARY_ADMIN):
            assert urlparse(url).hostname in ('127.0.0.1', 'localhost', '::1')
        with psycopg.connect(package.boundary.ADMIN) as conn, conn.cursor() as cur:
            composition.p09.wip.policy.bf.verified(cur)
            before = package.boundary.snapshot(cur)
            public_before = composition.f05.public_state(cur)
            functions_before = composition.p09.functions(cur)
            conn.rollback()
            originals, install = composition.install(cur)
            conn.commit()
            installed = True
            report['install'] = install
            report['verify'] = composition.verify(cur)
            conn.rollback()
        report['races'] = modes.run_races(backup_cases, composition.verify, 'astra_xc2_backup')
    except Exception as exc:
        report.update(error=str(exc), traceback=traceback.format_exc())
    finally:
        if installed:
            try:
                with psycopg.connect(package.boundary.ADMIN) as conn, conn.cursor() as cur:
                    composition.uninstall(cur, originals)
                    conn.commit()
                    report['restore'] = dict(boundary=package.boundary.snapshot(cur) == before,
                                           public=composition.f05.public_state(cur) == public_before,
                                           functions=composition.p09.functions(cur) == functions_before)
                    conn.rollback()
                    composition.p09.wip.policy.bf.verified(cur)
                    conn.rollback()
            except Exception as exc:
                report.update(restore_error=str(exc), restore_traceback=traceback.format_exc())
        group = report.get('races', {})
        report['case_verdicts'] = {key: value['status'] for key, value in group.get('races', {}).items()}
        good = group.get('counts') == {'PASS': 11} and not group.get('error') and not group.get('database_remaining') and not group.get('cleanup_failures')
        good = good and bool(report.get('restore')) and all(report.get('restore', {}).values()) and not report.get('error') and not report.get('restore_error')
        report['status'] = 'PASS' if good else 'INCOMPLETE'
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(report, indent=2, default=str) + '\n')
        print(json.dumps({key: report.get(key) for key in ('status', 'case_verdicts', 'error', 'restore', 'restore_error')}, default=str), flush=True)
    return dict(status=report['status'], production_go=False, independent_acceptance=False)


if __name__ == '__main__':
    package._writer_runtime = lambda browser_mode=False: run()
    package.run('install')
