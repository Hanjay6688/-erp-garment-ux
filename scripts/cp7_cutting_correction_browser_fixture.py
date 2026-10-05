"""Native cutting preparation/readback in the disposable browser database only."""
from datetime import date
from decimal import Decimal
from urllib.parse import urlparse
import json,os,sys
import psycopg
import cp7_cutting_correction_cases as cases
def main():
    target=os.environ['AUDITOR_BROWSER_DB_URL'];url=urlparse(target)
    assert url.hostname in('localhost','127.0.0.1')and url.path=='/cp6_auditor_browser','DISPOSABLE_BROWSER_ONLY'
    p=json.load(sys.stdin);operation=sys.argv[1]
    with psycopg.connect(target)as conn,conn.cursor()as cur:
        had=cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]
        acl=cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]
        if not had:cur.execute('grant usage on schema erp to authenticated')
        if operation=='prepare':
            f=cases.fixture(cur,date.fromisoformat(p['today']));out=dict(fixture=f,workspace=cases.read(cur,f))
        elif operation=='state':
            f=p['fixture'];f['qty']=Decimal(f['qty']);f['before_stock']=Decimal(f['before_stock'])
            original=cases.facts(cur,f);baseline=f['original']
            for field in('material_issue_posted','material_return_posted','status','row_version','updated_at'):
                original['group'].pop(field,None);baseline['group'].pop(field,None)
            movements=cases.movement_comparison(cur,f)
            out=dict(stock=str(cases.stock(cur,f)),issued=str(f['qty']),
                original_nonlifecycle_facts_unchanged=original==baseline,
                original_movements_unchanged=movements['exact_UTC_text_equal'],
                original_movement_observation=movements,
                gl_delta={k:str(v-Decimal(f['before_gl'].get(k,'0')))for k,v in cases.gl(cur).items()if v!=Decimal(f['before_gl'].get(k,'0'))},
                expected_gl_delta={k:str(-Decimal(v))for k,v in f['issue_lines'].items()if Decimal(v)!=0},
                history=cur.execute('select coalesce(jsonb_agg(jsonb_build_object(\'request_id\',request_id,\'group_id\',group_id,\'original_source\',original_source,\'Native_response\',Native_response)order by recorded_at),\'[]\')from '+cases.bundle.SCHEMA+'.history where group_id=%s',(f['group'],)).fetchone()[0],
                group=cur.execute('select to_jsonb(g)from erp.cutting_groups g where id=%s',(f['group'],)).fetchone()[0])
        else:raise ValueError('Unknown cutting-correction fixture operation')
        cases.b.api.admin(cur)
        if not had:cur.execute('revoke usage on schema erp from authenticated')
        assert cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]==acl
        conn.commit()
    print(json.dumps(out,default=str))
if __name__=='__main__':main()
