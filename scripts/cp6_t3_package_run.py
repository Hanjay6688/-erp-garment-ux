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
import cp6_t3_browser as browser
from cp6_t3_aligned_install import advisors,advisor_delta

boundary=awp.boundary
OUT=AUDITOR/'cp6-proof/t3'
# B2 (independent audit CP6-11): the job is green only on the whole gate below. The one reviewed advisor class that a
# release adds is INFO rls_enabled_no_policy on erp tables (owner-only tables with RLS on and no policy, reached only
# through security-definer RPCs; 54 of them at 208afce). Any other new finding, or a finding that cannot be compared,
# turns the job red.
ACCEPTED_NEW_ADVISOR=('rls_enabled_no_policy','INFO','erp')
DRILL_OK=('RESTORED_IDENTICAL','RESTORED_SAME_MEANING')


def advisors_ok(delta):
    if delta.get('status')=='NO_NEW_FINDINGS':return True
    return delta.get('status')=='REVIEW_REQUIRED' and all(
        (f.get('name'),f.get('level'),(f.get('metadata') or {}).get('schema'))==ACCEPTED_NEW_ADVISOR for f in delta.get('added',[]))


def fingerprint(url):
    with psycopg.connect(url) as conn,conn.cursor() as cur:
        conn.read_only=True
        return cur.execute(fp.SUMMARY).fetchone()[0]


def ledger(url):
    with psycopg.connect(url) as conn,conn.cursor() as cur:
        conn.read_only=True
        return dict(app=[r[0] for r in cur.execute("select version from erp.schema_migrations where version like 'v2.6.20a_' order by version")],
                    platform_last=cur.execute('select max(version) from supabase_migrations.schema_migrations').fetchone()[0])


HOSTED_CAPSULES=AUDITOR/'docs/evidence/cp6-t3/hosted_capsule_hashes.json'
CAPSULE_ROWS="""select t.object_identity,encode(extensions.digest(convert_to((to_jsonb(t)-array['captured_at','boundary_snapshot'])::text,'UTF8'),'sha256'),'hex'),
 t.definition_sha256,t.acl_snapshot,md5(t.object_definition) from erp.cp6_v2620_rollback_capsule t order by 1"""


def capsule_compare(url):
    """Hosted capsule hashes (read-only, docs/evidence/cp6-t3/hosted_capsule_hashes.json) against this clone, per capsule
    and, for cp6_v2620_rollback_capsule, per row and field."""
    hosted=json.loads(HOSTED_CAPSULES.read_text())
    [ao]=[r for r in package.package() if r['key']=='AO']
    formula=package.history((AUDITOR/ao['path']).read_text())['query']
    with psycopg.connect(url) as conn,conn.cursor() as cur:
        conn.read_only=True
        live=package.live_history(cur,formula,list(hosted['capsules']))
        rows={r[0]:dict(row_hash=r[1],definition_sha256=r[2],acl_snapshot=r[3],definition_md5=r[4]) for r in cur.execute(CAPSULE_ROWS).fetchall()}
    per_row=[]
    for h in hosted['cp6_v2620_rows']:
        c=rows.get(h['object'])
        if c is None:per_row.append(dict(object=h['object'],missing_on_clone=True));continue
        if c['row_hash']==h['row_hash']:continue
        per_row.append(dict(object=h['object'],fields=[k for k in ('definition_sha256','acl_snapshot','definition_md5') if c[k]!=h[k]],
                            acl_hosted=h['acl_snapshot'],acl_clone=c['acl_snapshot'],acl_same_set=sorted(h['acl_snapshot'])==sorted(c['acl_snapshot'] or [])))
    capsules={k:dict(hosted=v[1],clone=live[k],equal=live[k]==v[1]) for k,v in hosted['capsules'].items()}
    return dict(equal=all(c['equal'] for c in capsules.values()) and not per_row,capsules=capsules,cp6_v2620_rows_differing=per_row)


def verify_awx():
    import cp6_az_probe as azp
    import cp6_ba_probe as bap
    import cp6_bb_probe as bbp
    import cp6_bc_probe as bcp
    import cp6_bd_probe as bdp
    import cp6_be_probe as bep
    with psycopg.connect(boundary.ADMIN) as conn,conn.cursor() as cur:
        # The committed package decides the stage: with BC (or BB, BA) in it, that family and every earlier one are verified.
        verify=(bep.verified if bep.installed(cur) else bdp.bd_verified if bdp.bd_installed(cur) else bcp.bc_verified if bcp.bc_installed(cur) else bbp.bb_verified if bbp.bb_installed(cur)
                else bap.ba_verified if bap.ba_installed(cur) else azp.az_verified)
        result=verify(cur);conn.rollback()
    return {k:result.get(k) for k in ('stage','functions','sql_sha256','ax_sql_sha256','ay_sql_sha256','az_sql_sha256','ba_sql_sha256','bb_sql_sha256',
                                       'bc_sql_sha256','bd_sql_sha256','be_sql_sha256')}


