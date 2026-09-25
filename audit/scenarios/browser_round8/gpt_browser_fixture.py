"""Ordinary fixture commands only, on the browser mode's disposable copy.
Restores schema grants before the browser acts. Never an oracle or product patch.
"""
from pathlib import Path
from datetime import date,timedelta
from urllib.parse import urlsplit
import json,os,sys,uuid
import psycopg

sys.path.insert(0,str(Path.cwd()/'scripts'))
sys.path.append(str(Path.cwd().parent/'auditor/scripts'))
import cp6_aw_probe as awp
api,prod=awp.api,awp.chain.production


def fixture(kind,today):
    url=os.environ['AUDITOR_BROWSER_DB_URL']
    assert urlsplit(url).path=='/cp6_auditor_browser'
    with psycopg.connect(url) as conn,conn.cursor() as cur:
        api.admin(cur)
        initial=cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]
        if not initial: cur.execute('grant usage on schema erp to authenticated')
        prod.prior.set_open_period(cur,today-timedelta(days=4))
        out=dict(kind=kind)
        if kind in ('cutting','pickup'):
            f=prod.estimated_receipt(cur,today)
            api.admin(cur)
            po=uuid.uuid4();tag='G8UI-'+uuid.uuid4().hex[:14]
            cur.execute('''insert into erp.production_orders(id,po_number,model_id,target_qty_pcs,status,current_stage,physical_start_at,notes)
                values(%s,%s,%s,10,'CUTTING','CUTTING',%s,'GPT browser fixture draft PO')''',
                (po,tag,prod.MODEL,prod.at(today-timedelta(days=2),7)))
            payload=dict(action='SAVE_DRAFT',po_id=po,pattern_id=prod.PATTERN,source_location_id=f['location'],
                cut_at=prod.at(today-timedelta(days=2),8),change_reason='GPT browser fixture ordinary cutting',
                size_slots=[dict(slot_no=1,size_id=prod.base.SIZE,drawing_no=1)],
                rolls=[dict(roll_id=f['roll'],qty_issued=10,qty_consumed=10,qty_reported_remaining=0,
                            yields=[dict(slot_no=1,qty_pcs=10)])])
            draft=prod.rpc(cur,'public.erp_save_cutting_group_before_sewing_v2',payload)
            group=uuid.UUID(draft['cutting_group_id'])
            if kind=='pickup':
                prod.rpc(cur,'public.erp_save_cutting_group_before_sewing_v2',dict(payload,id=group,action='POST'),
                         expected_version=int(draft['row_version']))
            api.admin(cur)
            number=cur.execute('select group_number from erp.cutting_groups where id=%s',(group,)).fetchone()[0]
            out.update(group=str(group),group_number=number,po_number=tag,contractor=prod.CONTRACTOR)
        api.admin(cur)
        if not initial: cur.execute('revoke usage on schema erp from authenticated')
        final=cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]
        assert final==initial
        out.update(schema_usage_before=initial,schema_usage_after=final)
        conn.commit()
    return out


if __name__=='__main__':
    print(json.dumps(fixture(sys.argv[1],date.fromisoformat(sys.argv[2])),default=str))
