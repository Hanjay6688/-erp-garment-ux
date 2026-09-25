#!/usr/bin/env python3
"""T3 rollback of the release package's AW, AX, AY, AZ and BA: pre-use only, exact restore, reverse order.

AW..BA exist only as files of the combined release package (supabase/release/cp6-t3); each keeps a private rollback
capsule of the functions it replaces and a before/after hash of every erp table and of both ledgers, but the package
shipped no rollback file for them (MANIFEST rollbacks NOT_TESTED). This script adds them, the way AO..AV's rollbacks work:
closed and drained admission, own ledger row with the exact statements sha256 and no successor, the installed catalog
pinned, every historical and package capsule checked, data and both ledgers unchanged since the install (otherwise the
rollback is refused: pre-use only), the capsule's functions restored, the new objects dropped without CASCADE, both
ledger rows removed, and the predecessor's catalog, data and ledgers proved again before commit.

Modes (database modes run only on the local disposable clone cp6_rollback, asserted by the release applier):
  capture OUT.json   install the committed package on the aligned clone at AB; around AW..BA, run each file once in a
                     rolled-back transaction to learn its catalog delta (added, changed and removed objects of the
                     guard's own object query), describe every changed non-function object in the state before, then
                     install it. Prints the capture in the log (T3_ROLLBACK_CAPTURE_CHUNK lines and its sha256).
  build CAPTURE.json [BLOB_SHA256]  write supabase/release/cp6-t3-rollbacks/*.rollback.sql and ROLLBACKS.json from the
                     committed release files and the capture (no database); every delta object must be dropped or
                     restored by a reviewed kind, anything else stops the build.
  cycle OUT.json     install the package, then: refusals that change nothing (out of order, open admission), two cycles
                     of BA, AZ, AY, AX, AW rollback (each state equal to the one before that file's install) and reinstall,
                     the original AV rollback on the release chain (expected refusal: it pins the test chain), and a
                     refusal after a committed data change.
Label: T3_PREP (not release evidence). The AC..AV rollbacks of the release package (re-pinned for the hosted-faithful
chain) are not built here: NOT_BUILT.
"""
from pathlib import Path
import json,os,re,subprocess,sys,traceback

ROOT=Path(__file__).resolve().parents[1]
# Same module order as scripts/cp6_t3_package_run.py: the frozen writer's scripts (working directory) first, then these.
sys.path.insert(0,str(Path.cwd()/'scripts'))
sys.path.append(str(ROOT/'scripts'))
import cp6_t3_release_package as package
import cp6_t3_awx_release as awx

RELEASE=ROOT/'supabase/release/cp6-t3'
OUTDIR=ROOT/'supabase/release/cp6-t3-rollbacks'
CAPTURE=ROOT/'docs/evidence/cp6-t3/rollback_capture.json'
KEYS=['AW','AX','AY','AZ','BA']
FILES={f['key']:f for f in awx.FILES}
sha=package.sha
q=package.quote
# The one reviewed non-function change of the package: AX teaches the payroll view and check constraint the FG_REPAIR
# source. Their state before AX is restored from the capture; any other changed object stops the build.
RESTORABLE={'AX':{'VIEW:erp.v_payroll_eligible_work_lines','CONSTRAINT:erp.payroll_work_items.payroll_work_items_source_type_check'}}
LEDGER_HASH=awx.LEDGER_HASH
DATA=awx.DATA
PROBE_ROW=("insert into erp.audit_logs(entity_type,entity_id,action,new_data,change_reason) "
           "values('cp6_t3_rollback_probe',gen_random_uuid(),'INSERT','{}'::jsonb,'T3 rollback: committed data change after install')")


def manifest():
    files={f['key']:f for f in json.loads((RELEASE/'MANIFEST.json').read_text())['files']}
    for key in KEYS:assert key in files,('T3_ROLLBACK_PACKAGE_WITHOUT',key)
    return files


def release_text(entry):
    text=(ROOT/entry['file']).read_text()
    assert sha(text)==entry['package_sha256'],('T3_PACKAGE_FILE_DRIFT',entry['key'])
    return text


