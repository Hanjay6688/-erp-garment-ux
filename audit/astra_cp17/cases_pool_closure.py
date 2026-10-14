"""First executions of the two remaining CP3 pool leads, after Fable exposure.

Distinct legitimate payroll costs are not duplicate money merely because they
share sewn destinations. The first oracle is exact source/value conservation.
The second requires an ACTIVE pool to remain reproducible after a policy write.
"""
from datetime import timedelta
from decimal import Decimal as D
import json,uuid
import cp7_installment_cases as ins
from cases_stage import admin,check,save,wrap
from cases_payroll_leads import attempt
from cases_finance_observability import detectors

def call(cur,sql,args):
    return ins.physical.source.fixture_journal_call(cur,sql,args)

def policy(cur,cid,day):
    return ins.legacy.native(cur,'select public.erp_set_contractor_hpp_policy_v1(%s::jsonb,%s,null)',
        (json.dumps(dict(contractor_id=cid,effective_from=str(day),is_special=False,attendance_required=True,reason='Astra fixed normal Mandor policy')),uuid.uuid4()))

def pay_source(cur,today,start):
    b=ins.legacy;day=today-timedelta(days=1);admin(cur)
    ins.physical.source.receipt.aa.prior.set_open_period(cur,start-timedelta(days=1))
    tag='AS-POOL-'+uuid.uuid4().hex[:10]
    cid=str(cur.execute('insert into erp.contractors(contractor_code,contractor_name,attendance_required)values(%s,%s,true)returning id',(tag,tag)).fetchone()[0])
    pid=str(cur.execute('insert into erp.payroll_settlements(payroll_number,contractor_id,period_start,period_end,payment_date)values(%s,%s,%s,%s,%s)returning id',(tag,cid,start,day,day)).fetchone()[0])
    w=b.native(cur,'select public.erp_save_worker_roster_v1(%s::jsonb,%s,null)',(json.dumps(dict(contractor_id=cid,worker_code=tag,worker_name=tag,job_description='Jahit',pay_scheme='DAILY',initial_daily_rate=1000,rate_effective_from=str(day),joined_at=str(day),is_active=True,reason='Astra one earned day')),uuid.uuid4()))
    ap=b.native(cur,'select public.erp_save_attendance_period_v1(%s::jsonb,%s,null,false)',(json.dumps(dict(contractor_id=cid,period_number=tag+'-ATT',period_start=str(day),period_end=str(day),pay_date=str(day),reason='Astra actual attendance',attendance=[dict(worker_id=str(b.bc.awp.find(w,'worker_id')),attendance_date=str(day),status='PRESENT')])),uuid.uuid4()))
    b.native(cur,'select public.erp_post_attendance_period_v1(%s,%s,%s,%s)',(b.bc.awp.find(ap,'period_id'),'Astra posted source',uuid.uuid4(),b.bc.awp.find(ap,'row_version')))
    b.act(cur,'PREPARE',b.doc(cur,pid));b.act(cur,'APPROVE',b.doc(cur,pid))
    assert D(b.doc(cur,pid)['attendance_total'])==1000
    return dict(contractor=cid,payroll=pid,start=start,end=day)

def sewn(cur,today,cid,label):
    prod=ins.wip_source.b.chain.production;old=prod.CONTRACTOR
    try:
        prod.CONTRACTOR=cid
        return ins.wip_source.b.two_size_fixture(cur,today+timedelta(days=1),label,q1=7,q2=3)
    finally:prod.CONTRACTOR=old

def create_activate(cur,start,end):
    preview=call(cur,'select erp.preview_attendance_hpp_pool_v1(%s,%s)',(start,end))
    made=call(cur,'select erp.create_attendance_hpp_pool_v1(%s::jsonb,%s)',(json.dumps(dict(period_start=str(start),period_end=str(end),reason='Astra fixed pool closure oracle')),uuid.uuid4()))
    active=call(cur,'select erp.activate_attendance_hpp_pool_v1(%s,%s,%s,%s)',(made['pool_id'],'Astra observed sources',uuid.uuid4(),made['row_version']))
    return dict(preview=preview,made=made,active=active,id=made['pool_id'])

