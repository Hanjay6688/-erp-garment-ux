"""T3 backup and restore drill on the disposable candidate (owner: backup and restore drill in a separate environment).

Source: the clone the T3 install used (cp6_rollback, candidate installed, harness seed plus a small business fixture).
  1. pg_dump -Fc of the whole source database, inside the disposable container (never hosted).
  2. createdb from template0 and pg_restore as the cluster admin; every restore error is recorded as it is.
  3. Compare source and restored: the G-01 catalog fingerprint per kind (schemas erp and public), and per table of erp
     the row count and an md5 of the ordered rows.
  4. Run the same read-only engine call on both (AW preflight for yesterday) and compare the answers.
The operational backup (where and how often, encryption) is CP7C; this drill proves the dump restores into an
identical ERP. RESTORED_SAME_MEANING means identical rows and engine answers, and every catalog difference is a known
same-meaning form: a varchar IN list re-parsed by the restore (the G-01 mechanism), or pg_cron, which can exist only in
the database named postgres. Label: T3_PREP (not release evidence).
"""
from pathlib import Path
import hashlib,json,os,re,subprocess,sys,time
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


# Per-object text for the kinds whose stored text a dump round trip can change.
TEXTS={
 'constraint':"""select n.nspname||'.'||c.relname||'.'||co.conname,pg_get_constraintdef(co.oid) from pg_constraint co
   join pg_class c on c.oid=co.conrelid join pg_namespace n on n.oid=c.relnamespace where n.nspname in('erp','public')""",
 'index':"""select n.nspname||'.'||ic.relname,pg_get_indexdef(i.indexrelid) from pg_index i join pg_class ic on ic.oid=i.indexrelid
   join pg_namespace n on n.oid=ic.relnamespace where n.nspname in('erp','public')""",
 'view':"""select n.nspname||'.'||c.relname,pg_get_viewdef(c.oid) from pg_class c join pg_namespace n on n.oid=c.relnamespace
   where c.relkind in('v','m') and n.nspname in('erp','public')""",
 'extension':"""select x.extname,x.extversion||' in '||n.nspname from pg_extension x join pg_namespace n on n.oid=x.extnamespace""",
}
# pg_dump writes a varchar IN list as (ARRAY['a'::character varying, ...])::text[]; parsing that text again stores
# ARRAY[('a'::character varying)::text, ...] (the G-01 finding). Both become ARRAY<a,...> before comparing.
STORED=re.compile(r"\(ARRAY\[((?:'[^']*'::character varying(?:, )?)+)\]\)::text\[\]")
REPARSED=re.compile(r"ARRAY\[((?:\('[^']*'::character varying\)::text(?:, )?)+)\]")


def same_meaning(a,b):
    norm=lambda t:REPARSED.sub(lambda m:'ARRAY<%s>'%','.join(re.findall(r"'([^']*)'",m.group(1))),
                               STORED.sub(lambda m:'ARRAY<%s>'%','.join(re.findall(r"'([^']*)'",m.group(1))),t))
    return a is not None and b is not None and norm(a)==norm(b)


def texts(db,kind):
    with psycopg.connect(url(db)) as conn,conn.cursor() as cur:
        conn.read_only=True
        return dict(cur.execute(TEXTS[kind]).fetchall())


def classify(kinds):
    """Every differing object with its class: VARCHAR_IN_LIST_REPARSE (same meaning) or UNCLASSIFIED (both texts kept)."""
    out={}
    for kind in kinds:
        if kind not in TEXTS:out[kind]=dict(detail='NOT_COMPARED_PER_OBJECT');continue
        a,b=texts(SOURCE,kind),texts(TARGET,kind)
        rows=[]
        for key in sorted(set(a)|set(b)):
            if a.get(key)==b.get(key):continue
            if kind=='extension' and key=='pg_cron' and b.get(key) is None:cls='PG_CRON_ONLY_IN_DATABASE_POSTGRES'
            else:cls='VARCHAR_IN_LIST_REPARSE' if same_meaning(a.get(key),b.get(key)) else 'UNCLASSIFIED'
            row=dict(object=key,cls=cls)
            if cls=='UNCLASSIFIED':row.update(source=(a.get(key) or '')[:600],restored=(b.get(key) or '')[:600])
            rows.append(row)
        out[kind]=dict(differing=len(rows),by_class={c:sum(r['cls']==c for r in rows) for c in {r['cls'] for r in rows}},objects=rows)
    return out


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
        report['catalog']['objects']=classify(sorted(report['catalog']['differ']))
        a,b=data_hashes(SOURCE),data_hashes(TARGET)
        report['data']=dict(tables=len(a),rows=sum(v['rows'] for v in a.values()),
                            differ={t:dict(source=a.get(t),restored=b.get(t)) for t in sorted(set(a)|set(b)) if a.get(t)!=b.get(t)})
        e1,e2=engine(SOURCE,day),engine(TARGET,day)
        report['engine']=dict(day=str(day),equal=e1==e2,source_status=e1 and e1.get('status'),restored_status=e2 and e2.get('status'))
        with psycopg.connect(url(SOURCE)) as conn,conn.cursor() as cur:
            # pg_cron can live only in the database named postgres, so a restore into another database drops its jobs.
            has_cron=cur.execute("select to_regclass('cron.job') is not null").fetchone()[0]
            report['source_cron_jobs']=cur.execute('select count(*) from cron.job').fetchone()[0] if has_cron else None
        known={'VARCHAR_IN_LIST_REPARSE','PG_CRON_ONLY_IN_DATABASE_POSTGRES'}
        classes={o['cls'] for v in report['catalog']['objects'].values() for o in v.get('objects',[])}
        explained=all('objects' in v for v in report['catalog']['objects'].values()) and classes<=known
        same=not report['data']['differ'] and report['engine']['equal']
        report['status']=('RESTORED_IDENTICAL' if same and not report['catalog']['differ'] else
                          'RESTORED_SAME_MEANING' if same and explained else 'DIFFERENCES_RECORDED')
    except Exception as exc:
        report.update(status='INCOMPLETE',error=str(exc)[:3000])
    finally:
        docker('dropdb','-U','supabase_admin','--if-exists','--force',TARGET,check=False)
        docker('rm','-f',DUMP,check=False)
        Path(out).write_text(json.dumps(report,indent=2,default=str)+'\n')
    brief=dict(report);cat=report.get('catalog') or {}
    brief['catalog']=dict(match=cat.get('match'),differ=cat.get('differ'),
        objects={k:{x:v.get(x) for x in ('differing','by_class','detail')}|dict(unclassified=[o for o in v.get('objects',[]) if o['cls']=='UNCLASSIFIED'][:10])
                 for k,v in (cat.get('objects') or {}).items()})
    print(json.dumps(dict(t3_backup_restore_drill={k:brief.get(k) for k in ('status','dump','restore','catalog','data','engine','source_cron_jobs','error')}),default=str)[:20000],flush=True)
    return report


if __name__=='__main__':
    r=run(sys.argv[1]);raise SystemExit(0 if r['status']!='INCOMPLETE' else 1)
