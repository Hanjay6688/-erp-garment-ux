"""Read complete stopped-job rows after scheduler quiescence; never drive or change jobs."""
from urllib.parse import urlparse
import psycopg

def capture(admin_url,request_ids,capture_id):
    u=urlparse(admin_url)
    assert u.hostname in('localhost','127.0.0.1')and u.port==54322 and u.path=='/cp6_rollback'
    assert len(request_ids)==len(set(request_ids))==2
    with psycopg.connect(admin_url)as conn,conn.cursor()as cur:
        cur.execute('set local transaction read only')
        cur.execute("set local statement_timeout='8s'")
        assert cur.execute('select current_database()').fetchone()==('cp6_rollback',)
        assert cur.execute('show transaction_read_only').fetchone()==('on',)
        jobs=[row[0]for row in cur.execute("select to_jsonb(j)from cp7_analysis_stage.jobs j where request_id=any(%s::uuid[])order by request_id",(request_ids,)).fetchall()]
        captures=[row[0]for row in cur.execute('select to_jsonb(c)from cp7_finance_capture.captures c where id=%s',(capture_id,)).fetchall()]
        assert len(jobs)==2 and {row['request_id']for row in jobs}==set(request_ids)
        assert len(captures)==1 and captures[0]['id']==capture_id
        columns={}
        for schema,table in [('cp7_analysis_stage','jobs'),('cp7_finance_capture','captures')]:
            columns[schema+'.'+table]=[row[0]for row in cur.execute("select a.attname from pg_attribute a join pg_class c on c.oid=a.attrelid join pg_namespace n on n.oid=c.relnamespace where n.nspname=%s and c.relname=%s and a.attnum>0 and not a.attisdropped order by a.attnum",(schema,table)).fetchall()]
        assert all(set(row)==set(columns['cp7_analysis_stage.jobs'])for row in jobs)
        assert set(captures[0])==set(columns['cp7_finance_capture.captures'])
        return dict(read_only=True,statement_limit='8s',all_stored_columns_preserved=True,
            job_rows=jobs,finance_capture_rows=captures,column_inventory=columns,
            manual_steps=0,job_or_capture_state_changed=False)
