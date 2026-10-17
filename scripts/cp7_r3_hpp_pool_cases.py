"""R3-04 (Sol KNOWN-R2-POOL-UI S1, Astra ASTRA-C17-07 remainder; owner D16-1): the attendance HPP pool lifecycle screen.

Native, race and real-Auth HTTP cases for scripts/cp7-src/hpp-pool/pool.sql (cp7_hpp_pool_bundle.py), spliced into the CP17
harness through cp7_r3_cases.py. The fixture is the HPP01 one of cp7_cp17_fix_cases.py (Astra's pool witness), rebuilt here
per period: Mandor A has one approved attendance day of 1000 (the Native accrual debits WIP) and a normal-Mandor HPP policy,
and sews 10 pieces (7 + 3) on a PO of his own on that day; Mandor C sews 10 pieces on another PO the same day but has no HPP
policy yet, so the Native preview is 1000 / 10 = 100 per piece. The "source correction" after a cancel is C's policy (through
the accepted Native policy writer), which makes the replacement 1000 / 20 = 50 per piece, 500 to each PO.
Oracles read the erp tables directly (attendance_hpp_pools and its allocations and sources, journal_entries/journal_lines,
audit_logs, the Native ACTIVE-allocation view, payroll_settlements and sewing_terminal_events for the preview), the Native
validator, and the boundary snapshot for every refusal; never the facade's answer alone.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import date,timedelta
from decimal import Decimal as D
import json,threading,uuid
import psycopg
import cp7_snapshot_cases as auth
import cp7_master_cases as master
b=auth.b
refused=auth.refused

NATIVE=['CP17_R3_04_HPP_POOL_PREVIEW_READY_AND_BLOCKED','CP17_R3_04_HPP_POOL_CREATE_ACTIVATE_CANCEL_EQUALS_NATIVE',
        'CP17_R3_04_HPP_POOL_DRAFT_VOID_NO_JOURNAL','CP17_R3_04_HPP_POOL_CANCEL_SOURCE_CORRECTION_REPLACEMENT',
        'CP17_R3_04_HPP_POOL_CLOSED_PERIOD_REFUSED_ATOMICALLY','CP17_R3_04_HPP_POOL_PERMISSION_REMOVED_BETWEEN_READ_AND_SAVE',
        'CP17_R3_04_HPP_POOL_SAME_UUID_REPLAYS_ONCE','CP17_R3_04_HPP_POOL_CHANGED_REVIEW_TOKEN_REFUSED',
        'CP17_R3_04_HPP_POOL_OWNER_ADMIN_ONLY_AND_FIELDS','CP17_R3_04_HPP_POOL_FACADE_PRIVATE_AND_IMMUTABLE']
RACES=['CP17_RACE_R3_04_HPP_POOL_TWO_TABS_ACTIVATE_ONE_WINS','CP17_RACE_R3_04_HPP_POOL_TWO_TABS_CREATE_ONE_WINS',
       'CP17_RACE_R3_04_HPP_POOL_SAME_UUID_TWO_SESSIONS_ONE_EFFECT']
HTTP=['CP17_HTTP_R3_04_HPP_POOL_LIFECYCLE_AND_ROLES','CP17_HTTP_R3_04_HPP_POOL_PERMISSION_AND_CLOSED_PERIOD']
BROWSER=['CP17_BROWSER_R3_04_HPP_POOL_DESKTOP','CP17_BROWSER_R3_04_HPP_POOL_MOBILE']
FUNCTIONS=('erp_cp7_get_hpp_pools_v1','erp_cp7_save_hpp_pool_v1')
REASON='CP17 R3-04 pool absensi'

def one(cur,sql,args=()):return cur.execute(sql,args).fetchone()[0]
def cp17():
    import cp7_cp17_fix_cases as m
    return m
def native_call(cur,sql,args):
    """The database owner with OWNER claims (fixture/oracle only), as the HPP01 fixture calls the Native pool functions."""
    return cp17().instal.physical.source.fixture_journal_call(cur,sql,args)
def set_closed(cur,through):cp17().instal.physical.source.receipt.aa.prior.set_open_period(cur,through)

# ---------------------------------------------------------------- fixture (HPP01, per period)
def contractor(cur,tag):
    b.api.admin(cur)
    return str(one(cur,"insert into erp.contractors(contractor_code,contractor_name,contractor_type,attendance_required)values(%s,%s,'MANDOR',true)returning id",(tag,tag)))
def policy(cur,cid,effective):
    return cp17().s.native(cur,'select public.erp_set_contractor_hpp_policy_v1(%s::jsonb,%s,null)',(json.dumps(dict(contractor_id=cid,effective_from=str(effective),
        is_special=False,attendance_required=True,reason='CP17 R3-04 kebijakan mandor biasa')),uuid.uuid4()))
def attendance_payroll(cur,cid,tag,day):
    """One earned attendance day 1000 on `day`, approved (the Native accrual debits WIP)."""
    c=cp17();s,bc=c.s,c.bc
    set_closed(cur,day-timedelta(days=1))
    pid=str(one(cur,'insert into erp.payroll_settlements(payroll_number,contractor_id,period_start,period_end,payment_date)values(%s,%s,%s,%s,%s)returning id',(tag,cid,day,day,day)))
    w=s.native(cur,'select public.erp_save_worker_roster_v1(%s::jsonb,%s,null)',(json.dumps(dict(contractor_id=cid,worker_code=tag,worker_name=tag,job_description='Jahit',pay_scheme='DAILY',
        initial_daily_rate=1000,rate_effective_from=str(day),joined_at=str(day),is_active=True,reason='CP17 R3-04 satu hari kerja')),uuid.uuid4()))
    ap=s.native(cur,'select public.erp_save_attendance_period_v1(%s::jsonb,%s,null,false)',(json.dumps(dict(contractor_id=cid,period_number=tag+'-ATT',period_start=str(day),period_end=str(day),
        pay_date=str(day),reason='CP17 R3-04 absensi nyata',attendance=[dict(worker_id=str(bc.awp.find(w,'worker_id')),attendance_date=str(day),status='PRESENT')])),uuid.uuid4()))
    s.native(cur,'select public.erp_post_attendance_period_v1(%s,%s,%s,%s)',(bc.awp.find(ap,'period_id'),'CP17 R3-04 absensi diposting',uuid.uuid4(),bc.awp.find(ap,'row_version')))
    s.act(cur,'PREPARE',s.doc(cur,pid));s.act(cur,'APPROVE',s.doc(cur,pid));assert D(s.doc(cur,pid)['attendance_total'])==1000
    return pid
def sewn(cur,cid,label,day):
    """10 pieces (7 + 3) cut, picked up and SELESAI DIJAHIT by this Mandor on `day` (cp6_bd_probe two_size_fixture)."""
    src=cp17().instal.wip_source.b;prod=src.chain.production;old=prod.CONTRACTOR
    try:
        prod.CONTRACTOR=cid;g=src.two_size_fixture(cur,day+timedelta(days=2),label,q1=7,q2=3)
    finally:prod.CONTRACTOR=old
    assert g['day']==day,(g['day'],day)
    return g
def fixture(cur,today,offset=1):
    day=today-timedelta(days=offset);tag=uuid.uuid4().hex[:8].upper()
    a=contractor(cur,'R304-A-'+tag);pid=attendance_payroll(cur,a,'R304-'+tag,day);policy(cur,a,day-timedelta(days=1));ga=sewn(cur,a,'R304-A',day)
    c=contractor(cur,'R304-C-'+tag);gc=sewn(cur,c,'R304-C',day);b.api.admin(cur)
    return dict(day=day,a=a,c=c,c_code='R304-C-'+tag,payroll=pid,po_a=ga['po'],po_c=gc['po'])
def owner(cur):return master.role_actor(cur,'OWNER')

# ---------------------------------------------------------------- facade calls
def read(cur,subject,start=None,end=None,offset=0,limit=20):
    auth.actor(cur,subject);r=one(cur,'select public.erp_cp7_get_hpp_pools_v1(%s,%s,%s,%s)',(offset,limit,start,end));b.api.admin(cur);return r
def save(cur,subject,action,payload,key=None):
    auth.actor(cur,subject)
    r=one(cur,'select public.erp_cp7_save_hpp_pool_v1(%s,%s::jsonb,%s)',(action,json.dumps(payload),str(key or uuid.uuid4())));b.api.admin(cur);return r
def create_body(pv,reason=REASON,correction=None):
    return dict(period_start=pv['period_start'],period_end=pv['period_end'],correction_of_pool_id=correction,review_token=pv['review_token'],reason=reason)
def pool_body(p,reason):return dict(pool_id=p['id'],review_token=p['review_token'],reason=reason)
def pool_of(w,pid):
    found=[p for p in w['pools'] if p['id']==pid];assert len(found)==1,('CP17_R3_04_POOL_NOT_ON_FIRST_PAGE',pid);return found[0]
def facade_pool(cur,subject,pid):return pool_of(read(cur,subject),pid)

# ---------------------------------------------------------------- oracles (erp tables only)
def native_pools(cur,day):
    b.api.admin(cur)
    rows=cur.execute("""select id::text,status,numerator_amount,denominator_qty,unit_cost_per_sewn_pcs,correction_of_pool_id::text,post_journal_entry_id::text,
        cancellation_journal_entry_id::text,row_version,reason,cancellation_reason,source_manifest_sha256,pool_number
        from erp.attendance_hpp_pools where period_start=%s and period_end=%s order by created_at,id""",(day,day)).fetchall()
    keys=('id','status','numerator','denominator','unit','correction_of','journal','reversal','row_version','reason','cancellation_reason','sha','pool_number')
    return [dict(zip(keys,r)) for r in rows]
def allocations(cur,pool):
    b.api.admin(cur)
    return {str(p):D(a) for p,a in cur.execute('select po_id,sum(allocated_amount) from erp.attendance_hpp_pool_allocations where pool_id=%s group by po_id',(pool,)).fetchall()}
def journal(cur,jid):
    """Status and source of one journal, and its lines summed per (account, PO, contractor)."""
    b.api.admin(cur)
    head=cur.execute('select status,source_type,source_id::text,reversal_of_id::text,economic_date from erp.journal_entries where id=%s',(jid,)).fetchone()
    lines={(str(a),None if p is None else str(p),None if c is None else str(c)):(D(d),D(k)) for a,p,c,d,k in cur.execute(
        'select account_id,po_id,contractor_id,sum(debit),sum(credit) from erp.journal_lines where journal_entry_id=%s group by 1,2,3',(jid,)).fetchall()}
    return dict(status=head[0],source_type=head[1],source_id=head[2],reversal_of=head[3],economic_date=head[4],lines=lines)
def po_debits(j):
    out={}
    for (_,po,_),(d,_) in j['lines'].items():
        if po is not None and d>0:out[po]=out.get(po,D(0))+d
    return out
def net_zero(a,b2):
    keys=set(a['lines'])|set(b2['lines'])
    return all(a['lines'].get(k,(D(0),D(0)))[0]-a['lines'].get(k,(D(0),D(0)))[1]+b2['lines'].get(k,(D(0),D(0)))[0]-b2['lines'].get(k,(D(0),D(0)))[1]==0 for k in keys)
def active_view(cur,po):
    """Native erp.v_attendance_hpp_active_allocation_by_po: the attendance cost an ACTIVE pool gives this PO."""
    b.api.admin(cur);return D(one(cur,'select coalesce(sum(attendance_hpp_amount),0) from erp.v_attendance_hpp_active_allocation_by_po where po_id=%s',(po,)))
def lifecycle(cur,pool):
    b.api.admin(cur)
    return [tuple(r) for r in cur.execute("""select new_data->>'lifecycle_action',change_reason from erp.audit_logs
        where entity_type='attendance_hpp_pools' and entity_id=%s order by changed_at,id""",(pool,)).fetchall()]
def requests_of(cur,key):b.api.admin(cur);return one(cur,'select count(*) from cp7_hpp_pool.requests where request_id=%s',(str(key),))
def po_number(cur,po):b.api.admin(cur);return one(cur,'select po_number from erp.production_orders where id=%s',(po,))
def oracle_preview(cur,day):
    """The oracle's own figures for one exact period: approved/paid attendance of normal-Mandor policies covering it, and the
    SELESAI DIJAHIT pieces (WIB day, posted work, not reversed) of normal-Mandor policies covering it."""
    b.api.admin(cur)
    pol="""join lateral(select p.contractor_role_snapshot,p.attendance_required_snapshot,p.is_special from erp.contractor_hpp_policy_versions p
        where p.contractor_id=%s.contractor_id and p.effective_from<=%%(d)s and(p.effective_to is null or p.effective_to>=%%(d)s)
        order by p.effective_from desc,p.id desc limit 1)p on p.contractor_role_snapshot='MANDOR' and p.attendance_required_snapshot and not p.is_special"""
    cost=one(cur,"select coalesce(sum(ps.attendance_total),0) from erp.payroll_settlements ps "+pol%'ps'+
        " where ps.status in('APPROVED','PAID') and ps.period_start=%(d)s and ps.period_end=%(d)s and ps.attendance_total>0",dict(d=day))
    pcs=one(cur,"select coalesce(sum(e.qty_signed),0) from erp.sewing_terminal_events e join erp.work_completion_events w on w.id=e.source_work_completion_id "+pol%'e'+
        " where e.event_kind='SELESAI_DIJAHIT' and (e.physical_at at time zone 'Asia/Jakarta')::date=%(d)s and w.status='POSTED'"
        " and not exists(select 1 from erp.sewing_terminal_events r where r.reversal_of_id=e.id)",dict(d=day))
    return D(cost),int(pcs)
def same(cur,p,row):
    """The facade's pool equals the Native row: figures, status, version, lineage, journals, reasons, sources, cost per PO."""
    b.api.admin(cur)
    jn=lambda j:None if j is None else one(cur,'select journal_number from erp.journal_entries where id=%s',(j,))
    got=(p['id'],p['pool_number'],p['status'],D(p['numerator_amount']),p['denominator_qty'],None if p['unit_cost_per_sewn_pcs'] is None else D(p['unit_cost_per_sewn_pcs']),
         p['row_version'],(p['correction_of'] or {}).get('id'),p['journal_number'],p['reversal_journal_number'],p['reason'],p['cancellation_reason'])
    want=(row['id'],row['pool_number'],row['status'],D(row['numerator']),int(row['denominator']),None if row['unit'] is None else D(row['unit']),
          int(row['row_version']),row['correction_of'],jn(row['journal']),jn(row['reversal']),row['reason'],row['cancellation_reason'])
    assert got==want,('CP17_R3_04_FACADE_NOT_NATIVE',got,want)
    assert {a['po_id']:D(a['amount']) for a in p['allocations']}==allocations(cur,row['id'])
    assert p['source_count']==one(cur,'select count(*) from erp.attendance_hpp_pool_sources where pool_id=%s',(row['id'],))
    return True


