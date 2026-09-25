#!/usr/bin/env python3
"""T3 combined release package: the pending migrations AC..AV re-pinned for the hosted-faithful baseline.

Owner decision G-01 (23 Sep 2026), option (b): align the test chain with hosted Enteng (done by cp6_g01_align.py) and
let the combined release package take its pins from the aligned chain; the old migration files stay unchanged and no
guard is loosened. On the aligned chain the frozen path refuses at AC (run 35911530080, AC_VIEW_PREDECESSOR_MISMATCH:
erp.v_payroll_nota_browser), because some guards pin text that exists only in the test fixture chain. Every guard stays
in place with the same strictness; only these expected values change, each one recorded with the reason:

  * AC_VIEW: AC pins the source text of erp.v_payroll_nota_browser. Hosted keeps the IN-list form of two varchar
    lists (G-01); the pinned source becomes the IN-list source whose parse gives the hosted text (from the read-only
    hosted metadata), with its sha256 and the restore statement sha256.
  * LEDGER: every later migration pins the sha256 of its predecessor's ledger statements; a re-pinned predecessor
    gets the sha256 of its re-pinned text (a cascade through the package).
  * CATALOG: AO..AV pin the object count and fingerprint of the whole erp/public catalog before and after each
    install; they are recomputed on the aligned chain with each guard's own query.
  * CAPSULE: AO..AV pin a hash of every historical rollback capsule; a capsule whose content differs on the aligned
    chain (AC's relation capsule keeps the view source above) is recomputed with the guard's own query.

Modes (the chain modes run only on the local disposable clone cp6_rollback, asserted):
  capture PINS.json  build AC'..AV' step by step on the aligned clone at AB, capturing each live value, and install each
                     re-pinned file with the same applier as install; then AW/AX T1. Prints the pins in the log.
  build PINS.json [BLOB_SHA256]  write supabase/release/cp6-t3/*.sql and MANIFEST.json from the original files and the pins
                     (no DB): the pins must cover every package file in order, every substitution must be one reviewed kind
                     replacing exactly one guard pin of its file (LEDGER and AC_VIEW are derived again), and the pins blob
                     sha256 printed by the capture is recorded (and checked when given).
  install OUT.json   install the committed package on the aligned clone at AB, file by file, recording PASS or refusal.
Label: T3_PREP (not release evidence). Rollback files of the package are NOT_TESTED.
"""
from pathlib import Path
import difflib,hashlib,json,os,re,sys,time,traceback

ROOT=Path(__file__).resolve().parents[1]
MIGRATIONS=ROOT/'supabase/migrations'
RELEASE=ROOT/'supabase/release/cp6-t3'
META=ROOT/'docs/evidence/cp6-g01/hosted_alignment_metadata.json'
KEYS=['ac','ad','ae','af','ag','ah','ai','aj','ak','al','am','an','ao','ap','aq','ar','as','at','au','av','aw','ax','ay','az','ba']
# AW, AX, AY, AZ and BA release candidates are built by scripts/cp6_t3_awx_release.py (T1 bodies wrapped with AO..AV guards).
SOURCES=ROOT/'supabase/release/cp6-t3-src'
CLONE='postgresql://postgres:postgres@127.0.0.1:54322/cp6_rollback'
VIEW='erp.v_payroll_nota_browser'

CATALOG=re.compile(r"do \$catalog_guard\$\ndeclare actual jsonb;fingerprint text;object_count bigint;\nbegin\n select \* into actual from \(\n"
                   r"(?P<inner>.*?)\n\) catalog;\n select count\(\*\),(?P<agg>encode\(.*?\)) into object_count,fingerprint from "
                   r"jsonb_each_text\(actual\);\n if object_count<>(?P<count>\d+) or fingerprint is distinct from '(?P<fp>[0-9a-f]{64})' then\n"
                   r"  raise exception '(?P<code>[A-Z_]+)';\n end if;\nend \$catalog_guard\$;\n",re.S)
