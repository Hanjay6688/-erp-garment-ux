"""AUDITOR RUNTIME PROBE 1 (independent auditor, blind phase 1). Probes the writer-built runtime itself:
identity of the installed candidate, whether every function body of the four T1 dev files is installed verbatim
(including AX, whose ax_verified checks only a marker), what escapes the per-case savepoint, how arbitrary status
strings and duplicate case ids are counted, and (LAST case) whether a commit through a second connection is caught.
Statuses: PASS / COUNTEREXAMPLE / INCOMPLETE only; every case records observed facts."""
import hashlib,json,os,re,subprocess,traceback
import psycopg
import cp6_aw_probe as awp
import cp6_ax_probe as axp
import cp6_ay_probe as ayp
import cp6_az_probe as azp
api,boundary=awp.api,awp.boundary
FROZEN='9add57ea8c2b6b2dc37c0134717d4d39ba30b5dc'
DEV={'AW':awp.AW_SQL,'AX':axp.AX_SQL,'AY':ayp.AY_SQL,'AZ':azp.AZ_SQL}

def functions_in(text):
    """(schema.name, body) for every CREATE OR REPLACE FUNCTION ... AS $function$ body $function$ in a dev file."""
    out=[]
    for m in re.finditer(r'(?is)create or replace function\s+([a-z_]+\.[a-z0-9_]+)\s*\((.*?)\)\s*(.*?)\bas \$function\$(.*?)\$function\$',text):
        out.append((m.group(1),m.group(4)))
    return out

def identity():
    api.admin(awp_cur)
    cur=awp_cur
    head=subprocess.check_output(['git','-C',str(azp.AUDITOR),'rev-parse','HEAD'],text=True).strip()
    tree=subprocess.check_output(['git','-C',str(azp.AUDITOR),'rev-parse','HEAD^{tree}'],text=True).strip()
    dirty=subprocess.check_output(['git','-C',str(azp.AUDITOR),'diff','HEAD','--name-only'],text=True).strip().splitlines()
    untracked=subprocess.check_output(['git','-C',str(azp.AUDITOR),'status','--porcelain','--untracked-files=normal'],text=True).strip().splitlines()[:12]
    writer_head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    db=cur.execute("select current_database(),current_user,session_user,current_setting('TimeZone'),now()::text,(statement_timestamp() at time zone 'Asia/Jakarta')::date::text,version()").fetchone()
    closed=cur.execute('select closed_through::text from erp.accounting_period_control where singleton_id=1').fetchone()[0]
    versions=[r[0] for r in cur.execute('select version from erp.schema_migrations order by version').fetchall()]
    stamps=[r[0] for r in cur.execute('select version from supabase_migrations.schema_migrations order by version').fetchall()]
    nfunc=cur.execute("select count(*) from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname in('erp','public')").fetchone()[0]
    dev_sha={k:hashlib.sha256(v.read_bytes()).hexdigest() for k,v in DEV.items()}
    ok=head==FROZEN and not dirty
    return dict(status='PASS' if ok else 'COUNTEREXAMPLE',auditor_head=head,auditor_tree=tree,auditor_tracked_dirty=dirty,auditor_untracked_sample=untracked,writer_cwd_head=writer_head,
                db=dict(database=db[0],current_user=db[1],session_user=db[2],timezone=db[3],now=db[4],today_jakarta=db[5],version=db[6][:60]),
                closed_through=closed,erp_schema_migrations_tail=versions[-8:],supabase_migrations_tail=stamps[-8:],erp_public_functions=nfunc,dev_sql_sha256=dev_sha,
                sys_path_head=[p for p in __import__('sys').path[:3]],expected='auditor_head==9add57e and no tracked file modified')

def installed_bodies():
    cur=awp_cur; api.admin(cur)
    result={};mismatch=[]
    for key,path in DEV.items():
        funcs=functions_in(path.read_text())
        rows=[]
        for name,body in funcs:
            schema,fname=name.split('.')
            found=cur.execute("select p.oid::regprocedure::text,p.prosrc from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname=%s and p.proname=%s",(schema,fname)).fetchall()
            same=[sig for sig,src in found if src==body]
            rows.append(dict(name=name,overloads=len(found),verbatim=bool(same)))
            if not same:mismatch.append(dict(file=key,name=name,overloads=len(found),installed_sha=[hashlib.sha256(src.encode()).hexdigest()[:12] for _,src in found],dev_sha=hashlib.sha256(body.encode()).hexdigest()[:12]))
        result[key]=dict(functions=len(funcs),verbatim=sum(1 for r in rows if r['verbatim']),rows=rows)
    return dict(status='PASS' if not mismatch else 'COUNTEREXAMPLE',files=result,mismatch=mismatch,expected='every function body of the four dev files installed verbatim (prosrc equal)')

