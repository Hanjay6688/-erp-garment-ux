"""Ordinary source setup only; composer saves/posts occur through the real browser."""
from datetime import date,timedelta
from urllib.parse import urlparse
import json,os,sys,uuid
import psycopg
import cp7_nota_cases as n

def attendance_facts(cur,cid):
    zone=cur.execute('show timezone').fetchone()[0]
    try:
        cur.execute("select set_config('TimeZone','UTC',true)")
        return {table:cur.execute('select md5(coalesce(jsonb_agg(to_jsonb(t) order by t.id)::text,\'\')) from erp.'+table+' t where '+condition,(cid,)).fetchone()[0] for table,condition in {
          'contractor_workers':'t.contractor_id=%s','worker_daily_rate_versions':'exists(select 1 from erp.contractor_workers w where w.id=t.worker_id and w.contractor_id=%s)',
          'worker_employment_periods':'exists(select 1 from erp.contractor_workers w where w.id=t.worker_id and w.contractor_id=%s)',
          'attendance_periods':'t.contractor_id=%s','attendance_records':'t.contractor_id=%s','payroll_settlements':'t.contractor_id=%s'}.items()}
    finally:cur.execute("select set_config('TimeZone',%s,true)",(zone,))

def main():
    target=os.environ['AUDITOR_BROWSER_DB_URL'];url=urlparse(target)
    assert url.hostname in ('127.0.0.1','localhost') and url.path=='/cp6_auditor_browser','DISPOSABLE_BROWSER_ONLY'
    op=sys.argv[1];p=json.loads(sys.argv[2])
    with psycopg.connect(target) as conn,conn.cursor() as cur:
        had=cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]
        if not had:cur.execute('grant usage on schema erp to authenticated')
        if op=='create_attendance_write':
            import cp7_attendance_write_cases as a
            import cp7_settlement_cases as s
            today=date.fromisoformat(p['today']);f=n.source.repair(cur,today);label='Mandor Sumber '+uuid.uuid4().hex[:8]
            cur.execute('update erp.contractors set contractor_name=%s,attendance_required=true where id=%s',(label,f['contractor']))
            n.source.ax.post(cur,n.source.ax.repair_payload(f,1));bank=s.cash(cur)
            code,coa=cur.execute('select cash_account_code,coa_account_id::text from erp.cash_accounts where id=%s',(bank,)).fetchone()
            role=cur.execute("select id from erp.app_roles where role_code='ADMIN'").fetchone()[0];cur.execute('delete from erp.app_role_permissions where role_id=%s',(role,))
            for perm in a.PERMS+s.PERMS+('production.fg_handoff.view','production.fg_handoff.post'):cur.execute('insert into erp.app_role_permissions(role_id,permission_key) values(%s,%s)',(role,perm))
            out=dict(f,label=label,today=str(today),bank=bank,bank_code=code,bank_coa=coa,base_gl=s.gl(cur,f['contractor']),physical=s.physical(cur),facts=n.facts(cur),wip=s.acct(cur,'WIP'),payable=s.acct(cur,'CONTRACTOR_PAYABLE'))
            assert cur.execute('select count(*) from erp.contractor_workers where contractor_id=%s',(f['contractor'],)).fetchone()[0]==0
            assert cur.execute('select count(*) from erp.attendance_periods where contractor_id=%s',(f['contractor'],)).fetchone()[0]==0
            assert cur.execute('select count(*) from erp.payroll_settlements where contractor_id=%s',(f['contractor'],)).fetchone()[0]==0
        elif op=='read_attendance_pipeline':
            import cp7_settlement_cases as s
            out=dict(periods=cur.execute('select id::text,period_number,status,correction_of_period_id::text,row_version::text from erp.attendance_periods where contractor_id=%s order by period_number',(p['contractor'],)).fetchall(),
                records=cur.execute('select ar.id::text,ar.attendance_period_id::text,w.worker_name,ar.status,ar.paid_fraction::text,ar.record_lifecycle,ar.supersedes_attendance_record_id::text from erp.attendance_records ar join erp.contractor_workers w on w.id=ar.worker_id where ar.contractor_id=%s order by ar.attendance_period_id,w.worker_name',(p['contractor'],)).fetchall(),
                workers=cur.execute('select count(*) from erp.contractor_workers where contractor_id=%s',(p['contractor'],)).fetchone()[0],
                rates=cur.execute('select count(*) from erp.worker_daily_rate_versions r join erp.contractor_workers w on w.id=r.worker_id where w.contractor_id=%s',(p['contractor'],)).fetchone()[0],
                gl=s.gl(cur,p['contractor']),physical=s.physical(cur))
        elif op=='create_roster':
            import cp7_roster_cases as r
            today=date.fromisoformat(p['today']);f=n.source.repair(cur,today);label='Mandor Roster '+uuid.uuid4().hex[:8]
            cur.execute('update erp.contractors set contractor_name=%s where id=%s',(label,f['contractor']));r.admin_actor(cur)
            out=dict(contractor=f['contractor'],label=label,start=str(today-timedelta(days=6)),stop=str(today-timedelta(days=2)),restart=str(today),future=str(today+timedelta(days=1)),facts=n.facts(cur))
        elif op=='read_roster':
            out=dict(facts=n.facts(cur),workers=cur.execute('select id::text,worker_name,is_active,row_version::text from erp.contractor_workers where contractor_id=%s order by id',(p['contractor'],)).fetchall(),
                rates=cur.execute('select r.daily_rate::text,r.effective_from,r.effective_to from erp.worker_daily_rate_versions r join erp.contractor_workers w on w.id=r.worker_id where w.contractor_id=%s order by r.effective_from',(p['contractor'],)).fetchall(),
                employment=cur.execute('select e.started_on,e.ended_on from erp.worker_employment_periods e join erp.contractor_workers w on w.id=e.worker_id where w.contractor_id=%s order by e.started_on',(p['contractor'],)).fetchall())
        elif op=='create_attendance_read':
            import cp7_attendance_read_cases as a
            today=date.fromisoformat(p['today']);start=today-timedelta(days=4);workday=today-timedelta(days=3)
            f=n.source.repair(cur,today);label='Mandor Absensi '+uuid.uuid4().hex[:8];cur.execute('update erp.contractors set contractor_name=%s,attendance_required=true where id=%s',(label,f['contractor']))
            wid,wp=a.worker(cur,f,start,name='Pekerja riwayat');other,_=a.worker(cur,f,start,rate='50.000000',name='Pekerja aktif')
            r=a.s.native(cur,'select public.erp_save_attendance_period_v1(%s::jsonb,%s,null,false)',(json.dumps(dict(contractor_id=f['contractor'],period_number='ABS-UI-'+uuid.uuid4().hex[:8],period_start=str(workday),period_end=str(workday),pay_date=str(workday),reason='P12 ordinary browser source fixture',attendance=[dict(worker_id=wid,attendance_date=str(workday),status='PRESENT'),dict(worker_id=other,attendance_date=str(workday),status='HALF_DAY')])),uuid.uuid4()))
            pid=str(a.s.bc.awp.find(r,'period_id'));a.s.native(cur,'select public.erp_post_attendance_period_v1(%s,%s,%s,%s)',(pid,'P12 complete ordinary attendance source',uuid.uuid4(),a.s.bc.awp.find(r,'row_version')))
            a.rate(cur,wid,'200.654321',today+timedelta(days=1));a.stop(cur,wid,wp,today-timedelta(days=2));_,role=a.source.procurement.custom(cur,(a.PERM,))
            out=dict(contractor=f['contractor'],label=label,worker=wid,period=pid,role=str(role),workday=str(workday),facts=n.facts(cur),source_facts=attendance_facts(cur,f['contractor']))
        elif op=='read_attendance_facts':out=dict(facts=n.facts(cur),source_facts=attendance_facts(cur,p['contractor']))
        elif op in ('create','create_payroll_review','create_payroll_settlement'):
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
