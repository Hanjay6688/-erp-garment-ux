"""Identify the installed database and verify the exact active branch before taking observations."""
import os
from common import *
import cp7_supplier_payment_cases
import cp7_accessory_standard_report.cases
import cp7_recost_cases
import cp7_wa_forward_cases

with psycopg.connect(**db()) as c,c.cursor() as q:
    seal=measure_seal(q)
    rows=q.execute("select current_database(),current_user,version(),current_setting('cron.launch_active_jobs')").fetchone()
    assert rows[0]=='cp6_rollback' and rows[3]=='off'
    n=first(q,"select count(*) from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='public' and left(p.proname,4)='erp_'")
    inactive=q.execute("select jobname,active from cron.job where jobname in ('erp-wa-collect','erp-wa-analysis','erp-wa-send') order by jobname").fetchall()
    assert n==366 and len(inactive)==3 and all(not row[1] for row in inactive)
    save('opened',dict(seal=seal,session=rows,public_functions=n,scheduled_jobs=inactive,audit_head=os.environ.get('GITHUB_SHA'),method='Writer open action, preserved physical Global, internal network'))
    print('Global open; confirmed',seal['groups'],'catalogue groups and',n,'public functions',flush=True)
