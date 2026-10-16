"""Sol R2-10 (KNOWN-BF-WAVE): SELESAI DIJAHIT for a Potongan bound to SKU waves (BF commercial ranges), per SKU.

Native, race and real-Auth HTTP cases for the RECORD_WAVE path of scripts/cp7-src/cutting-correction/sewing.sql, spliced
into the CP17 r2 harness. The fixture is a posted cutting of three sizes (S and M bound to SKU A, L to SKU B; 4, 7 and 3
pieces) picked up by its own Mandor, the PO model's Work BOM of the G1 cases (Jahit default 2 with a Mandor rate 3, Obras
default 1) and two SKUs whose own Jahit rates are 10 (A) and 30 (B); Obras has no SKU rate, so the Native snapshot keeps the
base rate for it. Oracles read the Native rows (work completion lines and their SKU snapshot, WORK_COMPLETION journals,
sewing terminal events, erp.bf_work_capacity_v1) and, for the rates shown before the first record, what the Native snapshot
writer itself commits at the same instant (run in a savepoint and undone), never the facade's answer alone.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta,datetime
from decimal import Decimal as D
import json,threading,uuid
import psycopg
import cp7_snapshot_cases as auth
import cp7_cutting_correction_cases as cut
import cp6_bf_probe as bf
b=auth.b
refused=auth.refused

NATIVE=['CP17_R2_10_WAVE_SEWING_PER_SKU_WAGE','CP17_R2_10_WAVE_SEWING_PREVIEW_EQUALS_NATIVE','CP17_R2_10_WAVE_SEWING_REFUSALS_UNCHANGED',
        'CP17_R2_10_WAVE_SEWING_FAILURE_MIDWAY_LEAVES_NOTHING','CP17_R2_10_WAVE_SEWING_CANCEL_ONE_SKU']
RACES=['CP17_RACE_R2_10_WAVE_SEWING_TWO_TABS_ONE_WINS']
HTTP=['CP17_HTTP_R2_10_WAVE_SEWING']
BROWSER=['CP17_BROWSER_R2_10_WAVE_SEWING_DESKTOP','CP17_BROWSER_R2_10_WAVE_SEWING_MOBILE']
REASON='CP17 R2-10 setoran jahit per SKU'

def one(cur,sql,args=()):return cur.execute(sql,args).fetchone()[0]
def prod():return cut.cutting.qc.physical.b.chain.production
def cp17():
    import cp7_cp17_fix_cases as m
    return m
def now(cur):return one(cur,'select clock_timestamp()')

def fixture(cur,today,yields=(4,7,3)):
    """Three sizes on one roll, picked up by a fresh Mandor (the BD two-size fixture's Native cutting and pickup writers); two
    SKUs saved four minutes back (SAVE_GROUPS takes no earlier start) and bound to the wave by the Native BIND_WAVE; the PO
    model's Work BOM and Mandor rate of the G1 cases."""
    c=cp17();p=bf.b.chain.production;tag='R210-'+uuid.uuid4().hex[:8]
    rows=bf.products(cur,('S','M','L'),tag);roots=[r for r,_ in rows];sizes=[s for _,s in rows]
    mandor=c.mandor_row(cur,'CP17-'+tag);old=p.CONTRACTOR
    try:
        p.CONTRACTOR=mandor
        fx=bf.b.two_size_fixture(cur,today,'CP17-'+tag,size_quantities=list(zip(sizes,yields)),work_setup=lambda *a:None)
    finally:p.CONTRACTOR=old
    b.api.admin(cur)
    assert one(cur,'select contractor_id::text from erp.production_orders where id=%s',(fx['po'],))==mandor
    since=one(cur,"select clock_timestamp()-interval '4 minutes'")
    a=bf.group(cur,roots[:2],since,settings=cfg('10.00'));z=bf.group(cur,[roots[2]],since,settings=cfg('30.00'));bf.save(cur,[a,z],since)
    bf.call(cur,'BIND_WAVE',dict(cutting_group_id=fx['group'],expected_version=one(cur,'select erp.bf_wave_revision_v1(%s)',(fx['group'],)),
        references=[dict(size_id=s,sku_id=a['id'] if i<2 else z['id']) for i,s in enumerate(sizes)]))
    g=dict(group=fx['group'],po=fx['po'],mandor=mandor,day=fx['day'],at=lambda h,minute=0:p.at(fx['day'],h,minute),since=since,
           A=a,B=z,roots=roots,sizes=sizes,number=one(cur,'select group_number from erp.cutting_groups where id=%s',(fx['group'],)))
    g['rates']=c.work_rates(cur,g);b.api.admin(cur)
    return g
def cfg(rate):return dict(price='185000.00',bom=[],work_rates=[dict(contractor_id=None,work_component_id=str(prod().COMPONENT),rate=rate)],laundry_rates=[])
def read(cur,g,subject=None):
    auth.actor(cur,subject);w=one(cur,'select public.erp_cp7_get_sewing_completion_v1(%s)',(g['group'],));b.api.admin(cur);return w
def payload(w,lines,at,reason=REASON,token=None):
    return dict(action='RECORD_WAVE',group_id=w['group_id'],lines=[dict(sku_id=s,qty_pcs=str(q)) for s,q in lines],physical_at=at.isoformat(),
                review_token=token or w['review_token'],change_reason=reason)
def send(cur,w,body,key=None,expected=None,subject=None):
    auth.actor(cur,subject)
    r=one(cur,'select public.erp_cp7_save_sewing_completion_v1(%s,%s,%s)',(json.dumps(body),str(key or uuid.uuid4()),expected or w['group_version']))
    b.api.admin(cur);return r
def record(cur,w,lines,at,**kw):
    key,expected,subject=kw.pop('key',None),kw.pop('expected',None),kw.pop('subject',None)
    return send(cur,w,payload(w,lines,at,**kw),key,expected,subject)
def lines_of(cur,completion):
    """Native rows: per line the component, completed and payable pieces, rate, amount and the SKU of its snapshot."""
    b.api.admin(cur)
    return cur.execute("""select wc.component_code,l.qty_completed,l.qty_payable,l.rate_snapshot,l.amount_payable,v.sku_id::text
        from erp.work_completion_lines l join erp.po_work_component_snapshots s on s.id=l.po_component_snapshot_id
        join erp.work_components wc on wc.id=l.work_component_id left join erp.bf_sku_versions_v1 v on v.id=s.bf_sku_version_id
        where l.completion_id=%s order by s.sequence_no,s.id""",(completion,)).fetchall()
def codes(cur,g):
    b.api.admin(cur)
    return dict(cur.execute('select id::text,component_code from erp.work_components where id=any(%s::uuid[])',([g['rates']['component'],g['rates']['obras']],)).fetchall())
def segment(w,at):
    """The workspace segment holding a sewing time, as {sku_id: [(code, rate)]} or None when incomplete there."""
    for s in w['wave']['timeline']:
        if datetime.fromisoformat(s['from'])<=at and(s['to'] is None or at<datetime.fromisoformat(s['to'])):
            return {k['sku_id']:[(x['code'],D(str(x['rate'])))for x in k['rates']]for k in s['skus']}if s['complete'] else None
    return None
def native_rates(cur,g,at):
    """What erp.ensure_po_work_component_snapshots_v2 (the writer the command calls) commits for a sewing at `at`, per SKU of
    the Potongan; run in a savepoint and undone. A refusal returns its message."""
    cur.execute('savepoint r210_native')
    try:
        prod().owner(cur);cur.execute('select erp.ensure_po_work_component_snapshots_v2(%s,%s,%s)',(g['po'],at,uuid.uuid4()));b.api.admin(cur)
        out={}
        for sku,code,rate in cur.execute("""select v.sku_id::text,wc.component_code,s.rate_per_pcs_snapshot from erp.po_work_component_snapshots s
            join erp.bf_sku_versions_v1 v on v.id=s.bf_sku_version_id join erp.work_components wc on wc.id=s.work_component_id
            where s.po_id=%s order by v.sku_id,s.sequence_no,s.id""",(g['po'],)).fetchall():out.setdefault(sku,[]).append((code,D(rate)))
        return out
    except psycopg.Error as e:return 'REFUSED: '+str(e).splitlines()[0]
    finally:cur.execute('rollback to savepoint r210_native');b.api.admin(cur)
def wage_journal(cur,completion):return cp17().wage_journal(cur,completion)
def sewn_ready(cur,g):return cp17().sewn_ready(cur,g)
def counts(cur,g):
    b.api.admin(cur)
    return cur.execute("""select(select count(*) from erp.work_completion_events where cutting_group_id=%s and status='POSTED'),
        (select count(*) from erp.sewing_terminal_events where cutting_group_id=%s),
        (select count(*) from erp.po_work_component_snapshots where po_id=%s),
        (select count(*) from cp7_cutting_correction.sewing_wave_history where group_id=%s)""",(g['group'],g['group'],g['po'],g['group'])).fetchone()


def cases(cur,today):
    c=cp17()
    def per_sku():
        g=fixture(cur,today);w=read(cur,g);A,B=g['A']['id'],g['B']['id'];code=codes(cur,g)
        jahit,obras=code[g['rates']['component']],code[g['rates']['obras']]
        assert w['eligible'] and w['blockers']==[] and w['business_DML'] is False and w['wave'] is not None,w['blockers']
        # The base Work BOM is not this Potongan's wage: no base components or base preview; the totals follow the SKUs.
        assert (w['components'],w['rate_preview'],w['rate_timeline'],w['rates_committed'],w['wave']['rates_committed'])==([],[],[],False,False),w
        skus={k['sku_id']:k for k in w['wave']['skus']}
        assert [(skus[x]['capacity'],skus[x]['max_qty'],skus[x]['posted_qty'],len(skus[x]['sizes']))for x in(A,B)]==[(11,11,0,2),(3,3,0,1)] and w['max_qty']==14,skus
        at=now(cur)-timedelta(seconds=30)
        shown=segment(w,at)
        assert shown=={A:[(jahit,D(10)),(obras,D(1))],B:[(jahit,D(30)),(obras,D(1))]},shown
        assert native_rates(cur,g,at)==shown,('CP17_R210_PREVIEW_NOT_NATIVE',native_rates(cur,g,at),shown)
        key=uuid.uuid4();r=record(cur,w,[(A,5),(B,2)],at,key=key);again=record(cur,w,[(A,5),(B,2)],at,key=key)
        assert again==r and r['action']=='RECORD_WAVE' and r['result']['qty_pcs']==7 and D(str(r['result']['wage_amount']))==117,r
        changed=refused(cur,lambda:record(cur,w,[(A,4),(B,2)],at,key=key),'CP7_SEWING_REQUEST_CHANGED')
        la,lb=r['result']['lines']
        assert (la['sku_id'],la['qty_pcs'],lb['sku_id'],lb['qty_pcs'])==(A,5,B,2),r['result']['lines']
        # Native rows: each SKU has its own completion on its own SKU snapshot, at the SKU's rate (Obras the base rate).
        assert lines_of(cur,la['work_completion_id'])==[(jahit,5,5,D(10),D(50),A),(obras,5,5,D(1),D(5),A)],lines_of(cur,la['work_completion_id'])
        assert lines_of(cur,lb['work_completion_id'])==[(jahit,2,2,D(30),D(60),B),(obras,2,2,D(1),D(2),B)],lines_of(cur,lb['work_completion_id'])
        assert wage_journal(cur,la['work_completion_id'])==(D(55),D(55),1) and wage_journal(cur,lb['work_completion_id'])==(D(62),D(62),1)
        assert [one(cur,'select qty_signed from erp.sewing_terminal_events where id=%s',(x['sewing_event_id'],))for x in(la,lb)]==[5,2]
        assert sewn_ready(cur,g)==(7,7),sewn_ready(cur,g)
        # The pieces each SKU may take are what the Native per-SKU guard allows (erp.bf_work_capacity_v1 on the pinned snapshot).
        snap={sku:one(cur,"""select s.id from erp.po_work_component_snapshots s join erp.bf_sku_versions_v1 v on v.id=s.bf_sku_version_id
            where s.po_id=%s and v.sku_id=%s and s.work_component_id=%s""",(g['po'],sku,g['rates']['component']))for sku in(A,B)}
        assert [one(cur,'select erp.bf_work_capacity_v1(%s,%s,14)',(g['group'],snap[x]))for x in(A,B)]==[11,3]
        w2=read(cur,g);k2={k['sku_id']:k for k in w2['wave']['skus']}
        assert w2['wave']['rates_committed'] and w2['wave']['timeline']==[] and w2['max_qty']==7,w2['wave']
        assert [(k2[x]['max_qty'],k2[x]['posted_qty'],[(y['code'],D(str(y['rate'])))for y in k2[x]['rates']])for x in(A,B)]==[
            (6,5,shown[A]),(1,2,shown[B])],k2
        assert {e['sku'] for e in w2['events']}=={g['A']['sku'],g['B']['sku']},w2['events']
        record(cur,w2,[(A,6),(B,1)],now(cur)-timedelta(seconds=10))
        w3=read(cur,g)
        assert not w3['eligible'] and w3['max_qty']==0 and [x['kind']for x in w3['blockers']]==['NOTHING_TO_SEW'] and sewn_ready(cur,g)==(14,14),w3['blockers']
        assert counts(cur,g)[3]==4
        return dict(status='PASS',per_sku=dict(A=dict(pieces=[5,6],wage_per_pcs='Jahit 10 (SKU) + Obras 1 (base)'),B=dict(pieces=[2,1],wage_per_pcs='Jahit 30 (SKU) + Obras 1 (base)')),
                    first_request_wage=dict(A='WIP 55 / CONTRACTOR_PAYABLE 55',B='WIP 62 / CONTRACTOR_PAYABLE 62'),preview_equals_native_snapshot=True,
                    capacity_native=dict(A=11,B=3),same_uuid_same_answer=True,changed_payload_refused=changed,nothing_left_blocker=True)
    def preview_native():
        g=fixture(cur,today);A,B=g['A']['id'],g['B']['id'];code=codes(cur,g)
        jahit,obras=code[g['rates']['component']],code[g['rates']['obras']]
        # Later SKU A version (Jahit 15) and a Mandor rate for Obras (2): the rates change twice after the first SKU version.
        t=now(cur);v2=t-timedelta(minutes=2);m=t-timedelta(minutes=1)
        a2=bf.group(cur,g['roots'][:2],v2,sku=g['A']['sku'],gid=A,revision=1,settings=cfg('15.00'));bf.save(cur,[a2],v2)
        model=one(cur,'select model_id from erp.production_orders where id=%s',(g['po'],))
        cur.execute('insert into erp.contractor_work_rates(contractor_id,model_id,work_component_id,rate_per_pcs,effective_from)values(%s,%s,%s,2,%s)',
                    (g['mandor'],model,g['rates']['obras'],m))
        w=read(cur,g);assert w['eligible'] and not w['wave']['rates_committed'],w['blockers']
        instants=dict(before_sku_versions=g['at'](10),first_versions=g['since']+timedelta(seconds=30),sku_a_second_version=v2+timedelta(seconds=30),
                      mandor_obras_rate=m+timedelta(seconds=30))
        expected=dict(first_versions={A:[(jahit,D(10)),(obras,D(1))],B:[(jahit,D(30)),(obras,D(1))]},
                      sku_a_second_version={A:[(jahit,D(15)),(obras,D(1))],B:[(jahit,D(30)),(obras,D(1))]},
                      mandor_obras_rate={A:[(jahit,D(15)),(obras,D(2))],B:[(jahit,D(30)),(obras,D(2))]})
        seen={}
        for name,at in instants.items():
            shown,native=segment(w,at),native_rates(cur,g,at);seen[name]=dict(screen=str(shown),native=str(native))
            if name=='before_sku_versions':
                assert shown is None and isinstance(native,str) and 'BF_WORK_VERSION_MISSING' in native,(name,shown,native)
            else:assert shown==native==expected[name],(name,shown,native)
        # The record at a time inside the second segment commits exactly what the screen showed for it.
        r=record(cur,w,[(A,1),(B,1)],instants['sku_a_second_version'])
        assert [lines_of(cur,x['work_completion_id'])[0][3] for x in r['result']['lines']]==[D(15),D(30)]
        k={x['sku_id']:x for x in read(cur,g)['wave']['skus']}
        assert [(y['code'],D(str(y['rate'])))for y in k[A]['rates']]==expected['sku_a_second_version'][A]
        return dict(status='PASS',instants=seen,rule='per SKU: pinned version, else the version at the sewing time; SKU rate else base rate',
                    committed_equals_preview=True)
    def refusals():
        g=fixture(cur,today);w=read(cur,g);A,B=g['A']['id'],g['B']['id'];at=now(cur)-timedelta(seconds=30)
        base=dict(action='RECORD',group_id=g['group'],qty_pcs='2',physical_at=at.isoformat(),review_token=w['review_token'],change_reason=REASON)
        plain=c.pickup_fixture(cur,today);c.work_rates(cur,plain);wp=c.sewing_workspace(cur,plain);assert wp['wave'] is None and wp['eligible']
        before=b.boundary.snapshot(cur)
        out=dict(
            single_quantity_on_wave=refused(cur,lambda:send(cur,w,base),'CP7_SEWING_WAVE_PER_SKU'),
            wave_on_ordinary=refused(cur,lambda:record(cur,wp,[(A,1)],at),'CP7_SEWING_NOT_WAVE'),
            sku_outside_wave=refused(cur,lambda:record(cur,w,[(str(uuid.uuid4()),1)],at),'CP7_SEWING_WAVE_SKU'),
            above_sku_remaining=refused(cur,lambda:record(cur,w,[(B,4)],at),'CP7_SEWING_QTY_ABOVE_REMAINING'),
            same_sku_twice=refused(cur,lambda:record(cur,w,[(A,1),(A,2)],at),'CP7_SEWING_FIELDS'),
            no_lines=refused(cur,lambda:record(cur,w,[],at),'CP7_SEWING_FIELDS'),
            zero_pieces=refused(cur,lambda:record(cur,w,[(A,0)],at),'CP7_SEWING_FIELDS'),
            extra_line_field=refused(cur,lambda:send(cur,w,dict(payload(w,[(A,1)],at),lines=[dict(sku_id=A,qty_pcs='1',size_id=g['sizes'][0])])),'CP7_SEWING_FIELDS'),
            stale_review=refused(cur,lambda:record(cur,w,[(A,1)],at,token='0'*32),'CP7_SEWING_STALE_REVIEW'),
            before_pickup=refused(cur,lambda:record(cur,w,[(A,1)],g['at'](8)),'CP7_SEWING_BEFORE_PICKUP'),
            future=refused(cur,lambda:record(cur,w,[(A,1)],now(cur)+timedelta(days=2)),'CP7_SEWING_FUTURE'))
        c.unchanged(cur,before,'wave sewing refusals')
        # Outside the command the Native trigger refuses a base-rate line on a wave Potongan (the path the screen does not take).
        def base_line():
            prod().owner(cur);cur.execute('select erp.ensure_po_work_component_snapshots_v2(%s,%s,%s)',(g['po'],at,uuid.uuid4()));b.api.admin(cur)
            snap,comp=cur.execute('select id,work_component_id from erp.po_work_component_snapshots where po_id=%s and bf_sku_version_id is null order by sequence_no limit 1',(g['po'],)).fetchone()
            e=uuid.uuid4();b.chain.peer.ordinary(cur)
            cur.execute("insert into erp.work_completion_events(id,completion_number,po_id,contractor_id,cutting_group_id,physical_at,status,notes,created_by)values(%s,%s,%s,%s,%s,%s,'DRAFT','CP17 R2-10 base',%s)",
                        (e,'CP17-R210-'+str(e),g['po'],g['mandor'],g['group'],at,b.chain.base.OPERATOR_APP))
            cur.execute('insert into erp.work_completion_lines(completion_id,po_component_snapshot_id,work_component_id,qty_completed,qty_payable,rate_snapshot)values(%s,%s,%s,1,1,0)',(e,snap,comp))
        out['native_base_line_refused']=refused(cur,base_line,'BF_WORK_SCOPE_REQUIRED')
        c.unchanged(cur,before,'native base line')
        return dict(status='PASS',**out)
    def failure_midway():
        g=fixture(cur,today);w=read(cur,g);A,B=g['A']['id'],g['B']['id'];at=now(cur)-timedelta(seconds=30)
        # Fault injected into this case's own transaction only: the second line's SELESAI_DIJAHIT (2 pieces) is refused after the
        # first SKU's completion, wage journal and SELESAI_DIJAHIT and the second SKU's completion and journal are written.
        cur.execute("""create function public.cp17_r210_fault()returns trigger language plpgsql as $f$begin
            if new.qty_signed=2 then raise exception 'CP17_R210_INJECTED_FAULT posted=% sewn=%',
              (select count(*) from erp.work_completion_events where cutting_group_id=new.cutting_group_id and status='POSTED'),
              (select count(*) from erp.sewing_terminal_events where cutting_group_id=new.cutting_group_id);end if;return new;end$f$""")
        cur.execute('create trigger cp17_r210_fault before insert on erp.sewing_terminal_events for each row execute function public.cp17_r210_fault()')
        before=b.boundary.snapshot(cur);n0=counts(cur,g);key=uuid.uuid4()
        fault=refused(cur,lambda:record(cur,w,[(A,5),(B,2)],at,key=key),'CP17_R210_INJECTED_FAULT')
        assert 'posted=2 sewn=1' in fault,fault
        c.unchanged(cur,before,'failure midway');assert counts(cur,g)==n0==(0,0,0,0),(counts(cur,g),n0)
        assert one(cur,'select count(*) from cp7_cutting_correction.sewing_requests where request_id=%s',(key,))==0
        cur.execute('drop trigger cp17_r210_fault on erp.sewing_terminal_events');cur.execute('drop function public.cp17_r210_fault()')
        # The same request again once the fault is gone: one full answer, then the same answer.
        r=record(cur,w,[(A,5),(B,2)],at,key=key);again=record(cur,w,[(A,5),(B,2)],at,key=key)
        assert again==r and counts(cur,g)[:2]==(2,2) and counts(cur,g)[3]==2 and sewn_ready(cur,g)==(7,7)
        return dict(status='PASS',refused_after=dict(first_sku='completion + journal + SELESAI_DIJAHIT',second_sku='completion + journal'),fault=fault,
                    left_after_refusal=dict(completions=0,sewing_events=0,snapshots=0,history=0,request=0),resend_same_uuid=r['result']['qty_pcs'])
    def cancel_one():
        g=fixture(cur,today);w=read(cur,g);A,B=g['A']['id'],g['B']['id'];at=now(cur)-timedelta(seconds=30)
        r=record(cur,w,[(A,5),(B,2)],at);la,lb=r['result']['lines']
        journal=one(cur,"select id from erp.journal_entries where source_type='WORK_COMPLETION' and source_id=%s",(la['work_completion_id'],))
        w2=read(cur,g);event={e['id']:e for e in w2['events']}[la['sewing_event_id']]
        assert event['cancel_blocker'] is None and event['sku']==g['A']['sku'],event
        c.sewing_command(cur,w2,event=la['sewing_event_id'],reason='CP17 R2-10 salah SKU')
        assert one(cur,'select status from erp.work_completion_events where id=%s',(la['work_completion_id'],))=='REVERSED'
        assert one(cur,'select status from erp.journal_entries where id=%s',(journal,))=='REVERSED'
        assert one(cur,'select status from erp.work_completion_events where id=%s',(lb['work_completion_id'],))=='POSTED'
        w3=read(cur,g);k={x['sku_id']:x for x in w3['wave']['skus']}
        assert (k[A]['max_qty'],k[A]['posted_qty'],k[B]['max_qty'],k[B]['posted_qty'],w3['max_qty'])==(11,0,1,2,12) and sewn_ready(cur,g)==(2,2),(k,w3['max_qty'])
        return dict(status='PASS',cancelled=dict(sku='A',pieces=5,work_completion='REVERSED',wage_journal='REVERSED'),other_sku_kept=dict(sku='B',pieces=2),
                    sku_a_can_take_again=11)
    named=[per_sku,preview_native,refusals,failure_midway,cancel_one]
    assert len(named)==len(NATIVE)
    return list(zip(NATIVE,named))


def races(tools,today):
    def two_tabs():
        with tools.connect()as conn,conn.cursor()as cur:
            g=fixture(cur,today);w=read(cur,g);at=now(cur)-timedelta(seconds=30);conn.commit()
        A,B=g['A']['id'],g['B']['id'];barrier=threading.Barrier(2)
        def go(lines):
            with tools.connect()as conn,conn.cursor()as cur:
                barrier.wait(5)
                try:r=record(cur,w,lines,at);conn.commit();return('PASS',r['result']['qty_pcs'])
                except psycopg.Error as e:conn.rollback();return('REFUSED',str(e).splitlines()[0])
        with ThreadPoolExecutor(max_workers=2)as pool:results=[x.result(60)for x in[pool.submit(go,l)for l in([(A,6),(B,3)],[(A,7),(B,2)])]]
        assert sorted(x[0]for x in results)==['PASS','REFUSED'] and 'CP7_SEWING_STALE_REVIEW' in next(x[1]for x in results if x[0]=='REFUSED'),results
        with tools.connect()as conn,conn.cursor()as cur:
            n=counts(cur,g);ready=sewn_ready(cur,g)
        assert n[:2]==(2,2) and ready==(9,9),(n,ready)
        return dict(status='PASS',one_tab_recorded=9,other_tab=next(x[1]for x in results if x[0]=='REFUSED')[:160],completions=2)
    return list(zip(RACES,[two_tabs]))


def http_cases(http,today):
    def wave_http():
        admin=http.login('ADMIN','cp17-wave-sewing')
        with http.connect()as conn,conn.cursor()as cur:
            g=fixture(cur,today)
            role=one(cur,'select role_id from erp.app_users where auth_user_id=%s',(admin.auth_user_id,))
            for key in('production.wip.view','production.wip.post'):
                cur.execute('insert into erp.app_role_permissions(role_id,permission_key)values(%s,%s)on conflict do nothing',(role,key))
            at=now(cur)-timedelta(seconds=30);conn.commit()
        w=admin.rpc('erp_cp7_get_sewing_completion_v1',dict(p_group=g['group']))
        assert w['status']==200 and w['body']['eligible'] and w['body']['wave'] and w['body']['max_qty']==14,w
        body=payload(w['body'],[(g['A']['id'],3),(g['B']['id'],1)],at);key=str(uuid.uuid4())
        r=admin.rpc('erp_cp7_save_sewing_completion_v1',dict(p_payload=body,p_request=key,p_expected=w['body']['group_version']))
        assert r['status']==200 and r['body']['result']['qty_pcs']==4 and D(str(r['body']['result']['wage_amount']))==64,r
        again=admin.rpc('erp_cp7_save_sewing_completion_v1',dict(p_payload=body,p_request=key,p_expected=w['body']['group_version']))
        assert again['status']==200 and again['body']==r['body'],again
        with http.connect()as conn,conn.cursor()as cur:
            assert counts(cur,g)[:2]==(2,2) and sewn_ready(cur,g)==(4,4)
            assert [wage_journal(cur,x['work_completion_id'])for x in r['body']['result']['lines']]==[(D(33),D(33),1),(D(31),D(31),1)]
        return dict(status='PASS',real_Auth_recorded=dict(A=3,B=1),wage='33 + 31',same_uuid_same_answer=True)
    return list(zip(HTTP,[wave_http]))
