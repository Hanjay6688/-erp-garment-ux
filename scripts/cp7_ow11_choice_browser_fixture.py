"""Read-back and real Native source mutation; only the disposable browser copy."""
import json,os,sys
from urllib.parse import urlparse
import psycopg
import cp7_ow11_analog_choice_cases as native

def main():
    url=os.environ['AUDITOR_BROWSER_DB_URL'];p=json.load(sys.stdin)
    assert urlparse(url).hostname in('localhost','127.0.0.1')and urlparse(url).path=='/cp6_auditor_browser'
    with psycopg.connect(url)as conn,conn.cursor()as cur:
        op=sys.argv[1]
        had=cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]
        acl=cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]
        if not had:cur.execute('grant usage on schema erp to authenticated')
        if op=='state':
            rows=cur.execute('select revision::text,action,request_id::text,evidence,reason from cp7_product_analog_choice.choices where target_key=%s order by revision',(p['target'],)).fetchall()
            out=dict(rows=[dict(zip(('revision','action','request','evidence','reason'),r))for r in rows],commands=cur.execute('select count(*)from cp7_product_analog_choice.commands where actor=%s',(p['actor'],)).fetchone()[0])
        elif op=='change':
            product=cur.execute('select id::text from erp.products where identity_root_id=%s::uuid and size_id=%s::uuid limit 1',tuple(p['target'].split(':'))).fetchone()[0]
            native.plan.found_fg(cur,dict(root=product),'1')
            out=dict(actual_Native_stock_change=True,physical=native.plan.monetary_state(cur))
        else:raise ValueError('UNKNOWN_CHOICE_BROWSER_CONTROL')
        native.plan.b.api.admin(cur)
        if not had:cur.execute('revoke usage on schema erp from authenticated')
        assert cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]==acl
        conn.commit()
    print(json.dumps(out,default=str))

if __name__=='__main__':main()