def capsule(key):return 'erp.cp6_v2620%s_rollback_capsule'%key.lower()


def rollback_path(entry):return OUTDIR/('%s_%s.rollback.sql'%(entry['stamp'],entry['name']))


# ---------------------------------------------------------------- build (no database)

def split_key(key):
    kind,ident=key.split(':',1)
    return kind,ident


def drops(key,cap):
    """The statements that remove what the file added, in order (no CASCADE), and the added keys they cover."""
    added=cap['added'];detail=cap['added_detail']
    tables=[i for k,i in map(split_key,added) if k=='RELATION' and detail[k+':'+i]=='r']
    # New tables go in reverse creation order (a later table may reference an earlier one); they are exactly the file's.
    created=['erp.'+t for t in FILES[key]['new_tables']]
    assert sorted(tables)==sorted(created),('T3_ROLLBACK_NEW_TABLES',key,tables,created)
    tables=created[::-1]
    views=[i for k,i in map(split_key,added) if k=='RELATION' and detail[k+':'+i]=='v']
    functions=[i for k,i in map(split_key,added) if k=='FUNCTION']
    covered=set()
    out=[]
    for k in added:
        kind,ident=split_key(k)
        if kind=='TRIGGER':
            schema,table,name=ident.split('.')
            if '%s.%s'%(schema,table) in tables:covered.add(k);continue
            out.append('drop trigger %s on %s.%s;'%(name,schema,table));covered.add(k)
    restore_at=len(out)
    for v in views:out.append('drop view %s;'%v);covered.add('RELATION:'+v)
    for t in tables:out.append('drop table %s;'%t);covered.add('RELATION:'+t)
    for f in functions:out.append('drop function %s;'%f);covered.add('FUNCTION:'+f)
    # Objects that live inside a dropped relation go with it (columns, constraints, indexes, triggers, policies, the
    # view text of a dropped view); nothing else may remain uncovered.
    owned=tuple('%s.'%r for r in tables+views)
    for k in added:
        kind,ident=split_key(k)
        if k in covered:continue
        if kind in ('COLUMN','CONSTRAINT','INDEX','TRIGGER','POLICY') and ident.startswith(owned):covered.add(k);continue
        if kind=='INDEX':
            # An index name is not qualified by its table in the key; the capture records the table it belongs to.
            if detail.get(k) and detail[k] in tables:covered.add(k);continue
        if kind=='VIEW' and ident in views:covered.add(k);continue
    missing=sorted(set(added)-covered)
    assert not missing,('T3_ROLLBACK_UNCOVERED_ADDITIONS',key,missing)
    return out,restore_at


def restores(key,cap):
    """Statements that put back the reviewed non-function objects the file changed."""
    changed=[k for k in cap['changed'] if not k.startswith('FUNCTION:')]
    assert set(changed)<=RESTORABLE.get(key,set()),('T3_ROLLBACK_UNREVIEWED_CHANGE',key,sorted(set(changed)-RESTORABLE.get(key,set())))
    out=[]
    for k in changed:
        kind,ident=split_key(k);before=cap['before'][k];after=cap['after'][k]
        if kind=='VIEW':
            viewdef=before['viewdef'].rstrip().rstrip(';').rstrip()
            options=before['reloptions'] or []
            if (after['reloptions'] or [])!=options and after['reloptions']:
                out.append('alter view %s reset (%s);'%(ident,','.join(o.split('=')[0] for o in after['reloptions'])))
            out.append('create or replace view %s%s as\n%s;'%(ident,' with (%s)'%','.join(options) if options else '',viewdef))
        elif kind=='CONSTRAINT':
            schema,table,name=ident.split('.')
            out.append('alter table %s.%s drop constraint %s;'%(schema,table,name))
            out.append('alter table %s.%s add constraint %s %s;'%(schema,table,name,before['definition']))
        else:raise AssertionError(('T3_ROLLBACK_RESTORE_KIND',key,k))
    return out


