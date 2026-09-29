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
        if op in ('create','create_payroll_review','create_payroll_settlement'):
            f=n.source.repair(cur,date.fromisoformat(p['today']));label='Mandor Nota '+uuid.uuid4().hex[:8]
            cur.execute('update erp.contractors set contractor_name=%s where id=%s',(label,f['contractor']))
            n.source.ax.post(cur,n.source.ax.repair_payload(f,1));out=dict(f,label=label,facts=n.facts(cur))
            if op in ('create_payroll_review','create_payroll_settlement'):
                note=n.command(cur,'SAVE',n.payload(cur,f,date.fromisoformat(p['today'])));note=n.act(cur,'POST',note)
                out.update(note=note['note_id'],payroll=note['payroll_id'])
            if op=='create_payroll_settlement':
                import cp7_settlement_cases as s
                s.attendance(cur,f,date.fromisoformat(p['today']));bank=s.cash(cur)
                code,coa=cur.execute('select cash_account_code,coa_account_id::text from erp.cash_accounts where id=%s',(bank,)).fetchone()
                _,role=s.source.procurement.custom(cur,s.PERMS)
                out.update(bank=bank,bank_code=code,bank_coa=coa,role=str(role),base_gl=s.gl(cur,f['contractor']),physical=s.physical(cur),wip=s.acct(cur,'WIP'),payable=s.acct(cur,'CONTRACTOR_PAYABLE'))
            if p.get('ops') or op=='create_payroll_review':
                role=cur.execute("select id from erp.app_roles where role_code='ADMIN'").fetchone()[0];cur.execute('delete from erp.app_role_permissions where role_id=%s',(role,))
                for perm in (('finance.payroll.view',) if op=='create_payroll_review' else ('production.fg_handoff.view','production.fg_handoff.post')):cur.execute('insert into erp.app_role_permissions(role_id,permission_key) values(%s,%s)',(role,perm))
        elif op=='bind_settlement_actor':
            role=cur.execute('select role_code from erp.app_roles where id=%s',(p['role'],)).fetchone()[0]
            assert role.startswith('P02_') and role not in ('OWNER','ADMIN')
            cur.execute("update erp.app_users set role='STAFF',role_id=%s where auth_user_id=%s",(p['role'],p['actor']))
            assert cur.rowcount==1
            out=dict(role_code=role)
        elif op=='read_settlement':
            import cp7_settlement_cases as s
            out=dict(document=s.doc(cur,p['payroll']),gl=s.gl(cur,p['contractor']),physical=s.physical(cur),payment=s.journal(cur,p['payroll'],'PAYROLL_PAYMENT'),accrual=s.journal(cur,p['payroll'],'PAYROLL_ATTENDANCE_ACCRUAL'),note=n.read(cur,id=p['note'])['page']['rows'][0],sources=n.read(cur,'SOURCES',contractor_id=p['contractor'])['page']['total'])
        elif op=='read':
            rows=cur.execute('select id::text,status,posted_payroll_id::text,row_version::text from cp7_payroll.notes where contractor_id=%s order by created_at,id',(p['contractor'],)).fetchall()
            payroll=cur.execute('select id::text,status,labor_total::text,net_payable::text,settled_at from erp.payroll_settlements where contractor_id=%s',(p['contractor'],)).fetchall()
            qty=cur.execute('select count(*),coalesce(sum(i.qty_payable),0),coalesce(sum(i.amount),0)::text from erp.payroll_work_items i join erp.payroll_settlements h on h.id=i.payroll_id where h.contractor_id=%s',(p['contractor'],)).fetchone()
            out=dict(notes=[dict(id=r[0],status=r[1],payroll_id=r[2],version=r[3]) for r in rows],payroll=payroll,allocated=qty,facts=n.facts(cur))
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
