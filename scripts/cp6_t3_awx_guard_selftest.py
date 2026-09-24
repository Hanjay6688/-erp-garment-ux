#!/usr/bin/env python3
"""Adversarial self-test of the AW/AX release guards on a throwaway local PostgreSQL (no Supabase stack).

Not install evidence: the database is a stub with only what the guards read (both ledgers, the rollback capsule
tables, two predecessor functions, one business table), and the T1 body is replaced by a small stub. It checks that
the guard blocks built by scripts/cp6_t3_awx_release.py parse and run, install on the stub, and refuse each tamper with
its own code. The closed-admission block is left out (single local session). Pins are derived on the stub the way the
T3 capture derives them. Label: T3_PREP_LOCAL_SELFTEST.

Usage: CP6_T3_SELFTEST_DSN='host=... port=... user=postgres' python scripts/cp6_t3_awx_guard_selftest.py OUT.json
The DSN must point at a disposable local cluster (the script drops and creates the database cp6_awx_selftest).
"""
from pathlib import Path
import json,os,sys
import psycopg

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import cp6_t3_release_package as package
import cp6_t3_awx_release as awx

DSN=os.environ['CP6_T3_SELFTEST_DSN']
DB='cp6_awx_selftest'
assert 'host=' in DSN and ('127.0.0.1' in DSN or 'localhost' in DSN or 'host=/' in DSN),'LOCAL_ONLY'
MARK={'AW':"insert into erp.schema_migrations(version,description) values('v2.6.20aw','x');\n",
      'AX':"insert into erp.schema_migrations(version,description) values('v2.6.20ax','x');\n"}
STUB={'AW':"""create table erp.accounting_close_filings_v1(id int);
create table erp.laundry_rate_owner_estimates_v1(id int);
CREATE OR REPLACE FUNCTION erp.close_accounting_through(p_closed_through date, p_reason text) RETURNS void LANGUAGE sql AS $$select 1$$;
CREATE OR REPLACE FUNCTION erp.get_owner_financial_snapshot_v2(p_from date,p_to date,p_as_of date default current_date) returns jsonb language sql as $$select '{"a":1}'::jsonb$$;
create function erp.period_readiness_v1(date,date) returns int language sql as $$select 1$$;
"""+MARK['AW'],'AX':"""create table erp.fg_unsourced_receipts_v1(id int);
create function erp.post_fg_unsourced_receipt_v1(jsonb,uuid) returns int language sql as $$select 1$$;
"""+MARK['AX']}


def url(db):return DSN+' dbname='+db


def setup():
    with psycopg.connect(url('postgres'),autocommit=True) as c:
        c.execute('drop database if exists %s with (force)'%DB);c.execute('create database %s'%DB)
        for r in ('anon','authenticated','service_role'):
            if not c.execute('select 1 from pg_roles where rolname=%s',(r,)).fetchone():c.execute('create role '+r)
    hist=package.history(awx.AV.read_text())
    caps=sorted(set(hist['pins'])|{'cp6_v2620%s_rollback_capsule'%k for k in awx.PACKAGE_CAPSULES})
    with psycopg.connect(url(DB),autocommit=True) as c:
        x=c.execute
        x("create schema extensions;create extension pgcrypto schema extensions;create schema erp;create schema supabase_migrations")
        x("create table erp.schema_migrations(version text primary key,description text)")
        x("create table supabase_migrations.schema_migrations(version text primary key,name text,statements text[])")
        x("""create table erp.cp6_v2620an_rollback_capsule(object_identity text primary key,object_regidentity text not null unique,object_definition text not null,
         definition_sha256 text not null,installed_definition_sha256 text,acl_snapshot text[],owner_snapshot text not null,
         captured_at timestamptz not null default clock_timestamp(),boundary_snapshot jsonb)""")
        for t in caps:
            if t!='cp6_v2620an_rollback_capsule':x("create table erp.%s(like erp.cp6_v2620an_rollback_capsule including all)"%t)
            x("alter table erp.%s enable row level security"%t);x("revoke all on erp.%s from public,anon,authenticated,service_role"%t)
            x("""insert into erp.%s(object_identity,object_regidentity,object_definition,definition_sha256,owner_snapshot,boundary_snapshot)
                 values('x','x','d',encode(extensions.digest('d','sha256'),'hex'),'postgres','{"before":1,"after":1,"platform_before":1,"markers_before":1}')"""%t)
        x("create table erp.bs_resolutions(id int primary key);insert into erp.bs_resolutions values(1),(2)")
        x("create function erp.close_accounting_through(p_closed_through date,p_reason text) returns void language sql as $$select$$")
        x("create function erp.get_owner_financial_snapshot_v2(p_from date,p_to date,p_as_of date default current_date) returns jsonb language sql as $$select '{}'::jsonb$$")
        x("create function erp.untouched(a int) returns int language sql as $$select a$$")
        for k in package.KEYS[:package.KEYS.index('av')+1]:
            m=awx.migration(k);text=next(awx.MIGRATIONS.glob('*_erp_v2_6_20%s_*.sql'%k)).read_text()
            x("insert into erp.schema_migrations values(%s,'x')",(m['marker'],))
            x("insert into supabase_migrations.schema_migrations values(%s,%s,%s)",(m['stamp'],m['name'],[text]))


def source(key):
    [p]=[q for q in awx.SRC.glob('*.sql') if '_20%s_'%key.lower() in q.name]
    return p.read_text()


def variant(text,key,extra=''):
    text=text.replace(awx.block(text,'closed_admission'),'')
    start=text.index('end $before_data$;\n')+len('end $before_data$;\n');end=text.index('do $catalog_guard$',start)
    return text[:start]+STUB[key].replace(MARK[key],extra+MARK[key])+text[end:]


