"""R3-09 (owner D16-2, D16-3, D16-4): choosing the PO's locked rate or today's Mandor rate when sewing is finished.

Native, race and real-Auth HTTP cases for scripts/cp7-src/cutting-correction/sewing.sql and the declared Native deltas of
cp7_rate_revision_bundle.py, spliced into the CP17 harness through cp7_r3_cases.py. The fixture is the G1 one: a posted
cutting of 10 picked up by its own Mandor, the PO model's Work BOM (Jahit default 2 with a Mandor rate 3, Obras default 1).
The first record locks Jahit 3 + Obras 1 for the PO; then the Mandor's Jahit rate is raised to 5 from the next WIB day through
the Mandor rate screen facade (erp_cp7_save_work_rate_v1), as the owner would. Oracles read Native rows (work completion
lines and the snapshot row each names, WORK_COMPLETION journals, the payroll eligibility view, the Native financial and
rework detectors before and after), never the facade's answer alone.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from decimal import Decimal as D
import json,threading,uuid
import psycopg
import cp7_snapshot_cases as auth
import cp7_master_cases as master
b=auth.b
refused=auth.refused

NATIVE=['CP17_R3_09_SAME_RATE_NO_CHOICE','CP17_R3_09_CHANGED_RATE_NEEDS_CHOICE','CP17_R3_09_CHOOSE_OLD_PAYS_LOCKED_RATE',
        'CP17_R3_09_CHOOSE_NEW_PAYS_THROUGH_REVISION','CP17_R3_09_ALWAYS_NEW_SWITCH','CP17_R3_09_SWITCH_REFUSALS_AND_ACCESS',
        'CP17_R3_09_CANCEL_NEW_RATE_RECORD','CP17_R3_09_NEW_RATE_WAGE_TO_PAYROLL_AND_DETECTORS','CP17_R3_09_WAVE_CHOICE_PER_SKU',
        'CP17_R3_09_DECLARED_NATIVE_DELTAS_AND_RESTORE_REFUSAL','CP17_R3_09_REVISIONS_IMMUTABLE_AND_PRIVATE']
RACES=['CP17_RACE_R3_09_TWO_TABS_CHOOSE_NEW_ONE_WINS','CP17_RACE_R3_09_SWITCH_AND_RECORD_ONE_WINS']
HTTP=['CP17_HTTP_R3_09_CHOICE_AND_SWITCH']
BROWSER=['CP17_BROWSER_R3_09_RATE_CHOICE_DESKTOP','CP17_BROWSER_R3_09_RATE_CHOICE_MOBILE']
REASON='CP17 R3-09 setoran jahit mandor'

def one(cur,sql,args=()):return cur.execute(sql,args).fetchone()[0]
def cp17():
    import cp7_cp17_fix_cases as m
    return m
def wave():
    import cp7_wave_sewing_cases as w
    return w

def fixture(cur,today):
    """The G1 fixture (posted cutting of 10, its own Mandor, Work BOM Jahit 2 / Obras 1, Mandor Jahit rate 3 from the day)."""
    c=cp17();g=c.pickup_fixture(cur,today);g['rates']=c.work_rates(cur,g);b.api.admin(cur)
    g['model']=str(one(cur,'select model_id from erp.production_orders where id=%s',(g['po'],)))
    return g
def raise_rate(cur,g,rate,day,component=None):
    """A new Mandor rate version from a WIB day, through the Mandor rate screen facade (as the owner would)."""
    comp=component or g['rates']['component']
    w=master.rws(cur,dict(contractor_id=g['mandor'],model_id=g['model']))
    c=[x for x in w['model']['components'] if x['component_id']==comp][0]
    return master.rsave(cur,'SET_RATE',dict(contractor_id=g['mandor'],model_id=g['model'],work_component_id=comp,rate=str(rate),
        effective_date=master.wib(day),review_token=c['review_token'],reason='Tarif mandor naik'))
def read(cur,g,subject=None):
    auth.actor(cur,subject);w=one(cur,'select public.erp_cp7_get_sewing_completion_v1(%s)',(g['group'],));b.api.admin(cur);return w
def body(w,qty,at,choice=None,reason=REASON,token=None):
    p=dict(action='RECORD',group_id=w['group_id'],qty_pcs=str(qty),physical_at=at.isoformat(),review_token=token or w['review_token'],change_reason=reason)
    if choice is not None:p['rate_choice']=choice
    return p
def switch_body(w,reason='Tarif mandor naik, pakai yang baru',token=None):
    return dict(action='USE_NEW_RATES',group_id=w['group_id'],review_token=token or w['review_token'],change_reason=reason)
def send(cur,w,p,key=None,expected=None,subject=None):
    auth.actor(cur,subject)
    r=one(cur,'select public.erp_cp7_save_sewing_completion_v1(%s,%s,%s)',(json.dumps(p),str(key or uuid.uuid4()),expected or w['group_version']))
    b.api.admin(cur);return r
def record(cur,w,qty,at,choice=None,**kw):
    key,expected,subject=kw.pop('key',None),kw.pop('expected',None),kw.pop('subject',None)
    return send(cur,w,body(w,qty,at,choice,**kw),key,expected,subject)
def lines(cur,completion):
    """Native rows: per line the component, pieces, rate, amount, and whether the snapshot it names is a rate revision."""
    b.api.admin(cur)
    return cur.execute("""select l.work_component_id::text,l.qty_completed,l.rate_snapshot,l.amount_payable,s.rate_per_pcs_snapshot,
        exists(select 1 from cp7_cutting_correction.rate_revisions r where r.snapshot_id=s.id)
        from erp.work_completion_lines l join erp.po_work_component_snapshots s on s.id=l.po_component_snapshot_id
        where l.completion_id=%s order by s.sequence_no,s.id""",(completion,)).fetchall()
def snapshots(cur,g):
    b.api.admin(cur)
    return cur.execute("""select s.work_component_id::text,s.rate_per_pcs_snapshot,r.basis_at is not null,r.basis_at
        from erp.po_work_component_snapshots s left join cp7_cutting_correction.rate_revisions r on r.snapshot_id=s.id
        where s.po_id=%s order by s.sequence_no,s.committed_at,s.id""",(g['po'],)).fetchall()
def segment(timeline,at):
    from datetime import datetime
    for s in timeline:
        if datetime.fromisoformat(s['from'])<=at and(s['to'] is None or at<datetime.fromisoformat(s['to'])):
            return [(x['code'],D(str(x['rate'])))for x in s['rates']]if s['complete'] else None
    return None
def detectors(cur):
    """Issue counts of the Native financial report and BS/rework integrity detectors (the AI_WORK_SOURCE checks among them)."""
    b.api.admin(cur);out={}
    for fn in('erp.run_v268_financial_report_checks','erp.run_v263c_bs_rework_integrity_checks'):
        for row in cur.execute(f'select to_jsonb(x) from {fn}() x').fetchall():
            r=row[0];out[fn+':'+str(r.get('check_name'))]=r.get('issue_count')
    return out
def locked_then_raised(cur,today,qty=4):
    """First record at the fixture day 10:00 (locks Jahit 3 + Obras 1), then the Mandor's Jahit rate 5 from the next day."""
    g=fixture(cur,today);w=read(cur,g)
    first=record(cur,w,qty,g['at'](10))
    raise_rate(cur,g,5,g['day']+timedelta(days=1))
    g['next']=g['day']+timedelta(days=1)
    g['later']=lambda h,minute=0:cp17().cut.cutting.qc.physical.b.chain.production.at(g['next'],h,minute)
    return g,first


