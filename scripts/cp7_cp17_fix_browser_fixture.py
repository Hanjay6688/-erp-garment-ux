"""CP17 browser fixtures (SG-01 pickup reversal, SG-02 fabric return) in the disposable browser database only.

The same Native-writer fixtures as the native CP17 cases (cp7_cp17_fix_cases.pickup_fixture / fabric_fixture); the state
readback is direct SQL on the rows the screens change, never the CP7 command's own answer.
"""
from datetime import date
from urllib.parse import urlparse
import json,os,sys
import psycopg
import cp7_cp17_fix_cases as cases

def main():
    target=os.environ['AUDITOR_BROWSER_DB_URL'];url=urlparse(target)
    assert url.hostname in('localhost','127.0.0.1')and url.path=='/cp6_auditor_browser','DISPOSABLE_BROWSER_ONLY'
    p=json.load(sys.stdin);operation=sys.argv[1]
    with psycopg.connect(target)as conn,conn.cursor()as cur:
        had=cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]
        acl=cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]
        if not had:cur.execute('grant usage on schema erp to authenticated')
        one=lambda sql,args=():cur.execute(sql,args).fetchone()
        if operation=='pickup':
            f=cases.pickup_fixture(cur,date.fromisoformat(p['today']));cases.b.api.admin(cur)
            out=dict(group=f['group'],po=f['po'],pickup=f['pickup'],mandor=f['mandor'],executor=f['executor'],
                     po_before=[None if x is None else str(x) for x in f['po_before']],
                     number=one('select group_number from erp.cutting_groups where id=%s',(f['group'],))[0])
        elif operation=='pickup_state':
            pk=one('select status,reversal_reason from erp.cutting_pickups where id=%s',(p['pickup'],))
            g=one('select status,picked_up_at,executor_name,material_issue_posted from erp.cutting_groups where id=%s',(p['group'],))
            po=one('select status,current_stage,contractor_id from erp.production_orders where id=%s',(p['po'],))
            out=dict(pickup_status=pk[0],reversal_reason=pk[1],group_status=g[0],picked_up_at=g[1],executor=g[2],fabric_posted=g[3],
                     po=[None if x is None else str(x) for x in po],
                     history=one('select count(*) from cp7_cutting_correction.pickup_history where pickup_id=%s',(p['pickup'],))[0],
                     active_pickups=one("select count(*) from erp.cutting_pickups where cutting_group_id=%s and status in('DRAFT','POSTED')",(p['group'],))[0])
        elif operation=='fabric':
            f=cases.fabric_fixture(cur,date.fromisoformat(p['today']));cases.b.api.admin(cur)
            out=dict(f,number=one('select group_number from erp.cutting_groups where id=%s',(f['group'],))[0],
                     roll_number=one('select roll_number from erp.material_rolls where id=%s',(f['roll'],))[0],
                     stock=str(one('select coalesce(sum(qty_signed),0) from erp.material_stock_movements where roll_id=%s and location_id=%s',(f['roll'],f['location']))[0]))
        elif operation=='fabric_state':
            out=dict(stock=str(one('select coalesce(sum(qty_signed),0) from erp.material_stock_movements where roll_id=%s and location_id=%s',(p['roll'],p['location']))[0]),
                     returns=one("select count(*) from erp.material_stock_movements where source_type='CUTTING_GROUP_RETURN' and source_id=%s",(p['group'],))[0],
                     return_posted=one('select material_return_posted from erp.cutting_groups where id=%s',(p['group'],))[0],
                     history=one('select count(*) from cp7_cutting_correction.return_history where group_id=%s',(p['group'],))[0])
        else:raise ValueError('Unknown CP17 browser fixture operation')
        cases.b.api.admin(cur)
        if not had:cur.execute('revoke usage on schema erp from authenticated')
        assert cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]==acl
        conn.commit()
    print(json.dumps(out,default=str))
if __name__=='__main__':main()
