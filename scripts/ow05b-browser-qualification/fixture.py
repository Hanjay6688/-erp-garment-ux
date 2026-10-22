"""Native setup/read oracles on the loopback browser copy; every journey write goes through the actual UI."""
from datetime import date
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo
import json
import os
import sys
import uuid

operation=sys.argv[1]if len(sys.argv)==2 else None
sys.argv=sys.argv[:1]
sys.dont_write_bytecode=True
REPO=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(REPO/'scripts'))
from cp7_contractor_correction import native_cases as n
import cp7_nota_cases as nota
import cp7_settlement_cases as payroll
import psycopg


def main():
    args=json.load(sys.stdin)
    url=os.environ['AUDITOR_BROWSER_DB_URL'];parsed=urlparse(url)
    assert parsed.hostname in('127.0.0.1','localhost')and parsed.path=='/cp6_auditor_browser'
    with psycopg.connect(url)as conn,conn.cursor()as cur:
        n.auth.b.api.admin(cur)
        if operation=='prepare':
            today=date.fromisoformat(args['today'])
            g=n.fixture(cur,today,reverse=False)
            # The old Mandor's sewing is already in an approved nota: the workspace must name and open it.
            workday=n.one(cur,"select(%s::timestamptz at time zone'Asia/Jakarta')::date",(g['at'](10),))
            p=nota.payload(cur,dict(contractor=g['mandor']),today);p.update(period_start=str(workday),period_end=str(today))
            note=nota.command(cur,'SAVE',p);note=nota.act(cur,'POST',note);pid=note['payroll_id']
            payroll.act(cur,'PREPARE',payroll.doc(cur,pid));payroll.act(cur,'APPROVE',payroll.doc(cur,pid))
            n.auth.b.api.admin(cur)
            g['payroll']=str(pid)
            g['payroll_number']=n.one(cur,'select payroll_number from erp.payroll_settlements where id=%s',(pid,))
            g['number']=n.one(cur,'select group_number from erp.cutting_groups where id=%s',(g['group'],))
            g['po_number']=n.one(cur,'select po_number from erp.production_orders where id=%s',(g['po'],))
            g['mandor_name']=n.one(cur,'select contractor_name from erp.contractors where id=%s',(g['mandor'],))
            g['target_name']=n.one(cur,'select contractor_name from erp.contractors where id=%s',(g['target'],))
            physical=g.pop('at')(10)
            g['physical_iso']=physical.isoformat()
            g['physical_local']=physical.astimezone(ZoneInfo('Asia/Jakarta')).strftime('%Y-%m-%dT%H:%M')
            conn.commit();return g
        assert operation=='observe'
        g=args['fixture']
        for key in('po','group','pickup','mandor','target','completion','terminal','payroll'):uuid.UUID(g[key])
        result=dict(preserved=n.preserved(cur,g),
            payroll_status=n.one(cur,'select status from erp.payroll_settlements where id=%s',(g['payroll'],)),
            current_mandor=n.one(cur,'select contractor_id::text from erp.production_orders where id=%s',(g['po'],)),
            old_pickup_status=n.one(cur,'select status from erp.cutting_pickups where id=%s',(g['pickup'],)),
            old_work_status=n.one(cur,'select status from erp.work_completion_events where id=%s',(g['completion'],)),
            posted_work_count=n.one(cur,"select count(*)from erp.work_completion_events where po_id=%s and status='POSTED'",(g['po'],)),
            old_payable=str(-n.balance(cur,g['po'],'CONTRACTOR_PAYABLE',g['mandor'])),
            new_payable=str(-n.balance(cur,g['po'],'CONTRACTOR_PAYABLE',g['target'])),
            wip_increment=str(n.balance(cur,g['po'],'WIP')-Decimal(g['base_wip'])),
            history=n.one(cur,'select cp7_contractor_guidance.history_v1(%s)',(g['po'],)),
            context_count=n.one(cur,'select count(*)from cp7_contractor_correction.context_v1'))
        conn.rollback();return result


if __name__=='__main__':print(json.dumps(main(),default=str))