def cases(cur,today):
    c=cp17()
    def preview_ready_and_blocked():
        f=fixture(cur,today);day=f['day'];o=owner(cur)
        w=read(cur,o,day,day);pv=w['preview'];cost,pcs=oracle_preview(cur,day)
        assert (cost,pcs)==(D(1000),10),('CP17_R3_04_FIXTURE',cost,pcs)
        assert (pv['status'],D(pv['numerator_amount']),pv['denominator_qty'],D(pv['unit_cost_per_sewn_pcs']),pv['source_count'],pv['blocker'],pv['can_create'])==('READY',cost,pcs,cost/pcs,1,None,True),pv
        assert pv['pos']==[dict(po_id=f['po_a'],po_number=po_number(cur,f['po_a']),sewing_qty=10)],pv['pos']
        b.api.admin(cur);assert pv['manifest_sha256']==one(cur,'select erp._cp3_manifest_sha256(erp._build_attendance_hpp_manifest_v1(%s,%s))',(day,day))
        assert w['closed_through']==str(one(cur,'select closed_through from erp.accounting_period_control where singleton_id=1'))
        # A period without any attendance cost, and one whose attendance payroll has no HPP policy: refusals without figures.
        empty=read(cur,o,date(2001,1,1),date(2001,1,1))['preview']
        x=contractor(cur,'R304-X-'+uuid.uuid4().hex[:8].upper());day2=day-timedelta(days=2);attendance_payroll(cur,x,'R304-X-'+uuid.uuid4().hex[:8],day2)
        missing=read(cur,o,day2,day2)['preview']
        figures=('numerator_amount','denominator_qty','unit_cost_per_sewn_pcs','source_count','destination_count','po_count','manifest_sha256','review_token')
        for blocked,code in((empty,'NO_ATTENDANCE_COST'),(missing,'MISSING_POLICY')):
            assert blocked['status']=='BLOCKED' and blocked['blocker']['code']==code and all(blocked[k] is None for k in figures) and blocked['pos']==[] and not blocked['can_create'],blocked
        # Reading changes nothing (the attendance payroll above is fixture; the snapshot is taken again after it).
        after=b.boundary.snapshot(cur);read(cur,o,day,day);assert b.boundary.snapshot(cur)==after
        refused(cur,lambda:read(cur,o,day,None),'CP7_HPP_POOL_FIELDS');refused(cur,lambda:read(cur,o,limit=51),'CP7_HPP_POOL_FIELDS')
        refused(cur,lambda:read(cur,o,day,day-timedelta(days=1)),'CP7_HPP_POOL_FIELDS')
        return dict(status='PASS',finding='R3-04',ready=dict(cost=str(cost),pcs=pcs,per_pcs=pv['unit_cost_per_sewn_pcs']),oracle_equal=True,
                    native_manifest_hash_equal=True,blocked=[empty['blocker']['code'],missing['blocker']['code']],blocked_without_figures=True,
                    read_side_effect_free=True)
    def lifecycle_equals_native():
        f=fixture(cur,today);day=f['day'];o=owner(cur);pv=read(cur,o,day,day)['preview']
        cr=save(cur,o,'CREATE',create_body(pv));rows=native_pools(cur,day)
        assert len(rows)==1 and rows[0]['id']==cr['pool_id'] and rows[0]['status']=='DRAFT' and rows[0]['sha']==pv['manifest_sha256'] and rows[0]['reason']==REASON,rows
        assert (D(rows[0]['numerator']),rows[0]['denominator'],D(rows[0]['unit']))==(D(1000),10,D(100)) and rows[0]['journal'] is None
        p=facade_pool(cur,o,cr['pool_id']);same(cur,p,rows[0]);assert p['actions']==['ACTIVATE','CANCEL'] and allocations(cur,cr['pool_id'])=={f['po_a']:D(1000)}
        assert active_view(cur,f['po_a'])==0
        ac=save(cur,o,'ACTIVATE',pool_body(p,'CP17 R3-04 sumber diperiksa'));rows=native_pools(cur,day)
        assert rows[0]['status']=='ACTIVE' and ac['journal_entry_id']==rows[0]['journal'] and ac['row_version']==rows[0]['row_version']==2,(ac,rows)
        posted=journal(cur,rows[0]['journal'])
        assert (posted['status'],posted['source_type'],posted['source_id'],str(posted['economic_date']))==('POSTED','ATTENDANCE_HPP_POOL',cr['pool_id'],str(day)),posted
        assert po_debits(posted)=={f['po_a']:D(1000)} and sum(d for d,_ in posted['lines'].values())==sum(k for _,k in posted['lines'].values())==D(1000),posted
        assert active_view(cur,f['po_a'])==1000
        native_call(cur,'select erp.validate_attendance_hpp_pool_v1(%s)',(cr['pool_id'],))
        p=facade_pool(cur,o,cr['pool_id']);same(cur,p,rows[0]);assert p['activation_reason']=='CP17 R3-04 sumber diperiksa' and p['actions']==['CANCEL']
        cx=save(cur,o,'CANCEL',pool_body(p,'CP17 R3-04 kebijakan mandor C belum ada'));rows=native_pools(cur,day)
        assert rows[0]['status']=='CANCELLED' and cx['reversal_journal_entry_id']==rows[0]['reversal'] and rows[0]['cancellation_reason']=='CP17 R3-04 kebijakan mandor C belum ada',rows
        original,reversal=journal(cur,rows[0]['journal']),journal(cur,rows[0]['reversal'])
        assert original['status']=='REVERSED' and reversal['status']=='POSTED' and net_zero(original,reversal),(original,reversal)
        assert active_view(cur,f['po_a'])==0
        native_call(cur,'select erp.validate_attendance_hpp_pool_v1(%s)',(cr['pool_id'],))
        p=facade_pool(cur,o,cr['pool_id']);same(cur,p,rows[0]);assert p['actions']==['REPLACE']
        assert lifecycle(cur,cr['pool_id'])==[('CREATE_DRAFT',REASON),('ACTIVATE','CP17 R3-04 sumber diperiksa'),('CANCEL_ACTIVE','CP17 R3-04 kebijakan mandor C belum ada')]
        return dict(status='PASS',finding='R3-04',facade_equals_native_rows=['DRAFT','ACTIVE','CANCELLED'],journal='ATTENDANCE_HPP_POOL Dr WIP PO 1000, reversed to zero',
                    native_view_active_cost=[0,1000,0],native_validator_pass=True,audit=['CREATE_DRAFT','ACTIVATE','CANCEL_ACTIVE'],reversal_of=reversal['reversal_of'])
    def draft_void():
        f=fixture(cur,today);day=f['day'];o=owner(cur);pv=read(cur,o,day,day)['preview']
        cr=save(cur,o,'CREATE',create_body(pv));p=facade_pool(cur,o,cr['pool_id'])
        vd=save(cur,o,'CANCEL',pool_body(p,'CP17 R3-04 draf salah periode'))
        rows=native_pools(cur,day);b.api.admin(cur)
        assert vd['status']==rows[0]['status']=='VOIDED' and vd['journal_entry_id'] is None and vd['reversal_journal_entry_id'] is None,(vd,rows)
        assert one(cur,"select count(*) from erp.journal_entries where source_type='ATTENDANCE_HPP_POOL' and source_id=%s",(cr['pool_id'],))==0
        p=facade_pool(cur,o,cr['pool_id']);same(cur,p,rows[0]);assert p['actions']==[] and p['cancellation_reason']=='CP17 R3-04 draf salah periode'
        before=b.boundary.snapshot(cur);pv=read(cur,o,day,day)['preview']
        assert pv['cancelled_pools']==[] and pv['existing_pool'] is None and pv['can_create']
        wrong=refused(cur,lambda:save(cur,o,'CREATE',create_body(pv,correction=cr['pool_id'])),'CP7_HPP_POOL_CORRECTION');c.unchanged(cur,before,'a voided draft is not a cancelled pool')
        again=save(cur,o,'CREATE',create_body(pv,'CP17 R3-04 draf yang benar'))
        assert [r['status'] for r in native_pools(cur,day)]==['VOIDED','DRAFT'] and again['pool_id']!=cr['pool_id']
        assert lifecycle(cur,cr['pool_id'])==[('CREATE_DRAFT',REASON),('VOID_DRAFT','CP17 R3-04 draf salah periode')]
        return dict(status='PASS',finding='R3-04',draft_removed_as='VOIDED (Dihapus draf)',journals=0,voided_not_a_correction_source=wrong,new_draft_same_period=True)
    def replacement():
        f=fixture(cur,today);day=f['day'];o=owner(cur);pv=read(cur,o,day,day)['preview']
        cr=save(cur,o,'CREATE',create_body(pv));p=facade_pool(cur,o,cr['pool_id']);save(cur,o,'ACTIVATE',pool_body(p,'CP17 R3-04 sumber diperiksa'))
        # While the pool is ACTIVE, the source correction is refused by the HPP01 guard and the payroll stays consumed.
        before=b.boundary.snapshot(cur)
        guard=refused(cur,lambda:policy(cur,f['c'],day-timedelta(days=1)),'CP7_HPP_POLICY_CHANGES_ACTIVE_POOL');c.unchanged(cur,before,'policy while the pool is ACTIVE')
        p=facade_pool(cur,o,cr['pool_id']);assert p['actions']==['CANCEL']
        save(cur,o,'CANCEL',pool_body(p,'CP17 R3-04 batalkan sebelum kebijakan baru'))
        policy(cur,f['c'],day-timedelta(days=1))
        cost,pcs=oracle_preview(cur,day);assert (cost,pcs)==(D(1000),20)
        w=read(cur,o,day,day);pv=w['preview'];old=pool_of(w,cr['pool_id'])
        assert old['actions']==['REPLACE'] and pv['cancelled_pools']==[dict(id=cr['pool_id'],pool_number=old['pool_number'])]
        assert (D(pv['numerator_amount']),pv['denominator_qty'],D(pv['unit_cost_per_sewn_pcs']),pv['po_count'])==(cost,pcs,D(50),2),pv
        before=b.boundary.snapshot(cur)
        bad=refused(cur,lambda:save(cur,o,'CREATE',create_body(pv,correction=str(uuid.uuid4()))),'CP7_HPP_POOL_CORRECTION');c.unchanged(cur,before,'correction of an unknown pool')
        rp=save(cur,o,'CREATE',create_body(pv,'CP17 R3-04 pengganti sesudah kebijakan C',cr['pool_id']))
        assert rp['correction_of_pool_id']==cr['pool_id']
        np=facade_pool(cur,o,rp['pool_id']);save(cur,o,'ACTIVATE',pool_body(np,'CP17 R3-04 pengganti diperiksa'))
        rows=native_pools(cur,day);assert [(r['id'],r['status'],r['correction_of']) for r in rows]==[(cr['pool_id'],'CANCELLED',None),(rp['pool_id'],'ACTIVE',cr['pool_id'])],rows
        assert allocations(cur,rp['pool_id'])=={f['po_a']:D(500),f['po_c']:D(500)}
        assert po_debits(journal(cur,rows[1]['journal']))=={f['po_a']:D(500),f['po_c']:D(500)}
        assert (active_view(cur,f['po_a']),active_view(cur,f['po_c']))==(D(500),D(500))
        native_call(cur,'select erp.validate_attendance_hpp_pool_v1(%s)',(rp['pool_id'],))
        w=read(cur,o);same(cur,pool_of(w,rp['pool_id']),rows[1]);same(cur,pool_of(w,cr['pool_id']),rows[0])
        assert pool_of(w,cr['pool_id'])['replaced_by']==[dict(id=rp['pool_id'],pool_number=rows[1]['pool_number'],status='ACTIVE')] and pool_of(w,cr['pool_id'])['actions']==[]
        assert pool_of(w,rp['pool_id'])['correction_of']==dict(id=cr['pool_id'],pool_number=rows[0]['pool_number'],status='CANCELLED')
        return dict(status='PASS',finding='R3-04',path='ACTIVE -> policy refused -> cancel -> policy for C -> replacement (correction_of) -> ACTIVE',
                    policy_refused_while_active=guard,unknown_correction_refused=bad,replacement='1000 / 20 = 50, PO A 500, PO C 500',native_validator_pass=True)
    def closed_period():
        f=fixture(cur,today);day=f['day'];o=owner(cur);pv=read(cur,o,day,day)['preview']
        set_closed(cur,day);before=b.boundary.snapshot(cur);n=one(cur,'select count(*) from cp7_hpp_pool.requests')
        w=read(cur,o,day,day);assert w['preview']['period_closed'] and not w['preview']['can_create'] and w['closed_through']==str(day)
        create=refused(cur,lambda:save(cur,o,'CREATE',create_body(w['preview'])),'CP7_HPP_POOL_PERIOD_CLOSED')
        c.unchanged(cur,before,'create in closed books');assert native_pools(cur,day)==[] and one(cur,'select count(*) from cp7_hpp_pool.requests')==n
        # One day before the period end the books are open: the same review creates the draft.
        set_closed(cur,day-timedelta(days=1));cr=save(cur,o,'CREATE',create_body(pv));p=facade_pool(cur,o,cr['pool_id'])
        set_closed(cur,day);before=b.boundary.snapshot(cur);rows=native_pools(cur,day)
        assert facade_pool(cur,o,cr['pool_id'])['actions']==[] and facade_pool(cur,o,cr['pool_id'])['period_closed']
        activate=refused(cur,lambda:save(cur,o,'ACTIVATE',pool_body(p,'CP17 R3-04 aktifkan')),'CP7_HPP_POOL_PERIOD_CLOSED')
        void=refused(cur,lambda:save(cur,o,'CANCEL',pool_body(p,'CP17 R3-04 hapus draf')),'CP7_HPP_POOL_PERIOD_CLOSED')
        c.unchanged(cur,before,'activate/cancel in closed books');assert native_pools(cur,day)==rows
        b.api.admin(cur);assert one(cur,"select count(*) from erp.journal_entries where source_type='ATTENDANCE_HPP_POOL' and source_id=%s",(cr['pool_id'],))==0
        set_closed(cur,day-timedelta(days=1));save(cur,o,'ACTIVATE',pool_body(p,'CP17 R3-04 aktifkan'));p=facade_pool(cur,o,cr['pool_id'])
        set_closed(cur,day);before=b.boundary.snapshot(cur);rows=native_pools(cur,day)
        cancel=refused(cur,lambda:save(cur,o,'CANCEL',pool_body(p,'CP17 R3-04 batalkan')),'CP7_HPP_POOL_PERIOD_CLOSED')
        c.unchanged(cur,before,'cancel an ACTIVE pool in closed books');assert native_pools(cur,day)==rows and rows[0]['status']=='ACTIVE'
        set_closed(cur,day-timedelta(days=1));x=save(cur,o,'CANCEL',pool_body(p,'CP17 R3-04 batalkan'));assert x['status']=='CANCELLED'
        return dict(status='PASS',finding='R3-04',closed_through_equal_to_period_end_refused=dict(create=create,activate=activate,void=void,cancel=cancel),
                    day_before_period_end_allowed=True,boundary_unchanged=True,no_request_row_on_refusal=True)
    def permission_removed():
        f=fixture(cur,today);day=f['day'];adm=master.role_actor(cur,'ADMIN');b.api.admin(cur)
        role=one(cur,'select role_id from erp.app_users where auth_user_id=%s',(adm,))
        w=read(cur,adm,day,day);assert w['can_manage'] is True and w['preview']['status']=='READY'
        cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='finance.hpp.manage'",(role,))
        before=b.boundary.snapshot(cur)
        create=refused(cur,lambda:save(cur,adm,'CREATE',create_body(w['preview'])),'CP7_HPP_POOL_DENIED');c.unchanged(cur,before,'create after the manage right was removed')
        assert native_pools(cur,day)==[] and read(cur,adm,day,day)['can_manage'] is False
        # A draft made by the owner; the ADMIN read it while still holding the right, then lost it before saving.
        cur.execute("insert into erp.app_role_permissions(role_id,permission_key)values(%s,'finance.hpp.manage')on conflict do nothing",(role,))
        o=owner(cur);cr=save(cur,o,'CREATE',create_body(read(cur,o,day,day)['preview']));p=facade_pool(cur,adm,cr['pool_id'])
        cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='finance.hpp.manage'",(role,))
        before=b.boundary.snapshot(cur);rows=native_pools(cur,day)
        activate=refused(cur,lambda:save(cur,adm,'ACTIVATE',pool_body(p,'CP17 R3-04 aktifkan')),'CP7_HPP_POOL_DENIED');c.unchanged(cur,before,'activate after the manage right was removed')
        assert native_pools(cur,day)==rows
        cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='finance.hpp.view'",(role,))
        view=refused(cur,lambda:read(cur,adm),'CP7_HPP_POOL_DENIED')
        return dict(status='PASS',finding='R3-04',admin_read_then_manage_removed=dict(create=create,activate=activate),read_without_manage_can_manage_false=True,
                    view_removed_read_refused=view,boundary_unchanged=True)
    def same_uuid():
        f=fixture(cur,today);day=f['day'];o=owner(cur);pv=read(cur,o,day,day)['preview'];key=uuid.uuid4()
        first=save(cur,o,'CREATE',create_body(pv),key);again=save(cur,o,'CREATE',create_body(pv),key)
        assert first==again and len(native_pools(cur,day))==1 and requests_of(cur,key)==1
        before=b.boundary.snapshot(cur)
        changed=refused(cur,lambda:save(cur,o,'CREATE',create_body(pv,'CP17 R3-04 alasan lain'),key),'CP7_HPP_POOL_REQUEST_CHANGED')
        other=refused(cur,lambda:save(cur,o,'CANCEL',dict(pool_id=first['pool_id'],review_token=pv['review_token'],reason=REASON),key),'CP7_HPP_POOL_REQUEST_CHANGED')
        c.unchanged(cur,before,'same request id with another payload')
        p=facade_pool(cur,o,first['pool_id']);k2=uuid.uuid4()
        a1=save(cur,o,'ACTIVATE',pool_body(p,'CP17 R3-04 aktifkan'),k2);a2=save(cur,o,'ACTIVATE',pool_body(p,'CP17 R3-04 aktifkan'),k2)
        b.api.admin(cur)
        assert a1==a2 and one(cur,"select count(*) from erp.journal_entries where source_type='ATTENDANCE_HPP_POOL' and source_id=%s",(first['pool_id'],))==1
        # The first answer is kept as it was, even after the pool moved on.
        assert save(cur,o,'CREATE',create_body(pv),key)==first and first['status']=='DRAFT' and native_pools(cur,day)[0]['status']=='ACTIVE'
        return dict(status='PASS',finding='R3-04',create_replayed_once=True,activate_replayed_once=True,journals=1,changed_payload_refused=changed,
                    other_action_same_id_refused=other,first_answer_immutable=True)
    def review_token():
        f=fixture(cur,today);day=f['day'];o=owner(cur);pv=read(cur,o,day,day)['preview']
        before=b.boundary.snapshot(cur)
        forged=refused(cur,lambda:save(cur,o,'CREATE',dict(create_body(pv),review_token='0'*32)),'CP7_HPP_POOL_REVIEW_CHANGED')
        malformed=refused(cur,lambda:save(cur,o,'CREATE',dict(create_body(pv),review_token='X')),'CP7_HPP_POOL_FIELDS')
        c.unchanged(cur,before,'forged or malformed preview token')
        # The source changes after the review (C's policy): the reviewed preview no longer matches.
        policy(cur,f['c'],day-timedelta(days=1));before=b.boundary.snapshot(cur)
        stale_preview=refused(cur,lambda:save(cur,o,'CREATE',create_body(pv)),'CP7_HPP_POOL_REVIEW_CHANGED');c.unchanged(cur,before,'preview changed after review')
        pv=read(cur,o,day,day)['preview'];cr=save(cur,o,'CREATE',create_body(pv));p=facade_pool(cur,o,cr['pool_id'])
        before=b.boundary.snapshot(cur)
        forged_pool=refused(cur,lambda:save(cur,o,'ACTIVATE',dict(pool_body(p,'CP17 R3-04 aktifkan'),review_token='f'*32)),'CP7_HPP_POOL_REVIEW_CHANGED')
        c.unchanged(cur,before,'forged pool token')
        # A DRAFT whose source changes after it was made: the Native validator fails, the screen offers only removal.
        extra=sewn(cur,f['a'],'R304-A2',day);assert oracle_preview(cur,day)==(D(1000),30)
        q=facade_pool(cur,o,cr['pool_id']);assert q['stale'] and q['actions']==['CANCEL'] and q['review_token']==p['review_token'],q
        before=b.boundary.snapshot(cur)
        stale=refused(cur,lambda:save(cur,o,'ACTIVATE',pool_body(q,'CP17 R3-04 aktifkan')),'CP7_HPP_POOL_SOURCE_CHANGED');c.unchanged(cur,before,'activate a stale draft')
        save(cur,o,'CANCEL',pool_body(q,'CP17 R3-04 hapus draf basi'))
        before=b.boundary.snapshot(cur)
        old_token=refused(cur,lambda:save(cur,o,'CANCEL',pool_body(q,'CP17 R3-04 hapus lagi')),'CP7_HPP_POOL_REVIEW_CHANGED');c.unchanged(cur,before,'token of a pool that moved on')
        return dict(status='PASS',finding='R3-04',forged=forged,malformed=malformed,preview_changed=stale_preview,pool_token_forged=forged_pool,
                    stale_draft_activate_refused=stale,moved_pool_token_refused=old_token,extra_sewing_po=extra['po'])
    def roles_and_fields():
        f=fixture(cur,today);day=f['day'];o=owner(cur);adm=master.role_actor(cur,'ADMIN')
        keu,qc=master.role_actor(cur,'KEUANGAN'),master.role_actor(cur,'PRODUKSI_QC');b.api.admin(cur)
        perms=set(x for (x,)in cur.execute("""select p.permission_key from erp.app_role_permissions p join erp.app_roles r on r.id=p.role_id
            where r.role_code='KEUANGAN' and p.permission_key in('finance.hpp.view','finance.hpp.manage')""").fetchall())
        assert perms=={'finance.hpp.view','finance.hpp.manage'},perms
        pv=read(cur,o,day,day)['preview'];assert read(cur,adm,day,day)['preview']['review_token']==pv['review_token']
        before=b.boundary.snapshot(cur);denied={}
        for name,subject in(('KEUANGAN',keu),('PRODUKSI_QC',qc)):
            denied[name]=dict(read=refused(cur,lambda:read(cur,subject,day,day),'CP7_HPP_POOL_DENIED'),
                              save=refused(cur,lambda:save(cur,subject,'CREATE',create_body(pv)),'CP7_HPP_POOL_DENIED'))
        service=refused(cur,lambda:(auth.actor(cur,o,'service_role'),cur.execute('select public.erp_cp7_get_hpp_pools_v1(0,20,null,null)')),'CP7_HPP_POOL_DENIED')
        fields={}
        for label,action,body in(('short_reason','CREATE',create_body(pv,'abc')),('extra_key','CREATE',dict(create_body(pv),note='x')),
                                 ('missing_key','CREATE',{k:v for k,v in create_body(pv).items() if k!='correction_of_pool_id'}),
                                 ('unknown_action','DELETE',create_body(pv)),('bad_date','CREATE',dict(create_body(pv),period_end='2026-02-30')),
                                 ('end_before_start','CREATE',dict(create_body(pv),period_start=str(day),period_end=str(day-timedelta(days=1)))),
                                 ('pool_not_uuid','ACTIVATE',dict(pool_id='x',review_token=pv['review_token'],reason=REASON))):
            fields[label]=refused(cur,lambda:save(cur,o,action,body),'CP7_HPP_POOL_FIELDS')
        c.unchanged(cur,before,'other roles and malformed commands')
        cr=save(cur,adm,'CREATE',create_body(pv));p=facade_pool(cur,o,cr['pool_id']);ac=save(cur,o,'ACTIVATE',pool_body(p,'CP17 R3-04 owner aktifkan'))
        rows=native_pools(cur,day);b.api.admin(cur)
        users=cur.execute('select created_by::text,activated_by::text from erp.attendance_hpp_pools where id=%s',(cr['pool_id'],)).fetchone()
        assert ac['status']=='ACTIVE' and rows[0]['status']=='ACTIVE' and users==(one(cur,'select id::text from erp.app_users where auth_user_id=%s',(adm,)),one(cur,'select id::text from erp.app_users where auth_user_id=%s',(o,)))
        return dict(status='PASS',finding='R3-04',admin_created_owner_activated=True,keuangan_has_hpp_rights_but_refused=denied['KEUANGAN'],
                    produksi_qc_refused=denied['PRODUKSI_QC'],service_role_claims_refused=service,fields=fields)
    def private_immutable():
        import cp7_hpp_pool_bundle as bundle
        b.api.admin(cur);proof=bundle.verify(cur)
        f=fixture(cur,today);day=f['day'];o=owner(cur);pv=read(cur,o,day,day)['preview'];key=uuid.uuid4();save(cur,o,'CREATE',create_body(pv),key)
        b.api.admin(cur)
        upd=refused(cur,lambda:cur.execute('update cp7_hpp_pool.requests set payload=payload where request_id=%s',(str(key),)),'CP7_HPP_POOL_REQUESTS_IMMUTABLE')
        dele=refused(cur,lambda:cur.execute('delete from cp7_hpp_pool.requests where request_id=%s',(str(key),)),'CP7_HPP_POOL_REQUESTS_IMMUTABLE')
        trunc=refused(cur,lambda:cur.execute('truncate cp7_hpp_pool.requests'),'CP7_HPP_POOL_REQUESTS_IMMUTABLE')
        assert requests_of(cur,key)==1
        direct=refused(cur,lambda:(auth.actor(cur,o),cur.execute('select erp.create_attendance_hpp_pool_v1(%s::jsonb,%s)',(json.dumps(dict(period_start=str(day),period_end=str(day),reason=REASON)),uuid.uuid4()))),'permission denied')
        private=refused(cur,lambda:(auth.actor(cur,o),cur.execute('select cp7_hpp_pool.workspace(0,20,null,null)')),'permission denied')
        table=refused(cur,lambda:(auth.actor(cur,o),cur.execute('select count(*) from cp7_hpp_pool.requests')),'permission denied')
        return dict(status='PASS',finding='R3-04',bundle=proof,requests_update_delete_truncate_refused=[upd,dele,trunc],native_writer_direct_refused=direct,
                    private_function_refused=private,request_table_private=table)
    named=[preview_ready_and_blocked,lifecycle_equals_native,draft_void,replacement,closed_period,permission_removed,same_uuid,review_token,roles_and_fields,private_immutable]
    assert len(named)==len(NATIVE)
    return list(zip(NATIVE,named))


