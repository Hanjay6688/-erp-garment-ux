"""Compile-check the plpgsql functions of a CP7 SQL file on a throwaway local PostgreSQL (env PGCHECK_DSN, PGCHECK_DB; never a
hosted database): each schema the file names is recreated empty, each table it names becomes an empty stub row type, then
every language plpgsql function is created with check_function_bodies. It does not catch name clashes at run time; run
scripts/cp7_plpgsql_clash_check.py too (docs/ERP_BEST_PRACTICES.md E25c)."""
import sys,re,pglast,psycopg
text=open(sys.argv[1]).read();b=text.encode()
import os
conn=psycopg.connect(os.environ.get('PGCHECK_DSN','host=/tmp/pgcheck port=55432 user=postgres')+' dbname='+os.environ.get('PGCHECK_DB','postgres'),autocommit=True)
cur=conn.cursor()
schemas=sorted(set(re.findall(r'\b(erp|auth|extensions|cp7_[a-z_0-9]+)\.[a-z_0-9]+',text))|{'erp','auth','extensions'})
for s in schemas:cur.execute(f'drop schema if exists {s} cascade');cur.execute(f'create schema {s}')
types=set(re.findall(r'\b((?:erp|cp7_[a-z_0-9]+)\.[a-z_0-9]+)\b',text))
for t in sorted(types):
    try:cur.execute(f'create table {t}()')
    except Exception as e:pass
ok=bad=0
for raw in pglast.parse_sql(text):
    s=raw.stmt
    if s.__class__.__name__!='CreateFunctionStmt':continue
    lang=[o.arg.sval for o in (s.options or []) if o.defname=='language']
    if lang!=['plpgsql']:continue
    stmt=b[raw.stmt_location:raw.stmt_location+(raw.stmt_len or len(b))].decode()
    try:
        cur.execute(stmt);ok+=1
    except Exception as e:
        bad+=1;print('ERROR',s.funcname[-1].sval,':',str(e)[:1500])
print('plpgsql compiled',ok,'errors',bad)
