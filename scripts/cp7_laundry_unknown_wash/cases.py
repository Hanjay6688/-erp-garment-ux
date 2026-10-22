"""OW-08b Native cases: a failed wash may wait for its laundry vendor price (owner LAU-DEC04).

Business rows come only from the retained writers: the CP6 laundry facade (POST_DELIVERY, POST_RECEIPT, POST_FAILED_WASH,
REVERSE_RECEIPT, REVERSE_DELIVERY, POST_FINAL_SKU), the BD facade (process rates, policies, invoices, the new
SET_FAILED_WASH_PRICE), the sales writers and the CP7 period control. The delivery's own wash process has a known rate; the
failed (re)wash process is a second process without a rate, so the only unknown price is the attempt's.

Twins run on the SAME state inside rolled-back savepoints: the same attempt posted with a known rate (the old path) is the
oracle for physical effects and, after the price is set to that rate, for accrual, journals by account and date, and HPP.
The exact replaced (OW07) definitions are read side by side inside rolled-back savepoints, so every case shows what the
original engine did on the same state. Two privileged corruptions (two effective rates; a priced line behind an UNKNOWN
record) are explicit, inside nested savepoints, and always rolled back.
"""
from collections import Counter
from datetime import timedelta
from decimal import Decimal as D
import json
import re
import uuid

import psycopg

import cp6_bd_probe as bd
import cp7_snapshot_cases as auth
import cp7_period_cases as period
from cp7_laundry_unknown_wash import native_delta

b=auth.b
chain=bd.chain
IDS=('OW08B_WASH_UNKNOWN_RECORDED_NOT_ZERO_HPP_NOT_FINAL',
     'OW08B_WASH_WITHOUT_FLAG_REFUSED_AS_BEFORE',
     'OW08B_WASH_TWO_EFFECTIVE_RATES_REFUSED',
     'OW08B_WASH_CLOSE_BLOCKED_UNTIL_PRICED_EQUALS_KNOWN_TWIN',
     'OW08B_WASH_RETURN_UNPROCESSED_UNKNOWN_PRICE',
     'OW08B_WASH_PRICE_SET_ONCE_OWNER_ADMIN_ONLY',
     'OW08B_WASH_REVERSE_UNKNOWN_NO_MONEY_EFFECT',
     'OW08B_WASH_SALE_FOLLOWS_LAU_DEC04',
     'OW08B_WASH_INVOICE_REFUSED_UNTIL_PRICED',
     'OW08B_WASH_OTHER_LAUNDRY_COMMANDS_UNCHANGED',
     'OW08B_WASH_STATE_DETECTOR_AND_PRIVATE_SCHEMA')
REASON='OW08b cuci gagal ditagih vendor'
CODE='LAUNDRY_FAILED_WASH_PRICE_UNKNOWN'
MISMATCH='LAUNDRY_FAILED_WASH_PRICE_STATE_MISMATCH'
OLD_RATE_REFUSAL='Exactly one authoritative failed-wash rate must be effective for this vendor/process/time'
ORIGINALS=None  # set by the probe: the exact OW07-product definitions this stage replaced
AS_OWNER=None   # set by the probe: the verified predecessor role switch


def one(cur,sql,args=()):
    return cur.execute(sql,args).fetchone()[0]


def at(w,hour,minute=0):
    return chain.production.at(w['day'],hour,minute).isoformat()


def savepoint(cur,fn,prefix):
    """fn on the current state, then everything it wrote is rolled back."""
    name=prefix+'_'+uuid.uuid4().hex
    cur.execute('savepoint '+name)
    try:return fn()
    finally:
        cur.execute('rollback to savepoint '+name);cur.execute('release savepoint '+name);b.api.admin(cur)


def original(cur,fn,signatures=native_delta.SIGNATURES):
    """The same state read or written through the exact replaced definitions, then restored."""
    def run():
        with AS_OWNER(cur,'postgres'):
            for sig in signatures:cur.execute(ORIGINALS[sig],prepare=False)
        b.api.admin(cur)
        return fn()
    return savepoint(cur,run,'ow08b_original')


def fixture(cur,today,label,qty=10):
    """Ten pieces sent to a fresh vendor at hour 11 on a known rate (2.00); the failed process has no rate."""
    fx=bd.fixture(cur,today-timedelta(days=3),label+'-'+uuid.uuid4().hex[:8])
    bd.process_rate(cur,fx,'2.00');b.api.admin(cur)
    failed_process=str(uuid.uuid4())
    cur.execute('insert into erp.wash_processes(id,process_code,process_name,is_active)values(%s,%s,%s,true)',
                (failed_process,'OW08B-'+uuid.uuid4().hex[:12],'OW08b cuci ulang '+label))
    w=dict(fx=fx,po=fx['po'],vendor=fx['vendor'],day=fx['day'],failed=failed_process)
    w['delivery']=str(bd.plain_delivery(cur,fx,qty,11));b.api.admin(cur)
    w['size']=str(chain.base.delivery_size_line(cur,w['delivery']))
    return w


def known_rate(cur,w,rate='3.00'):
    bd.process_rate(cur,dict(w['fx'],process=w['failed']),rate);b.api.admin(cur)


def failed(cur,w,hour,qty=10,outcome='RETRY_AT_VENDOR',unknown=True,extra=None,delivery=None,size=None):
    p=dict(delivery_id=delivery or w['delivery'],wash_process_id=w['failed'],custody_outcome=outcome,physical_at=at(w,hour),reason=REASON,
           lines=[dict(delivery_batch_size_line_id=size or w['size'],qty_attempted_pcs=qty)])
    if unknown:p['price_status']='UNKNOWN'
    if extra:p.update(extra)
    r=chain.laundry_action(cur,'POST_FAILED_WASH',p,chain.base.delivery_version(cur,delivery or w['delivery']))
    b.api.admin(cur);return r


