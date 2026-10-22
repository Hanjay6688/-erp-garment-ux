"""OW-07 Native cases: close waits for undivided pocket fabric and attendance pools; a pool on a FINISHED PO leaves no WIP.

Business rows come only from the retained writers (procurement receipt, pocket fabric REGISTER/POST/POST_PERIOD/
CANCEL_PERIOD, opening import, attendance payroll, HPP policy, sewing, PO finish, and the CP7 attendance pool facade).
Each case runs in its own savepoint. The original (pre-OW-07) engine is read side by side on the same state inside a
rolled-back savepoint, so every case shows exactly which close blockers OW-07 adds and that nothing else changes.
Explicit corruption (one case) is privileged, inside a nested savepoint, and always rolled back.
"""
from collections import Counter
from datetime import timedelta
from decimal import Decimal as D
import json
import uuid

import cp7_r3_hpp_pool_cases as hp
import cp7_material_cases as material
import cp7_period_cases as period
import cp6_be_pocket_probe as opening

b=hp.b
auth=hp.auth
IDS=('OW07_POCKET_DAILY_USAGE_HOLDS_CLOSE_UNTIL_DIVIDED',
     'OW07_POCKET_OPENING_USAGE_HOLDS_CLOSE_UNTIL_DIVIDED',
     'OW07_ATTENDANCE_POOL_HOLDS_CLOSE_UNTIL_ACTIVE',
     'OW07_ATTENDANCE_POLICY_MISSING_HOLDS_CLOSE',
     'OW07_ATTENDANCE_SOURCE_UNCLEAR_HOLDS_CLOSE',
     'OW07_ATTENDANCE_ZERO_OUTPUT_REPORTED_NOT_BLOCKING',
     'OW07_FINISHED_PO_POOL_ACTIVATE_CANCEL_LEAVES_NO_WIP')
REASON='OW07 cek HPP tutup buku'
ORIGINALS=None  # set by the probe: the exact pre-OW-07 definitions it replaced
AS_OWNER=None   # set by the probe: the verified predecessor role switch
BLOCKERS='erp.period_blockers_v1(date,date)'
ACTIVATE='erp.activate_attendance_hpp_pool_v1(uuid,text,uuid,bigint)'


def one(cur,sql,args=()):
    return cur.execute(sql,args).fetchone()[0]


def readiness(cur,through):
    b.api.admin(cur)
    r=one(cur,'select erp.period_readiness_v1(%s,erp.period_completeness_from_v1())',(through,))
    key=lambda x:(x['family'],x['code'],x['severity'],x['impact_date'],json.dumps(x['reference'],sort_keys=True))
    return dict(status=r['status'],blockers=Counter(map(key,r['blockers'])),info=Counter(map(key,r['info'])),
                rows=[x for x in r['blockers']+r['info']if x['family']=='HPP_POOL'])


def original(cur,fn,signatures=(BLOCKERS,)):
    """The same state read (or written) through the exact replaced definitions, then restored."""
    name='ow07_original_'+uuid.uuid4().hex
    cur.execute('savepoint '+name)
    try:
        with AS_OWNER(cur,'postgres'):
            for sig in signatures:cur.execute(ORIGINALS[sig],prepare=False)
        b.api.admin(cur)
        return fn()
    finally:
        cur.execute('rollback to savepoint '+name);cur.execute('release savepoint '+name);b.api.admin(cur)


def added(cur,through):
    """Close blockers and info rows OW-07 adds over the original engine on this state; nothing may be removed."""
    new=readiness(cur,through);old=original(cur,lambda:readiness(cur,through))
    assert not(old['blockers']-new['blockers'])and not(old['info']-new['info']),('OW07_REMOVED_A_BLOCKER',old,new)
    assert not old['rows'],('OW07_ORIGINAL_HAS_HPP_POOL',old['rows'])
    return dict(new=new,old_status=old['status'],
                blockers=sorted(new['blockers']-old['blockers']),info=sorted(new['info']-old['info']))


def rows(state,code):
    return [r for r in state['new']['rows']if r['code']==code]


