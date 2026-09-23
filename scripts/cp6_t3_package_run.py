"""T3 preparation on the hosted-faithful baseline: the combined release package, then AW/AX T1, advisors and the
backup and restore drill.

The disposable chain is rebuilt to v2.6.20, aligned with hosted (G-01 option 1) and continued through the frozen path
to AB (the frozen AC refuses there, run 35911530080). The clone cp6_rollback of that AB state receives:
  PACKAGE  AC'..AV' from scripts/cp6_t3_release_package.py (mode capture: derive and print the pins while installing;
           mode install: the committed package in supabase/release/cp6-t3), each file PASS or its exact refusal;
  AW_T1, AX_T1  the T1 family files, unchanged;
then the Supabase security advisors at AB and at the end, and the backup and restore drill of the final clone.
Owner (23 Sep 2026): T3 stays HOLD until every difference is explained and the AO-AV install passes.
Label: T3_PREP (not release evidence).
"""
from pathlib import Path
import json,os,subprocess,sys,traceback
import psycopg

AUDITOR=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(Path.cwd()/'scripts'))
sys.path.append(str(AUDITOR/'scripts'))
import cp6_aw_probe as awp
import cp6_ax_probe as axp
import cp6_g01_fingerprint as fp
import cp6_t3_backup_restore_drill as drill
import cp6_t3_release_package as package
from cp6_t3_aligned_install import advisors,advisor_delta

boundary=awp.boundary
OUT=AUDITOR/'cp6-proof/t3'


def fingerprint(url):
    with psycopg.connect(url) as conn,conn.cursor() as cur:
        conn.read_only=True
        return cur.execute(fp.SUMMARY).fetchone()[0]


def ledger(url):
    with psycopg.connect(url) as conn,conn.cursor() as cur:
        conn.read_only=True
        return dict(app=[r[0] for r in cur.execute("select version from erp.schema_migrations where version like 'v2.6.20a_' order by version")],
                    platform_last=cur.execute('select max(version) from supabase_migrations.schema_migrations').fetchone()[0])


def run(mode):
    assert mode in ('capture','install')
    assert os.environ.get('CP6_AR_CONFIRM')=='cp6_rollback' and os.environ.get('CP6_DATABASE_CONTAINER')=='supabase_db_cp5-local'
    OUT.mkdir(parents=True,exist_ok=True)
    report=dict(label='T3_PREP',mode=mode,status='INCOMPLETE',stages=[],production_go=False,release_evidence=False)
    def save():(OUT/('T3_PACKAGE_%s.json'%mode.upper())).write_text(json.dumps(report,indent=2,default=str)+'\n')
    primary=None
    try:
        with psycopg.connect(boundary.PRIMARY_ADMIN) as conn,conn.cursor() as cur:primary=boundary.snapshot(cur)
        start=ledger(boundary.ADMIN);report['ledger_start']=start
        assert start['app'][-1]=='v2.6.20ab' and start['platform_last']=='20260914190500',('T3_CLONE_NOT_AT_AB',start)
        report['fingerprint_AB']=fingerprint(boundary.ADMIN)
        advisors_AB=advisors(boundary.PG)
        committed=AUDITOR/'docs/evidence/cp6-t3/release_pins.json'
        stages=[('PACKAGE',lambda:(package.capture if mode=='capture' else package.install)(OUT/('T3_PACKAGE_FILES_%s.json'%mode.upper()))['status']),
                ('AW_T1',lambda:awp.install_aw()),
                ('AX_T1',lambda:axp.install_ax())]
        for name,operation in stages:
            try:
                result=operation()
                ok=name!='PACKAGE' or result in ('CAPTURED_AND_INSTALLED','ALL_FILES_INSTALLED')
                row=dict(stage=name,status='PASS' if ok else 'REFUSED',result=result)
            except Exception as exc:
                row=dict(stage=name,status='REFUSED',error=str(exc)[:4000],traceback=traceback.format_exc()[-4000:])
            report['stages'].append(row);save()
            print(json.dumps(dict(group='T3_PACKAGE_RUN',**row),default=str)[:6000],flush=True)
            if row['status']!='PASS':break
        if mode=='capture' and committed.exists() and (OUT/'T3_PACKAGE_FILES_CAPTURE.json').exists():
            # Determinism: the pins captured now must give the same package as the committed pins.
            now={f['key']:f.get('package_sha256') for f in json.loads((OUT/'T3_PACKAGE_FILES_CAPTURE.json').read_text())['files']}
            then={f['key']:f['package_sha256'] for f in json.loads(committed.read_text())['files']}
            report['pins_reproduced']=dict(equal=now==then,differ=sorted(k for k in set(now)|set(then) if now.get(k)!=then.get(k)))
            print(json.dumps(dict(group='T3_PINS_REPRODUCED',**report['pins_reproduced'])),flush=True)
        report['ledger_final']=ledger(boundary.ADMIN)
        report['fingerprint_final']=fingerprint(boundary.ADMIN)
        advisors_final=advisors(boundary.PG)
        installed=[s['stage'] for s in report['stages'] if s['status']=='PASS']
        report['security_advisors']=dict(AB=advisors_AB,final=advisors_final,delta=advisor_delta(advisors_AB,advisors_final),installed_stages=installed)
        delta=report['security_advisors']['delta']
        compact=lambda f:[f.get('name'),f.get('level'),(f.get('metadata') or {}).get('schema'),(f.get('metadata') or {}).get('name'),(f.get('metadata') or {}).get('type')]
        print(json.dumps(dict(group='T3_SECURITY_ADVISORS',status=delta.get('status'),before=delta.get('before'),after=delta.get('after'),
                              added=[compact(f) for f in delta.get('added',[])],removed=[compact(f) for f in delta.get('removed',[])]),default=str),flush=True)
        report['status']='ALL_STAGES_INSTALLED' if len(installed)==len(stages) else 'REFUSED'
        report['backup_restore_drill']=drill.run(OUT/'T3_BACKUP_RESTORE_DRILL.json',installed)['status']
    except Exception as exc:
        report.update(status='INCOMPLETE',error=str(exc)[:4000],traceback=traceback.format_exc()[-4000:])
    finally:
        subprocess.run(['docker','exec','supabase_db_cp5-local','dropdb','-U','supabase_admin','--if-exists','--force',
                        '--maintenance-db=template1','cp6_rollback'],check=True)
        with psycopg.connect(boundary.PRIMARY_ADMIN) as conn,conn.cursor() as cur:
            report['primary_unchanged']=primary is not None and boundary.snapshot(cur)==primary
        save()
    print(json.dumps(dict(t3_package_run={k:v for k,v in report.items() if k not in('stages','security_advisors')}),default=str)[:8000],flush=True)
    # A refusal is a recorded finding, not a crash; only an incomplete run fails the job.
    assert report['status']!='INCOMPLETE',report.get('error')


if __name__=='__main__':run(sys.argv[1])