def price(cur,attempt,rate='3.00',status='KNOWN',reason='OW08b nota vendor datang',key=None,subject=None):
    return bd.bd(cur,'SET_FAILED_WASH_PRICE',dict(failed_wash_attempt_id=str(attempt),rate_status=status,rate_per_pcs=rate,reason=reason),
                 key=key,auth=subject)


def attempt_line(cur,attempt):
    b.api.admin(cur)
    return cur.execute("""select l.actual_rate_snapshot,l.actual_cost,l.actual_cost_status from erp.laundry_receipt_lines l
        where l.id=(select receipt_line_id from erp.laundry_failed_wash_attempts where id=%s)""",(attempt,)).fetchone()


def money(cur,po):
    """Accrual, every journal line of the PO by account and economic date, and the current HPP of its lots."""
    b.api.admin(cur)
    journal=[list(r)for r in cur.execute("""select a.account_code::text,je.economic_date::text,sum(l.debit-l.credit)::numeric(20,2)::text
        from erp.journal_lines l join erp.journal_entries je on je.id=l.journal_entry_id join erp.chart_accounts a on a.id=l.account_id
        where l.po_id=%s and je.status in('POSTED','REVERSED') group by 1,2 having sum(l.debit-l.credit)<>0 order by 1,2""",(po,)).fetchall()]
    hpp=[list(r)for r in cur.execute("""select l.initial_qty_pcs,h.total_cost::numeric(20,2)::text,h.cost_state::text from erp.fg_lots l
        join erp.hpp_versions h on h.lot_id=l.id and h.is_current where l.po_id=%s and l.lot_origin='PRODUCTION' order by 1,2,3""",(po,)).fetchall()]
    return dict(desired=str(one(cur,'select coalesce(erp.desired_laundry_accrual(%s),0)::numeric(20,2)',(po,))),
        accrued=str(one(cur,'select coalesce((select accrued_amount from erp.laundry_cost_accrual_state where po_id=%s),0)::numeric(20,2)',(po,))),
        journal=journal,hpp=hpp)


def journal_count(cur,po):
    b.api.admin(cur)
    return one(cur,'select count(distinct l.journal_entry_id)from erp.journal_lines l where l.po_id=%s',(po,))


def delivery_view(cur,w,delivery=None):
    """The delivery as the Laundry page reads it (custody, returns, attempts), without money and identities."""
    delivery=delivery or w['delivery']
    b.api.admin(cur);number=one(cur,'select delivery_number from erp.laundry_deliveries where id=%s',(delivery,))
    auth.actor(cur)
    r=one(cur,"select public.erp_get_laundry_qc_workspace_v1('LAUNDRY',%s)",(number,));b.api.admin(cur)
    d=next((x for x in r.get('deliveries',[])if x.get('delivery_id')==delivery),None)
    if d is None:return None
    keep=lambda x,keys:{k:x.get(k)for k in keys}
    return dict(keep(d,('status','physical_outstanding_qty_pcs','returned_qty_pcs','returned_unprocessed_qty_pcs','active_claim_qty_pcs')),
        sizes=[keep(s,('qty_sent_pcs','good_returned_qty_pcs','bs_returned_qty_pcs','outstanding_qty_pcs'))for s in d.get('sizes',[])],
        receipts=sorted((keep(x,('event_kind','custody_outcome','attempted_qty_pcs','status','reversible'))for x in d.get('receipts',[])),
                        key=lambda x:json.dumps(x,sort_keys=True)))


def physical(cur,w,r,delivery=None):
    """Every physical fact of one attempt and its PO, without ids, money and document numbers."""
    b.api.admin(cur);attempt=str(r['failed_wash_attempt_id']);delivery=delivery or w['delivery']
    a=cur.execute('select custody_outcome::text,qty_attempted_pcs,return_wip_event_id is not null from erp.laundry_failed_wash_attempts where id=%s',(attempt,)).fetchone()
    sizes=[list(x)for x in cur.execute('select size_id::text,qty_attempted_pcs from erp.laundry_failed_wash_batch_size_lines where attempt_id=%s order by 1,2',(attempt,)).fetchall()]
    line=cur.execute("""select l.qty_good_received,l.qty_bs_laundry,l.qty_stuck,l.qty_missing,l.actual_wash_process_id::text,r.status::text
        from erp.laundry_receipt_lines l join erp.laundry_receipts r on r.id=l.receipt_id
        where l.id=(select receipt_line_id from erp.laundry_failed_wash_attempts where id=%s)""",(attempt,)).fetchone()
    return dict(attempt=list(a),sizes=sizes,line=list(line),
        delivery=list(cur.execute('select status::text,row_version from erp.laundry_deliveries where id=%s',(delivery,)).fetchone()),
        group=one(cur,'select status::text from erp.cutting_groups where id=%s',(w['fx']['group'],)),
        po=list(cur.execute('select status::text,current_stage::text from erp.production_orders where id=%s',(w['po'],)).fetchone()),
        wip=[list(x)for x in cur.execute("""select source_type::text,stage_from::text,stage_to::text,sum(qty_pcs)::text,count(*)
            from erp.wip_stage_events where po_id=%s group by 1,2,3 order by 1,2,3""",(w['po'],)).fetchall()],
        view=delivery_view(cur,w,delivery),
        response={k:r.get(k)for k in('custody_outcome','qty_attempted_pcs','delivery_status','receipt_status','stock_effect')})


