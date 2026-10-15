"""Astra starting fixtures and readback only; business bridge actions are Chromium clicks."""
from pathlib import Path
from urllib.parse import urlparse
from contextlib import redirect_stdout
from datetime import date
import os,sys,json,uuid
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
import psycopg
import cp7_f03_e01_cases as e
import cp7_cp17_fix_cases as c
import cp7_nota_cases as n
import cp7_settlement_cases as s
import cp7_f03_e24_issue_cases as ax

def production_state(cur,f):
    return dict(raw=cur.execute('select sum(qty_signed),sum(qty_signed*unit_cost_snapshot) from erp.material_stock_movements where material_id=%s',(f['material'],)).fetchone(),
      work=cur.execute("select coalesce(sum(l.qty_completed),0),coalesce(sum(l.amount_payable),0) from erp.work_completion_lines l join erp.work_completion_events h on h.id=l.completion_id where h.po_id=%s and h.status='POSTED'",(f['po'],)).fetchone(),
      batches=cur.execute('select b.id::text from erp.cutting_distribution_batches b join erp.cutting_pickups p on p.id=b.pickup_id where p.cutting_group_id=%s',(f['group'],)).fetchall(),fg=e.physical(cur,f),po=c.po_state(cur,f['po']))

def main():
    target=os.environ['AUDITOR_BROWSER_DB_URL'];u=urlparse(target)
    assert u.hostname in ('127.0.0.1','localhost') and u.path=='/cp6_auditor_browser','DISPOSABLE_ONLY'
    op,p=sys.argv[1],json.loads(sys.argv[2])
    with psycopg.connect(target) as conn,conn.cursor() as cur,redirect_stdout(sys.stderr):
      acl=cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]
      had=cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]
      if not had:cur.execute('grant usage on schema erp to authenticated')
      if op=='production_prepare':
        out=e.production(cur,date.fromisoformat(p['today']),cutting_draft_only=True)
        e.b.api.admin(cur)
        vendor,process=[str(uuid.uuid4())for _ in range(2)]
        cur.execute('insert into erp.laundry_vendors(id,vendor_code,vendor_name) values(%s,%s,%s)',(vendor,out['tag'],out['tag']))
        cur.execute('insert into erp.wash_processes(id,process_code,process_name) values(%s,%s,%s)',(process,out['tag'],out['tag']))
        e.laundry.process_rate(cur,dict(vendor=vendor,process=process,start=e.prod.at(out['production_day'],0)), '2.00')
        out.update(vendor=vendor,process=process,size_code=cur.execute('select size_code from erp.sizes where id=%s',(e.base.SIZE,)).fetchone()[0])
        out['before']=production_state(cur,out)
      elif op=='production_read':out=production_state(cur,p)
      elif op=='payroll_prepare':
        out=ax.fixture(cur,date.fromisoformat(p['today']));e.b.api.admin(cur)
        work=n.source.repair(cur,date.fromisoformat(p['today']));n.source.ax.post(cur,n.source.ax.repair_payload(work,1));e.b.api.admin(cur)
        label='Astra Chain '+uuid.uuid4().hex[:10]
        cur.execute('update erp.contractors set contractor_name=%s where id=%s',(label,work['contractor']))
        bank=s.cash(cur);code,coa=cur.execute('select cash_account_code,coa_account_id::text from erp.cash_accounts where id=%s',(bank,)).fetchone()
        out.update(contractor=work['contractor'],mandor=work['contractor'],label=label,bank=bank,bank_code=code,bank_coa=coa,work_source=work)
        out['before']=ax.observe(cur,out)
      elif op=='payroll_read':
        out=dict(accessory=ax.observe(cur,p),notes=cur.execute('select id::text,status,posted_payroll_id::text from cp7_payroll.notes where contractor_id=%s order by created_at',(p['contractor'],)).fetchall(),gl=s.gl(cur,p['contractor']),physical=s.physical(cur))
        ids=cur.execute('select id::text from erp.payroll_settlements where contractor_id=%s',(p['contractor'],)).fetchall()
        out['payroll']=[s.doc(cur,row[0])for row in ids]
        out['payment']=[s.journal(cur,row[0],'PAYROLL_PAYMENT')for row in ids]
        out['deduction_journal']=[s.journal(cur,row[0],'PAYROLL_MATERIAL_DEDUCTION')for row in ids]
      else:raise ValueError(op)
      e.b.api.admin(cur)
      if not had:cur.execute('revoke usage on schema erp from authenticated')
      assert cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]==acl
      conn.commit()
    print(json.dumps(out,default=str))
if __name__=='__main__':main()