HISTORY=re.compile(r"do \$historical_capsules\$\ndeclare r record;actual text;\nbegin\n for r in select \* from jsonb_each_text\('(?P<json>\{[^']*\})'::jsonb\) loop\n"
                   r"  execute format\(\$caps\$(?P<query>.*?)\$caps\$,r\.key\) into actual;\n",re.S)


def sha(data):return hashlib.sha256(data.encode() if isinstance(data,str) else data).hexdigest()


def package():
    rows=[]
    for key in KEYS:
        [path]=sorted((SOURCES if key in('aw','ax','ay','az','ba') else MIGRATIONS).glob('*_erp_v2_6_20%s_*.sql'%key))
        stamp,name=re.match(r'(\d{14})_(.+)\.sql$',path.name).groups()
        text=path.read_text()
        rows.append(dict(key=key.upper(),path=str(path.relative_to(ROOT)),stamp=stamp,name=name,
                         closed='$closed_admission$' in text,source_sha256=sha(text)))
    return rows


def sql_literal(text,start):
    """Value of the single-quoted SQL literal whose opening quote is at start, and the index after its closing quote."""
    assert text[start]=="'"
    out=[];k=start+1
    while True:
        c=text[k]
        if c=="'":
            if text[k+1]=="'":out.append("'");k+=2;continue
            return ''.join(out),k+1
        out.append(c);k+=1


def quote(value):return "'"+value.replace("'","''")+"'"


def apply_subs(text,subs):
    for s in subs:
        n=text.count(s['old'])
        assert n==s['count'],('SUBSTITUTION_COUNT',s['kind'],s.get('what'),n,s['count'])
        text=text.replace(s['old'],s['new'])
    return text


def ac_view_subs(text):
    """AC_VIEW: the pinned source of erp.v_payroll_nota_browser, rebuilt from the read-only hosted text."""
    sys.path.insert(0,str(ROOT/'scripts'))
    import cp6_g01_align as align
    meta=json.loads(META.read_text())
    [hosted]=[v for v in meta['views'] if v['view']==VIEW]
    assert hashlib.md5(hosted['def'].encode()).hexdigest()==hosted['md5']
    head="('%s',"%VIEW
    assert text.count(head)==1
    i=text.index(head)+len(head)
    before,k=sql_literal(text,i)
    assert text[k]==','
    before_sha,k2=sql_literal(text,k+1)
    assert before_sha==sha(before)
    options=','.join(hosted['reloptions'])
    restore_old=sha('CREATE OR REPLACE VIEW %s WITH (%s) AS\n%s;'%(VIEW,options,before))
    assert text.count("'%s'"%restore_old)==1,'AC_RESTORE_PIN_NOT_UNIQUE'
    source=align.to_source(hosted['def'].strip()).rstrip(';').rstrip()
    # Only the two varchar IN lists may differ from the pinned test-chain source (G-01 view finding).
    changed=[l for l in difflib.ndiff(before.splitlines(),source.splitlines()) if l[:2] in('- ','+ ')]
    assert len(changed)==4 and all(' = ANY (ARRAY[' in l for l in changed if l[:2]=='- ') \
        and all(' IN (' in l for l in changed if l[:2]=='+ '),('AC_VIEW_UNEXPECTED_DIFFERENCE',changed)
    restore_new=sha('CREATE OR REPLACE VIEW %s WITH (%s) AS\n%s;'%(VIEW,options,source))
    return [dict(kind='AC_VIEW',what=VIEW+' source',old=head+quote(before)+','+quote(before_sha),
                 new=head+quote(source)+','+quote(sha(source)),count=1),
            dict(kind='AC_VIEW',what=VIEW+' restore statement sha256',old="'%s'"%restore_old,new="'%s'"%restore_new,count=1)]


def ledger_subs(text,renamed):
    """LEDGER: the sha256 of every re-pinned predecessor's statements."""
    return [dict(kind='LEDGER',what=r['key'],old=r['old'],new=r['new'],count=text.count(r['old']))
            for r in renamed if r['old'] in text]


def catalog_blocks(text):
    return [dict(start=m.start(),end=m.end(),inner=m.group('inner'),agg=m.group('agg'),count=int(m.group('count')),
                 fingerprint=m.group('fp'),code=m.group('code'),text=m.group(0)) for m in CATALOG.finditer(text)]