def readiness(cur,through):
    b.api.admin(cur)
    return one(cur,'select erp.period_readiness_v1(%s,erp.period_completeness_from_v1())',(through,))


def kinds(r):
    """Close rows by family, code, severity and date (references carry ids that differ between twins)."""
    return Counter((x['family'],x['code'],x['severity'],x['impact_date'])for x in r['blockers']+r['info'])


def mine(r,attempt):
    return [x for x in r['blockers']if x['code']==CODE and (x.get('reference')or{}).get('failed_wash_attempt_id')==str(attempt)]


def close_refused(cur,day,attempt):
    """The close screen's own read names this attempt, and the close command refuses with no effect."""
    r=period.read(cur,day)
    found=[x for x in r['preflight']['blockers']if x['code']==CODE and (x.get('reference')or{}).get('failed_wash_attempt_id')==str(attempt)]
    assert r['preflight']['status']=='BLOCKED'and len(found)==1,r['preflight']
    before=b.boundary.snapshot(cur)
    auth.refused(cur,lambda:period.command(cur,'CLOSE',period.intent(r)),'CLOSE_BLOCKED')
    assert b.boundary.snapshot(cur)==before
    return found[0]['reason']


def preflight_codes(cur,day):
    r=period.read(cur,day)
    return [x['code']for x in r['preflight']['blockers']]


def normal(value):
    """Responses and reads of two runs on the same state: identities, generated numbers and read times removed."""
    def walk(v,key=''):
        if isinstance(v,dict):return {k:walk(x,k)for k,x in v.items()if not(k.endswith('number')or k in('as_of','request_id','client_request_id','replayed'))}
        if isinstance(v,list):return [walk(x)for x in v]
        if isinstance(v,str):
            v=re.sub(r'[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}','U',v)
            return re.sub(r'[0-9A-Fa-f]{32}','H',v)
        return v
    return walk(json.loads(json.dumps(value,default=str)))


