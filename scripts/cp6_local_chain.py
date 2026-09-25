#!/usr/bin/env python3
"""LOCAL_PG16_DEV (not evidence): the CP6 chain on a plain local PostgreSQL 16 for fast development iterations.

Restores the CP4.5a catalog fixture with small Supabase stubs (roles, auth.uid/jwt, storage.buckets), applies every later
migration with its platform-ledger row, then the AW..BB T1 files. Only for the writer's own loop: PG16 has no MAINTAIN
privilege, so MAINTAIN grants are dropped and the migrations' catalog/capsule fingerprint guards (which pin PG17 catalog
output) are neutralized in the local copy, and erp usage is granted to authenticated. Native evidence stays the CI
workflows on the pinned Supabase PostgreSQL 17 runtime.
usage: python3 scripts/cp6_local_chain.py [--upto NAME] [--db NAME]   (PG at host=/tmp port=55439 user=postgres)"""
import gzip,re,subprocess,sys,time
from pathlib import Path
ROOT=Path('/home/user/-erp-garment-ux')
DB=sys.argv[sys.argv.index('--db')+1] if '--db' in sys.argv else 'chain'
PSQL=['psql','-h','/tmp','-p','55439','-U','postgres','-X','-q','-v','ON_ERROR_STOP=1']
def run(sql=None,f=None,db=DB,label=''):
    cmd=PSQL+['-d',db]+(['-f',str(f)] if f else ['-c',sql])
    t=time.time();p=subprocess.run(cmd,capture_output=True,text=True)
    if p.returncode:
        print('FAIL',label,p.stderr[-3000:]);sys.exit(1)
    print('ok',label,'%.1fs'%(time.time()-t),flush=True)
run('drop database if exists %s'%DB,db='postgres',label='drop');run('create database %s'%DB,db='postgres',label='create')
PRE="""
do $$begin
 if not exists(select 1 from pg_roles where rolname='anon') then create role anon nologin; end if;
 if not exists(select 1 from pg_roles where rolname='authenticated') then create role authenticated nologin; end if;
 if not exists(select 1 from pg_roles where rolname='service_role') then create role service_role nologin bypassrls; end if;
 if not exists(select 1 from pg_roles where rolname='supabase_admin') then create role supabase_admin superuser; end if;
 if not exists(select 1 from pg_roles where rolname='authenticator') then create role authenticator noinherit login; end if;
end$$;
create schema extensions;create schema vault;create schema auth;create schema storage;
create extension pgcrypto with schema extensions;create extension "uuid-ossp" with schema extensions;
create table auth.users(id uuid primary key,email text,raw_app_meta_data jsonb,raw_user_meta_data jsonb,created_at timestamptz default now(),deleted_at timestamptz,banned_until timestamptz,last_sign_in_at timestamptz,email_confirmed_at timestamptz,is_sso_user boolean default false,is_anonymous boolean default false);
create function auth.uid() returns uuid language sql stable as $f$select coalesce(nullif(current_setting('request.jwt.claim.sub',true),''),(nullif(current_setting('request.jwt.claims',true),'')::jsonb->>'sub'))::uuid$f$;
create function auth.jwt() returns jsonb language sql stable as $f$select coalesce(nullif(current_setting('request.jwt.claim',true),''),nullif(current_setting('request.jwt.claims',true),''))::jsonb$f$;
create function auth.role() returns text language sql stable as $f$select coalesce(nullif(current_setting('request.jwt.claim.role',true),''),(nullif(current_setting('request.jwt.claims',true),'')::jsonb->>'role'))::text$f$;
create table storage.buckets(id text primary key,name text,public boolean default false);
grant usage on schema auth,extensions to anon,authenticated,service_role;
alter database %s set search_path to "$user",public,extensions;
"""%DB
run(PRE,label='stubs')
fx=gzip.open(ROOT/'supabase/tests/fixtures/erp_enteng_cp45a_catalog_bootstrap.sql.gz','rt').read()
fx=re.sub(r'(?m)^create extension if not exists (pg_stat_statements|supabase_vault|pg_cron)[^;]*;','',fx)
fx=re.sub(r'(?m)^create extension if not exists (pgcrypto|"uuid-ossp")[^;]*;','',fx)
fx=re.sub(r'(?m)^grant MAINTAIN on [^;]*;','',fx)
import tempfile
TMP=Path(tempfile.mkdtemp(prefix='cp6_local_chain_'))
out=TMP/'fx_local.sql';out.write_text(fx)
run(f=out,label='fixture')
run(f=ROOT/'supabase/tests/fixtures/erp_enteng_cp45a_external_application_triggers.sql',label='external triggers')
upto=sys.argv[sys.argv.index('--upto')+1] if '--upto' in sys.argv else None
files=[f for f in sorted((ROOT/'supabase/migrations').glob('*.sql')) if f.name[:14]>'20260902185106']
files+=[ROOT/'supabase/dev'/('cp6_%s_t1_family.sql'%k) for k in ('aw','ax','ay','az','ba','bb')]
PATCHED=TMP/'patched';PATCHED.mkdir(exist_ok=True)
for f in files:
    txt=f.read_text().replace('arwdDxtm','arwdDxt')
    txt=re.sub(r"if object_count<>\d+ or fingerprint is distinct from '[0-9a-f]+' then",'if false then',txt)
    txt=re.sub(r"(?i)raise exception ('[A-Z_]*(CATALOG_DRIFT|CAPSULE_DRIFT|CAPSULE_SHAPE_DRIFT|CAPSULE_SOURCE_DRIFT)[^']*')",r"raise notice \1",txt)
    closed='PACKAGE_REQUIRES_CLOSED_DRAINED_DATABASE' in txt
    if closed:txt='update pg_database set datallowconn=false where datname=current_database();\n'+txt
    pf=PATCHED/f.name;pf.write_text(txt)
    try:run(f=pf,label=f.name)
    finally:
        if closed:run('alter database %s with allow_connections true'%DB,db='postgres',label='reopen')
    if f.parent.name=='migrations':
        v,n=f.stem.split('_',1)
        import psycopg
        with psycopg.connect('host=/tmp port=55439 user=postgres dbname=%s'%DB) as c:
            c.execute('insert into supabase_migrations.schema_migrations(version,name,statements) values(%s,%s,%s)',(v,n,[f.read_text()]))
    if upto and upto in f.name:break
run('grant usage on schema erp to authenticated,service_role',label='erp usage (local)')