def cases(cur,today):
    c=cp17()
    def same_rate():
        g=fixture(cur,today);w=read(cur,g)
        assert w['rates_committed'] is False and w['new_rate_timeline']==[] and w['rate_mode'] is None and w['can_use_new_rates'] is False,w
        # A first record never asks: it locks the rates of its own sewing time.
        before=b.boundary.snapshot(cur)
        unexpected=refused(cur,lambda:record(cur,w,4,g['at'](10),'NEW'),'CP7_SEWING_RATE_CHOICE_UNEXPECTED');c.unchanged(cur,before,'choice on a first record')
        r=record(cur,w,4,g['at'](10))
        assert (r['result']['rate_choice'],r['result']['rate_used'],r['result']['revised_components'])==(None,'LOCKED',0),r['result']
        w2=read(cur,g)
        assert w2['rates_committed'] and w2['can_use_new_rates'] and segment(w2['new_rate_timeline'],g['at'](11))==[(x['code'],D(str(x['rate'])))for x in w2['components']],w2
        # Same Mandor rate later: no choice, the locked rate, no revision.
        before=b.boundary.snapshot(cur)
        again=refused(cur,lambda:record(cur,w2,2,g['at'](11),'OLD'),'CP7_SEWING_RATE_CHOICE_UNEXPECTED');c.unchanged(cur,before,'choice where rates are equal')
        r2=record(cur,w2,2,g['at'](11))
        assert [(x[0],x[2],x[5])for x in lines(cur,r2['result']['work_completion_id'])]==[(g['rates']['component'],D(3),False),(g['rates']['obras'],D(1),False)]
        assert one(cur,'select count(*) from cp7_cutting_correction.rate_revisions where po_id=%s',(g['po'],))==0
        return dict(status='PASS',first_record_choice_refused=unexpected,equal_rates_choice_refused=again,locked_rates=[3,1],revisions=0)
    def needs_choice():
        g,_=locked_then_raised(cur,today);w=read(cur,g)
        shown_old=[(x['code'],D(str(x['rate'])))for x in w['components']];shown_new=segment(w['new_rate_timeline'],g['later'](10))
        assert [r for _,r in shown_old]==[D(3),D(1)] and [r for _,r in shown_new]==[D(5),D(1)],(shown_old,shown_new)
        # Before the new version (still the fixture day) the rates are equal.
        assert segment(w['new_rate_timeline'],g['at'](12))==shown_old,w['new_rate_timeline']
        before=b.boundary.snapshot(cur)
        required=refused(cur,lambda:record(cur,w,2,g['later'](10)),'CP7_SEWING_RATE_CHOICE_REQUIRED');c.unchanged(cur,before,'no choice where rates differ')
        bad=refused(cur,lambda:send(cur,w,dict(body(w,2,g['later'](10)),rate_choice='LATEST')),'CP7_SEWING_FIELDS');c.unchanged(cur,before,'unknown choice')
        bad_type=refused(cur,lambda:send(cur,w,dict(body(w,2,g['later'](10)),rate_choice=True)),'CP7_SEWING_FIELDS');c.unchanged(cur,before,'choice not a string')
        return dict(status='PASS',shown_locked=[str(r) for _,r in shown_old],shown_new_at_sewing_time=[str(r) for _,r in shown_new],
                    no_choice_refused=required,unknown_choice_refused=bad,non_string_choice_refused=bad_type)
    def choose_old():
        g,_=locked_then_raised(cur,today);w=read(cur,g)
        r=record(cur,w,2,g['later'](10),'OLD');comp=r['result']['work_completion_id']
        assert (r['result']['rate_choice'],r['result']['rate_used'],r['result']['revised_components'],D(str(r['result']['wage_amount'])))==('OLD','LOCKED',0,D(8)),r['result']
        assert [(x[2],x[3],x[5])for x in lines(cur,comp)]==[(D(3),D(6),False),(D(1),D(2),False)],lines(cur,comp)
        assert c.wage_journal(cur,comp)==(D(8),D(8),1)
        assert one(cur,'select count(*) from cp7_cutting_correction.rate_revisions where po_id=%s',(g['po'],))==0
        return dict(status='PASS',paid='Jahit 3 + Obras 1 (locked)',wage='WIP 8 / CONTRACTOR_PAYABLE 8',revisions=0)
    def choose_new():
        g,first=locked_then_raised(cur,today);w=read(cur,g);det=detectors(cur)
        at=g['later'](10);key=uuid.uuid4()
        r=record(cur,w,2,at,'NEW',key=key);again=record(cur,w,2,at,'NEW',key=key)
        assert again==r and (r['result']['rate_choice'],r['result']['rate_used'],r['result']['revised_components'],D(str(r['result']['wage_amount'])))==('NEW','NEW',1,D(12)),r['result']
        comp=r['result']['work_completion_id']
        # Native rows: Jahit at 5 on a rate revision whose own rate is 5; Obras (unchanged) on the original row.
        assert [(x[0],x[2],x[3],x[4],x[5])for x in lines(cur,comp)]==[(g['rates']['component'],D(5),D(10),D(5),True),(g['rates']['obras'],D(1),D(2),D(1),False)],lines(cur,comp)
        assert c.wage_journal(cur,comp)==(D(12),D(12),1)
        # The first record keeps its locked wage.
        assert [(x[2],x[5])for x in lines(cur,first['result']['work_completion_id'])]==[(D(3),False),(D(1),False)]
        snaps=snapshots(cur,g)
        assert [(x[0],x[1],x[2])for x in snaps]==[(g['rates']['component'],D(3),False),(g['rates']['component'],D(5),True),(g['rates']['obras'],D(1),False)],snaps
        assert snaps[1][3]==at,snaps
        # A second record at the same sewing time reuses that revision; another sewing time gets its own.
        w2=read(cur,g);r2=record(cur,w2,1,at,'NEW')
        assert [x[5] for x in lines(cur,r2['result']['work_completion_id'])]==[True,False]
        assert one(cur,'select count(*) from cp7_cutting_correction.rate_revisions where po_id=%s',(g['po'],))==1
        w3=read(cur,g);record(cur,w3,1,g['later'](11),'NEW')
        assert one(cur,'select count(*) from cp7_cutting_correction.rate_revisions where po_id=%s',(g['po'],))==2
        # The workspace keeps showing the locked rates; the sewn total and the per-component posted pieces count every record.
        w4=read(cur,g)
        assert [(x['rate'],x['posted_qty'])for x in w4['components']]==[(3,8),(1,8)] and w4['max_qty']==2,w4['components']
        assert detectors(cur)==det,('CP17_R3_09_DETECTOR_CHANGED',{k:(det.get(k),v)for k,v in detectors(cur).items() if det.get(k)!=v})
        return dict(status='PASS',paid='Jahit 5 (revision) + Obras 1 (locked row)',wage='WIP 12 / CONTRACTOR_PAYABLE 12',same_uuid_same_answer=True,
                    revision_reused_same_time=True,revision_per_sewing_time=2,first_wage_unchanged=True,native_detectors_unchanged=True)
    def always_new():
        g,first=locked_then_raised(cur,today);w=read(cur,g)
        assert w['can_use_new_rates'] and w['rate_mode'] is None
        key=uuid.uuid4();s=send(cur,w,switch_body(w),key);again=send(cur,w,switch_body(w),key)
        assert again==s and s['action']=='USE_NEW_RATES' and s['result']['rate_mode']=='ALWAYS_NEW' and s['result']['po_id']==g['po'],s
        assert one(cur,'select count(*) from cp7_cutting_correction.po_rate_modes where po_id=%s',(g['po'],))==1
        w2=read(cur,g)
        assert w2['rate_mode']=='ALWAYS_NEW' and w2['rate_mode_at'] and w2['can_use_new_rates'] is False,w2
        before=b.boundary.snapshot(cur)
        unexpected=refused(cur,lambda:record(cur,w2,2,g['later'](10),'OLD'),'CP7_SEWING_RATE_CHOICE_UNEXPECTED');c.unchanged(cur,before,'choice on a switched PO')
        twice=refused(cur,lambda:send(cur,w2,switch_body(w2)),'CP7_SEWING_RATE_MODE_ALREADY');c.unchanged(cur,before,'switch twice')
        r=record(cur,w2,2,g['later'](10))
        assert (r['result']['rate_choice'],r['result']['rate_mode'],r['result']['rate_used'],D(str(r['result']['wage_amount'])))==(None,'ALWAYS_NEW','NEW',D(12)),r['result']
        # A sewing time before the new Mandor rate: the rate then is the locked one, so nothing is revised.
        w3=read(cur,g);r2=record(cur,w3,1,g['at'](12))
        assert (r2['result']['rate_used'],r2['result']['revised_components'])==('LOCKED',0),r2['result']
        assert [(x[2],x[5])for x in lines(cur,first['result']['work_completion_id'])]==[(D(3),False),(D(1),False)]
        return dict(status='PASS',switch_same_uuid_same_answer=True,choice_after_switch_refused=unexpected,switch_twice_refused=twice,
                    after_switch_new_rate_without_asking=12,before_new_version_locked_rate=True,old_wages_unchanged=True)
    def switch_refusals():
        g=fixture(cur,today);w=read(cur,g);before=b.boundary.snapshot(cur)
        not_locked=refused(cur,lambda:send(cur,w,switch_body(w)),'CP7_SEWING_RATE_MODE_NOT_LOCKED');c.unchanged(cur,before,'switch before rates are locked')
        record(cur,w,4,g['at'](10));w=read(cur,g);before=b.boundary.snapshot(cur)
        fields=refused(cur,lambda:send(cur,w,dict(switch_body(w),qty_pcs='1')),'CP7_SEWING_FIELDS');c.unchanged(cur,before,'extra key')
        short=refused(cur,lambda:send(cur,w,switch_body(w,reason='x')),'CP7_SEWING_FIELDS');c.unchanged(cur,before,'short reason')
        stale=refused(cur,lambda:send(cur,w,switch_body(w,token='0'*32)),'CP7_SEWING_STALE_REVIEW');c.unchanged(cur,before,'stale review')
        # Owner D16-4: only Owner/Admin choose the new rate or switch the PO; a production role with the WIP rights is refused.
        # The production role is given the WIP rights here, so only its role (not a missing right) can refuse it.
        subject=master.role_actor(cur,'PRODUKSI_QC');b.api.admin(cur)
        role=one(cur,'select role_id from erp.app_users where auth_user_id=%s',(subject,))
        for key in('production.wip.view','production.wip.post','production.wip.reverse'):
            cur.execute('insert into erp.app_role_permissions(role_id,permission_key)values(%s,%s)on conflict do nothing',(role,key))
        # The boundary is taken again after this actor exists (first CI run 39003879442 compared it with the one before the
        # actor's own fixture rows; log kept).
        before=b.boundary.snapshot(cur)
        denied_read=refused(cur,lambda:read(cur,g,subject),'CP7_SEWING_DENIED')
        denied_switch=refused(cur,lambda:send(cur,w,switch_body(w),subject=subject),'CP7_SEWING_DENIED');c.unchanged(cur,before,'non Owner/Admin switch')
        raise_rate(cur,g,5,g['day']+timedelta(days=1));w=read(cur,g);before=b.boundary.snapshot(cur)
        at=c.cut.cutting.qc.physical.b.chain.production.at(g['day']+timedelta(days=1),10)
        denied_new=refused(cur,lambda:record(cur,w,1,at,'NEW',subject=subject),'CP7_SEWING_DENIED');c.unchanged(cur,before,'non Owner/Admin new rate')
        return dict(status='PASS',before_lock=not_locked,extra_key=fields,short_reason=short,stale_review=stale,
                    non_owner_admin=dict(read=denied_read,switch=denied_switch,new_rate=denied_new))
    def cancel_new():
        g,_=locked_then_raised(cur,today);w=read(cur,g)
        r=record(cur,w,2,g['later'](10),'NEW');comp=r['result']['work_completion_id'];event=r['result']['sewing_event_id']
        journal=one(cur,"select id from erp.journal_entries where source_type='WORK_COMPLETION' and source_id=%s",(comp,))
        w2=read(cur,g);x=send(cur,w2,dict(action='REVERSE',group_id=w2['group_id'],event_id=event,review_token=w2['review_token'],change_reason='CP17 R3-09 salah tarif'))
        assert x['result']['status']=='CANCELLED',x
        assert one(cur,'select status from erp.work_completion_events where id=%s',(comp,))=='REVERSED'
        assert one(cur,'select status from erp.journal_entries where id=%s',(journal,))=='REVERSED'
        # The revision stays (snapshot rows are never deleted); a new record may still choose either rate.
        assert one(cur,'select count(*) from cp7_cutting_correction.rate_revisions where po_id=%s',(g['po'],))==1
        w3=read(cur,g);r2=record(cur,w3,2,g['later'](10),'OLD')
        assert [x[2] for x in lines(cur,r2['result']['work_completion_id'])]==[D(3),D(1)]
        return dict(status='PASS',cancelled='REVERSED with its WORK_COMPLETION journal',revision_kept=True,later_choice_free=True)
    def payroll_and_detectors():
        g,_=locked_then_raised(cur,today);w=read(cur,g);det=detectors(cur)
        r=record(cur,w,6,g['later'](10),'NEW');comp=r['result']['work_completion_id']
        ids=[str(x[0]) for x in cur.execute('select id from erp.work_completion_lines where completion_id=%s',(comp,)).fetchall()]
        b.api.admin(cur)
        elig=cur.execute('select count(*),sum(source_qty_payable) from erp.v_payroll_production_work_eligibility where source_id=any(%s::uuid[])',(ids,)).fetchone()
        assert elig==(2,12),('CP17_R3_09_NEW_RATE_NOT_IN_PAYROLL_PIPELINE',elig)
        amount=one(cur,'select sum(amount_payable) from erp.work_completion_lines where completion_id=%s',(comp,))
        assert D(amount)==D(36) and c.wage_journal(cur,comp)==(D(36),D(36),1),amount
        assert detectors(cur)==det,('CP17_R3_09_DETECTOR_CHANGED',{k:(det.get(k),v)for k,v in detectors(cur).items() if det.get(k)!=v})
        hpp=one(cur,'select to_jsonb(x) from erp.get_hpp_completeness(%s)x',(g['po'],))
        return dict(status='PASS',payroll_pipeline_lines=2,payable_pieces=12,wage='6 pcs x (5 + 1) = 36',native_detectors_unchanged=True,
                    hpp_completeness_reads=bool(hpp))
    def wave_choice():
        wv=wave();g=wv.fixture(cur,today);w=wv.read(cur,g);A,B=g['A']['id'],g['B']['id']
        at=wv.now(cur)-timedelta(seconds=40);first=wv.record(cur,w,[(A,2),(B,1)],at)
        # Obras has no SKU rate, so each SKU takes the base Obras rate: raise the Mandor's Obras rate (base rule) now.
        b.api.admin(cur);obras=g['rates']['obras'];model=str(one(cur,'select model_id from erp.production_orders where id=%s',(g['po'],)))
        since=one(cur,"select clock_timestamp()-interval '20 seconds'")
        cur.execute('insert into erp.contractor_work_rates(contractor_id,model_id,work_component_id,rate_per_pcs,effective_from)values(%s,%s,%s,2,%s)',(g['mandor'],model,obras,since))
        later=wv.now(cur)-timedelta(seconds=5);w2=wv.read(cur,g)
        seg=None
        from datetime import datetime
        for s in w2['wave']['new_timeline']:
            if datetime.fromisoformat(s['from'])<=later and(s['to'] is None or later<datetime.fromisoformat(s['to'])):seg=s
        assert seg is not None,w2['wave']['new_timeline']
        per={k['sku_id']:sorted(D(str(x['rate']))for x in k['rates'])for k in seg['skus']}
        assert per=={A:[D(2),D(10)],B:[D(2),D(30)]},per
        before=b.boundary.snapshot(cur)
        required=refused(cur,lambda:wv.send(cur,w2,wv.payload(w2,[(A,1)],later)),'CP7_SEWING_RATE_CHOICE_REQUIRED');c.unchanged(cur,before,'wave without choice')
        p=dict(wv.payload(w2,[(A,1),(B,1)],later),rate_choice='NEW');r=wv.send(cur,w2,p)
        assert (r['result']['rate_used'],r['result']['revised_components'],D(str(r['result']['wage_amount'])))==('NEW',2,D(12)+D(32)),r['result']
        la,lb=r['result']['lines']
        got={l['sku_id']:[(row[0],row[3],row[5]) for row in wv.lines_of(cur,l['work_completion_id'])] for l in(la,lb)}
        assert got[A][1][1]==D(2) and got[B][1][1]==D(2) and got[A][0][1]==D(10) and got[B][0][1]==D(30),got
        revised=cur.execute("""select v.sku_id::text,s.rate_per_pcs_snapshot from cp7_cutting_correction.rate_revisions r join erp.po_work_component_snapshots s on s.id=r.snapshot_id
            join erp.bf_sku_versions_v1 v on v.id=s.bf_sku_version_id where r.po_id=%s order by 1""",(g['po'],)).fetchall()
        assert sorted(revised)==sorted([(A,D(2)),(B,D(2))]),revised
        for l in first['result']['lines']:
            assert [row[3] for row in wv.lines_of(cur,l['work_completion_id'])][1]==D(1)
        return dict(status='PASS',new_obras_rate_per_sku=2,choice_required=required,revisions_per_sku=2,first_wave_wage_unchanged=True)
    def native_deltas():
        import cp7_rate_revision_bundle as rr
        b.api.admin(cur);rr.verify(cur)
        g,_=locked_then_raised(cur,today);w=read(cur,g);record(cur,w,1,g['later'](10),'NEW')
        # The accepted index cannot come back while a revision exists: the restore refuses and changes nothing.
        cur.execute('savepoint r309_restore')
        try:
            cur.execute(rr.restore_index());restored=None
        except psycopg.Error as e:restored=e.diag.message_primary
        cur.execute('rollback to savepoint r309_restore')
        assert restored and restored.startswith('CP7_RATE_REVISIONS_IN_USE'),restored
        assert rr.index_definition(cur)==rr.NEW_INDEX
        # A SKU pinned after a base revision takes the original base rows only (erp.bf_ensure_work_v1 delta): one row per component.
        dup=cur.execute("""select count(*) from(select po_id,work_component_id,bf_sku_version_id from erp.po_work_component_snapshots
            where po_id=%s and not exists(select 1 from cp7_cutting_correction.rate_revisions r where r.snapshot_id=id)
            group by 1,2,3 having count(*)>1)x""",(g['po'],)).fetchone()[0]
        assert dup==0
        guard=one(cur,"select md5(pg_get_functiondef('erp.guard_used_contractor_work_rate()'::regprocedure))") if one(cur,"select to_regprocedure('erp.guard_used_contractor_work_rate()') is not null")else None
        return dict(status='PASS',deltas=sorted(rr.PATCHES)+[rr.INDEX_KEY],restore_refused_with_revision=restored,original_rows_unique=True,
                    used_rate_guard_md5=guard)
    def immutable_private():
        g,_=locked_then_raised(cur,today);w=read(cur,g);record(cur,w,1,g['later'](10),'NEW');send(cur,read(cur,g),switch_body(read(cur,g)))
        b.api.admin(cur)
        upd=refused(cur,lambda:cur.execute('update cp7_cutting_correction.rate_revisions set basis_at=basis_at where po_id=%s',(g['po'],)),'')
        dele=refused(cur,lambda:cur.execute('delete from cp7_cutting_correction.po_rate_modes where po_id=%s',(g['po'],)),'')
        for table in('rate_revisions','po_rate_modes'):
            for who in('anon','authenticated','service_role','cp7_cutting_read','cp7_cutting_write'):
                assert not one(cur,"select has_table_privilege(%s,%s,'SELECT,INSERT,UPDATE,DELETE')",(who,'cp7_cutting_correction.'+table)),(who,table)
        for fn in('sewing_rule_rates(uuid,timestamptz)','sewing_wave_rule(uuid,timestamptz)','sewing_revision(uuid,uuid,numeric,uuid,timestamptz,uuid)'):
            for who in('anon','authenticated','service_role','cp7_cutting_read','cp7_cutting_write'):
                assert not one(cur,"select has_function_privilege(%s,%s,'EXECUTE')",(who,'cp7_cutting_correction.'+fn)),(who,fn)
        return dict(status='PASS',revision_update_refused=upd,switch_delete_refused=dele,tables_private=True,helpers_not_executable=True)
    named=[same_rate,needs_choice,choose_old,choose_new,always_new,switch_refusals,cancel_new,payroll_and_detectors,wave_choice,native_deltas,immutable_private]
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
        with ThreadPoolExecutor(max_workers=len(args))as pool:return [x.result(60) for x in [pool.submit(go,a) for a in args]]
    def choose_new_two_tabs():
        with tools.connect()as conn,conn.cursor()as cur:
            g,_=locked_then_raised(cur,today);w=read(cur,g);conn.commit()
        results=two(lambda cur,n:record(cur,w,1,g['later'](10),'NEW')['result']['rate_used'],[1,2])
        assert sorted(x[0] for x in results)==['PASS','REFUSED'] and 'CP7_SEWING_STALE_REVIEW' in next(x[1] for x in results if x[0]=='REFUSED'),results
        with tools.connect()as conn,conn.cursor()as cur:
            b.api.admin(cur);n=one(cur,'select count(*) from cp7_cutting_correction.rate_revisions where po_id=%s',(g['po'],))
        assert n==1,n
        return dict(status='PASS',two_tabs=results,one_revision=True)
    def switch_and_record():
        with tools.connect()as conn,conn.cursor()as cur:
            g,_=locked_then_raised(cur,today);w=read(cur,g);conn.commit()
        results=two(lambda cur,a:send(cur,w,switch_body(w))['action'] if a=='SWITCH' else record(cur,w,1,g['later'](10),'OLD')['action'],['SWITCH','RECORD'])
        assert sorted(x[0] for x in results)==['PASS','REFUSED'] and 'CP7_SEWING_STALE_REVIEW' in next(x[1] for x in results if x[0]=='REFUSED'),results
        with tools.connect()as conn,conn.cursor()as cur:
            b.api.admin(cur)
            state=(one(cur,'select count(*) from cp7_cutting_correction.po_rate_modes where po_id=%s',(g['po'],)),
                   one(cur,"select count(*) from erp.work_completion_events where cutting_group_id=%s and status='POSTED'",(g['group'],)))
        assert state in((1,1),(0,2)),state
        return dict(status='PASS',two_tabs=results,one_effect=dict(switches=state[0],posted_records=state[1]))
    return list(zip(RACES,[choose_new_two_tabs,switch_and_record]))