def cases(cur,today):
    def recorded():
        w=fixture(cur,today,'OW08B-REC');m0=money(cur,w['po'])
        def twin():
            known_rate(cur,w);r=failed(cur,w,12,unknown=False)
            return physical(cur,w,r),money(cur,w['po']),r
        known_physical,known_money,known=savepoint(cur,twin,'ow08b_twin')
        r=failed(cur,w,12);attempt=str(r['failed_wash_attempt_id'])
        assert r['cost_status']=='PRICE_UNKNOWN'and r['rate_per_pcs']is None and r['actual_cost']is None,r
        assert r['hpp_effect']=='FAILED_WASH_COST_UNKNOWN_HPP_NOT_FINAL'and known['cost_status']=='ESTIMATED_UNBILLED',(r,known)
        assert D(str(known['actual_cost']))==30,known
        line=attempt_line(cur,attempt)
        assert line==(None,None,'PENDING'),line
        reg=cur.execute("""select p.price_status,p.recorded_reason,p.recorded_by=a.created_by,p.po_id::text,p.rate_per_pcs,p.priced_at
            from cp7_laundry_unknown_wash.prices_v1 p join erp.laundry_failed_wash_attempts a on a.id=p.attempt_id where p.attempt_id=%s""",(attempt,)).fetchone()
        assert reg==('UNKNOWN',REASON,True,w['po'],None,None),reg
        unknown_physical=physical(cur,w,r)
        assert unknown_physical==known_physical,(unknown_physical,known_physical)
        m1=money(cur,w['po'])
        assert m1==m0 and D(known_money['desired'])-D(m0['desired'])==30,(m0,m1,known_money)
        # HPP of the PO is not final: goods finished after the attempt.
        rec=bd.receive(cur,w['delivery'],w['fx'],10,13);product,lot=bd.finish_goods(cur,w['fx'],rec['receipt_id'],10,14);b.api.admin(cur)
        hpp=money(cur,w['po'])['hpp']
        lot_unknown=one(cur,'select erp.bd_lot_laundry_unknown_v1(%s)',(lot,))
        lot_unknown_original=original(cur,lambda:one(cur,'select erp.bd_lot_laundry_unknown_v1(%s)',(lot,)),(native_delta.LOT,))
        goods=[g for g in bd.pending_cost(cur,w['vendor'])['goods']if g['lot_id']==lot]
        goods_original=original(cur,lambda:[g for g in bd.pending_cost(cur,w['vendor'])['goods']if g['lot_id']==lot])
        listed=[x for x in bd.bd_ws(cur,dict(vendor_id=w['vendor']))['failed_wash_prices']if x['attempt_id']==attempt]
        assert [s for _,_,s in hpp]==['ESTIMATED']and lot_unknown is True and lot_unknown_original is False,(hpp,lot_unknown,lot_unknown_original)
        assert len(goods)==1 and goods[0]['hpp_state']=='NOT_FINAL'and goods_original==[],(goods,goods_original)
        assert len(listed)==1 and listed[0]['price_status']=='UNKNOWN'and listed[0]['rate']is None and listed[0]['amount']is None,listed
        return dict(status='PASS',attempt=attempt,response_cost_status=r['cost_status'],stored_rate_cost_status=[None,None,'PENDING'],
            known_twin_cost=str(known['actual_cost']),physical_equal_to_known_twin=True,money_unchanged_by_unknown=m1,
            known_twin_desired_accrual=known_money['desired'],hpp_after_goods=hpp,lot_unknown_patched=lot_unknown,
            lot_unknown_original_engine=lot_unknown_original,hpp_not_final_listed=goods[0],workspace_row=listed[0])

    def without_flag():
        w=fixture(cur,today,'OW08B-NOFLAG')
        new=auth.refused(cur,lambda:failed(cur,w,12,unknown=False),OLD_RATE_REFUSAL)
        old=original(cur,lambda:auth.refused(cur,lambda:failed(cur,w,12,unknown=False),OLD_RATE_REFUSAL))
        assert new==old and 'found 0'in new,(new,old)
        key_original=original(cur,lambda:auth.refused(cur,lambda:failed(cur,w,12),'unexpected key price_status'))
        other_value=auth.refused(cur,lambda:failed(cur,w,12,extra=dict(price_status='KNOWN')),'CP7_FAILED_WASH_PRICE_STATUS')
        not_text=auth.refused(cur,lambda:failed(cur,w,12,extra=dict(price_status=0)),'CP7_FAILED_WASH_PRICE_STATUS')
        def rate_exists():
            known_rate(cur,w)
            return auth.refused(cur,lambda:failed(cur,w,12),'CP7_FAILED_WASH_RATE_KNOWN')
        known=savepoint(cur,rate_exists,'ow08b_rate')
        b.api.admin(cur)
        nothing=one(cur,'select count(*)from erp.laundry_failed_wash_attempts where delivery_id=%s',(w['delivery'],))
        assert nothing==0 and one(cur,'select count(*)from cp7_laundry_unknown_wash.prices_v1 where po_id=%s',(w['po'],))==0
        return dict(status='PASS',without_flag=new,original_engine_same_message=old,original_engine_refuses_new_key=key_original,
            other_value_refused=other_value,non_text_refused=not_text,known_rate_not_recorded_as_unknown=known,nothing_written=True)

    def two_rates():
        w=fixture(cur,today,'OW08B-TWO');b.api.admin(cur)
        insert="insert into erp.laundry_vendor_rate_versions(vendor_id,wash_process_id,rate_per_pcs,effective_from,notes)values(%s,%s,%s,%s,%s)"
        start=chain.production.at(w['day'],0)
        cur.execute(insert,(w['vendor'],w['failed'],3,start,'OW08b first rate'))
        guard=auth.refused(cur,lambda:cur.execute(insert,(w['vendor'],w['failed'],4,start,'OW08b overlapping rate')),'Overlapping laundry vendor rate')
        def ambiguous():
            b.api.admin(cur)
            # Explicit privileged corruption: the Native overlap trigger is bypassed for one insert, then restored.
            cur.execute('alter table erp.laundry_vendor_rate_versions disable trigger user')
            cur.execute(insert,(w['vendor'],w['failed'],4,start,'OW08b overlapping rate'))
            cur.execute('alter table erp.laundry_vendor_rate_versions enable trigger user')
            count=one(cur,'select count(*)from erp.laundry_vendor_rate_versions where vendor_id=%s and wash_process_id=%s',(w['vendor'],w['failed']))
            flagged=auth.refused(cur,lambda:failed(cur,w,12),OLD_RATE_REFUSAL)
            plain=auth.refused(cur,lambda:failed(cur,w,12,unknown=False),OLD_RATE_REFUSAL)
            old=original(cur,lambda:auth.refused(cur,lambda:failed(cur,w,12,unknown=False),OLD_RATE_REFUSAL))
            return count,flagged,plain,old
        count,flagged,plain,old=savepoint(cur,ambiguous,'ow08b_corrupt')
        assert count==2 and 'found 2'in flagged and flagged==plain==old,(count,flagged,plain,old)
        assert one(cur,'select count(*)from erp.laundry_failed_wash_attempts where delivery_id=%s',(w['delivery'],))==0
        return dict(status='PASS',overlap_guard=guard,corruption='USER_TRIGGERS_DISABLED_FOR_ONE_INSERT_ROLLED_BACK',
            with_unknown_flag=flagged,without_flag=plain,original_engine=old,nothing_written=True)

    def close_and_twin():
        w=fixture(cur,today,'OW08B-CLOSE');day=w['day']
        def path(unknown):
            def run():
                if not unknown:known_rate(cur,w)
                r=failed(cur,w,12,unknown=unknown)
                rec=bd.receive(cur,w['delivery'],w['fx'],10,13);bd.finish_goods(cur,w['fx'],rec['receipt_id'],10,14);b.api.admin(cur)
                return r
            return run
        def twin():
            path(False)()
            return money(cur,w['po']),kinds(readiness(cur,day))
        known_money,known_kinds=savepoint(cur,twin,'ow08b_twin')
        r=path(True)();attempt=str(r['failed_wash_attempt_id'])
        pending=readiness(cur,day);earlier=readiness(cur,day-timedelta(days=1))
        row=mine(pending,attempt)
        assert len(row)==1 and row[0]['severity']=='POLICY'and row[0]['impact_date']==str(day)and row[0]['family']=='LAUNDRY',row
        assert row[0]['reference']['qty_attempted_pcs']=='10'and 'Harga & tagihan'in row[0]['reason'],row
        extra=kinds(pending)-known_kinds;gone=known_kinds-kinds(pending)
        assert sorted(extra)==[('LAUNDRY',CODE,'POLICY',str(day))]and not gone,(extra,gone)
        assert not mine(earlier,attempt),earlier['blockers']
        original_rows=original(cur,lambda:mine(readiness(cur,day),attempt))
        assert original_rows==[],original_rows
        shown=close_refused(cur,day,attempt)
        not_final=money(cur,w['po'])
        price(cur,attempt,'3.00')
        priced=money(cur,w['po']);after=readiness(cur,day)
        assert priced==known_money,(priced,known_money)
        assert not mine(after,attempt)and kinds(after)==known_kinds,(kinds(after),known_kinds)
        assert CODE not in preflight_codes(cur,day)
        return dict(status='PASS',attempt=attempt,close_row=row[0],original_engine_rows=original_rows,screen_reason=shown,
            close_refused_without_effect=True,only_added_close_kind=sorted(extra),not_before_attempt_date=True,
            money_while_unknown=not_final,money_after_price=priced,money_of_known_twin=known_money,equal_to_known_twin=True,
            close_kinds_after_price_equal_to_known_twin=True)

    def return_unprocessed():
        w=fixture(cur,today,'OW08B-RU');fx=w['fx']
        def redispatch_finish_invoice():
            second=str(bd.plain_delivery(cur,fx,10,13));b.api.admin(cur)
            rec=bd.receive(cur,second,fx,10,14);bd.finish_goods(cur,fx,rec['receipt_id'],10,15);b.api.admin(cur)
            bd.invoice_policies(cur);bd.invoice(cur,fx,[dict(line=bd.receipt_line(cur,rec['receipt_id']),qty=10,amount='20.00')],'20.00')
            b.api.admin(cur);return second
        def twin():
            known_rate(cur,w);r=failed(cur,w,12,outcome='RETURN_UNPROCESSED',unknown=False)
            p=physical(cur,w,r);redispatch_finish_invoice()
            return p,money(cur,w['po'])
        known_physical,known_money=savepoint(cur,twin,'ow08b_twin')
        r=failed(cur,w,12,outcome='RETURN_UNPROCESSED');attempt=str(r['failed_wash_attempt_id'])
        unknown_physical=physical(cur,w,r)
        assert unknown_physical==known_physical,(unknown_physical,known_physical)
        assert unknown_physical['delivery'][0]=='REVERSED'and unknown_physical['attempt'][2]is True,unknown_physical
        assert attempt_line(cur,attempt)==(None,None,'PENDING')
        redispatch_finish_invoice()
        states=[s for _,_,s in money(cur,w['po'])['hpp']]
        def rebuilt_by_original():
            b.api.admin(cur);cur.execute("select erp.rebuild_po_hpp(%s,'OW08b original engine')",(w['po'],))
            return [s for _,_,s in money(cur,w['po'])['hpp']]
        original_states=original(cur,rebuilt_by_original,(native_delta.HPP,))
        assert states==['ESTIMATED']and original_states!=['ESTIMATED'],(states,original_states)
        row=mine(readiness(cur,w['day']),attempt);assert len(row)==1 and row[0]['reference']['custody_outcome']=='RETURN_UNPROCESSED',row
        price(cur,attempt,'3.00')
        priced=money(cur,w['po'])
        assert priced==known_money,(priced,known_money)
        assert not mine(readiness(cur,w['day']),attempt)
        return dict(status='PASS',attempt=attempt,physical_equal_to_known_twin=unknown_physical,hpp_state_patched=states,
            hpp_state_original_engine=original_states,money_after_price=priced,equal_to_known_twin=True)

    def set_once():
        w=fixture(cur,today,'OW08B-ONCE')
        r=failed(cur,w,12,qty=4);attempt=str(r['failed_wash_attempt_id'])
        gudang=b.user(cur,'GUDANG')
        non_owner=auth.refused(cur,lambda:price(cur,attempt,subject=gudang),'OWNER or ADMIN access required')
        zero=auth.refused(cur,lambda:price(cur,attempt,'0.00'),'BD_AMOUNT_INVALID')
        free_not_zero=auth.refused(cur,lambda:price(cur,attempt,'1.00','FREE'),'BD_FREE_REQUIRES_ZERO')
        unknown=auth.refused(cur,lambda:price(cur,attempt,'3.00','UNKNOWN'),'BD_RATE_STATUS')
        key=uuid.uuid4()
        first=price(cur,attempt,'3.00',key=key)
        replay=price(cur,attempt,'3.00',key=key)
        twice=auth.refused(cur,lambda:price(cur,attempt,'4.00'),'CP7_FAILED_WASH_PRICE_ALREADY_SET')
        reuse=auth.refused(cur,lambda:price(cur,attempt,'4.00',key=key),'BD_REQUEST_REUSED')
        assert first['action']=='SET_FAILED_WASH_PRICE'and first['actual_cost']=='12.00'and first['rate_per_pcs']=='3.00'and first['economic_date']==str(w['day']),first
        assert replay.get('replayed')is True and {k:v for k,v in replay.items()if k!='replayed'}==first,replay
        b.api.admin(cur)
        stored=cur.execute("""select p.price_status,p.rate_per_pcs::text,p.price_reason,p.priced_by=a.created_by,p.priced_at is not null,p.price_request_id::text
            from cp7_laundry_unknown_wash.prices_v1 p join erp.laundry_failed_wash_attempts a on a.id=p.attempt_id where p.attempt_id=%s""",(attempt,)).fetchone()
        assert stored==('KNOWN','3.00','OW08b nota vendor datang',True,True,str(key)),stored
        assert attempt_line(cur,attempt)==(D('3.00'),D('12.00'),'ESTIMATED')
        audit=one(cur,"select count(*)from erp.audit_logs where entity_type='laundry_failed_wash_attempts' and entity_id=%s and action='SET_PRICE'",(attempt,))
        changed=auth.refused(cur,lambda:cur.execute("update cp7_laundry_unknown_wash.prices_v1 set price_reason='ubah' where attempt_id=%s",(attempt,)),'CP7_FAILED_WASH_PRICE_HISTORY_IMMUTABLE')
        deleted=auth.refused(cur,lambda:cur.execute('delete from cp7_laundry_unknown_wash.prices_v1 where attempt_id=%s',(attempt,)),'CP7_FAILED_WASH_PRICE_HISTORY_IMMUTABLE')
        # FREE / WAIVED: an explicit known zero with its reason, never an assumed zero.
        r2=failed(cur,w,13,qty=2);second=str(r2['failed_wash_attempt_id']);m=money(cur,w['po'])
        free=price(cur,second,'0.00','FREE',reason='Vendor tidak menagih attempt ini')
        assert free['actual_cost']=='0.00'and attempt_line(cur,second)==(D('0.00'),D('0.00'),'ESTIMATED')and money(cur,w['po'])==m,free
        assert audit==1 and not mine(readiness(cur,w['day']),attempt)and not mine(readiness(cur,w['day']),second)
        return dict(status='PASS',non_owner_refused=non_owner,zero_known_refused=zero,free_not_zero_refused=free_not_zero,
            unknown_status_refused=unknown,first=first,same_request_replayed=True,second_price_refused=twice,request_reuse_refused=reuse,
            reason_actor_time_kept=list(stored),history_update_refused=changed,history_delete_refused=deleted,free_zero_with_reason=free)

    def reverse_unknown():
        w=fixture(cur,today,'OW08B-REV');m0=money(cur,w['po']);j0=journal_count(cur,w['po'])
        r=failed(cur,w,12);attempt=str(r['failed_wash_attempt_id'])
        assert mine(readiness(cur,w['day']),attempt)
        version=one(cur,'select row_version from erp.laundry_receipts where id=%s',(r['receipt_id'],))
        done=chain.laundry_action(cur,'REVERSE_RECEIPT',dict(receipt_id=str(r['receipt_id']),reason='OW08b cuci gagal salah catat'),version);b.api.admin(cur)
        m1=money(cur,w['po']);j1=journal_count(cur,w['po'])
        assert done['status']=='REVERSED'and m1==m0 and j1==j0,(done,m0,m1,j0,j1)
        assert not mine(readiness(cur,w['day']),attempt)
        kept=one(cur,'select price_status from cp7_laundry_unknown_wash.prices_v1 where attempt_id=%s',(attempt,))
        listed=[x for x in bd.bd_ws(cur,dict(vendor_id=w['vendor']))['failed_wash_prices']if x['attempt_id']==attempt]
        refused=auth.refused(cur,lambda:price(cur,attempt),'CP7_FAILED_WASH_ATTEMPT_REVERSED')
        assert kept=='UNKNOWN'and len(listed)==1 and listed[0]['attempt_status']=='REVERSED',(kept,listed)
        return dict(status='PASS',attempt=attempt,reversal=normal(done),money_before=m0,money_after=m1,journals_before=j0,journals_after=j1,
            close_row_gone=True,history_kept_unknown=True,price_after_reversal_refused=refused)

    def sale_guard():
        w=fixture(cur,today,'OW08B-SALE');fx=w['fx']
        r=failed(cur,w,12);attempt=str(r['failed_wash_attempt_id'])
        rec=bd.receive(cur,w['delivery'],fx,10,13);product,lot=bd.finish_goods(cur,fx,rec['receipt_id'],10,14);b.api.admin(cur)
        state=one(cur,"select status from erp.bd_policy_settings_v1 where policy_key='LAU_DEC04'")
        if state=='SET':bd.policy(cur,'LAU_DEC04',operation='CLEAR')
        unset=auth.refused(cur,lambda:bd.sell(cur,fx,product,2,15),'BD_SALE_LAUNDRY_PRICE_UNKNOWN')
        bd.policy(cur,'LAU_DEC04',dict(sale_with_unknown_laundry='REFUSE'))
        refuse=auth.refused(cur,lambda:bd.sell(cur,fx,product,2,15),'BD_SALE_LAUNDRY_PRICE_UNKNOWN')
        original_allows=original(cur,lambda:bool(bd.sell(cur,fx,product,2,15)),(native_delta.LOT,))
        posted=lambda:one(cur,"select count(*)from erp.sales_items i join erp.sales_headers h on h.id=i.sale_id where i.product_id=%s and h.status='POSTED'",(product,))
        b.api.admin(cur);assert posted()==0
        bd.policy(cur,'LAU_DEC04',dict(sale_with_unknown_laundry='ALLOW_PENDING'))
        lv0=bd.lot_value(cur,lot);sale=bd.sell(cur,fx,product,2,15);b.api.admin(cur)
        recorded=cur.execute('select qty_pcs,policy_version from erp.bd_pending_price_sales_v1 where sale_id=%s',(sale,)).fetchall()
        view1=bd.pending_cost(cur,w['vendor'])
        lot1=[x for x in view1['goods']if x['lot_id']==lot];sale1=[x for x in view1['sales']if x['sale_id']==sale]
        assert len(recorded)==1 and recorded[0][0]==2 and len(lot1)==1 and lot1[0]['hpp_state']=='NOT_FINAL'and sale1[0]['hpp_state']=='NOT_FINAL',(recorded,lot1,sale1)
        keys=('FG_INVENTORY','COGS');g1={k:b.gl(cur,k)for k in keys}
        bd.policy(cur,'LAU_DEC04',dict(sale_with_unknown_laundry='REFUSE'))
        price(cur,attempt,'3.00')
        lv1=bd.lot_value(cur,lot);g2={k:b.gl(cur,k)for k in keys};delta={k:g2[k]-g1[k]for k in keys}
        view2=bd.pending_cost(cur,w['vendor'])
        sale2=[x for x in view2['sales']if x['sale_id']==sale]
        assert lv1-lv0==30 and delta['COGS']==6 and delta['FG_INVENTORY']==24,(lv0,lv1,delta)
        assert not [x for x in view2['goods']if x['lot_id']==lot]and sale2[0]['hpp_state']=='RECOSTED',(view2,sale2)
        bd.sell(cur,fx,product,2,16);b.api.admin(cur)
        assert posted()==2
        return dict(status='PASS',attempt=attempt,unset_refused=unset,refuse_refused=refuse,original_engine_sold_under_refuse=original_allows,
            allow_pending_recorded=[list(x)for x in recorded],lot_value_before=str(lv0),lot_value_after_price=str(lv1),
            gl_delta={k:str(v)for k,v in delta.items()},sale_recosted=True,sold_after_price_under_refuse=True)

    def invoice():
        w=fixture(cur,today,'OW08B-INV');fx=w['fx']
        r=failed(cur,w,12);attempt=str(r['failed_wash_attempt_id'])
        line=str(one(cur,'select receipt_line_id from erp.laundry_failed_wash_attempts where id=%s',(attempt,)))
        bd.invoice_policies(cur)
        bill=lambda:bd.invoice(cur,fx,[dict(line=line,category='FAILED_ATTEMPT',qty=10,amount='30.00')],'30.00')
        refused=auth.refused(cur,bill,'CP7_FAILED_WASH_PRICE_UNKNOWN')
        def original_engine():
            draft,_=bd.invoice(cur,fx,[dict(line=line,category='FAILED_ATTEMPT',qty=10,amount='30.00')],'30.00',post=False)
            return auth.refused(cur,lambda:bd.post_draft(cur,draft),'BD_INVOICE_SOURCE_NOT_ESTIMATED')
        old=original(cur,original_engine)
        billable=lambda:[x for x in(bd.bd_ws(cur,dict(vendor_id=w['vendor']))['billable_receipts']or[])if x['receipt_line_id']==line]
        assert billable()==[]
        price(cur,attempt,'3.00')
        listed=billable()
        assert len(listed)==1 and listed[0]['failed_attempt']is True and listed[0]['estimate']=='30.00',listed
        ap0=D(bd.ap(cur,w['vendor']));accrual0=bd.accrual(cur,w['po'])
        _,posted=bill()
        ap1=D(bd.ap(cur,w['vendor']));accrual1=bd.accrual(cur,w['po'])
        l0=posted['lines'][0]
        assert posted['status']=='POSTED'and ap1-ap0==30 and (l0['released_estimate'],l0['variance'])==('30.00','0.00'),(posted,ap0,ap1)
        assert D(accrual0['booked'])-D(accrual1['booked'])==30,(accrual0,accrual1)
        return dict(status='PASS',attempt=attempt,draft_refused=refused,original_engine_post_refused=old,not_billable_before_price=True,
            billable_after_price=listed[0],invoice_line=l0,payable_delta=str(ap1-ap0),accrual=[accrual0,accrual1])

    def unchanged():
        w=fixture(cur,today,'OW08B-SAME');fx=w['fx'];known_rate(cur,w)
        def digest():
            b.api.admin(cur)
            return dict(money=money(cur,w['po']),
                deliveries=[list(x)for x in cur.execute('select status::text,row_version from erp.laundry_deliveries where po_id=%s order by physical_at,status',(w['po'],)).fetchall()],
                lines=[list(map(str,x))for x in cur.execute("""select l.qty_good_received,l.qty_bs_laundry,l.actual_rate_snapshot,l.actual_cost,l.actual_cost_status,r.status
                    from erp.laundry_receipt_lines l join erp.laundry_receipts r on r.id=l.receipt_id join erp.laundry_deliveries d on d.id=r.delivery_id
                    where d.po_id=%s order by r.physical_at,l.qty_good_received""",(w['po'],)).fetchall()],
                attempts=[list(x)for x in cur.execute('select a.custody_outcome::text,a.qty_attempted_pcs from erp.laundry_failed_wash_attempts a join erp.laundry_deliveries d on d.id=a.delivery_id where d.po_id=%s order by 2',(w['po'],)).fetchall()],
                group=one(cur,'select status::text from erp.cutting_groups where id=%s',(fx['group'],)),
                po=list(cur.execute('select status::text,current_stage::text from erp.production_orders where id=%s',(w['po'],)).fetchone()),
                registered=one(cur,'select count(*)from cp7_laundry_unknown_wash.prices_v1 where po_id=%s',(w['po'],)))
        def commands():
            out={}
            # Refusals first, while the delivery is still SENT with no later history (their checks come after the time check).
            out['refused_no_rate']=auth.refused(cur,lambda:failed(cur,dict(w,failed=fresh),12,unknown=False),OLD_RATE_REFUSAL)
            out['refused_extra_key']=auth.refused(cur,lambda:failed(cur,w,12,unknown=False,extra=dict(note='x')),'unexpected key note')
            r1=failed(cur,w,12,qty=4,unknown=False);out['POST_FAILED_WASH']=r1
            r2=bd.receive(cur,w['delivery'],fx,10,13);out['POST_RECEIPT']=r2
            product,lot=bd.finish_goods(cur,fx,r2['receipt_id'],10,14);b.api.admin(cur)
            out['POST_FINAL_SKU_lot_unknown']=one(cur,'select erp.bd_lot_laundry_unknown_v1(%s)',(lot,))
            version=one(cur,'select row_version from erp.laundry_receipts where id=%s',(r1['receipt_id'],))
            out['REVERSE_RECEIPT']=chain.laundry_action(cur,'REVERSE_RECEIPT',dict(receipt_id=str(r1['receipt_id']),reason='OW08b sama dengan mesin lama'),version)
            b.api.admin(cur)
            draft,_=bd.invoice(cur,fx,[dict(line=bd.receipt_line(cur,r2['receipt_id']),qty=10,amount='20.00')],'20.00',post=False)
            out['SAVE_INVOICE_DRAFT']=draft
            ws=bd.bd_ws(cur,dict(vendor_id=w['vendor']));ws.pop('failed_wash_prices',None);ws.pop('pagination',None)
            out['workspace']=ws;out['pending_cost']=bd.pending_cost(cur,w['vendor'])
            out['close_kinds']=sorted(map(list,kinds(readiness(cur,w['day'])).items()),key=json.dumps)
            out['state']=digest()
            return normal(out)
        b.api.admin(cur);fresh=str(uuid.uuid4())
        cur.execute('insert into erp.wash_processes(id,process_code,process_name,is_active)values(%s,%s,%s,true)',(fresh,'OW08B-'+uuid.uuid4().hex[:12],'OW08b tanpa tarif'))
        new=savepoint(cur,commands,'ow08b_new');old=original(cur,commands)
        assert new==old,(new,old)
        second=fixture(cur,today,'OW08B-SAME-RD')
        def reverse_delivery():
            version=chain.base.delivery_version(cur,second['delivery'])
            r=chain.laundry_action(cur,'REVERSE_DELIVERY',dict(delivery_id=second['delivery'],reason='OW08b kirim dibatalkan'),version);b.api.admin(cur)
            return normal(dict(r=r,money=money(cur,second['po']),delivery=one(cur,'select status::text from erp.laundry_deliveries where id=%s',(second['delivery'],))))
        rd_new=savepoint(cur,reverse_delivery,'ow08b_new');rd_old=original(cur,reverse_delivery)
        assert rd_new==rd_old,(rd_new,rd_old)
        return dict(status='PASS',compared=sorted(k for k in new if k!='state')+['REVERSE_DELIVERY'],state_equal=True,
            known_attempt_cost=new['POST_FAILED_WASH'].get('actual_cost'),refusals=[new['refused_no_rate'],new['refused_extra_key']])

    def detector():
        b.api.admin(cur)
        healthy=one(cur,"select count(*)from erp.period_blockers_v1(%s,null)where code=%s",(today,MISMATCH))
        w=fixture(cur,today,'OW08B-DET')
        r=failed(cur,w,12);attempt=str(r['failed_wash_attempt_id']);b.api.admin(cur)
        count=lambda:one(cur,"select count(*)from erp.period_blockers_v1(%s,null)where code=%s",(w['day'],MISMATCH))
        zero=count()
        def corrupt():
            b.api.admin(cur)
            cur.execute('alter table erp.laundry_receipt_lines disable trigger user')
            cur.execute("""update erp.laundry_receipt_lines set actual_rate_snapshot=3,actual_cost=30,actual_cost_status='ESTIMATED'
                where id=(select receipt_line_id from erp.laundry_failed_wash_attempts where id=%s)""",(attempt,))
            cur.execute('alter table erp.laundry_receipt_lines enable trigger user')
            return cur.execute("select severity,scope,reference from erp.period_blockers_v1(%s,null)where code=%s",(w['day'],MISMATCH)).fetchall()
        rows=savepoint(cur,corrupt,'ow08b_corrupt')
        back=count()
        assert healthy==0 and zero==0 and back==0,(healthy,zero,back)
        assert len(rows)==1 and rows[0][0]=='CRITICAL'and rows[0][1]=='CURRENT_STATE'and rows[0][2]['attempt_ids']==[attempt],rows
        line_guard=auth.refused(cur,lambda:cur.execute("""update erp.laundry_receipt_lines set actual_rate_snapshot=3,actual_cost_status='ESTIMATED'
            where id=(select receipt_line_id from erp.laundry_failed_wash_attempts where id=%s)""",(attempt,)),'CP7_FAILED_WASH_PRICE_UNKNOWN')
        def call(sql):
            auth.actor(cur);return cur.execute(sql).fetchall()
        private=[auth.refused(cur,lambda sql=sql:call(sql),'permission denied')for sql in(
            'select * from cp7_laundry_unknown_wash.unknown_v1()','select * from cp7_laundry_unknown_wash.prices_v1',
            "select cp7_laundry_unknown_wash.set_price_v1('{}'::jsonb,gen_random_uuid())")]
        b.api.admin(cur)
        return dict(status='PASS',healthy_book_detector=healthy,detector_zero_one_zero=[zero,len(rows),back],corruption='USER_TRIGGERS_DISABLED_ROLLED_BACK',
            detector_row=rows[0][2],line_leaves_pending_only_through_price=line_guard,authenticated_refused=private)

    operations=(recorded,without_flag,two_rates,close_and_twin,return_unprocessed,set_once,reverse_unknown,sale_guard,invoice,unchanged,detector)
    assert len(operations)==len(IDS)
    return list(zip(IDS,operations))
