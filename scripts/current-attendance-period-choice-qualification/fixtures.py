"""Prepared Native fixtures/oracles; no DB connection and no posted-row seeds.

Masters and DRAFT headers are explicit administrative fixtures as in accepted
R3/HPP01. Attendance, approval, physical/cost/journal posts use existing writers.
Native sessions with administrative actor claims are not real Auth/browser.
"""
from datetime import timedelta,datetime,time
from decimal import Decimal as D
from zoneinfo import ZoneInfo
import json,uuid
import cp7_r3_hpp_pool_cases as hp
from cp7_attendance_period_choice import composition

REASON='D17-19C sumber, tanggal dan pilihan biaya absensi ditinjau Owner'
AMOUNT=D('1000.03');CENTS=100003

def one(cur,sql,args=()):return cur.execute(sql,args).fetchone()[0]
def admin(cur):hp.b.api.admin(cur)
def census(cur):admin(cur);return composition.runtime()[4]._data(cur)
def native(cur,sql,args=()):return hp.native_call(cur,sql,args)
def body(day,choice=None,output=None,reason=REASON):
    return dict(period_start=str(day),period_end=str(day),choice=choice,
        output_start=None if output is None else str(output),output_end=None if output is None else str(output),reason=reason)
def call(cur,subject,rpc,args):
    hp.auth.actor(cur,subject)
    placeholders={'erp_cp7_preview_attendance_choice_v1':'%s,%s::jsonb',
        'erp_cp7_save_attendance_choice_v1':'%s,%s::jsonb,%s::uuid',
        'erp_cp7_get_attendance_choice_v1':'%s::date,%s::date,%s::integer,%s::integer'}
    try:return one(cur,'select public.'+rpc+'('+placeholders[rpc]+')',args)
    finally:
        if cur.connection.info.transaction_status.name!='INERROR':admin(cur)
def review(cur,subject,action,payload):return call(cur,subject,'erp_cp7_preview_attendance_choice_v1',(action,json.dumps(payload)))
def command(cur,subject,action,payload,key=None):return call(cur,subject,'erp_cp7_save_attendance_choice_v1',(action,json.dumps(payload),str(key or uuid.uuid4())))
def save(cur,subject,action,payload,key=None):
    r=review(cur,subject,action,payload);return command(cur,subject,action,dict(payload,review_token=r['review_token']),key)
def read(cur,subject,day,offset=0,limit=25):return call(cur,subject,'erp_cp7_get_attendance_choice_v1',(day,day,offset,limit))
def refused(cur,fn,code):
    before=census(cur);detail=hp.auth.refused(cur,fn,code)
    assert census(cur)==before,('S03_REFUSAL_CHANGED_FULL_BUSINESS_ROWS_OR_SEQUENCES',code)
    return detail

def quiet_days(cur,today,count=2,before=None):
    """Choose empty exact periods; no deletion/blanket exclusions to obtain quiet.

    Every Native date/cutover guard remains authoritative. A date rejected by a
    valid writer is an actual INCOMPLETE fixture, never silently retried/shifted.
    """
    admin(cur);days=[]
    for offset in range(5,91):
        day=today-timedelta(days=offset)
        if before is not None and day>=before:continue
        occupied=one(cur,"""select exists(select 1 from erp.payroll_settlements where period_start<=%s and period_end>=%s)
        or exists(select 1 from erp.sewing_terminal_events where erp._cp3_business_date(physical_at)=%s)
        or exists(select 1 from erp.attendance_hpp_pools where period_start<=%s and period_end>=%s)
        or exists(select 1 from cp7_attendance_choice.decisions_v1 where period_start<=%s and period_end>=%s)""",(day,day,day,day,day,day,day))
        if not occupied:days.append(day)
        if len(days)==count:return sorted(days)
    raise ValueError('S03_PREPARED_FIXTURE_NO_LAWFUL_QUIET_PERIOD_AVAILABLE')

