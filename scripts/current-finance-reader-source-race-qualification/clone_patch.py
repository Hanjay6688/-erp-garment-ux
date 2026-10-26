"""Temporary committed DDL only in the isolated cp6_rollback qualification database.

The prior rollback experiment cannot test a fresh transaction's snapshot while its
DDL is uncommitted. This fixture installs the same exact bodies, commits in the
disposable database, then restores every original definition and full catalog.
This is not a product installer or an approved migration.
"""
from pathlib import Path
from hashlib import sha256
import importlib.util

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
def load(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
reuse=load('source_race_exact_reuse_bodies',ROOT/'scripts/current-finance-check-reuse-diagnostic/reuse.py')
opening=reuse.reader
REPORT_UNIT='cp7_finance_capture.report_unit(jsonb)'

def definition(cur,signature):
    return cur.execute('select pg_get_functiondef(%s::regprocedure)',(signature,)).fetchone()[0]

def held_report_definition(original,key):
    assert original.startswith('CREATE OR REPLACE FUNCTION cp7_finance_capture.report_unit(')
    assert key.startswith('CP7:FINANCE_READER_RACE:')and all(c.isalnum()or c in':-_'for c in key)
    anchor='begin\n select cp7_finance.workspace('
    assert original.count(anchor)==1,'REPORT_UNIT_HOLD_ANCHOR_CHANGED'
    inserted="begin\n perform pg_advisory_xact_lock(hashtextextended('"+key+"',0));\n select cp7_finance.workspace("
    value=original.replace(anchor,inserted,1)
    assert value.replace(inserted,anchor,1)==original
    return value

def install(cur,catalog,key):
    assert cur.connection.info.host in('localhost','127.0.0.1')and cur.connection.info.port==54322
    assert cur.execute('select current_database()').fetchone()==('cp6_rollback',)
    assert cur.execute('select to_regprocedure(%s)',(opening.PRIVATE,)).fetchone()[0]is None
    before=catalog._catalog_rows(cur)
    originals={s:definition(cur,s)for s in(opening.REPORT,reuse.SNAPSHOT,REPORT_UNIT)}
    native=cur.execute('select prosrc,provolatile,prosecdef,pg_get_userbyid(proowner),proconfig from pg_proc where oid=%s::regprocedure',(opening.ORIGINAL,)).fetchone()
    assert native[1:]==('v',True,'postgres',['search_path=erp, public'])
    snapshot=cur.execute('select prosrc,provolatile,prosecdef,pg_get_userbyid(proowner),proconfig from pg_proc where oid=%s::regprocedure',(reuse.SNAPSHOT,)).fetchone()
    assert snapshot[1:]==('s',True,'postgres',['search_path=erp, public, pg_catalog, pg_temp'])
    body=reuse.rewrite(snapshot[0]);assert originals[reuse.SNAPSHOT].count(snapshot[0])==1
    changed={opening.REPORT:opening.report_definition(originals[opening.REPORT]),
        reuse.SNAPSHOT:originals[reuse.SNAPSHOT].replace(snapshot[0],body,1),
        REPORT_UNIT:held_report_definition(originals[REPORT_UNIT],key)}
    cur.execute(opening.definition(native[0]),prepare=False)
    cur.execute('alter function '+opening.PRIVATE+' owner to postgres')
    cur.execute('revoke all on function '+opening.PRIVATE+' from public,anon,authenticated,service_role,cp7_capture,cp7_finance_read')
    for signature,text in changed.items():cur.execute(text,prepare=False);assert definition(cur,signature)==text
    for role in('anon','authenticated','service_role','cp7_capture','cp7_finance_read'):
        assert not cur.execute("select has_function_privilege(%s,%s,'EXECUTE')",(role,opening.PRIVATE)).fetchone()[0]
    assert cur.execute('select prosrc from pg_proc where oid=%s::regprocedure',(opening.ORIGINAL,)).fetchone()[0]==native[0]
    return dict(before_catalog=before,originals=originals,changed=changed,
        evidence=dict(temporary_disposable_database_patch=True,committed_before_measured_transactions=True,
            original_posting_resolver_unchanged=True,private_helper_browser_worker_denied=True,
            original_bodies={k:sha256(v.encode()).hexdigest()for k,v in originals.items()},
            patched_bodies={k:sha256(v.encode()).hexdigest()for k,v in changed.items()},
            production_go=False,product_adoption=False))

def remove_hold(cur,state):
    assert definition(cur,REPORT_UNIT)==state['changed'][REPORT_UNIT]
    cur.execute(state['originals'][REPORT_UNIT],prepare=False)
    state['changed'][REPORT_UNIT]=state['originals'][REPORT_UNIT]

def restore(cur,catalog,state):
    for signature,text in state['changed'].items():assert definition(cur,signature)==text,signature
    for signature,text in state['originals'].items():cur.execute(text,prepare=False)
    cur.execute('drop function '+opening.PRIVATE)
    assert catalog._catalog_rows(cur)==state['before_catalog'],'SOURCE_RACE_PATCH_CATALOG_NOT_RESTORED'
