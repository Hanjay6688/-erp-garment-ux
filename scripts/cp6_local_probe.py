#!/usr/bin/env python3
"""LOCAL_PG16_DEV (not evidence): run one T1 probe module's PLAN on a local chain built by scripts/cp6_local_chain.py and
seeded with the fixture foundation (cp6_ao_ap_installed.seed). Each case in a rolled-back savepoint, like the CI group.
usage: python3 scripts/cp6_local_probe.py MODULE [DB] [filter] [OUT.json]"""
import importlib,json,sys,traceback,os
from pathlib import Path
os.chdir(Path(__file__).resolve().parents[1]);sys.path.insert(0,'scripts')
import psycopg
mod=importlib.import_module(sys.argv[1]);db=sys.argv[2] if len(sys.argv)>2 else 'chain_seed';flt=sys.argv[3] if len(sys.argv)>3 else ''
api=mod.api
res={}
with psycopg.connect('host=/tmp port=55439 user=postgres dbname=%s'%db) as conn,conn.cursor() as cur:
    cur.execute("set timezone='Asia/Jakarta'")
    today=cur.execute("select (statement_timestamp() at time zone 'Asia/Jakarta')::date").fetchone()[0]
    for key,expected,fn in mod.PLAN:
        if flt and flt not in key:continue
        api.admin(cur);cur.execute('savepoint c')
        try:r=fn(cur,today)
        except Exception as e:r=dict(status='ERROR',error=str(e)[:600],tb=traceback.format_exc()[-1500:])
        finally:cur.execute('rollback to savepoint c');api.admin(cur);cur.execute('release savepoint c')
        res[key]=r
        json.dumps(dict(case=key,**r),default=str)  # the CI group prints dict(case=key,**row)
        print(json.dumps(dict(case=key,expected=expected,status=r.get('status'),error=r.get('error') or (r.get('refusal') or {}).get('message')),default=str)[:700],flush=True)
    conn.rollback()
if len(sys.argv)>4:Path(sys.argv[4]).write_text(json.dumps(res,indent=1,default=str))