def races(tools,today):
    def two(fn,args):
        barrier=threading.Barrier(len(args))
        def go(a):
            with tools.connect()as conn,conn.cursor()as cur:
                barrier.wait(5)
                try:r=fn(cur,a);conn.commit();return('PASS',r)
                except psycopg.Error as e:conn.rollback();return('REFUSED',str(e).splitlines()[0])
        with ThreadPoolExecutor(max_workers=len(args))as pool:return [x.result(120) for x in [pool.submit(go,a) for a in args]]
    def setup(draft):
        with tools.connect()as conn,conn.cursor()as cur:
            f=fixture(cur,today);o=owner(cur);pv=read(cur,o,f['day'],f['day'])['preview'];p=None
            if draft:cr=save(cur,o,'CREATE',create_body(pv));p=facade_pool(cur,o,cr['pool_id'])
            conn.commit()
        return f,o,pv,p
    def journals(cur,pool):
        b.api.admin(cur);return one(cur,"select count(*) from erp.journal_entries where source_type='ATTENDANCE_HPP_POOL' and source_id=%s and status='POSTED'",(pool,))
    def activate_two_tabs():
        f,o,pv,p=setup(True)
        results=two(lambda cur,n:save(cur,o,'ACTIVATE',pool_body(p,f'CP17 R3-04 tab {n} aktifkan'))['status'],[1,2])
        assert sorted(x[0] for x in results)==['PASS','REFUSED'] and 'CP7_HPP_POOL_REVIEW_CHANGED' in next(x[1] for x in results if x[0]=='REFUSED'),results
        with tools.connect()as conn,conn.cursor()as cur:
            rows=native_pools(cur,f['day']);n=journals(cur,p['id'])
            acts=one(cur,"select count(*) from cp7_hpp_pool.requests where pool_id=%s and action='ACTIVATE'",(p['id'],))
        assert [(r['status'],r['row_version']) for r in rows]==[('ACTIVE',2)] and (n,acts)==(1,1),(rows,n,acts)
        return dict(status='PASS',finding='R3-04',two_tabs=results,one_activation=True,journals=1)
    def create_two_tabs():
        f,o,pv,_=setup(False)
        results=two(lambda cur,n:save(cur,o,'CREATE',create_body(pv,f'CP17 R3-04 tab {n} buat draf'))['status'],[1,2])
        assert sorted(x[0] for x in results)==['PASS','REFUSED'] and 'CP7_HPP_POOL_EXISTS' in next(x[1] for x in results if x[0]=='REFUSED'),results
        with tools.connect()as conn,conn.cursor()as cur:rows=native_pools(cur,f['day'])
        assert [r['status'] for r in rows]==['DRAFT'],rows
        return dict(status='PASS',finding='R3-04',two_tabs=results,one_draft=True)
    def same_uuid_two_sessions():
        f,o,pv,p=setup(True);key=uuid.uuid4()
        results=two(lambda cur,n:save(cur,o,'ACTIVATE',pool_body(p,'CP17 R3-04 kirim ulang'),key),[1,2])
        assert [x[0] for x in results]==['PASS','PASS'] and results[0][1]==results[1][1],results
        with tools.connect()as conn,conn.cursor()as cur:
            rows=native_pools(cur,f['day']);n=journals(cur,p['id']);k=requests_of(cur,key)
        assert [r['status'] for r in rows]==['ACTIVE'] and (n,k)==(1,1),(rows,n,k)
        return dict(status='PASS',finding='R3-04',same_answer_both_sessions=True,journals=1,request_rows=1)
    return list(zip(RACES,[activate_two_tabs,create_two_tabs,same_uuid_two_sessions]))


