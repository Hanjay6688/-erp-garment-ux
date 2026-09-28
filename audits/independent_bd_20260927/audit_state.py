"""Auditor-authored data and catalogue readback; no product test oracle."""
import json,hashlib,psycopg
from psycopg import sql
DSN='postgresql://postgres:postgres@127.0.0.1:54322/cp6_rollback'
def digest(x):return hashlib.sha256(json.dumps(x,sort_keys=True,default=str,separators=(',',':')).encode()).hexdigest()
def snapshot():
    with psycopg.connect(DSN) as c:
        c.execute("set timezone='UTC'")
        funcs=c.execute("select n.nspname,p.oid::regprocedure::text,pg_get_functiondef(p.oid),pg_get_userbyid(p.proowner),p.proacl::text from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname in ('erp','public') and p.prokind in ('f','p') order by 1,2").fetchall()
        relations=c.execute("select n.nspname,r.relname,r.relkind,r.relrowsecurity,r.relforcerowsecurity,pg_get_userbyid(r.relowner),r.relacl::text from pg_class r join pg_namespace n on n.oid=r.relnamespace where n.nspname in ('erp','public') order by 1,2").fetchall()
        columns=c.execute("select table_schema,table_name,column_name,data_type,udt_name,is_nullable,column_default,numeric_precision,numeric_scale from information_schema.columns where table_schema in ('erp','public') order by table_schema,table_name,column_name").fetchall()
        data={}
        for schema,table in c.execute("select schemaname,tablename from pg_tables where schemaname in ('erp','public','supabase_migrations') order by 1,2").fetchall():
            q=sql.SQL("select to_jsonb(t) from {}.{} t order by to_jsonb(t)::text").format(sql.Identifier(schema),sql.Identifier(table))
            rows=c.execute(q).fetchall();data[schema+'.'+table]={'count':len(rows),'sha256':digest(rows)}
    return {'functions':digest(funcs),'relations':digest(relations),'columns':digest(columns),'data':data,
            'limits':'Sequence counters, constraints, and indexes are not separately compared by this independent readback.'}