def catalog_query(block):
    return 'select count(*),%s from jsonb_each_text((\n%s\n))'%(block['agg'],block['inner'])


def catalog_sub(block,count,fingerprint):
    old="if object_count<>%d or fingerprint is distinct from '%s' then\n  raise exception '%s';"%(block['count'],block['fingerprint'],block['code'])
    new="if object_count<>%d or fingerprint is distinct from '%s' then\n  raise exception '%s';"%(count,fingerprint,block['code'])
    return dict(kind='CATALOG',what=block['code'],old=old,new=new,count=1)


CATALOG_SUB=re.compile(r"if object_count<>\d+ or fingerprint is distinct from '[0-9a-f]{64}' then\n  raise exception '(?P<code>[A-Z_]+)';\Z")
CAPSULE_SUB=re.compile(r'"(?P<key>[a-z0-9_]+_rollback_capsule)":"[0-9a-f]{64}"\Z')


def check_subs(row,text,subs):
    """Every recorded substitution is one of the four reviewed kinds and replaces exactly one guard pin of this file."""
    blocks=catalog_blocks(text);hist=history(text)
    catalog_old={catalog_sub(b,b['count'],b['fingerprint'])['old']:b['code'] for b in blocks}
    capsule_old={'"%s":"%s"'%(k,v):k for k,v in (hist['pins'].items() if hist else [])}
    for s in subs:
        assert s['kind'] in ('AC_VIEW','LEDGER','CATALOG','CAPSULE'),('T3_SUB_KIND',row['key'],s['kind'])
        assert s['kind']!='AC_VIEW' or row['key']=='AC',('T3_SUB_AC_VIEW_OUTSIDE_AC',row['key'])
        if s['kind']=='CATALOG':
            o=CATALOG_SUB.match(s['old']);n=CATALOG_SUB.match(s['new'])
            assert o and n and o['code']==n['code']==catalog_old.get(s['old']) and s['count']==1,('T3_SUB_CATALOG',row['key'],s.get('what'))
        if s['kind']=='CAPSULE':
            o=CAPSULE_SUB.match(s['old']);n=CAPSULE_SUB.match(s['new'])
            assert o and n and o['key']==n['key']==capsule_old.get(s['old'])==s['what'] and s['count']==1,('T3_SUB_CAPSULE',row['key'],s.get('what'))
    final=apply_subs(text,subs)
    after=catalog_blocks(final)
    assert [b['code'] for b in after]==[b['code'] for b in blocks] and len(after)==(2 if row['closed'] else 0),('T3_SUB_CATALOG_SHAPE',row['key'])
    assert (history(final) is None)==(hist is None) and (hist is None or list(history(final)['pins'])==list(hist['pins'])),('T3_SUB_HISTORY_SHAPE',row['key'])
    return final


def history(text):
    m=HISTORY.search(text)
    return None if m is None else dict(pins=json.loads(m.group('json')),json=m.group('json'),query=m.group('query'))


# ---------------------------------------------------------------- database side (disposable clone only)

def session(cur):
    # The guards run with these settings (set local in every package file); catalog text depends on search_path.
    cur.execute("set local role postgres;set local search_path='';set local timezone='UTC'")


def live_catalog(cur,block):
    session(cur)
    return cur.execute(catalog_query(block)).fetchone()


def live_history(cur,query,keys):
    from psycopg import sql
    assert query.count('%I')==1 and query.count('%')==1
    session(cur)
    out={}
    for key in keys:
        left,right=query.split('%I')
        out[key]=cur.execute(sql.SQL(left)+sql.Identifier(key)+sql.SQL(right)).fetchone()[0]
    return out


def sql_body(text):
    """Unwrap only the reviewed top-level transaction (same rule as cp6_ao_ap_runtime.sql_body)."""
    lines=text.splitlines(keepends=True)
    assert lines[0].startswith('-- CP6 ') and lines[1]=='begin;\n' and lines[-1]=='commit;\n'
    return ''.join(lines[2:-1])