def rollback_sql(key,entry,text,cap,capture_sha):
    f=FILES[key];c=capsule(key);code=key
    blocks=package.catalog_blocks(text)
    assert len(blocks)==2 and blocks[0]['code']==code+'_PREDECESSOR_CATALOG_DRIFT' and blocks[1]['code']==code+'_INSTALLED_CATALOG_DRIFT'
    assert cap['package_sha256']==entry['package_sha256'],('T3_ROLLBACK_CAPTURE_FOR_OTHER_PACKAGE',key)
    changed_functions=sorted(k.split(':',1)[1] for k in cap['changed'] if k.startswith('FUNCTION:'))
    assert changed_functions==sorted(f['replaced']),('T3_ROLLBACK_CAPSULE_IS_NOT_THE_CHANGE',key,changed_functions)
    assert not cap['removed'],('T3_ROLLBACK_FILE_REMOVED_OBJECTS',key,cap['removed'])
    drop,restore_at=drops(key,cap)
    body=drop[:restore_at]+restores(key,cap)+drop[restore_at:]
    installed=blocks[1]['text'].replace("raise exception '%s_INSTALLED_CATALOG_DRIFT'"%code,"raise exception '%s_ROLLBACK_CATALOG_DRIFT'"%code)
    restored=blocks[0]['text'].replace("raise exception '%s_PREDECESSOR_CATALOG_DRIFT'"%code,"raise exception '%s_RESTORED_CATALOG_DRIFT'"%code)
    assert installed!=blocks[1]['text'] and restored!=blocks[0]['text']
    tables=("select c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace\n"
            "  where n.nspname='erp' and c.relkind in('r','p') and c.relname<>all(array[%s]::text[]) order by 1")
    s=("-- CP6 %s rollback: exact pre-use restore of the T3 release package to its predecessor; closed, drained maintenance required.\n"
       "begin;\n"
       "-- Built by scripts/cp6_t3_rollback.py from %s (sha256 %s) and docs/evidence/cp6-t3/rollback_capture.json (sha256 %s).\n"
       "set local lock_timeout='10s';set local statement_timeout='240s';set local timezone='UTC';set local search_path='';\n"
       "set local role postgres;\n")%(key,entry['file'],entry['package_sha256'],capture_sha)
    s+=awx.block(text,'closed_admission')
    s+="lock table erp.schema_migrations,supabase_migrations.schema_migrations in share row exclusive mode;\n"
    s+=awx.block(text,'lock_business')
    s+=("do $platform$ begin\n if not exists(select 1 from erp.schema_migrations where version=%(v)s)\n"
        "  or (select count(*) from supabase_migrations.schema_migrations where name=%(n)s)<>1\n"
        "  or not exists(select 1 from supabase_migrations.schema_migrations where version=%(s)s and name=%(n)s\n"
        "   and encode(extensions.digest(convert_to(array_to_string(statements,E'\\n'),'UTF8'),'sha256'),'hex')=%(h)s)\n"
        "  or exists(select 1 from supabase_migrations.schema_migrations where version>%(s)s)\n"
        " then raise exception '%(k)s_ROLLBACK_PLATFORM_OR_SUCCESSOR';end if;\nend $platform$;\n")%dict(
        v=q(f['version']),n=q(entry['name']),s=q(entry['stamp']),h=q(entry['package_sha256']),k=code)
    s+=awx.block(text,'prior_platform')+installed+awx.block(text,'historical_capsules')+awx.block(text,'prior_capsules')
    s+=awx.block(text,'capsule_guard')
    s+="create temporary table cp6_t3_rollback_boundary on commit drop as select boundary_snapshot from %s limit 1;\n"%c
    s+=("do $pre_use$ declare v_table text;v_hash jsonb;v_after jsonb;b jsonb; begin\n"
        " select boundary_snapshot into b from pg_temp.cp6_t3_rollback_boundary;\n v_after:='{}'::jsonb;\n"
        " for v_table in %(tables)s loop\n  %(data)s\n  v_after:=v_after||jsonb_build_object(v_table,v_hash);\n end loop;\n"
        " if b is null or v_after is distinct from b->'after' then raise exception '%(k)s_POST_USE_ROLLBACK_REFUSED';end if;\n"
        " if (select %(lh)s from supabase_migrations.schema_migrations t where version<>%(s)s) is distinct from b->>'platform_before'\n"
        "  or (select %(lh)s from erp.schema_migrations t where version<>%(v)s) is distinct from b->>'markers_before'\n"
        " then raise exception '%(k)s_PRIOR_HISTORY_DRIFT';end if;\nend $pre_use$;\n")%dict(
        tables=tables%("'schema_migrations','%s'"%c.split('.')[1]),data=DATA,k=code,lh=LEDGER_HASH,s=q(entry['stamp']),v=q(f['version']))
    s+=("do $restore_function$ declare r record; begin\n for r in select object_definition from %(c)s order by object_regidentity loop execute r.object_definition;end loop;\n"
        " if exists(select 1 from %(c)s x join pg_proc p on p.oid=to_regprocedure(x.object_regidentity)\n"
        "  where encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex') is distinct from x.definition_sha256\n"
        "   or array(select a::text from unnest(p.proacl)a order by a::text) is distinct from x.acl_snapshot\n"
        "   or pg_get_userbyid(p.proowner) is distinct from x.owner_snapshot)\n"
        "  or (select count(*) from %(c)s x where to_regprocedure(x.object_regidentity) is not null)<>%(n)d\n"
        " then raise exception '%(k)s_FUNCTION_RESTORE_MISMATCH';end if;\nend $restore_function$;\n")%dict(c=c,n=len(f['replaced']),k=code)
    s+=''.join(x+'\n' for x in body)
    s+="drop table %s;\n"%c
    s+="delete from erp.schema_migrations where version=%s;\n"%q(f['version'])
    s+="delete from supabase_migrations.schema_migrations where version=%s and name=%s;\n"%(q(entry['stamp']),q(entry['name']))
    s+=restored
    s+=("do $restored_data$ declare v_table text;v_hash jsonb;v_before jsonb;b jsonb; begin\n"
        " select boundary_snapshot into b from pg_temp.cp6_t3_rollback_boundary;\n v_before:='{}'::jsonb;\n"
        " for v_table in %(tables)s loop\n  %(data)s\n  v_before:=v_before||jsonb_build_object(v_table,v_hash);\n end loop;\n"
        " if v_before is distinct from b->'before'\n"
        "  or (select %(lh)s from supabase_migrations.schema_migrations t) is distinct from b->>'platform_before'\n"
        "  or (select %(lh)s from erp.schema_migrations t) is distinct from b->>'markers_before'\n"
        " then raise exception '%(k)s_EXACT_RESTORE_FAILED';end if;\nend $restored_data$;\n")%dict(
        tables=tables%"'schema_migrations'",data=DATA,lh=LEDGER_HASH,k=code)
    s+="commit;\n"
    assert 'cascade' not in s.lower().replace('on delete cascade','')
    return s


