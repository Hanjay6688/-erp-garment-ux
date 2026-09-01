#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
HAR=ROOT/'scripts/cp3_r4_full_schema_concurrency.py'
MAN=ROOT/'docs/evidence/cp3_r4_source_hashes.json'

def once(text,old,new,label):
    count=text.count(old)
    if count!=1: raise SystemExit(f'{label}: expected one anchor, found {count}')
    return text.replace(old,new,1)

text=HAR.read_text()
old='''        normal_a = one(admin, "select id::text from erp.contractors where contractor_code='CP3R3-NORMAL-A'")["id"]
        completion_a = one(admin, """
            select id::text,erp._cp3_business_date(physical_at)::text business_date
            from erp.work_completion_events where completion_number='CP3R3-WC-A'
        """)
        sewing_a = one(admin, """
            select id::text,row_version from erp.sewing_terminal_events
            where source_work_completion_id=%s::uuid and event_kind='SELESAI_DIJAHIT'
              and not exists(select 1 from erp.sewing_terminal_events rv where rv.reversal_of_id=sewing_terminal_events.id)
            order by created_at,id limit 1
        """, (completion_a["id"],))
'''
new='''        completion_a = one(admin, """
            select wc.id::text,wc.contractor_id::text,
                   erp._cp3_business_date(wc.physical_at)::text business_date
            from erp.work_completion_events wc
            where wc.completion_number like 'CP3R3-WC-%' and wc.status='POSTED'
              and exists(
                select 1 from erp.sewing_terminal_events e
                where e.source_work_completion_id=wc.id and e.event_kind='SELESAI_DIJAHIT'
                  and not exists(select 1 from erp.sewing_terminal_events rv where rv.reversal_of_id=e.id)
              )
            order by wc.completion_number limit 1
        """)
        normal_a = completion_a["contractor_id"]
        sewing_a = one(admin, """
            select id::text,row_version from erp.sewing_terminal_events
            where source_work_completion_id=%s::uuid and event_kind='SELESAI_DIJAHIT'
              and not exists(select 1 from erp.sewing_terminal_events rv where rv.reversal_of_id=sewing_terminal_events.id)
            order by created_at,id limit 1
        """, (completion_a["id"],))
'''
text=once(text,old,new,'active sewing/work-completion discovery')
old2='''        clear_open_pools(admin, start, end)
        pending_c = create_pending_payroll(admin, "C", start, end, 111)
        pending_d = create_pending_payroll(admin, "D", start, end, 222)
        admin.commit()
'''
new2='''        clear_open_pools(admin, start, end)
        if not scalar(admin, """
            select exists(select 1 from erp.payroll_settlements ps
              join erp.journal_entries je on je.source_id=ps.id
             where ps.period_start=%s::date and ps.period_end=%s::date
               and ps.status in ('APPROVED','PAID') and ps.attendance_total>0
               and je.source_type='PAYROLL_ATTENDANCE_ACCRUAL' and je.status='POSTED')
        """, (start,end)):
            base = create_pending_payroll(admin, "BASE", start, end, 77)
            admin.execute("select erp.approve_payroll(%s::uuid)", (base["payroll_id"],))
        pending_c = create_pending_payroll(admin, "C", start, end, 111)
        pending_d = create_pending_payroll(admin, "D", start, end, 222)
        admin.commit()
'''
text=once(text,old2,new2,'approved basis fallback')
HAR.write_text(text)
manifest=json.loads(MAN.read_text())
for rel in manifest['files']:
    data=(ROOT/rel).read_bytes(); manifest['files'][rel]={'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)}
MAN.write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
print(json.dumps({'status':'PASS','fixture_discovery':'active-authoritative'},sort_keys=True))