def observe(cur,pids,day):
    admin(cur)
    return dict(pools=[r[0]for r in cur.execute('select to_jsonb(x)from erp.attendance_hpp_pools x where id=any(%s::uuid[])order by id',(pids,)).fetchall()],
        sources=[r[0]for r in cur.execute('select to_jsonb(x)from erp.attendance_hpp_pool_sources x where pool_id=any(%s::uuid[])order by pool_id,payroll_id',(pids,)).fetchall()],
        allocations=[r[0]for r in cur.execute('select to_jsonb(x)from erp.attendance_hpp_pool_allocations x where pool_id=any(%s::uuid[])order by pool_id,sewing_terminal_event_id',(pids,)).fetchall()],
        detectors=detectors(cur))

def cases(cur,today):
    day=today-timedelta(days=1)
    def overlap():
        a=pay_source(cur,today,day-timedelta(days=1));b=pay_source(cur,today,day)
        policy(cur,a['contractor'],day-timedelta(days=2));policy(cur,b['contractor'],day-timedelta(days=2))
        sewn(cur,today,a['contractor'],'AS-POOL-A');sewn(cur,today,b['contractor'],'AS-POOL-B')
        one=create_activate(cur,a['start'],day);two=create_activate(cur,b['start'],day)
        w=observe(cur,[one['id'],two['id']],day);w.update(first=one,second=two,payrolls=[a,b],scope='Both actual costs 1000; shared destination alone is not duplicate cost')
        save('CP17_POOL_DISTINCT_PERIODS_FIRST',w)
        check(len(w['sources'])==2 and {x['payroll_id']for x in w['sources']}=={a['payroll'],b['payroll']},'Each actual payroll accrual appears exactly once',witness=w)
        check(sum(D(str(x['allocated_amount']))for x in w['allocations'])==2000,'Two legitimate1000 costs allocate2000 total, not4000',witness=w)
        return w
    def late_policy():
        a=pay_source(cur,today,day);policy(cur,a['contractor'],day-timedelta(days=1));sewn(cur,today,a['contractor'],'AS-POOL-POL-A')
        admin(cur);tag='AS-NOPOL-'+uuid.uuid4().hex[:10]
        cid=str(cur.execute('insert into erp.contractors(contractor_code,contractor_name,attendance_required)values(%s,%s,true)returning id',(tag,tag)).fetchone()[0])
        sewn(cur,today,cid,'AS-POOL-POL-C')
        one=create_activate(cur,day,day);before=observe(cur,[one['id']],day)
        assert D(str(one['preview']['numerator_amount']))==1000 and int(one['preview']['denominator_qty'])==10,one
        outcome=attempt(cur,lambda:policy(cur,cid,day-timedelta(days=1)))
        validation=attempt(cur,lambda:call(cur,'select erp.validate_attendance_hpp_pool_v1(%s)',(one['id'],)))
        after=observe(cur,[one['id']],day)
        w=dict(pool=one,excluded_contractor=cid,before=before,policy_attempt=outcome,validation=validation,after=after)
        save('CP17_POOL_POLICY_AFTER_ACTIVE_FIRST',w)
        if not outcome['accepted']:
            check(any(x in outcome['message'].lower() for x in ('pool','active','hpp')),'Policy rejected by relevant pool dependency',witness=w)
        else:
            check(validation['accepted'],'Accepted policy must not leave an ACTIVE pool with STALE_POOL_INPUT',witness=w)
        return w
    return [wrap('CP17-ASTRA-POOL-02-DISTINCT-PERIOD-CONSERVATION',overlap),wrap('CP17-ASTRA-POOL-03-POLICY-AFTER-ACTIVE',late_policy)]
