"""Reserve the original attendance scenario's own two days, using named inverse.

Only newly created, zero-paid-fraction OFF periods from this qualifier's seed
receipts may be reversed. Original paid attendance is never approved afterwards.
"""
from datetime import timedelta
import cp7_retained_cp6_fixture as fixture

CONTRACTOR='a1000000-0000-0000-0000-000000000001'


def reserve(cur,day,evidence):
    aw=fixture.aw
    seed=evidence['seed_completion']['attendance']
    pools=evidence.get('attendance_pools',{})
    seed=seed+pools.get('seed_completion_before_pool_activation',{}).get('attendance',[])
    own={p['period_id']for c in seed if c['contractor']==CONTRACTOR for p in c['periods']}
    aw.api.admin(cur)
    periods=cur.execute("""select id::text,row_version,period_start,period_end from erp.attendance_periods
        where contractor_id=%s and status='POSTED' and period_start<=%s and period_end>=%s order by period_start""",
        (CONTRACTOR,day+timedelta(days=1),day)).fetchall()
    assert periods and all(pid in own for pid,_,_,_ in periods),'CROSSFLOW_ATTENDANCE_NOT_OWN_ZERO_OFF_FIXTURE'
    result=dict(contractor=CONTRACTOR,start=str(day),end=str(day+timedelta(days=1)),reversed=[],refilled=[])
    for pid,version,start,end in periods:
        count,nonzero=cur.execute("""select count(*),count(*)filter(where paid_fraction is distinct from 0)
            from erp.attendance_records where attendance_period_id=%s and record_lifecycle='POSTED'""",(pid,)).fetchone()
        assert count>0 and nonzero==0,('CROSSFLOW_FIXTURE_HAS_PAID_ATTENDANCE',pid)
        inverse=aw.reverse_attendance(cur,dict(period_id=pid,row_version=version))
        result['reversed'].append(dict(period_id=pid,receipt=inverse,only_owned_OFF_records=True))
        for lo,hi in ((start,min(end,day-timedelta(days=1))),(max(start,day+timedelta(days=2)),end)):
            if lo<=hi:result['refilled'].append(aw.post_attendance(cur,CONTRACTOR,lo,hi))
    aw.api.admin(cur)
    assert cur.execute("""select count(*)from erp.attendance_records where contractor_id=%s
        and attendance_date between %s and %s and record_lifecycle='POSTED'""",
        (CONTRACTOR,day,day+timedelta(days=1))).fetchone()[0]==0
    evidence['reserved_original_attendance_days']=result
    return result


def fill_for_other_case(cur,day):
    return fixture.aw.post_attendance(cur,CONTRACTOR,day,day+timedelta(days=1))