def http_fixture(http,today,offset):
    """The fixture committed on the HTTP copy. Its helpers reach schema erp the way the native cases do, so the test-only
    USAGE grant of the race/browser copies is given for the fixture only and taken back before the commit."""
    with http.connect()as conn,conn.cursor()as cur:
        had=one(cur,"select has_schema_privilege('authenticated','erp','USAGE')");acl=one(cur,"select nspacl::text from pg_namespace where nspname='erp'")
        if not had:cur.execute('grant usage on schema erp to authenticated')
        f=fixture(cur,today,offset);f['oracle']=oracle_preview(cur,f['day']);b.api.admin(cur)
        if not had:cur.execute('revoke usage on schema erp from authenticated')
        assert one(cur,"select nspacl::text from pg_namespace where nspname='erp'")==acl
        conn.commit()
    return f

def http_cases(http,today):
    def ok(r):assert r['status']==200,r;return r['body']
    def no(r,code):assert r['status']>=400 and code in json.dumps(r['body']),r;return r['status']
    def lifecycle_and_roles():
        o=http.login('OWNER','cp17-r3-04-owner');adm=http.login('ADMIN','cp17-r3-04-admin');keu=http.login('KEUANGAN','cp17-r3-04-keuangan')
        f=http_fixture(http,today,9);day=str(f['day']);cost,pcs=f['oracle']
        w=ok(o.rpc('erp_cp7_get_hpp_pools_v1',dict(p_offset=0,p_limit=20,p_period_start=day,p_period_end=day)));pv=w['preview']
        assert (pv['status'],D(pv['numerator_amount']),pv['denominator_qty'])==('READY',cost,pcs),(pv,cost,pcs)
        refusals=dict(keuangan_read=no(keu.rpc('erp_cp7_get_hpp_pools_v1',dict(p_offset=0,p_limit=20,p_period_start=day,p_period_end=day)),'CP7_HPP_POOL_DENIED'),
                      keuangan_save=no(keu.rpc('erp_cp7_save_hpp_pool_v1',dict(p_action='CREATE',p_payload=create_body(pv),p_request=str(uuid.uuid4()))),'CP7_HPP_POOL_DENIED'),
                      anon=http.anon_rpc('erp_cp7_get_hpp_pools_v1',dict(p_offset=0,p_limit=20,p_period_start=None,p_period_end=None))['status'])
        assert refusals['anon']>=400,refusals
        key=str(uuid.uuid4());cr=ok(o.rpc('erp_cp7_save_hpp_pool_v1',dict(p_action='CREATE',p_payload=create_body(pv),p_request=key)))
        assert ok(o.rpc('erp_cp7_save_hpp_pool_v1',dict(p_action='CREATE',p_payload=create_body(pv),p_request=key)))==cr
        w=ok(adm.rpc('erp_cp7_get_hpp_pools_v1',dict(p_offset=0,p_limit=20,p_period_start=None,p_period_end=None)));p=pool_of(w,cr['pool_id'])
        assert w['can_manage'] is True
        ac=ok(adm.rpc('erp_cp7_save_hpp_pool_v1',dict(p_action='ACTIVATE',p_payload=pool_body(p,'CP17 R3-04 admin aktifkan'),p_request=str(uuid.uuid4()))))
        p=pool_of(ok(o.rpc('erp_cp7_get_hpp_pools_v1',dict(p_offset=0,p_limit=20,p_period_start=None,p_period_end=None))),cr['pool_id'])
        cx=ok(o.rpc('erp_cp7_save_hpp_pool_v1',dict(p_action='CANCEL',p_payload=pool_body(p,'CP17 R3-04 owner batalkan'),p_request=str(uuid.uuid4()))))
        with http.connect()as conn,conn.cursor()as cur:
            rows=native_pools(cur,f['day']);original,reversal=journal(cur,rows[0]['journal']),journal(cur,rows[0]['reversal'])
            w=ok(o.rpc('erp_cp7_get_hpp_pools_v1',dict(p_offset=0,p_limit=20,p_period_start=None,p_period_end=None)));same(cur,pool_of(w,cr['pool_id']),rows[0])
        assert [(r['id'],r['status']) for r in rows]==[(cr['pool_id'],'CANCELLED')] and ac['journal_entry_id']==rows[0]['journal']==cx['journal_entry_id']
        assert po_debits(original)=={f['po_a']:cost} and original['status']=='REVERSED' and net_zero(original,reversal)
        return dict(status='PASS',finding='R3-04',real_auth=True,owner_create_admin_activate_owner_cancel=True,same_uuid_same_body=True,
                    facade_equals_native_after_http=True,refusals=refusals)
    def permission_and_closed():
        adm=http.login('ADMIN','cp17-r3-04-admin-rights')
        f=http_fixture(http,today,10);day=str(f['day'])
        w=ok(adm.rpc('erp_cp7_get_hpp_pools_v1',dict(p_offset=0,p_limit=20,p_period_start=day,p_period_end=day)));pv=w['preview'];assert w['can_manage'] is True
        with http.connect()as conn,conn.cursor()as cur:
            role=one(cur,'select role_id from erp.app_users where auth_user_id=%s',(adm.auth_user_id,))
            previous=one(cur,'select closed_through from erp.accounting_period_control where singleton_id=1')
            cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='finance.hpp.manage'",(role,));conn.commit()
        try:
            denied=no(adm.rpc('erp_cp7_save_hpp_pool_v1',dict(p_action='CREATE',p_payload=create_body(pv),p_request=str(uuid.uuid4()))),'CP7_HPP_POOL_DENIED')
            view=ok(adm.rpc('erp_cp7_get_hpp_pools_v1',dict(p_offset=0,p_limit=20,p_period_start=None,p_period_end=None)))['can_manage']
        finally:
            with http.connect()as conn,conn.cursor()as cur:
                cur.execute("insert into erp.app_role_permissions(role_id,permission_key)values(%s,'finance.hpp.manage')on conflict do nothing",(role,));conn.commit()
        with http.connect()as conn,conn.cursor()as cur:set_closed(cur,f['day']);conn.commit()
        try:
            closed=no(adm.rpc('erp_cp7_save_hpp_pool_v1',dict(p_action='CREATE',p_payload=create_body(pv),p_request=str(uuid.uuid4()))),'CP7_HPP_POOL_PERIOD_CLOSED')
            shown=ok(adm.rpc('erp_cp7_get_hpp_pools_v1',dict(p_offset=0,p_limit=20,p_period_start=day,p_period_end=day)))['preview']
        finally:
            with http.connect()as conn,conn.cursor()as cur:set_closed(cur,previous);conn.commit()
        with http.connect()as conn,conn.cursor()as cur:rows=native_pools(cur,f['day'])
        assert view is False and shown['period_closed'] is True and shown['can_create'] is False and rows==[],(view,shown,rows)
        made=ok(adm.rpc('erp_cp7_save_hpp_pool_v1',dict(p_action='CREATE',p_payload=create_body(pv),p_request=str(uuid.uuid4()))))
        with http.connect()as conn,conn.cursor()as cur:rows=native_pools(cur,f['day'])
        assert [(r['id'],r['status']) for r in rows]==[(made['pool_id'],'DRAFT')]
        return dict(status='PASS',finding='R3-04',real_auth=True,manage_removed_refused=denied,view_kept_can_manage_false=True,closed_books_refused=closed,
                    nothing_written_while_refused=True,allowed_after_restore=True)
    return list(zip(HTTP,[lifecycle_and_roles,permission_and_closed]))