class Applier:
    """Install one package file the way the harness does: open files through psql semantics with their own
    transaction and a ledger row (statements = the whole file) afterwards; closed-admission files (AO..AV) inside a
    closed, drained clone with the ledger row in the same transaction, as the AO..AV runtimes do."""

    def __init__(self,pg,control):
        import psycopg
        import cp6_preuse_rollback_maintenance as core
        import cp6_ao_ap_maintenance as maintenance
        self.psycopg,self.core,self.maintenance=psycopg,core,maintenance
        assert pg==CLONE,'T3_PACKAGE_DISPOSABLE_CLONE_ONLY'
        self.database,_=core._validate_connections(pg,control)
        self.pg,self.control=pg,control

    def ledger(self,cur,row,text):
        cur.execute('insert into supabase_migrations.schema_migrations(version,name,statements) values(%s,%s,%s)',
                    (row['stamp'],row['name'],[text]))

    def open_install(self,row,text):
        with self.psycopg.connect(self.pg,autocommit=True,application_name='cp6-t3-package') as conn:
            conn.execute(text,prepare=False)
            with conn.transaction(),conn.cursor() as cur:self.ledger(cur,row,text)

    def closed(self,work):
        psycopg,core=self.psycopg,self.core
        from psycopg import sql
        with psycopg.connect(self.pg,autocommit=True,application_name='cp6-t3-package') as conn,\
             psycopg.connect(self.control,autocommit=True) as control:
            a=core._endpoint_snapshot(conn);b=core._endpoint_snapshot(control)
            assert a['database']==self.database and a['user']=='postgres' and b['user']=='cp6_maintenance_admission'
            assert all(a[k] and a[k]==b[k] for k in ('server_address','server_port','system_identifier'))
            control.execute(self.maintenance.LOCK)
            try:
                pid=core._scalar(conn,'select pg_backend_pid()')
                control.execute(sql.SQL('alter database {} with allow_connections false').format(sql.Identifier(self.database)))
                deadline=time.monotonic()+15
                while True:
                    others=control.execute('select pid from pg_stat_activity where datname=%s and pid<>%s',(self.database,pid)).fetchall()
                    if others:
                        assert time.monotonic()<deadline,('T3_PACKAGE_REQUIRES_DRAINED_CLONE',others)
                        time.sleep(.05);continue
                    try:
                        return work(conn)
                    except psycopg.Error as exc:
                        if exc.sqlstate!='P0001' or 'PACKAGE_REQUIRES_CLOSED_DRAINED_DATABASE' not in str(exc):raise
                        if time.monotonic()>=deadline:raise
                        time.sleep(.05)
            finally:
                control.execute(sql.SQL('alter database {} with allow_connections true').format(sql.Identifier(self.database)))
                control.execute(self.maintenance.UNLOCK)

    def closed_install(self,row,text):
        def work(conn):
            with conn.transaction(),conn.cursor() as cur:
                cur.execute(sql_body(text),prepare=False);self.ledger(cur,row,text)
        self.closed(work)

    def closed_capture(self,text,block):
        """Run the file without its installed catalog guard, read that guard's live value, and roll everything back."""
        class Captured(Exception):pass
        def work(conn):
            try:
                with conn.transaction(),conn.cursor() as cur:
                    cur.execute(sql_body(text.replace(block['text'],'',1)),prepare=False)
                    value=live_catalog(cur,block)
                    raise Captured(value)
            except Captured as done:
                return done.args[0]
        return self.closed(work)

    def install(self,row,text):
        (self.closed_install if row['closed'] else self.open_install)(row,text)


