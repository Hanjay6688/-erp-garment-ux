"""T3 preparation: install the pending release path AO..AV (and the AW/AX T1 files) on the clone of the aligned chain.

The chain below this point is the hosted-faithful baseline (G-01 option 1) upgraded through the frozen path to AN.
Each stage runs through the same installer the T1/T2 evidence uses, and records PASS or the exact refusal; the first
refusal stops the run. A refusal is the finding: no guard, pin or oracle is changed here. Owner (23 Sep 2026): T3 stays
HOLD until every difference is explained and the AO-AV install passes. After the stages, the backup and restore drill
(scripts/cp6_t3_backup_restore_drill.py) dumps the clone as installed and restores it into a separate database of the
same disposable cluster. Label: T3_PREP (not release evidence).
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

r1,boundary,prior=awp.r1,awp.boundary,awp.prior
OUT=AUDITOR/'cp6-proof/t3'


def fingerprint(url):
    with psycopg.connect(url) as conn,conn.cursor() as cur:
        conn.read_only=True
        return cur.execute(fp.SUMMARY).fetchone()[0]


def advisors(url):
    """Supabase security advisors on the clone (same pinned CLI and flags as the AQ..AU runtimes); recorded only."""
    r=subprocess.run(['supabase','db','advisors','--db-url',url,'--type','security','--level','info','--fail-on','none',
                      '--output-format','text','--agent','no'],capture_output=True,text=True,timeout=180)
    if r.returncode!=0:return dict(status='FAILED',exit=r.returncode,stderr=r.stderr[-3000:])
    if r.stdout.strip():findings=json.loads(r.stdout)
    elif 'No issues found' in r.stderr.splitlines():findings=[]
    else:return dict(status='MISSING_RESULT',stderr=r.stderr[-3000:])
    return dict(status='RECORDED',findings=findings)


def advisor_delta(before,after):
    if before.get('status')!='RECORDED' or after.get('status')!='RECORDED':
        return dict(status='NOT_COMPARABLE',before=before.get('status'),after=after.get('status'))
    key=lambda f:json.dumps(f,sort_keys=True)
    old={key(f) for f in before['findings']};new={key(f) for f in after['findings']}
    added=[f for f in after['findings'] if key(f) not in old];removed=[f for f in before['findings'] if key(f) not in new]
    # A new finding is not accepted here: it goes to review with its name, level and object.
    return dict(status='NO_NEW_FINDINGS' if not added else 'REVIEW_REQUIRED',before=len(before['findings']),
                after=len(after['findings']),added=added,removed=removed)


def run():
    assert os.environ.get('CP6_AR_CONFIRM')=='cp6_rollback' and os.environ.get('CP6_DATABASE_CONTAINER')=='supabase_db_cp5-local'
    OUT.mkdir(parents=True,exist_ok=True)
    control=os.environ['CP6_ADMISSION_CONTROL_PGURL']
    report=dict(label='T3_PREP',status='INCOMPLETE',stages=[],production_go=False,release_evidence=False,source=r1.source())
    stages=[('AO_AS',lambda:r1.writer.peer_trial.install_as()),
            ('AT',lambda:r1.writer.predecessor_runtime.change('install',boundary.PG,control)),
            ('AU',lambda:awp.au_runtime.change('install',boundary.PG,control)['status']),
            ('AV',lambda:awp.av_runtime.change('install',boundary.PG,control)['status']),
            ('AW_T1',lambda:awp.install_aw()),
            ('AX_T1',lambda:axp.install_ax())]
    primary=None
    try:
        with psycopg.connect(boundary.PRIMARY_ADMIN) as conn,conn.cursor() as cur:prior.verified(cur,'AN');primary=boundary.snapshot(cur)
        report['fingerprint_AN']=fingerprint(boundary.ADMIN)
        advisors_AN=advisors(boundary.PG)
        for name,operation in stages:
            try:
                result=operation();row=dict(stage=name,status='PASS',result=result)
            except Exception as exc:
                row=dict(stage=name,status='REFUSED',error=str(exc)[:4000],traceback=traceback.format_exc()[-4000:])
            report['stages'].append(row)
            print(json.dumps(dict(group='T3_ALIGNED_INSTALL',**row),default=str)[:6000],flush=True)
            (OUT/'T3_ALIGNED_INSTALL.json').write_text(json.dumps(report,indent=2,default=str)+'\n')
            if row['status']!='PASS':break
        report['fingerprint_final']=fingerprint(boundary.ADMIN)
        advisors_final=advisors(boundary.PG)
        report['security_advisors']=dict(AN=advisors_AN,final=advisors_final,delta=advisor_delta(advisors_AN,advisors_final),
                                         installed_stages=[s['stage'] for s in report['stages'] if s['status']=='PASS'])
        print(json.dumps(dict(group='T3_SECURITY_ADVISORS',delta=report['security_advisors']['delta']),default=str)[:6000],flush=True)
        report['status']='ALL_STAGES_INSTALLED' if all(s['status']=='PASS' for s in report['stages']) and len(report['stages'])==len(stages) else 'REFUSED'
        # Backup and restore drill of the clone as installed (owner: drill in a separate environment); it records its
        # own result and never changes the install outcome.
        report['backup_restore_drill']=drill.run(OUT/'T3_BACKUP_RESTORE_DRILL.json',
                                                 [s['stage'] for s in report['stages'] if s['status']=='PASS'])['status']
    except Exception as exc:
        report.update(status='INCOMPLETE',error=str(exc),traceback=traceback.format_exc())
    finally:
        subprocess.run(['docker','exec','supabase_db_cp5-local','dropdb','-U','supabase_admin','--if-exists','--force','--maintenance-db=template1','cp6_rollback'],check=True)
        with psycopg.connect(boundary.PRIMARY_ADMIN) as conn,conn.cursor() as cur:
            prior.verified(cur,'AN');report['primary_unchanged']=primary is not None and boundary.snapshot(cur)==primary
        (OUT/'T3_ALIGNED_INSTALL.json').write_text(json.dumps(report,indent=2,default=str)+'\n')
    print(json.dumps(dict(t3_aligned_install={k:v for k,v in report.items() if k not in('stages',)}),default=str)[:8000],flush=True)
    # A refusal is a recorded finding, not a crash; only an incomplete run fails the job.
    assert report['status']!='INCOMPLETE',report.get('error')


if __name__=='__main__':run()