def new_since(base,now):
    """Blocker rows OW-07 adds now that it did not add on the base state, and base rows that went away."""
    return sorted(Counter(now['blockers'])-Counter(base['blockers'])),sorted(Counter(base['blockers'])-Counter(now['blockers']))


def ids(row,key):
    return [u['id']for u in row['reference'].get(key,[])]if key=='usages'else row['reference'].get(key,[])


def preflight_refuses(cur,day,code):
    """The close screen's own read names the blocker, and the close command refuses it with no effect."""
    r=period.read(cur,day)
    found=[x for x in r['preflight']['blockers']if x['code']==code]
    assert r['preflight']['status']=='BLOCKED'and len(found)==1,r['preflight']
    before=b.boundary.snapshot(cur)
    auth.refused(cur,lambda:period.command(cur,'CLOSE',period.intent(r)),'CLOSE_BLOCKED')
    assert b.boundary.snapshot(cur)==before
    return found[0]['reason']


def pocket(cur,action,payload,key=None):
    return opening.call(cur,action,payload,key)


def pocket_workspace(cur,query):
    opening.b.bcp.session(cur)
    r=one(cur,'select public.erp_get_pocket_fabric_workspace_v1(%s)',(query,));b.api.admin(cur);return r


def pocket_state(cur,ident):
    b.api.admin(cur);return one(cur,'select erp.pocket_period_state_v1(%s)',(ident,))


def contractor(cur,tag,attendance):
    b.api.admin(cur)
    return str(one(cur,"insert into erp.contractors(contractor_code,contractor_name,contractor_type,attendance_required)values(%s,%s,'MANDOR',%s)returning id",
                   (tag,tag,attendance)))


def pool_cycle(cur,day,reason):
    o=hp.owner(cur);pv=hp.read(cur,o,day,day)['preview'];assert pv['status']=='READY',pv
    made=hp.save(cur,o,'CREATE',hp.create_body(pv,reason=reason))
    return o,made['pool_id']


