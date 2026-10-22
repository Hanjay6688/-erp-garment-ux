"""Read-only counters on the one declared disposable browser database."""
import json,os,sys
from urllib.parse import urlparse
import psycopg

assert sys.argv[1:]==['snapshot']
url=os.environ['AUDITOR_BROWSER_DB_URL'];p=urlparse(url)
assert p.hostname in('127.0.0.1','localhost')and p.path=='/cp6_auditor_browser'
with psycopg.connect(url)as conn,conn.cursor()as cur:
    cur.execute('set transaction read only')
    cur.execute('select pg_stat_clear_snapshot()')
    rows=cur.execute("select f.funcid::regprocedure::text,f.calls,f.total_time,f.self_time "
        "from pg_stat_user_functions f join pg_proc p on p.oid=f.funcid join pg_namespace n on n.oid=p.pronamespace "
        "where n.nspname='erp'or n.nspname like 'cp7_%'or n.nspname like 'ow04_%'order by f.funcid").fetchall()
    print(json.dumps(dict(track_functions=cur.execute("show track_functions").fetchone()[0],
        functions={name:dict(calls=c,total_ms=t,self_ms=s)for name,c,t,s in rows}),default=str))
    conn.rollback()