def capture(out):
    import psycopg
    control=os.environ['CP6_ADMISSION_CONTROL_PGURL']
    applier=Applier(CLONE,control)
    report=dict(label='T3_PREP_RELEASE_PACKAGE_CAPTURE',status='INCOMPLETE',files=[],production_go=False,release_evidence=False)
    renamed=[]
    try:
        for row in package():
            text=Path(ROOT/row['path']).read_text();subs=[]
            entry=dict(row,subs=subs,status='INCOMPLETE');report['files'].append(entry)
            if row['key']=='AC':subs+=ac_view_subs(text)
            subs+=ledger_subs(text,renamed)
            hist=history(text)
            if hist:
                with psycopg.connect(CLONE) as conn,conn.cursor() as cur:
                    live=live_history(cur,hist['query'],list(hist['pins']));conn.rollback()
                for key,value in hist['pins'].items():
                    if live[key]!=value:
                        subs.append(dict(kind='CAPSULE',what=key,old='"%s":"%s"'%(key,value),new='"%s":"%s"'%(key,live[key]),count=1))
            blocks=catalog_blocks(text)
            assert len(blocks)==(2 if row['closed'] else 0),('T3_CATALOG_GUARD_SHAPE',row['key'],len(blocks))
            if blocks:
                with psycopg.connect(CLONE) as conn,conn.cursor() as cur:
                    count,fingerprint=live_catalog(cur,blocks[0]);conn.rollback()
                if (count,fingerprint)!=(blocks[0]['count'],blocks[0]['fingerprint']):subs.append(catalog_sub(blocks[0],count,fingerprint))
                staged=apply_subs(text,subs)
                count,fingerprint=applier.closed_capture(staged,catalog_blocks(staged)[1])
                if (count,fingerprint)!=(blocks[1]['count'],blocks[1]['fingerprint']):subs.append(catalog_sub(blocks[1],count,fingerprint))
            final=apply_subs(text,subs)
            entry['package_sha256']=sha(final)
            try:
                applier.install(row,final);entry['status']='PASS'
            except Exception as exc:
                entry.update(status='REFUSED' if getattr(exc,'sqlstate',None)=='P0001' else 'ERROR',error=str(exc)[:3000]);raise
            if final!=text:renamed.append(dict(key=row['key'],old=row['source_sha256'],new=entry['package_sha256']))
            print(json.dumps(dict(group='T3_PACKAGE_CAPTURE',key=row['key'],status=entry['status'],
                                  subs=[dict(kind=s['kind'],what=s['what']) for s in subs]),default=str),flush=True)
        report['status']='CAPTURED_AND_INSTALLED'
    except Exception as exc:
        report.update(status='REFUSED' if any(f.get('status')=='REFUSED' for f in report['files']) else 'INCOMPLETE',
                      error=str(exc)[:3000],traceback=traceback.format_exc()[-3000:])
    finally:
        Path(out).write_text(json.dumps(report,indent=2,default=str)+'\n')
        pins=dict(format='CP6_T3_RELEASE_PINS_V1',status=report['status'],
                  files=[{k:f.get(k) for k in ('key','path','stamp','name','closed','source_sha256','package_sha256','subs','status')}
                         for f in report['files']])
        blob=json.dumps(pins,separators=(',',':'))
        # The pins are printed in the log in numbered chunks so they can be committed without the artifact store.
        for i in range(0,len(blob),6000):print('T3_PINS_CHUNK %04d %s'%(i//6000,blob[i:i+6000]),flush=True)
        print('T3_PINS_SHA256 %s %d'%(sha(blob),len(blob)),flush=True)
    return report


def build(pins_path,expected_blob=None):
    """Write the committed package from the original files and the recorded substitutions (no database)."""
    pins=json.loads(Path(pins_path).read_text())
    assert pins['format']=='CP6_T3_RELEASE_PINS_V1' and pins['status']=='CAPTURED_AND_INSTALLED'
    # The pins must cover the whole package, in order; the blob sha256 is the one the capture printed in its log.
    rows={r['key']:r for r in package()}
    assert [f['key'] for f in pins['files']]==list(rows),('T3_PINS_DO_NOT_COVER_THE_PACKAGE',[f['key'] for f in pins['files']])
    blob=json.dumps(pins,separators=(',',':'))
    if expected_blob:assert sha(blob)==expected_blob,('T3_PINS_BLOB_SHA256',sha(blob))
    RELEASE.mkdir(parents=True,exist_ok=True)
    manifest=dict(format='CP6_T3_RELEASE_PACKAGE_V1',label='T3_PREP',decision='G-01 option (b), owner 23 Sep 2026',files=[],
                  production_go=False,release_evidence=False,rollbacks='NOT_TESTED',
                  pins=dict(file=os.path.relpath(Path(pins_path).resolve(),ROOT),blob_sha256=sha(blob),blob_bytes=len(blob)))
    renamed=[]
    for f in pins['files']:
        row=rows[f['key']];text=(ROOT/row['path']).read_text()
        assert sha(text)==f['source_sha256']==row['source_sha256'],('T3_SOURCE_DRIFT',f['key'])
        expected=[s for s in f['subs'] if s['kind']=='LEDGER']
        assert expected==ledger_subs(text,renamed),('T3_LEDGER_CASCADE_MISMATCH',f['key'])
        if f['key']=='AC':assert [s for s in f['subs'] if s['kind']=='AC_VIEW']==ac_view_subs(text)
        final=check_subs(row,text,f['subs'])
        assert sha(final)==f['package_sha256'],('T3_PACKAGE_SHA_MISMATCH',f['key'])
        target=RELEASE/Path(row['path']).name
        target.write_text(final)
        if final!=text:renamed.append(dict(key=f['key'],old=f['source_sha256'],new=f['package_sha256']))
        manifest['files'].append(dict(key=f['key'],file=str(target.relative_to(ROOT)),stamp=row['stamp'],name=row['name'],
            closed_admission=row['closed'],source=row['path'],source_sha256=row['source_sha256'],package_sha256=sha(final),
            substitutions=[dict(kind=s['kind'],what=s['what'],count=s['count']) for s in f['subs']]))
    (RELEASE/'MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps(dict(files=len(manifest['files']),changed=len(renamed)),indent=1))


def install(out):
    """Install the committed package on the aligned clone at AB; each file records PASS or its exact refusal."""
    control=os.environ['CP6_ADMISSION_CONTROL_PGURL']
    applier=Applier(CLONE,control)
    manifest=json.loads((RELEASE/'MANIFEST.json').read_text())
    report=dict(label='T3_PREP_RELEASE_PACKAGE_INSTALL',status='INCOMPLETE',files=[],production_go=False,release_evidence=False)
    try:
        for f in manifest['files']:
            text=(ROOT/f['file']).read_text()
            assert sha(text)==f['package_sha256'],('T3_PACKAGE_FILE_DRIFT',f['key'])
            row=dict(stamp=f['stamp'],name=f['name'],closed=f['closed_admission'])
            try:
                applier.install(row,text);entry=dict(key=f['key'],status='PASS')
            except Exception as exc:
                # Only a guard's own refusal (raise exception, SQLSTATE P0001) is a REFUSED file; anything else is an error.
                entry=dict(key=f['key'],status='REFUSED' if getattr(exc,'sqlstate',None)=='P0001' else 'ERROR',error=str(exc)[:3000])
            report['files'].append(entry);print(json.dumps(dict(group='T3_PACKAGE_INSTALL',**entry),default=str),flush=True)
            if entry['status']!='PASS':break
        report['status']='ALL_FILES_INSTALLED' if len(report['files'])==len(manifest['files']) and all(
            f['status']=='PASS' for f in report['files']) else ('REFUSED' if report['files'][-1]['status']=='REFUSED' else 'INCOMPLETE')
    except Exception as exc:
        report.update(status='INCOMPLETE',error=str(exc)[:3000],traceback=traceback.format_exc()[-3000:])
    finally:
        Path(out).write_text(json.dumps(report,indent=2,default=str)+'\n')
    return report


if __name__=='__main__':
    mode=sys.argv[1]
    if mode=='plan':print(json.dumps(package(),indent=1))
    elif mode=='capture':raise SystemExit(0 if capture(sys.argv[2])['status']=='CAPTURED_AND_INSTALLED' else 1)
    elif mode=='build':build(sys.argv[2],sys.argv[3] if len(sys.argv)>3 else None)
    elif mode=='install':raise SystemExit(0 if install(sys.argv[2])['status']=='ALL_FILES_INSTALLED' else 1)
    else:raise SystemExit(__doc__)
