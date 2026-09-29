"""Ordinary source setup only; composer saves/posts occur through the real browser."""
from datetime import date
from urllib.parse import urlparse
import json,os,sys,uuid
import psycopg
import cp7_nota_cases as n

def main():
    target=os.environ['AUDITOR_BROWSER_DB_URL'];url=urlparse(target)
    assert url.hostname in ('127.0.0.1','localhost') and url.path=='/cp6_auditor_browser','DISPOSABLE_BROWSER_ONLY'
    op=sys.argv[1];p=json.loads(sys.argv[2])
    with psycopg.connect(target) as conn,conn.cursor() as cur:
        had=cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]
        if not had:cur.execute('grant usage on schema erp to authenticated')
        if op=='create':
            f=n.source.repair(cur,date.fromisoformat(p['today']));label='Mandor Nota '+uuid.uuid4().hex[:8]
            cur.execute('update erp.contractors set contractor_name=%s where id=%s',(label,f['contractor']))
            n.source.ax.post(cur,n.source.ax.repair_payload(f,1));out=dict(f,label=label,facts=n.book.facts(cur))
            if p.get('ops'):
                role=cur.execute("select id from erp.app_roles where role_code='ADMIN'").fetchone()[0];cur.execute('delete from erp.app_role_permissions where role_id=%s',(role,))
                for perm in ('production.fg_handoff.view','production.fg_handoff.post'):cur.execute('insert into erp.app_role_permissions(role_id,permission_key) values(%s,%s)',(role,perm))
        elif op=='read':
            rows=cur.execute('select id::text,status,posted_payroll_id::text,row_version::text from cp7_payroll.notes where contractor_id=%s order by created_at,id',(p['contractor'],)).fetchall()
            payroll=cur.execute('select id::text,status,labor_total::text,net_payable::text,settled_at from erp.payroll_settlements where contractor_id=%s',(p['contractor'],)).fetchall()
            qty=cur.execute('select count(*),coalesce(sum(i.qty_payable),0),coalesce(sum(i.amount),0)::text from erp.payroll_work_items i join erp.payroll_settlements h on h.id=i.payroll_id where h.contractor_id=%s',(p['contractor'],)).fetchone()
            out=dict(notes=[dict(id=r[0],status=r[1],payroll_id=r[2],version=r[3]) for r in rows],payroll=payroll,allocated=qty,facts=n.book.facts(cur))
        elif op=='cancel':
            pid=cur.execute('select posted_payroll_id from cp7_payroll.notes where contractor_id=%s and status=\'POSTED\'',(p['contractor'],)).fetchone()[0]
            n.b.chain.production.owner(cur);cur.execute('select erp.cancel_unpaid_payroll(%s,%s)',(pid,'P12 native cancellation control after browser note posting'));n.b.api.admin(cur);out=dict(ok=True)
        else:raise ValueError('Unknown Nota fixture action')
        n.b.api.admin(cur)
        if not had:cur.execute('revoke usage on schema erp from authenticated')
        assert cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]==had
        conn.commit()
    print(json.dumps(out,default=str))

if __name__=='__main__':main()
