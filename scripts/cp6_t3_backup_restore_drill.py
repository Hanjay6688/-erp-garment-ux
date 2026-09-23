"""T3 backup and restore drill on the disposable candidate (owner: backup and restore drill in a separate environment).

Source: the clone the T3 install used (cp6_rollback, candidate installed, harness seed plus a small business fixture).
  1. pg_dump -Fc of the whole source database, inside the disposable container (never hosted).
  2. createdb from template0 and pg_restore as the cluster admin; every restore error is recorded as it is.
  3. Compare source and restored: the G-01 catalog fingerprint per kind (schemas erp and public), and per table of erp
     the row count and an md5 of the ordered rows.
  4. Run the same read-only engine call on both (AW preflight for yesterday) and compare the answers.
The operational backup (where and how often, encryption) is CP7C; this drill proves the dump restores into an
identical ERP. Label: T3_PREP (not release evidence).
"""
from pathlib import Path
import hashlib,json,os,subprocess,sys,time
import psycopg
from psycopg import sql

AUDITOR=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(Path.cwd()/'scripts'))
sys.path.append(str(AUDITOR/'scripts'))
import cp6_g01_fingerprint as fp
import cp6_aw_probe as awp

boundary=awp.boundary
CONTAINER='supabase_db_cp5-local'
SOURCE='cp6_rollback'
TARGET='cp6_restore_drill'
DUMP='/tmp/cp6_t3_drill.dump'


def docker(*args,check=True):
    return subprocess.run(['docker','exec',CONTAINER,*args],capture_output=True,text=True,check=check)


def url(db):return boundary.ADMIN.rsplit('/',1)[0]+'/'+db


def data_hashes(db):
    with psycopg.connect(url(db)) as conn,conn.cursor() as cur:
        conn.read_only=True
        tables=[r[0] for r in cur.execute("""select c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace
            where n.nspname='erp' and c.relkind in('r','p') order by 1""").fetchall()]
        out={}
        for t in tables:
            n,h=cur.execute(f"""select count(*),md5(coalesce(string_agg(x::text,chr(10) order by x::text),''))
                from erp.{sql.Identifier(t).as_string(conn)} x""").fetchone()
            out[t]=dict(rows=n,md5=h)
        return out


def catalog(db):
    with psycopg.connect(url(db)) as conn,conn.cursor() as cur:
        conn.read_only=True
        return cur.execute(fp.SUMMARY).fetchone()[0]


def engine(db,day):
    with psycopg.connect(url(db)) as conn,conn.cursor() as cur:
        awp.api.admin(cur)
        if cur.execute("select to_regprocedure('erp.accounting_close_preflight_v1(date)') is null").fetchone()[0]:return None
        r=cur.execute('select erp.accounting_close_preflight_v1(%s)',(day,)).fetchone()[0]
        conn.rollback();return r


def run(out,installed=None):
    report=dict(label='T3_PREP_BACKUP_RESTORE_DRILL',status='INCOMPLETE',source=SOURCE,target=TARGET,installed_stages=installed,
                production_go=False,release_evidence=False)
    try:
        t0=time.monotonic()
        d=docker('pg_dump','-U','supabase_admin','-d',SOURCE,'-Fc','-f',DUMP,check=False)
        report['dump']=dict(exit=d.returncode,stderr=d.stderr[-3000:],seconds=round(time.monotonic()-t0,1),
                            bytes=int(docker('stat','-c','%s',DUMP).stdout.strip() or 0) if d.returncode==0 else None)
        assert d.returncode==0,'DRILL_DUMP_FAILED'
        docker('dropdb','-U','supabase_admin','--if-exists','--force',TARGET)
        docker('createdb','-U','supabase_admin','-T','template0',TARGET)
        t1=time.monotonic()
        r=docker('pg_restore','-U','supabase_admin','-d',TARGET,'--no-password',DUMP,check=False)
        errors=[l for l in r.stderr.splitlines() if 'error' in l.lower()]
        report['restore']=dict(exit=r.returncode,seconds=round(time.monotonic()-t1,1),error_count=len(errors),errors=errors[:80])
        with psycopg.connect(url(SOURCE)) as conn,conn.cursor() as cur:
            day=cur.execute("select (statement_timestamp() at time zone 'Asia/Jakarta')::date-1").fetchone()[0]
        src,dst=catalog(SOURCE),catalog(TARGET)
        report['catalog']=dict(match=sorted(k for k in src if src.get(k)==dst.get(k)),
                               differ={k:dict(source=src.get(k),restored=dst.get(k)) for k in sorted(set(src)|set(dst)) if src.get(k)!=dst.get(k)})
        a,b=data_hashes(SOURCE),data_hashes(TARGET)
        report['data']=dict(tables=len(a),rows=sum(v['rows'] for v in a.values()),
                            differ={t:dict(source=a.get(t),restored=b.get(t)) for t in sorted(set(a)|set(b)) if a.get(t)!=b.get(t)})
        e1,e2=engine(SOURCE,day),engine(TARGET,day)
        report['engine']=dict(day=str(day),equal=e1==e2,source_status=e1 and e1.get('status'),restored_status=e2 and e2.get('status'))
        ok=not report['catalog']['differ'] and not report['data']['differ'] and report['engine']['equal']
        report['status']='RESTORED_IDENTICAL' if ok else 'DIFFERENCES_RECORDED'
    except Exception as exc:
        report.update(status='INCOMPLETE',error=str(exc)[:3000])
    finally:
        docker('dropdb','-U','supabase_admin','--if-exists','--force',TARGET,check=False)
        docker('rm','-f',DUMP,check=False)
        Path(out).write_text(json.dumps(report,indent=2,default=str)+'\n')
    print(json.dumps(dict(t3_backup_restore_drill={k:report.get(k) for k in ('status','dump','restore','catalog','data','engine','error')}),default=str)[:12000],flush=True)
    return report


if __name__=='__main__':
    r=run(sys.argv[1]);raise SystemExit(0 if r['status']!='INCOMPLETE' else 1)