def build(capture_path=CAPTURE,expected_blob=None,write=True):
    raw=Path(capture_path).read_text()
    cap=json.loads(raw)
    blob=json.dumps(cap,separators=(',',':'))
    assert cap['format']=='CP6_T3_ROLLBACK_CAPTURE_V1' and cap['status']=='CAPTURED',('T3_ROLLBACK_CAPTURE_STATUS',cap.get('status'))
    if expected_blob:assert sha(blob)==expected_blob,('T3_ROLLBACK_CAPTURE_BLOB_SHA256',sha(blob))
    files=manifest();out={}
    for key in KEYS:
        entry=files[key];text=release_text(entry)
        out[key]=(rollback_path(entry),rollback_sql(key,entry,text,cap['files'][key],sha(blob)))
    index=dict(format='CP6_T3_ROLLBACKS_V1',label='T3_PREP',production_go=False,release_evidence=False,
               order=','.join(reversed(KEYS))+' (reverse install order; each only while it is the last file and before any use)',
               capture=dict(file=os.path.relpath(Path(capture_path).resolve(),ROOT),blob_sha256=sha(blob)),
               builder_sha256=sha(Path(__file__).read_bytes()),
               not_built='AC..AV rollbacks re-pinned for the release package (the files in supabase/rollbacks pin the test chain)',
               files=[dict(key=k,file=str(p.relative_to(ROOT)),sha256=sha(t),package_file=files[k]['file'],
                           package_sha256=files[k]['package_sha256']) for k,(p,t) in out.items()])
    if write:
        OUTDIR.mkdir(parents=True,exist_ok=True)
        for p,t in out.values():p.write_text(t)
        (OUTDIR/'ROLLBACKS.json').write_text(json.dumps(index,indent=2)+'\n')
        print(json.dumps({k:dict(file=str(p.relative_to(ROOT)),sha256=sha(t)) for k,(p,t) in out.items()},indent=1))
    return out,index