def earned(cur,contractor,day,amount=AMOUNT,*,approve=True):
    """Parameterized accepted R3 attendance writer sequence, exact daily cents.

    Only the DRAFT payroll header is created administratively. No attendance
    item, approved status, WIP journal or payable is inserted as a posted seed.
    """
    c=hp.cp17();tag='S03-'+uuid.uuid4().hex[:12]
    admin(cur);hp.set_closed(cur,day-timedelta(days=1))
    payroll=str(one(cur,'insert into erp.payroll_settlements(payroll_number,contractor_id,period_start,period_end,payment_date)values(%s,%s,%s,%s,%s)returning id',(tag,contractor,day,day,day)))
    w=c.s.native(cur,'select public.erp_save_worker_roster_v1(%s::jsonb,%s,null)',(json.dumps(dict(contractor_id=contractor,worker_code=tag,worker_name=tag,job_description='Jahit',pay_scheme='DAILY',initial_daily_rate=str(amount),rate_effective_from=str(day),joined_at=str(day),is_active=True,reason=REASON)),uuid.uuid4()))
    ap=c.s.native(cur,'select public.erp_save_attendance_period_v1(%s::jsonb,%s,null,false)',(json.dumps(dict(contractor_id=contractor,period_number=tag+'-ATT',period_start=str(day),period_end=str(day),pay_date=str(day),reason=REASON,attendance=[dict(worker_id=str(c.bc.awp.find(w,'worker_id')),attendance_date=str(day),status='PRESENT')])),uuid.uuid4()))
    c.s.native(cur,'select public.erp_post_attendance_period_v1(%s,%s,%s,%s)',(c.bc.awp.find(ap,'period_id'),REASON,uuid.uuid4(),c.bc.awp.find(ap,'row_version')))
    c.s.act(cur,'PREPARE',c.s.doc(cur,payroll))
    if approve:c.s.act(cur,'APPROVE',c.s.doc(cur,payroll))
    admin(cur)
    assert D(str(c.s.doc(cur,payroll)['attendance_total']))==amount
    return payroll

def source(cur,today,*,day=None,contractor=None):
    if day is None:day=quiet_days(cur,today,1)[0]
    m=contractor or hp.contractor(cur,'S03-'+uuid.uuid4().hex[:12]);hp.policy(cur,m,day-timedelta(days=1));p=earned(cur,m,day)
    admin(cur);capture=native(cur,'select cp7_attendance_choice.capture_v1(%s,%s,true)',(day,day))
    assert capture['amount_cents']==str(CENTS)and len(capture['native_manifest']['sources'])==1,capture
    return dict(day=day,contractor=m,payroll=p,owner=hp.owner(cur),capture=capture)