def cases(cur,today):
    def pocket_daily():
        day=today-timedelta(days=2);tag=uuid.uuid4().hex[:8].upper()
        sewer=contractor(cur,'OW07-PS-'+tag,False);g=hp.sewn(cur,sewer,'OW07-PS',day)
        m=material.fixture(cur,today)
        pocket(cur,'REGISTER',dict(material_id=m['material'],reason=REASON+' kain kantong bersama'))
        roll=next(r for r in pocket_workspace(cur,m['tag'])['rolls']if r['id']==m['roll'])
        base=readiness(cur,day)
        base_count=sum(int(r['reference']['usage_count'])for r in base['rows']if r['code']=='POCKET_USAGE_UNALLOCATED')
        pocket(cur,'POST',dict(roll_id=roll['id'],location_id=roll['location_id'],expected_revision=roll['revision'],mode='USED',
            quantity='5',date=str(day),reason=REASON+' kain kantong keluar'))
        usage=str(one(cur,'select adjustment_id from erp.pocket_fabric_usage where roll_id=%s',(m['roll'],)))
        value=D(one(cur,"select -((erp._cp6_material_adjustment_revaluation_state(%s)->>'current_value')::numeric)",(usage,)))
        assert value>0,value
        a=added(cur,day);row=rows(a,'POCKET_USAGE_UNALLOCATED')
        assert len(row)==1 and[x[1]for x in a['blockers']].count('POCKET_USAGE_UNALLOCATED')==1,a
        assert usage in ids(row[0],'usages')and int(row[0]['reference']['usage_count'])==base_count+1,row
        assert row[0]['severity']=='POLICY'and'Kain kantong'in row[0]['reason']and'Bagi ke HPP per periode'in row[0]['reason'],row
        earlier=readiness(cur,day-timedelta(days=1))
        assert all(usage not in ids(r,'usages')for r in earlier['rows']),earlier['rows']
        shown=preflight_refuses(cur,day,'POCKET_USAGE_UNALLOCATED')
        p=opening.preview(cur,day,day);assert p['can_post'],p
        made=pocket(cur,'POST_PERIOD',dict(period_start=str(day),period_end=str(day),expected_revision=p['revision'],reason=REASON+' bagi periode'))
        after=added(cur,day)
        assert all(usage not in ids(r,'usages')for r in after['new']['rows']),after
        assert base_count>0 or not rows(after,'POCKET_USAGE_UNALLOCATED'),after
        assert sum(int(r['reference']['usage_count'])for r in after['new']['rows']if r['code']=='POCKET_USAGE_UNALLOCATED')==base_count
        pocket(cur,'CANCEL_PERIOD',dict(id=made['id'],expected_revision=pocket_state(cur,made['id'])['revision'],reason=REASON+' batal bagi'))
        again=rows(added(cur,day),'POCKET_USAGE_UNALLOCATED')
        assert len(again)==1 and usage in ids(again[0],'usages'),again
        return dict(status='PASS',usage=usage,value=str(value),sewing_po=g['po'],original_engine_status=a['old_status'],
            patched_status=a['new']['status'],added_blockers=[x[1]for x in a['blockers']],screen_reason=shown,
            close_refused_without_effect=True,divided_removes_it=True,cancelled_division_restores_it=True)

    def pocket_opening():
        cut=today-timedelta(days=10)
        f=opening.b.bbp.production_post(cur,today,opening.active_unit(cur,opening.rows(cut)))
        b.api.admin(cur);usage=str(one(cur,'select id from erp.be_pocket_usage_v1 where batch_id=%s',(f['batch'],)))
        day=cut-timedelta(days=1)
        a=added(cur,day);row=rows(a,'POCKET_USAGE_UNALLOCATED')
        assert len(row)==1,a
        mine=[u for u in row[0]['reference']['usages']if u['id']==usage]
        assert mine==[dict(kind='OPENING',id=usage,date=str(day),amount='11.25')],row
        assert all(usage not in ids(r,'usages')for r in readiness(cur,day-timedelta(days=1))['rows'])
        p=opening.preview(cur,day,cut);assert p['can_post'],p
        made=pocket(cur,'POST_PERIOD',dict(period_start=str(day),period_end=str(cut),expected_revision=p['revision'],reason=REASON+' saldo awal'))
        assert all(usage not in ids(r,'usages')for r in readiness(cur,cut)['rows'])
        pocket(cur,'CANCEL_PERIOD',dict(id=made['id'],expected_revision=pocket_state(cur,made['id'])['revision'],reason=REASON+' batal saldo awal'))
        assert any(usage in ids(r,'usages')for r in readiness(cur,cut)['rows'])
        return dict(status='PASS',opening_usage=usage,amount='11.25',original_engine_status=a['old_status'],patched_status=a['new']['status'],
            divided_removes_it=True,cancelled_division_restores_it=True)

    def attendance_pool():
        base=added(cur,today-timedelta(days=1))
        f=hp.fixture(cur,today);day=f['day'];assert day==today-timedelta(days=1)
        a=added(cur,day);row=[r for r in rows(a,'ATTENDANCE_POOL_NOT_ACTIVE')if f['payroll']in ids(r,'payroll_ids')]
        more,gone=new_since(base,a)
        assert len(row)==1 and gone==[]and[x[1]for x in more]==['ATTENDANCE_POOL_NOT_ACTIVE'],(more,gone)
        assert row[0]['severity']=='POLICY'and row[0]['impact_date']==str(day)and row[0]['reference']['amount']=='1000.00'and row[0]['reference']['active_pools']==[],row
        assert'HPP & Rekalkulasi'in row[0]['reason'],row
        assert all(f['payroll']not in ids(r,'payroll_ids')for r in readiness(cur,day-timedelta(days=1))['rows'])
        shown=preflight_refuses(cur,day,'ATTENDANCE_POOL_NOT_ACTIVE')
        o,pool=pool_cycle(cur,day,REASON+' pool absen')
        assert any(f['payroll']in ids(r,'payroll_ids')for r in readiness(cur,day)['rows']),'DRAFT_MUST_STILL_HOLD'
        hp.save(cur,o,'ACTIVATE',hp.pool_body(hp.facade_pool(cur,o,pool),REASON+' aktifkan pool'))
        active=added(cur,day);assert new_since(base,active)==([],[])and all(f['payroll']not in ids(r,'payroll_ids')for r in active['new']['rows']),active
        hp.save(cur,o,'CANCEL',hp.pool_body(hp.facade_pool(cur,o,pool),REASON+' batalkan pool'))
        back=[r for r in rows(added(cur,day),'ATTENDANCE_POOL_NOT_ACTIVE')if f['payroll']in ids(r,'payroll_ids')];assert len(back)==1,back
        return dict(status='PASS',payroll=f['payroll'],amount='1000.00',screen_reason=shown,original_engine_status=a['old_status'],
            draft_still_holds=True,active_releases=True,cancel_holds_again=True,close_refused_without_effect=True)

    def policy_missing():
        day=today-timedelta(days=1);tag=uuid.uuid4().hex[:8].upper();base=added(cur,day)
        m=hp.contractor(cur,'OW07-PM-'+tag);payroll=hp.attendance_payroll(cur,m,'OW07-PM-'+tag,day);hp.sewn(cur,m,'OW07-PM',day)
        a=added(cur,day);row=[r for r in rows(a,'ATTENDANCE_POOL_POLICY_MISSING')if payroll in ids(r,'payroll_ids')]
        more,gone=new_since(base,a)
        assert len(row)==1 and gone==[]and[x[1]for x in more]==['ATTENDANCE_POOL_POLICY_MISSING'],(more,gone)
        assert'Master Data > Mandor'in row[0]['reason'],row
        preflight_refuses(cur,day,'ATTENDANCE_POOL_POLICY_MISSING')
        hp.policy(cur,m,day-timedelta(days=1))
        now=added(cur,day)
        assert all(payroll not in ids(r,'payroll_ids')for r in rows(now,'ATTENDANCE_POOL_POLICY_MISSING'))
        assert[r['code']for r in now['new']['rows']if payroll in ids(r,'payroll_ids')]==['ATTENDANCE_POOL_NOT_ACTIVE'],now
        return dict(status='PASS',payroll=payroll,missing_policy_holds=True,after_policy_pool_required=True)

    def source_unclear():
        f=hp.fixture(cur,today);day=f['day'];name='ow07_unclear_'+uuid.uuid4().hex
        cur.execute('savepoint '+name)
        try:
            b.api.admin(cur)
            try:
                cur.execute('savepoint '+name+'_d');cur.execute('update erp.payroll_settlements set attendance_total=attendance_total+1 where id=%s',(f['payroll'],))
                how='DIRECT'
            except Exception:
                cur.execute('rollback to savepoint '+name+'_d')
                cur.execute('alter table erp.payroll_settlements disable trigger user')
                cur.execute('update erp.payroll_settlements set attendance_total=attendance_total+1 where id=%s',(f['payroll'],))
                cur.execute('alter table erp.payroll_settlements enable trigger user');how='USER_TRIGGERS_DISABLED_FOR_ONE_STATEMENT'
            a=added(cur,day);row=[r for r in rows(a,'ATTENDANCE_POOL_SOURCE_UNCLEAR')if r['reference']['period_start']==str(day)]
            assert len(row)==1 and row[0]['severity']=='POLICY'and row[0]['reference']['payroll_count']=='1',a
            assert all(f['payroll']not in ids(r,'payroll_ids')for r in a['new']['rows']),a
        finally:
            cur.execute('rollback to savepoint '+name);cur.execute('release savepoint '+name);b.api.admin(cur)
        assert any(f['payroll']in ids(r,'payroll_ids')for r in rows(added(cur,day),'ATTENDANCE_POOL_NOT_ACTIVE'))
        return dict(status='PASS',corruption=how,rolled_back=True,unclear_holds=True)

    def zero_output():
        day=today-timedelta(days=1);tag=uuid.uuid4().hex[:8].upper();base=added(cur,day)
        m=hp.contractor(cur,'OW07-ZO-'+tag);payroll=hp.attendance_payroll(cur,m,'OW07-ZO-'+tag,day);hp.policy(cur,m,day-timedelta(days=1))
        b.api.admin(cur)
        others=one(cur,"""select count(*) from erp.sewing_terminal_events e where e.event_kind='SELESAI_DIJAHIT'
            and erp._cp3_business_date(e.physical_at)=%s""",(day,))
        a=added(cur,day);row=[r for r in rows(a,'ATTENDANCE_POOL_ZERO_OUTPUT')if payroll in ids(r,'payroll_ids')]
        assert others==0 and new_since(base,a)==([],[])and len(row)==1 and row[0]['severity']=='INFO',(others,a)
        assert sorted(Counter(a['info'])-Counter(base['info']))[0][1]=='ATTENDANCE_POOL_ZERO_OUTPUT'and row[0]['reference']['amount']=='1000.00',row
        return dict(status='PASS',payroll=payroll,reported_as_info=True,not_blocking=True,patched_status=a['new']['status'],
            original_engine_status=a['old_status'])

    def finished_po():
        c=hp.cp17();tag=uuid.uuid4().hex[:8].upper();m=hp.contractor(cur,'OW07-FP-'+tag)
        prod=c.bd.chain.production;old=prod.CONTRACTOR
        try:
            prod.CONTRACTOR=m;f=c.finish_fixture(cur,today,label='OW07-FP')
        finally:
            prod.CONTRACTOR=old
        po=f['po'];b.api.admin(cur)
        sewers=[str(x)for x,in cur.execute("select distinct contractor_id from erp.sewing_terminal_events where po_id=%s and event_kind='SELESAI_DIJAHIT'",(po,)).fetchall()]
        day=one(cur,"select min(erp._cp3_business_date(physical_at)) from erp.sewing_terminal_events where po_id=%s and event_kind='SELESAI_DIJAHIT'",(po,))
        assert sewers==[m],sewers
        payroll=hp.attendance_payroll(cur,m,'OW07-FP-'+tag,day);hp.policy(cur,m,day-timedelta(days=1))
        c.finish_command(cur,c.finish_workspace(cur,po),reason=REASON+' PO selesai')
        assert c.po_state(cur,po)['status']=='FINISHED'and c.po_wip_balance(cur,po)==0
        o,pool=pool_cycle(cur,day,REASON+' pool sesudah PO selesai')
        body=hp.pool_body(hp.facade_pool(cur,o,pool),REASON+' aktifkan sesudah PO selesai')
        events=lambda:[(str(e),D(a),r)for e,a,r in cur.execute('select id,residual_amount,reason from erp.po_wip_close_events where po_id=%s order by created_at,id',(po,)).fetchall()]
        b.api.admin(cur);before=events()
        def activate_original():
            hp.save(cur,o,'ACTIVATE',body);b.api.admin(cur);return c.po_wip_balance(cur,po),events()[len(before):]
        left_original,events_original=original(cur,activate_original,(ACTIVATE,))
        hp.save(cur,o,'ACTIVATE',body);b.api.admin(cur)
        activated=events()[len(before):]
        assert c.po_state(cur,po)['status']=='FINISHED'and c.po_wip_balance(cur,po)==0,(c.po_wip_balance(cur,po),activated)
        assert events_original==[]and sum(a for _,a,_ in activated)==left_original,(left_original,activated)
        assert all(r=='Attendance HPP pool activation '+pool for _,_,r in activated),activated
        allocation=hp.active_view(cur,po);assert allocation>0,allocation
        hp.save(cur,o,'CANCEL',hp.pool_body(hp.facade_pool(cur,o,pool),REASON+' batal sesudah PO selesai'));b.api.admin(cur)
        cancelled=events()[len(before)+len(activated):]
        assert c.po_wip_balance(cur,po)==0 and all(r=='Attendance HPP pool cancellation '+pool for _,_,r in cancelled),cancelled
        return dict(status='PASS',po=f['number'],payroll=payroll,attendance_to_po=str(allocation),
            original_left_in_wip=str(left_original),activation_residual_closed=[str(a)for _,a,_ in activated],
            cancellation_residual_closed=[str(a)for _,a,_ in cancelled],finished_po_wip_after_activate='0',finished_po_wip_after_cancel='0')

    return list(zip(IDS,(pocket_daily,pocket_opening,attendance_pool,policy_missing,source_unclear,zero_output,finished_po)))