# ---------------------------------------------------------------- database side (disposable clone only)

def object_map(cur,block):
    package.session(cur)
    return cur.execute('select (\n%s\n)'%block['inner']).fetchone()[0]


def describe(cur,key):
    package.session(cur)
    kind,ident=split_key(key)
    if kind=='VIEW':
        row=cur.execute("select pg_get_viewdef(%s::regclass,false),(select reloptions from pg_class where oid=%s::regclass)",(ident,ident)).fetchone()
        return dict(viewdef=row[0],reloptions=row[1])
    if kind=='CONSTRAINT':
        schema,table,name=ident.split('.')
        row=cur.execute("select pg_get_constraintdef(c.oid),c.contype::text,c.condeferrable,c.condeferred,c.convalidated from pg_constraint c "
                        "where c.conrelid=%s::regclass and c.conname=%s",('%s.%s'%(schema,table),name)).fetchone()
        return None if row is None else dict(definition=row[0],contype=row[1],deferrable=row[2],deferred=row[3],validated=row[4])
    if kind=='RELATION':
        row=cur.execute("select relkind::text,reloptions from pg_class where oid=to_regclass(%s)",(ident,)).fetchone()
        return None if row is None else dict(relkind=row[0],reloptions=row[1])
    if kind=='INDEX':
        row=cur.execute("select format('%%I.%%I',n.nspname,t.relname) from pg_index i join pg_class c on c.oid=i.indexrelid "
                        "join pg_class t on t.oid=i.indrelid join pg_namespace n on n.oid=t.relnamespace where c.oid=to_regclass(%s)",(ident,)).fetchone()
        return None if row is None else dict(table=row[0])
    return None


def dry_run(applier,text,block):
    """Run a package file in a transaction that is always rolled back; return the object map after it."""
    class Done(Exception):pass
    def work(conn):
        try:
            with conn.transaction(),conn.cursor() as cur:
                cur.execute(package.sql_body(text),prepare=False)
                after=object_map(cur,block)
                raise Done(after)
        except Done as done:
            return done.args[0]
    return applier.closed(work)


def dry_describe(applier,text,keys):
    class Done(Exception):pass
    def work(conn):
        try:
            with conn.transaction(),conn.cursor() as cur:
                cur.execute(package.sql_body(text),prepare=False)
                raise Done({k:describe(cur,k) for k in keys})
        except Done as done:
            return done.args[0]
    return applier.closed(work)