def sewn(cur,contractor,label,day):
    """Same retained physical writer, lawful compact clock for today's output.

    Only fixture timestamps are chosen; server time/date/guards are untouched.
    Times remain ordered strictly between actual WIB midnight and actual now.
    """
    admin(cur);current=f_now=one(cur,'select clock_timestamp()')
    if day!=current.astimezone(ZoneInfo('Asia/Jakarta')).date():return hp.sewn(cur,contractor,label,day)
    start=datetime.combine(day,time.min,ZoneInfo('Asia/Jakarta'))+timedelta(seconds=1)
    end=f_now-timedelta(seconds=1);span=end-start
    micros=(span.days*86400+span.seconds)*1000000+span.microseconds
    if micros<10000:raise ValueError('S03_CURRENT_DAY_PHYSICAL_CLOCK_NOT_YET_AVAILABLE')
    def when(hour,minute=0):return start+timedelta(microseconds=micros*(hour*60+minute)//720)
    src=hp.cp17().instal.wip_source.b;prod=src.chain.production;old=prod.CONTRACTOR
    try:
        prod.CONTRACTOR=contractor;g=src.two_size_fixture(cur,day+timedelta(days=2),label,q1=7,q2=3,clock=when)
    finally:prod.CONTRACTOR=old
    assert g['day']==day;return g

def pending_work(cur,contractor,day):
    """Native work post without its terminal, prepared before the guarded call."""
    c=hp.cp17();src=c.instal.wip_source.b;prod=src.chain.production;old=prod.CONTRACTOR;result={}
    def work(cur,po,group,batch,yields,when):
        snapshot,completion=str(uuid.uuid4()),str(uuid.uuid4());quantity=sum(n for _,_,n in yields)
        admin(cur)
        cur.execute('insert into erp.po_work_component_snapshots(id,po_id,work_component_id,sequence_no,rate_per_pcs_snapshot,committed_at)values(%s,%s,%s,1,0,%s)',(snapshot,po,prod.COMPONENT,when(9,30)))
        src.chain.peer.ordinary(cur)
        cur.execute("insert into erp.work_completion_events(id,completion_number,po_id,contractor_id,cutting_group_id,physical_at,status,notes,created_by)values(%s,%s,%s,%s,%s,%s,'DRAFT',%s,%s)",(completion,'S03-WC-'+completion,po,contractor,group,when(10),REASON,src.chain.base.OPERATOR_APP))
        cur.execute('insert into erp.work_completion_lines(completion_id,po_component_snapshot_id,work_component_id,qty_completed,qty_payable,rate_snapshot)values(%s,%s,%s,%s,%s,0)',(completion,snapshot,prod.COMPONENT,quantity,quantity))
        cur.execute('select erp.post_work_completion(%s)',(completion,));result['work']=completion
    try:
        prod.CONTRACTOR=contractor;g=src.two_size_fixture(cur,day+timedelta(days=2),'S03-PENDING',q1=7,q2=3,work_setup=work)
    finally:prod.CONTRACTOR=old
    assert g['day']==day;return dict(g,**result)

def destinations(cur,start,end):
    """Independent facts SQL implements the declared Native eligibility contract.
    Neither preview figures nor the carried pool response is a money oracle.
    """
    admin(cur)
    return cur.execute("""select e.id::text,e.po_id::text,e.qty_signed,e.physical_at
     from erp.sewing_terminal_events e join erp.work_completion_events w on w.id=e.source_work_completion_id
     join lateral(select p.*from erp.contractor_hpp_policy_versions p where p.contractor_id=e.contractor_id
       and p.effective_from<=%s and(p.effective_to is null or p.effective_to>=%s)order by p.effective_from desc,p.id desc limit 1)p on true
     where e.event_kind='SELESAI_DIJAHIT'and erp._cp3_business_date(e.physical_at)between %s and %s
      and w.status='POSTED'and p.contractor_role_snapshot='MANDOR'and p.attendance_required_snapshot and not p.is_special
      and not exists(select 1 from erp.sewing_terminal_events r where r.event_kind='REVERSAL'and r.reversal_of_id=e.id)
     order by e.physical_at,e.id""",(start,end,start,end)).fetchall()

def expected_allocations(facts,cents=CENTS):
    denominator=sum(row[2]for row in facts);assert denominator>0
    previous=0;running=0;result={}
    for event,po,qty,_ in facts:
        running+=qty;current=cents*running//denominator
        result[event]=dict(po=po,cents=current-previous);previous=current
    assert sum(x['cents']for x in result.values())==cents
    return denominator,result

def assert_pool(cur,fixture,result,output):
    admin(cur);pool=one(cur,'select to_jsonb(p)from erp.attendance_hpp_pools p where id=%s',(result['pool_id'],))
    facts=destinations(cur,output,output);denominator,expected=expected_allocations(facts)
    actual={str(e):dict(po=str(po),cents=int(D(amount)*100))for e,po,amount in cur.execute('select sewing_terminal_event_id,po_id,allocated_amount from erp.attendance_hpp_pool_allocations where pool_id=%s',(pool['id'],))}
    assert actual==expected,(actual,expected)
    assert(pool['period_start'],pool['period_end'],pool['status'],D(str(pool['numerator_amount'])),pool['denominator_qty'])==(str(fixture['day']),str(fixture['day']),'ACTIVE',AMOUNT,denominator),pool
    assert native(cur,'select erp.validate_attendance_hpp_pool_v1(%s)->>\'validation\'',(pool['id'],))=='PASS'
    admin(cur);j=one(cur,'select to_jsonb(j)from erp.journal_entries j where id=%s',(pool['post_journal_entry_id'],))
    assert j['economic_date']==str(output)and j['transaction_date']==str(one(cur,'select erp.resolve_accounting_transaction_date(%s)',(output,))),j
    links=cur.execute('select payroll_id::text,original_debit_journal_line_id::text,attendance_amount from erp.attendance_hpp_pool_sources where pool_id=%s',(pool['id'],)).fetchall()
    source=fixture['capture']['native_manifest']['sources'][0]
    assert links==[(fixture['payroll'],source['original_debit_journal_line_id'],AMOUNT)],links
    return dict(pool=pool,denominator=denominator,by_event=expected,journal=j)