def http_cases(http,today):
    def choice_and_switch():
        admin=http.login('ADMIN','cp17-r3-09-rate')
        with http.connect()as conn,conn.cursor()as cur:
            g,_=locked_then_raised(cur,today)
            role=one(cur,'select role_id from erp.app_users where auth_user_id=%s',(admin.auth_user_id,))
            for key in('production.wip.view','production.wip.post'):
                cur.execute('insert into erp.app_role_permissions(role_id,permission_key)values(%s,%s)on conflict do nothing',(role,key))
            at=g['later'](10).isoformat();conn.commit()
        w=admin.rpc('erp_cp7_get_sewing_completion_v1',dict(p_group=g['group']));assert w['status']==200,w;w=w['body']
        p=dict(action='RECORD',group_id=g['group'],qty_pcs='2',physical_at=at,review_token=w['review_token'],change_reason=REASON)
        missing=admin.rpc('erp_cp7_save_sewing_completion_v1',dict(p_payload=p,p_request=str(uuid.uuid4()),p_expected=w['group_version']))
        assert missing['status']>=400 and 'CP7_SEWING_RATE_CHOICE_REQUIRED' in json.dumps(missing['body']),missing
        key=str(uuid.uuid4());body=dict(p,rate_choice='NEW')
        r=admin.rpc('erp_cp7_save_sewing_completion_v1',dict(p_payload=body,p_request=key,p_expected=w['group_version']))
        assert r['status']==200 and r['body']['result']['rate_used']=='NEW' and D(str(r['body']['result']['wage_amount']))==12,r
        again=admin.rpc('erp_cp7_save_sewing_completion_v1',dict(p_payload=body,p_request=key,p_expected=w['group_version']))
        assert again['status']==200 and again['body']==r['body'],again
        w2=admin.rpc('erp_cp7_get_sewing_completion_v1',dict(p_group=g['group']))['body']
        s=admin.rpc('erp_cp7_save_sewing_completion_v1',dict(p_payload=switch_body(w2),p_request=str(uuid.uuid4()),p_expected=w2['group_version']))
        assert s['status']==200 and s['body']['result']['rate_mode']=='ALWAYS_NEW',s
        w3=admin.rpc('erp_cp7_get_sewing_completion_v1',dict(p_group=g['group']))['body']
        assert w3['rate_mode']=='ALWAYS_NEW' and w3['can_use_new_rates'] is False,w3
        r3=admin.rpc('erp_cp7_save_sewing_completion_v1',dict(p_payload=dict(p,qty_pcs='1',review_token=w3['review_token']),p_request=str(uuid.uuid4()),p_expected=w3['group_version']))
        assert r3['status']==200 and r3['body']['result']['rate_used']=='NEW' and r3['body']['result']['rate_choice'] is None,r3
        # The record after the switch has the same sewing time as the NEW record, so it reuses that revision (design 2.2); the
        # first CI run (39003879442, log kept) expected a second revision, which the design does not make.
        with http.connect()as conn,conn.cursor()as cur:
            b.api.admin(cur);n=one(cur,'select count(*) from cp7_cutting_correction.rate_revisions where po_id=%s',(g['po'],))
            reused=one(cur,"""select count(distinct l.po_component_snapshot_id) from erp.work_completion_lines l
                join cp7_cutting_correction.rate_revisions r on r.snapshot_id=l.po_component_snapshot_id
                where l.completion_id=any(%s::uuid[])""",([r['body']['result']['work_completion_id'],r3['body']['result']['work_completion_id']],))
        assert (n,reused)==(1,1),(n,reused)
        return dict(status='PASS',real_Auth=True,missing_choice_refused=True,new_rate_wage=12,same_uuid_same_answer=True,switched=True,
                    after_switch_without_choice=True,revisions=n)
    return list(zip(HTTP,[choice_and_switch]))