def print_chunks(tag,blob):
    for i in range(0,len(blob),6000):print('%s_CHUNK %04d %s'%(tag,i//6000,blob[i:i+6000]),flush=True)
    print('%s_SHA256 %s %d'%(tag,sha(blob),len(blob)),flush=True)


def capture(out):
    import psycopg
    applier=package.Applier(package.CLONE,os.environ['CP6_ADMISSION_CONTROL_PGURL'])
    files=json.loads((RELEASE/'MANIFEST.json').read_text())['files']
    report=dict(format='CP6_T3_ROLLBACK_CAPTURE_V1',label='T3_PREP_ROLLBACK_CAPTURE',status='INCOMPLETE',files={},
                production_go=False,release_evidence=False)
    try:
        for f in files:
            text=(ROOT/f['file']).read_text();assert sha(text)==f['package_sha256'],('T3_PACKAGE_FILE_DRIFT',f['key'])
            row=dict(stamp=f['stamp'],name=f['name'],closed=f['closed_admission'])
            if f['key'] in KEYS:
                block=package.catalog_blocks(text)[0]
                with psycopg.connect(package.CLONE) as conn,conn.cursor() as cur:
                    before=object_map(cur,block);conn.rollback()
                after=dry_run(applier,text,block)
                added=sorted(set(after)-set(before));removed=sorted(set(before)-set(after))
                changed=sorted(k for k in before if k in after and before[k]!=after[k])
                other=[k for k in changed+removed if not k.startswith('FUNCTION:')]
                with psycopg.connect(package.CLONE) as conn,conn.cursor() as cur:
                    described_before={k:describe(cur,k) for k in other};conn.rollback()
                detail_keys=[k for k in added if k.startswith(('RELATION:','INDEX:'))]
                described_after=dry_describe(applier,text,sorted(set(other+detail_keys)))
                report['files'][f['key']]=dict(package_sha256=f['package_sha256'],added=added,changed=changed,removed=removed,
                    added_detail={k:(described_after[k]['relkind'] if k.startswith('RELATION:') else (described_after[k] or {}).get('table'))
                                  for k in detail_keys},
                    before=described_before,after={k:described_after[k] for k in other},
                    counts=dict(before=len(before),after=len(after)))
                print(json.dumps(dict(group='T3_ROLLBACK_CAPTURE',key=f['key'],added=len(added),changed=changed,removed=removed)),flush=True)
            applier.install(row,text)
        report['status']='CAPTURED'
    except Exception as exc:
        report.update(error=str(exc)[:3000],traceback=traceback.format_exc()[-3000:])
    finally:
        Path(out).write_text(json.dumps(report,indent=2,default=str)+'\n')
        print_chunks('T3_ROLLBACK_CAPTURE',json.dumps(report,separators=(',',':'),default=str))
    return report


STATE_TABLES="select c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='erp' and c.relkind in('r','p') and c.relname<>'schema_migrations' order by 1"
FULL="select count(*),encode(extensions.digest(convert_to(coalesce(string_agg(h,',' order by h),''),'UTF8'),'sha256'),'hex') from(select encode(extensions.digest(convert_to((to_jsonb(t))::text,'UTF8'),'sha256'),'hex') h from erp.%I t)s"
STABLE="select count(*),encode(extensions.digest(convert_to(coalesce(string_agg(h,',' order by h),''),'UTF8'),'sha256'),'hex') from(select encode(extensions.digest(convert_to((to_jsonb(t)-array['captured_at','boundary_snapshot'])::text,'UTF8'),'sha256'),'hex') h from erp.%I t)s"


def state(url,block):
    """Catalog object map (the AZ guard's query, which leaves every package capsule out by name), every erp table's rows
    (full, and for rollback capsules without their capture time and boundary), and both ledgers."""
    import psycopg
    from psycopg import sql
    with psycopg.connect(url) as conn,conn.cursor() as cur:
        catalog=object_map(cur,block)
        tables=[r[0] for r in cur.execute(STATE_TABLES).fetchall()]
        full={};stable={}
        for t in tables:
            full[t]=list(cur.execute(sql.SQL(FULL.replace('%I','{}')).format(sql.Identifier(t))).fetchone())
            stable[t]=list(cur.execute(sql.SQL((STABLE if t.endswith('_rollback_capsule') else FULL).replace('%I','{}')).format(sql.Identifier(t))).fetchone())
        platform=[list(r) for r in cur.execute("select version,name,encode(extensions.digest(convert_to(array_to_string(statements,E'\\n'),'UTF8'),'sha256'),'hex') "
                                               "from supabase_migrations.schema_migrations order by version").fetchall()]
        markers=[list(r) for r in cur.execute('select version,description from erp.schema_migrations order by version').fetchall()]
        conn.rollback()
    return dict(catalog=catalog,full=full,stable=stable,platform=platform,markers=markers)


def diff(a,b,strict=True):
    out={}
    for part in ('catalog','full' if strict else 'stable','platform','markers'):
        x,y=a[part],b[part]
        if x==y:continue
        if isinstance(x,dict):
            out[part]=dict(only_before=sorted(set(x)-set(y))[:20],only_after=sorted(set(y)-set(x))[:20],
                           differ=sorted(k for k in x if k in y and x[k]!=y[k])[:20])
        else:out[part]=dict(before=x[-3:],after=y[-3:])
    return out


def cycle(out):
    import psycopg
    applier=package.Applier(package.CLONE,os.environ['CP6_ADMISSION_CONTROL_PGURL'])
    files=json.loads((RELEASE/'MANIFEST.json').read_text())['files']
    rollbacks=json.loads((OUTDIR/'ROLLBACKS.json').read_text())
    report=dict(label='T3_PREP_ROLLBACK_CYCLE',status='INCOMPLETE',checks=[],production_go=False,release_evidence=False)
    def save():Path(out).write_text(json.dumps(report,indent=2,default=str)+'\n')
    def check(name,ok,**detail):
        row=dict(check=name,status='PASS' if ok else 'FAIL',**detail);report['checks'].append(row);save()
        print(json.dumps(dict(group='T3_ROLLBACK_CYCLE',**row),default=str)[:6000],flush=True)
        return ok
    try:
        # The committed rollback files are exactly what the builder writes from the committed capture.
        built,index=build(write=False)
        committed={r['key']:r for r in rollbacks['files']}
        same=all((ROOT/committed[k]['file']).read_text()==t and sha(t)==committed[k]['sha256'] for k,(p,t) in built.items())
        check('ROLLBACK_FILES_REBUILT_IDENTICALLY',same and index['files']==rollbacks['files'])
        text={f['key']:release_text(f) for f in files}
        rb={k:(ROOT/committed[k]['file']).read_text() for k in KEYS}
        block=package.catalog_blocks(text[KEYS[-1]])[1]
        before={};after={}
        for f in files:
            if f['key'] in KEYS:before[f['key']]=state(package.CLONE,block)
            applier.install(dict(stamp=f['stamp'],name=f['name'],closed=f['closed_admission']),text[f['key']])
            if f['key'] in KEYS:after[f['key']]=state(package.CLONE,block)
        check('PACKAGE_INSTALLED',True,files=len(files))
        def closed_run(sql_text):
            def work(conn):
                with conn.transaction(),conn.cursor() as cur:cur.execute(package.sql_body(sql_text),prepare=False)
            applier.closed(work)
        def refusal(name,run,expected):
            s0=state(package.CLONE,block);error=None
            try:run()
            except psycopg.Error as exc:error=exc
            s1=state(package.CLONE,block)
            ok=error is not None and error.sqlstate=='P0001' and expected in str(error) and not diff(s0,s1)
            return check(name,ok,expected=expected,error=None if error is None else str(error)[:500],
                         sqlstate=getattr(error,'sqlstate',None),changed=diff(s0,s1))
        def open_run(sql_text):
            with psycopg.connect(package.CLONE,autocommit=True) as conn:
                try:conn.execute(sql_text,prepare=False)
                finally:
                    try:conn.execute('rollback')
                    except psycopg.Error:pass
        last,previous=KEYS[-1],KEYS[-2]
        refusal('REFUSED_OUT_OF_ORDER_%s_WHILE_%s_INSTALLED'%(previous,last),lambda:closed_run(rb[previous]),previous+'_ROLLBACK_PLATFORM_OR_SUCCESSOR')
        refusal('REFUSED_OPEN_ADMISSION',lambda:open_run(rb[last]),'PACKAGE_REQUIRES_CLOSED_DRAINED_DATABASE')
        for n in (1,2):
            for key in reversed(KEYS):
                error=None
                try:closed_run(rb[key])
                except psycopg.Error as exc:error=exc
                now=state(package.CLONE,block)
                # Cycle 1 restores every row exactly; in cycle 2 the earlier capsules were written again by the reinstall,
                # so their capture time differs and they are compared without it (full rows at AV, where none remains).
                strict=n==1 or key=='AW'
                d=diff(before[key],now,strict=strict)
                check('CYCLE_%d_ROLLBACK_%s_RESTORES_PREDECESSOR'%(n,key),error is None and not d,
                      error=None if error is None else str(error)[:800],differences=d,strict=strict)
            if n==2:
                original=sorted((ROOT/'supabase/rollbacks').glob('*_erp_v2_6_20av_*.rollback.sql'))
                if original:
                    refusal('ORIGINAL_AV_ROLLBACK_REFUSED_ON_RELEASE_CHAIN',lambda:closed_run(original[0].read_text()),'AV_ROLLBACK')
            for f in [x for x in files if x['key'] in KEYS]:
                error=None
                try:applier.install(dict(stamp=f['stamp'],name=f['name'],closed=True),text[f['key']])
                except psycopg.Error as exc:error=exc
                d=diff(after[f['key']],state(package.CLONE,block),strict=False)
                check('CYCLE_%d_REINSTALL_%s'%(n,f['key']),error is None and not d,error=None if error is None else str(error)[:800],differences=d)
        with psycopg.connect(package.CLONE) as conn:conn.execute(PROBE_ROW)
        refusal('REFUSED_AFTER_COMMITTED_DATA_CHANGE',lambda:closed_run(rb[last]),last+'_POST_USE_ROLLBACK_REFUSED')
        report['status']='PASS' if all(c['status']=='PASS' for c in report['checks']) else 'FAIL'
    except Exception as exc:
        report.update(status='INCOMPLETE',error=str(exc)[:3000],traceback=traceback.format_exc()[-3000:])
    finally:save()
    return report


def run(mode,out_name):
    """Workflow entry: the same clone discipline as scripts/cp6_t3_package_run.py (primary database unchanged, the
    clone dropped afterwards)."""
    import psycopg
    auditor=ROOT
    import cp6_aw_probe as awp
    boundary=awp.boundary
    assert os.environ.get('CP6_AR_CONFIRM')=='cp6_rollback' and os.environ.get('CP6_DATABASE_CONTAINER')=='supabase_db_cp5-local'
    outdir=auditor/'cp6-proof/t3';outdir.mkdir(parents=True,exist_ok=True)
    primary=None;result=dict(status='INCOMPLETE')
    try:
        with psycopg.connect(boundary.PRIMARY_ADMIN) as conn,conn.cursor() as cur:primary=boundary.snapshot(cur)
        with psycopg.connect(boundary.ADMIN) as conn,conn.cursor() as cur:
            last=cur.execute("select max(version) from erp.schema_migrations where version like 'v2.6.20a_'").fetchone()[0]
        assert last=='v2.6.20ab',('T3_CLONE_NOT_AT_AB',last)
        result=(capture if mode=='capture' else cycle)(outdir/out_name)
    finally:
        subprocess.run(['docker','exec','supabase_db_cp5-local','dropdb','-U','supabase_admin','--if-exists','--force',
                        '--maintenance-db=template1','cp6_rollback'],check=True)
        with psycopg.connect(boundary.PRIMARY_ADMIN) as conn,conn.cursor() as cur:
            unchanged=primary is not None and boundary.snapshot(cur)==primary
    print(json.dumps(dict(t3_rollback=dict(mode=mode,status=result.get('status'),primary_unchanged=unchanged,
                                           error=result.get('error')))),flush=True)
    assert unchanged,'T3_PRIMARY_CHANGED'
    assert result.get('status')==('CAPTURED' if mode=='capture' else 'PASS'),(result.get('status'),result.get('error'))


def auto_mode():
    """capture until the committed capture and rollback files cover every key of the committed package, cycle after."""
    try:cap=json.loads(CAPTURE.read_text());index=json.loads((OUTDIR/'ROLLBACKS.json').read_text())
    except FileNotFoundError:return 'capture'
    files=manifest()
    covered=all(k in cap.get('files',{}) and cap['files'][k]['package_sha256']==files[k]['package_sha256'] for k in KEYS)
    return 'cycle' if covered and [f['key'] for f in index['files'] if f['key'] in KEYS]==KEYS else 'capture'


if __name__=='__main__':
    mode=sys.argv[1] if len(sys.argv)>1 else ''
    if mode=='auto-mode':print(auto_mode())
    elif mode=='build':build(sys.argv[2] if len(sys.argv)>2 else CAPTURE,sys.argv[3] if len(sys.argv)>3 else None)
    elif mode in ('capture','cycle'):run(mode,'T3_ROLLBACK_%s.json'%mode.upper())
    else:raise SystemExit(__doc__)