def leak_set():
    cur=awp_cur
    cur.execute("select set_config('cp6audit.leak','armed',false)")
    cur.execute('select pg_advisory_lock(424242)')
    cur.execute("create temp table cp6audit_tmp(x int)")
    n=cur.execute("select nextval(pg_get_serial_sequence('erp.journal_entries','id')) is not null").fetchone()[0] if cur.execute("select pg_get_serial_sequence('erp.journal_entries','id') is not null").fetchone()[0] else None
    return dict(status='PASS',armed=True,setting=cur.execute("select current_setting('cp6audit.leak',true)").fetchone()[0],
                advisory_locks=cur.execute("select count(*) from pg_locks where locktype='advisory' and objid=424242 and pid=pg_backend_pid()").fetchone()[0],
                temp_table=cur.execute("select to_regclass('pg_temp.cp6audit_tmp') is not null").fetchone()[0],journal_entries_serial=n,
                expected='arms a session GUC, a session advisory lock and a temp table inside the case savepoint')

def leak_check():
    cur=awp_cur
    setting=cur.execute("select current_setting('cp6audit.leak',true)").fetchone()[0]
    locks=cur.execute("select count(*) from pg_locks where locktype='advisory' and objid=424242 and pid=pg_backend_pid()").fetchone()[0]
    tmp=cur.execute("select to_regclass('pg_temp.cp6audit_tmp') is not null").fetchone()[0]
    leaked=[k for k,v in dict(session_guc=(setting=='armed'),advisory_lock=(locks>0),temp_table=bool(tmp)).items() if v]
    return dict(status='COUNTEREXAMPLE' if leaked else 'PASS',setting=setting,advisory_locks=locks,temp_table=tmp,leaked=leaked,
                expected='nothing armed by the previous case survives rollback-to-savepoint; any survivor is a leak channel between cases')

def status_vocab():
    return dict(status='OK',expected="a status that is neither PASS/FAIL/COUNTEREXAMPLE/INCOMPLETE: read how the group counts it (it must not make the group PASS)",observed='returned literal OK')

def dup_first():
    return dict(status='COUNTEREXAMPLE',expected='this id appears twice; the group report must keep BOTH results or refuse duplicate ids',observed='first occurrence (COUNTEREXAMPLE)')

def dup_second():
    return dict(status='PASS',expected='same id as the previous case; if the final report counts only this PASS the earlier COUNTEREXAMPLE is hidden',observed='second occurrence (PASS)')

def second_connection_commit():
    """LAST case: commits through a second connection to the same clone. The runtime must report full_boundary_restored=false
    for this case (INCOMPLETE) and the run must end INCOMPLETE; if it stays PASS the boundary check does not cover this table."""
    cur=awp_cur; api.admin(cur)
    before=cur.execute('select count(*) from erp.app_users').fetchone()[0]
    with psycopg.connect(boundary.PG,autocommit=True) as c2,c2.cursor() as k:
        k.execute("select current_database()")
        db=k.fetchone()[0]
        try:
            k.execute("create table if not exists public.cp6_audit_leak_marker(id int primary key, note text)")
            k.execute("insert into public.cp6_audit_leak_marker values(1,'auditor second-connection commit') on conflict do nothing")
            created='public.cp6_audit_leak_marker'
        except Exception as exc:
            created='refused: '+str(exc)[:200]
    seen=cur.execute("select to_regclass('public.cp6_audit_leak_marker') is not null").fetchone()[0]
    return dict(status='PASS',expected='runtime flags this case (full_boundary_restored=false) because a committed table now exists outside the savepoint',
                observed=dict(second_connection_db=db,created=created,visible_from_case_session=seen,app_users_before=before))

awp_cur=None
def cases(cur,today):
    global awp_cur
    awp_cur=cur
    def wrap(fn):
        def run():
            try:return fn()
            except Exception as exc:return dict(status='INCOMPLETE',error=str(exc)[:800],traceback=traceback.format_exc()[-1500:])
        return run
    return [('RT:IDENTITY',wrap(identity)),
            ('RT:INSTALLED_BODIES_VERBATIM',wrap(installed_bodies)),
            ('RT:LEAK_ARM',wrap(leak_set)),
            ('RT:LEAK_CHECK',wrap(leak_check)),
            ('RT:STATUS_VOCAB_OK',wrap(status_vocab)),
            ('RT:DUP_ID',wrap(dup_first)),
            ('RT:DUP_ID',wrap(dup_second)),
            ('RT:SECOND_CONNECTION_COMMIT_LAST',wrap(second_connection_commit))]
