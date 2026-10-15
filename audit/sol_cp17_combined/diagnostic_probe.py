"""Exercise the unchanged diagnostic writer against a real synthetic PostgreSQL exception.
This tests evidence retention, not the original AZ failure and not an ERP command.
"""
from pathlib import Path
import hashlib, json, os, stat, sys
import psycopg

WORK_ROOT = Path.cwd()
ROOT = Path(__file__).resolve().parents[3] / 'auditor'
os.chdir(ROOT)  # The unchanged installer imports its pinned metadata relative to the candidate root.
sys.path.insert(0, str(ROOT / 'scripts'))
import cp6_readiness_owner_install as installer

OUT = WORK_ROOT / 'diagnostic-proof'
OUT.mkdir(exist_ok=True)
manifest = json.loads(Path(__file__).with_name('diagnostic_manifest.json').read_text())
report = dict(candidate_sha=manifest['candidate_sha'], layer=manifest['layer'],
              oracle_origin=manifest['oracle_origin'], fixture_origin=manifest['fixture_origin'],
              case_manifest_sha256=hashlib.sha256(Path(__file__).with_name('diagnostic_manifest.json').read_bytes()).hexdigest(),
              tested_source_sha256=hashlib.sha256((ROOT/'scripts/cp6_readiness_owner_install.py').read_bytes()).hexdigest(),
              cases={}, historical_AZ_root_claim=False, production_go=False)
url = os.environ['PGURL']
fixture = "do $sol$ begin raise exception using errcode='P0001', message='SOL_SYNTHETIC_PRIMARY', detail='SOL_SYNTHETIC_DETAIL', hint='SOL_SYNTHETIC_HINT'; end $sol$"
raw_error = None
try:
    with psycopg.connect(url, application_name='sol_diag_work') as work, \
         psycopg.connect(url, application_name='sol_diag_observer') as observer:
        observer.autocommit=True
        database, pid, version=work.execute('select current_database(),pg_backend_pid(),version()').fetchone()
        work.commit()
        report['environment'] = dict(database=database, server_version=version)
        report['other_sessions_before'] = observer.execute('select count(*) from pg_stat_activity where datname=%s and pid<>all(%s)',(database,[pid,observer.info.backend_pid])).fetchone()[0]
        try:
            work.execute(fixture)
            raise AssertionError('synthetic SQL failure not reached')
        except psycopg.errors.RaiseException as error:
            raw_error=error
            work.rollback()
            public=dict(files=[],current_file_key='SYNTHETIC_DIAGNOSTIC_ONLY')
            rows=[(dict(key='SYNTHETIC_DIAGNOSTIC_ONLY',package_sha256=hashlib.sha256(fixture.encode()).hexdigest()),fixture)]
            pointer=installer.private_diagnostic(error,public,OUT/'owner.json',work,rows,observer,database,pid)
            path=OUT/pointer['file']; body=path.read_bytes(); d=json.loads(body)
            assert d['sqlstate']=='P0001' and d['postgres']['message_primary']=='SOL_SYNTHETIC_PRIMARY', d
            assert d['postgres']['message_detail']=='SOL_SYNTHETIC_DETAIL' and d['postgres']['message_hint']=='SOL_SYNTHETIC_HINT',d
            assert 'PL/pgSQL' in d['postgres']['context'] and 'RAISE' in d['postgres']['context'],d
            assert d['session']['database']==database and d['session']['current_user']=='postgres',d
            assert any(x['application_name']=='sol_diag_observer' for x in d['other_backends']),d
            assert all('query' not in x for x in d['other_backends']),d
            report['cases']['SOL_DIAG_PG_FIELDS_AND_CONTEXT']=dict(status='PASS', diagnostic_file=path.name, sqlstate=d['sqlstate'], context=d['postgres']['context'])
            assert stat.S_IMODE(path.stat().st_mode)==0o600 and hashlib.sha256(body).hexdigest()==pointer['sha256'],pointer
            assert set(pointer)=={'file','sha256','permissions'} and pointer['permissions']=='0600',pointer
            assert error is raw_error and error.diag.message_primary=='SOL_SYNTHETIC_PRIMARY'
            report['cases']['SOL_DIAG_PRIVATE_FILE_HASH_MODE']=dict(status='PASS',pointer=pointer,actual_mode='0600',original_exception_preserved=True)
            blocked=OUT/'not-a-directory';blocked.write_text('synthetic file')
            unavailable=installer.private_diagnostic(error,public,blocked/'owner.json',work,rows,observer,database,pid)
            assert unavailable=={'unavailable':'FileExistsError'},unavailable
            assert error is raw_error and error.sqlstate=='P0001'
            report['cases']['SOL_DIAG_FAILURE_FAILS_EXPLICITLY']=dict(status='PASS',observed=unavailable,original_exception_preserved=True)
        report['other_sessions_after'] = observer.execute('select count(*) from pg_stat_activity where datname=%s and pid<>all(%s)',(database,[pid,observer.info.backend_pid])).fetchone()[0]
        assert report['other_sessions_before']==report['other_sessions_after']==0
        assert list(report['cases'])==[c['id'] for c in manifest['cases']]
        report.update(status='PASS',case_set_complete=True)
finally:
    if report.get('status')!='PASS':report['status']='INCOMPLETE'
    (OUT/'SOL_DIAGNOSTIC_RETEST.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(dict(status=report['status'],cases=len(report['cases']),layer=report['layer'])))
