"""AUDITOR RUNTIME PROBE 2 (independent auditor, blind phase 1). Does boundary.snapshot see a leak into an erp business
table made through a second connection? Do sequences survive rollback-to-savepoint? Do writer probe modules import from
the baseline (writer/scripts) instead of the candidate (auditor/scripts)? LAST case: a plain COMMIT on the case connection.
Statuses: PASS / COUNTEREXAMPLE / INCOMPLETE only."""
import hashlib,json,os,sys,traceback,uuid
import psycopg
import cp6_aw_probe as awp
import cp6_ax_probe as axp
import cp6_ay_probe as ayp
import cp6_az_probe as azp
api,boundary=awp.api,awp.boundary
C=None

def module_origins():
    names=['cp6_aw_probe','cp6_ax_probe','cp6_ay_probe','cp6_az_probe','cp6_au_r1_probe','cp6_ao_ap_installed','cp6_successor_regression','cp6_au_runtime','cp6_av_runtime','cp6_au_trial','cp6_au_browser_fixture','cp6_v2620al_import_review','cp6_ac_independent_audit','cp6_successor_specs','cp6_as_cases','cp6_at_cases','cp6_au_cases']
    out={}
    for n in names:
        m=sys.modules.get(n)
        if m is None:
            try:m=__import__(n)
            except Exception as exc:out[n]='IMPORT_ERROR '+str(exc)[:80];continue
        f=getattr(m,'__file__','')
        out[n]=('writer' if '/writer/' in f else 'auditor' if '/auditor/' in f else f)+':'+hashlib.sha256(open(f,'rb').read()).hexdigest()[:12]
    from_writer=[n for n,v in out.items() if v.startswith('writer')]
    return dict(status='PASS',origins=out,from_writer_baseline=from_writer,expected='informational: which helper modules come from the baseline checkout (ca7f095) because writer/scripts precedes auditor/scripts on sys.path')

def sequence_leak_arm():
    cur=C; api.admin(cur)
    seqs=[r[0] for r in cur.execute("select sequence_schema||'.'||sequence_name from information_schema.sequences where sequence_schema='erp' order by 1 limit 3").fetchall()]
    vals={}
    for s in seqs:
        vals[s]=cur.execute("select last_value from %s"%s).fetchone()[0]
        cur.execute("select nextval(%s)",(s,))
    return dict(status='PASS',sequences=seqs,last_value_before=vals,expected='advances erp sequences inside the case savepoint')

def sequence_leak_check():
    cur=C; api.admin(cur)
    seqs=[r[0] for r in cur.execute("select sequence_schema||'.'||sequence_name from information_schema.sequences where sequence_schema='erp' order by 1 limit 3").fetchall()]
    vals={s:cur.execute("select last_value,is_called from %s"%s).fetchone() for s in seqs}
    return dict(status='PASS',sequences_after=vals,expected='informational: PostgreSQL never rolls sequences back; compare with the previous case (is_called true / last_value advanced = leak channel not covered by snapshot)')

def erp_leak_second_connection():
    cur=C; api.admin(cur)
    cid=str(uuid.uuid4())
    with psycopg.connect(boundary.PG,autocommit=True) as c2,c2.cursor() as k:
        try:
            k.execute("insert into erp.contractors(id,contractor_code,contractor_name,contractor_type,attendance_required) values(%s,%s,%s,'MANDOR',false)",(cid,'AUDIT-LEAK-'+cid[:8],'auditor leak probe'))
            created='erp.contractors row '+cid
        except Exception as exc:
            created='refused: '+str(exc)[:300]
    seen=cur.execute("select count(*) from erp.contractors where id=%s::uuid",(cid,)).fetchone()[0]
    return dict(status='PASS',expected='runtime must flag this case: full_boundary_restored=false and run INCOMPLETE, because a committed erp row exists outside the savepoint',observed=dict(created=created,visible_from_case_session=seen))

def erp_leak_visible_next_case():
    cur=C; api.admin(cur)
    n=cur.execute("select count(*) from erp.contractors where contractor_name='auditor leak probe'").fetchone()[0]
    return dict(status='COUNTEREXAMPLE' if n else 'PASS',rows_visible=n,expected='0 rows if the previous case was isolated; >0 means the leak reached the next case')

def commit_on_case_connection_last():
    cur=C; api.admin(cur)
    try:
        cur.execute('commit')
        return dict(status='PASS',observed='COMMIT accepted on the case connection inside the group transaction',expected='runtime must refuse or flag; the following rollback-to-savepoint should now fail')
    except Exception as exc:
        return dict(status='PASS',observed='refused: '+str(exc)[:300],expected='refusal or INCOMPLETE')

def cases(cur,today):
    global C; C=cur
    def wrap(fn):
        def run():
            try:return fn()
            except Exception as exc:return dict(status='INCOMPLETE',error=str(exc)[:800],traceback=traceback.format_exc()[-1200:])
        return run
    return [('RT2:MODULE_ORIGINS',wrap(module_origins)),
            ('RT2:SEQ_ARM',wrap(sequence_leak_arm)),
            ('RT2:SEQ_CHECK',wrap(sequence_leak_check)),
            ('RT2:ERP_LEAK_SECOND_CONNECTION',wrap(erp_leak_second_connection)),
            ('RT2:ERP_LEAK_VISIBLE_NEXT',wrap(erp_leak_visible_next_case)),
            ('RT2:COMMIT_ON_CASE_CONNECTION_LAST',wrap(commit_on_case_connection_last))]