def run(mode):
    assert mode in ('capture','install','browser')
    assert os.environ.get('CP6_AR_CONFIRM')=='cp6_rollback' and os.environ.get('CP6_DATABASE_CONTAINER')=='supabase_db_cp5-local'
    OUT.mkdir(parents=True,exist_ok=True)
    report=dict(label='T3_PREP',mode=mode,status='INCOMPLETE',stages=[],production_go=False,release_evidence=False)
    import cp6_run_identity as run_identity
    report['run_identity']=run_identity.announce('T3_PREP',mode=mode)
    def save():(OUT/('T3_PACKAGE_%s.json'%mode.upper())).write_text(json.dumps(report,indent=2,default=str)+'\n')
    primary=None
    try:
        with psycopg.connect(boundary.PRIMARY_ADMIN) as conn,conn.cursor() as cur:
            primary=boundary.snapshot(cur);report['auth_users_before']=cur.execute('select count(*) from auth.users').fetchone()[0]
        start=ledger(boundary.ADMIN);report['ledger_start']=start
        assert start['app'][-1]=='v2.6.20ab' and start['platform_last']=='20260914190500',('T3_CLONE_NOT_AT_AB',start)
        report['fingerprint_AB']=fingerprint(boundary.ADMIN)
        report['hosted_capsules']=capsule_compare(boundary.ADMIN)
        print(json.dumps(dict(group='T3_HOSTED_CAPSULES',**report['hosted_capsules']),default=str),flush=True)
        # Pins are only taken or checked on a baseline whose historical capsules equal hosted (the catalog is checked
        # against hosted right after the alignment, scripts/cp6_t3_aligned_chain.py).
        assert report['hosted_capsules']['equal'],'T3_CLONE_CAPSULES_NOT_HOSTED'
        advisors_AB=advisors(boundary.PG)
        committed=AUDITOR/'supabase/release/cp6-t3/MANIFEST.json'
        # AC..AV and the AW/AX/AY/AZ/BA release candidates are all files of the one package; AW..BA T1 verification follows.
        stages=[('PACKAGE',lambda:(package.capture if mode=='capture' else package.install)(OUT/('T3_PACKAGE_FILES_%s.json'%mode.upper()))['status']),
                ('AW_AX_AY_AZ_VERIFY',lambda:verify_awx())]
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
        if mode=='browser':
            # Browser mode: the unchanged AU browser flow on the installed combined candidate, then cleanup. The status is
            # the flow's own result: 10 cases PASS and the candidate verified again afterwards.
            installed=len(report['stages'])==len(stages) and all(s['status']=='PASS' for s in report['stages'])
            report['browser']=browser.run(OUT/'T3_BROWSER.json') if installed else 'NOT_RUN'
            flow=report['browser'].get('status') if isinstance(report['browser'],dict) else None
            report['status']='BROWSER_PASS' if flow=='PASS' else ('REFUSED' if not installed else 'BROWSER_'+str(flow))
        else:
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
            # Round 9, W12 (b) and W6: the read-only cutover data checks on the final clone (frontend UUID pattern on every erp
            # uuid column; active cash accounts sharing a COA account). Observations of this baseline; on a cutover drill copy of
            # hosted/legacy data a FOUND must be resolved before cutover.
            try:
                import cp6_cutover_data_checks as data_checks
                with psycopg.connect(boundary.ADMIN) as conn,conn.cursor() as cur:
                    report['cutover_data_checks']=data_checks.run(cur);conn.rollback()
            except Exception as exc:
                report['cutover_data_checks']=dict(status='INCOMPLETE',error=str(exc)[:1000])
            print(json.dumps(dict(group='T3_CUTOVER_DATA_CHECKS',**report['cutover_data_checks']),default=str),flush=True)
    except Exception as exc:
        report.update(status='INCOMPLETE',error=str(exc)[:4000],traceback=traceback.format_exc()[-4000:])
    finally:
        subprocess.run(['docker','exec','supabase_db_cp5-local','dropdb','-U','supabase_admin','--if-exists','--force',
                        '--maintenance-db=template1','cp6_rollback'],check=True)
        with psycopg.connect(boundary.PRIMARY_ADMIN) as conn,conn.cursor() as cur:
            report['primary_unchanged']=primary is not None and boundary.snapshot(cur)==primary
            report['auth_users_after']=cur.execute('select count(*) from auth.users').fetchone()[0]
        save()
    gate=dict(installed=report['status'] in ('ALL_STAGES_INSTALLED','BROWSER_PASS'),primary_unchanged=report.get('primary_unchanged') is True)
    if mode!='browser':
        gate.update(backup_restore_drill=report.get('backup_restore_drill') in DRILL_OK,
                    security_advisors=advisors_ok(((report.get('security_advisors') or {}).get('delta')) or {}))
    report['gate']=gate;save()
    print(json.dumps(dict(t3_package_run={k:v for k,v in report.items() if k not in('stages','security_advisors')}),default=str)[:8000],flush=True)
    # Every outcome is recorded above; the job is red unless every part of the gate holds (read the gate line in the log).
    assert all(gate.values()),(report['status'],gate,report.get('error'))
    if mode=='capture':
        # The capture job also compares with the committed package: a difference means the committed package is stale, so
        # the job is red; the new pins are in the log (T3_PINS_CHUNK) for the rebuild.
        assert (report.get('pins_reproduced') or {}).get('equal'),('T3_COMMITTED_PACKAGE_STALE',report.get('pins_reproduced'))


if __name__=='__main__':run(sys.argv[1])