# ---------------------------------------------------------------- browser fixture operations (scripts/cp7_cp17_fix_browser_fixture.py)
def browser_fixture(cur,p):
    """R3-04 browser journey: the native cases' fixture for its own period (desktop and phone use different days)."""
    f=fixture(cur,date.fromisoformat(p['today']),int(p['offset']));cost,pcs=oracle_preview(cur,f['day']);b.api.admin(cur)
    return dict(day=str(f['day']),c=f['c'],c_code=f['c_code'],po_a=f['po_a'],po_c=f['po_c'],po_a_number=po_number(cur,f['po_a']),po_c_number=po_number(cur,f['po_c']),
                cost=str(cost),pcs=pcs,correction_from=str(f['day']-timedelta(days=1)))
def browser_state(cur,p):
    """Native rows only: the period's pools (oldest first) with journal states and cost per PO, C's policies, the oracle figures."""
    day=date.fromisoformat(p['day']);rows=native_pools(cur,day);cost,pcs=oracle_preview(cur,day);b.api.admin(cur)
    status=lambda j:None if j is None else one(cur,'select status from erp.journal_entries where id=%s',(j,))
    pools=[dict(id=r['id'],number=r['pool_number'],status=r['status'],numerator=str(r['numerator']),denominator=int(r['denominator']),
                unit=None if r['unit'] is None else str(r['unit']),correction_of=r['correction_of'],journal=status(r['journal']),
                reversal=status(r['reversal']),allocations={k:str(v) for k,v in allocations(cur,r['id']).items()},reason=r['reason'],
                cancellation_reason=r['cancellation_reason']) for r in rows]
    policies=one(cur,'select count(*) from erp.contractor_hpp_policy_versions where contractor_id=%s',(p['c'],))
    return dict(pools=pools,c_policies=policies,cost=str(cost),pcs=pcs)