def pin(text):
    subs=[];h=package.history(text)
    with psycopg.connect(url(DB)) as c,c.cursor() as cur:live=package.live_history(cur,h['query'],list(h['pins']))
    subs+=[dict(kind='CAPSULE',what=k,old='"%s":"%s"'%(k,v),new='"%s":"%s"'%(k,live[k]),count=1) for k,v in h['pins'].items() if live[k]!=v]
    b=package.catalog_blocks(text)
    with psycopg.connect(url(DB)) as c,c.cursor() as cur:n,f=package.live_catalog(cur,b[0])
    subs.append(package.catalog_sub(b[0],n,f))
    staged=package.apply_subs(text,subs);blk=package.catalog_blocks(staged)[1]
    with psycopg.connect(url(DB)) as c,c.cursor() as cur:
        cur.execute(package.sql_body(staged.replace(blk['text'],'',1)));n,f=package.live_catalog(cur,blk);c.rollback()
    subs.append(package.catalog_sub(blk,n,f))
    return package.apply_subs(text,subs)


def run(text):
    with psycopg.connect(url(DB)) as c,c.cursor() as cur:cur.execute(package.sql_body(text))


def attempt(text):
    try:run(text);return 'INSTALLED'
    except psycopg.Error as e:return str(e).splitlines()[0][:200]


CASES=[
 ('capsule row altered after pinning',"update erp.cp6_v2620ao_rollback_capsule set object_definition='tampered'",None,'AW_HISTORICAL_CAPSULE_DRIFT'),
 ('grant on a package capsule',"grant select on erp.cp6_v2620ap_rollback_capsule to authenticated",None,'AW_PRIOR_CAPSULE_SECURITY'),
 ('prior ledger statements altered',"update supabase_migrations.schema_migrations set statements=array['x'] where name like 'erp_v2_6_20ao_%'",None,'AW_PRIOR_PLATFORM_DRIFT'),
 ('prior app marker missing',"delete from erp.schema_migrations where version='v2.6.20ar'",None,'AW_PRIOR_PLATFORM_DRIFT'),
 ('successor ledger row present',"insert into supabase_migrations.schema_migrations values('20260924000001','later','{}')",None,'AW_EXACT_PREDECESSOR_REQUIRED'),
 ('body changes an unlisted function',None,"CREATE OR REPLACE FUNCTION erp.untouched(a int) returns int language sql as $$select a+1$$;\n",'AW_CAPSULE_INCOMPLETE'),
 ('body changes the ACL of an unlisted function',None,"grant execute on function erp.untouched(int) to authenticated;\n",'AW_CAPSULE_INCOMPLETE'),
 ('body changes business data',None,"update erp.bs_resolutions set id=id+10 where id=2;\n",'AW_INSTALL_CHANGED_DATA'),
 ('body fills a new table',None,"insert into erp.accounting_close_filings_v1 values(1);\n",'AW_INSTALL_CHANGED_DATA'),
 ('body changes a function after the pins (installed catalog pin kept)',None,"CREATE OR REPLACE FUNCTION erp.untouched(a int) returns int language sql as $$select a+2$$;\n",'AW_INSTALLED_CATALOG_DRIFT'),
]


def main(out):
    report=dict(label='T3_PREP_LOCAL_SELFTEST',server=None,positive={},negative=[],production_go=False,release_evidence=False)
    setup()
    with psycopg.connect(url(DB)) as c:report['server']=c.execute('show server_version').fetchone()[0]
    for key in ('AW','AX'):
        src=source(key);result=attempt(pin(variant(src,key)))
        with psycopg.connect(url(DB),autocommit=True) as c:
            rows=c.execute("select object_regidentity,installed_definition_sha256 is not null,boundary_snapshot ?& array['before','after','platform_before','markers_before'] from erp.cp6_v2620%s_rollback_capsule order by 1"%key.lower()).fetchall() if result=='INSTALLED' else None
            m=[f for f in awx.FILES if f['key']==key][0]
            # ledger row as the applier writes it; the successor checks the source statements (no cascade on the stub)
            if result=='INSTALLED':c.execute("insert into supabase_migrations.schema_migrations values(%s,%s,%s)",(m['stamp'],m['name'],[src]))
        report['positive'][key]=dict(result=result,capsule=rows)
    aw=source('AW')
    for name,tamper,extra,code in CASES:
        setup()
        if extra is None:
            text=pin(variant(aw,'AW'))
            with psycopg.connect(url(DB),autocommit=True) as c:c.execute(tamper)
        else:
            pinned=pin(variant(aw,'AW'))
            text=pinned.replace(MARK['AW'],extra+MARK['AW'])
            if code!='AW_INSTALLED_CATALOG_DRIFT':
                # the installed catalog pin would refuse any body change first; leave it out to reach the guard under test
                text=text.replace(package.catalog_blocks(text)[1]['text'],'')
        got=attempt(text)
        report['negative'].append(dict(case=name,expected=code,refusal=got,ok=code in got))
        print(('OK ' if code in got else 'FAIL ')+name+' -> '+got,flush=True)
    report['status']='PASS' if all(v['result']=='INSTALLED' for v in report['positive'].values()) and all(n['ok'] for n in report['negative']) else 'FAIL'
    with psycopg.connect(url('postgres'),autocommit=True) as c:c.execute('drop database if exists %s with (force)'%DB)
    Path(out).write_text(json.dumps(report,indent=2,default=str)+'\n')
    print(json.dumps(dict(status=report['status'],positive={k:v['result'] for k,v in report['positive'].items()})))
    return report


if __name__=='__main__':raise SystemExit(0 if main(sys.argv[1])['status']=='PASS' else 1)
