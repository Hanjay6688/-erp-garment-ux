"""AUDITOR SCENARIO — FG UNSOURCED (AX) + ACCESSORY RETAIL 7 PCS (AO/AQ) (independent auditor, blind phase 1).
ACC oracle = contract text: ACC-DEC02 (M:1066-1071: retail price typed manually, physical 7 stays exactly 7, no new rounding,
old posted amounts unchanged) and AQ checkpoint (M:94: draft 5 -> 7 at retail 3.25 gives 22.75, stock 300->293, master
36.00 per dozen unchanged, linked cancellation restores 300 and every account, posted detail stays 7 PCS; retry with the
same UUID posts once).
FG oracle = contract invariants only (the feature's policy itself is not in the contract: DECISION_MISSING): every value
entering FG has an equal credit leg (conservation), no silent Rp0 (M:6098 'jangan menebak', A04 'unknown tidak menjadi nol'),
reversal restores stock and ledger exactly, replay posts once, closed period keeps the physical economic date and posts the
GL date in the open period (M:1061), exact refusal texts from the AX SQL, PO lots untouched (M:5056-5065 'tidak mengubah
kontrak produksi normal'). Every expected number is computed by the auditor from the ledger, not taken from writer asserts."""
from datetime import timedelta
from decimal import Decimal,ROUND_HALF_UP
import json,traceback,uuid
import cp6_aw_probe as awp
import cp6_ax_probe as axp
import cp6_accessory_issue_trial as acc
api,boundary,chain,r1=awp.api,awp.boundary,awp.chain,awp.r1
D=lambda v:Decimal(str(v))

def ledger(cur):
    api.admin(cur)
    return {r[0]:str(r[1]) for r in cur.execute("""select a.mapping_key,sum(l.debit-l.credit) from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id
        join erp.accounting_account_mappings a on a.account_id=l.account_id where j.status in('POSTED','REVERSED') group by 1 order by 1""").fetchall()}

def lines(cur,journal):
    api.admin(cur)
    return [dict(key=r[0],debit=str(r[1]),credit=str(r[2]),product=str(r[3]) if r[3] else None) for r in cur.execute(
        """select a.mapping_key,l.debit,l.credit,l.product_id from erp.journal_lines l join erp.accounting_account_mappings a on a.account_id=l.account_id
           where l.journal_entry_id=%s order by l.debit desc,a.mapping_key""",(journal,)).fetchall()]

def my_average(cur,product,at):
    """Auditor's own stock-on-hand weighted average at instant `at` over the SKU's lots (all origins, all movements)."""
    api.admin(cur)
    rows=cur.execute("""select fl.id,hv.hpp_per_pcs,coalesce((select sum(m.qty_signed) from erp.fg_stock_movements m where m.lot_id=fl.id and m.physical_at<=%s and m.movement_type<>'SALE_RESERVE'
        and (m.reversal_of_id is null or (select x.movement_type from erp.fg_stock_movements x where x.id=m.reversal_of_id)<>'SALE_RESERVE')),0)
        from erp.fg_lots fl join erp.hpp_versions hv on hv.lot_id=fl.id and hv.is_current where fl.product_id=%s and fl.produced_at<=%s""",(at,product,at)).fetchall()
    qty=sum(D(q) for _,_,q in rows if q>0);value=sum(D(q)*D(h) for _,h,q in rows if q>0)
    return (value/qty).quantize(D('0.01'),ROUND_HALF_UP) if qty else None,[(str(i),str(h),str(q)) for i,h,q in rows]

def fg_found(cur,today):
    f=axp.stocked_product(cur,today);product=str(f['product']);at=r1.now(cur)-timedelta(minutes=10)
    avg,lots=my_average(cur,product,at)
    before=ledger(cur);po_lots_before=cur.execute("select count(*),coalesce(sum(hv.total_cost),0) from erp.fg_lots fl join erp.hpp_versions hv on hv.lot_id=fl.id and hv.is_current where fl.product_id=%s and fl.lot_origin='PRODUCTION'",(product,)).fetchone()
    view=axp.preview(cur,product,at)
    r=axp.post(cur,dict(source_kind='FOUND_AT_OPNAME',product_id=product,location_id=chain.base.LOCATION,qty_pcs=3,physical_at=at.isoformat(),reason='auditor found at opname'))
    after=ledger(cur);po_lots_after=cur.execute("select count(*),coalesce(sum(hv.total_cost),0) from erp.fg_lots fl join erp.hpp_versions hv on hv.lot_id=fl.id and hv.is_current where fl.product_id=%s and fl.lot_origin='PRODUCTION'",(product,)).fetchone()
    jl=lines(cur,r['journal_entry_id']);unit=D(r['unit_value']);total=(unit*3).quantize(D('0.01'))
    fg_move=D(after.get('FG_INVENTORY','0'))-D(before.get('FG_INVENTORY','0'))
    credits=[l for l in jl if D(l['credit'])>0];debits=[l for l in jl if D(l['debit'])>0]
    checks=dict(unit_value_equals_auditor_average=avg is not None and unit==avg,
                preview_equals_posted_unit=D(str(view.get('unit_value',view.get('unit',0))))==unit if isinstance(view,dict) and ('unit_value' in view or 'unit' in view) else None,
                fg_inventory_moves_by_3x_unit=fg_move==total,
                journal_balanced_debit_fg_equals_credit=sum(D(l['debit']) for l in debits)==sum(D(l['credit']) for l in credits)==total and debits and debits[0]['key']=='FG_INVENTORY',
                lot_not_a_production_lot=cur.execute("select lot_origin<>'PRODUCTION' and po_id is null from erp.fg_lots where id=%s",(r['lot_id'],)).fetchone()[0],
                production_lots_untouched=po_lots_before==po_lots_after,
                not_zero_without_reason=unit>0)
    checks={k:v for k,v in checks.items() if v is not None}
    return dict(status='PASS' if all(checks.values()) else 'COUNTEREXAMPLE',checks=checks,unit=str(unit),auditor_average=str(avg),lots_seen=lots,journal=jl,preview=view,credit_account=[l['key'] for l in credits],
                expected='conservation Dr FG = Cr <account> = 3 x unit; unit = auditor stock-on-hand average; separate non-PO lot; PO lots untouched; contract basis for the feature itself: DECISION_MISSING')

def fg_replay_and_reverse(cur,today):
    f=axp.stocked_product(cur,today);product=str(f['product']);at=r1.now(cur)-timedelta(minutes=10)
    before=ledger(cur);stock_before=axp.counts(cur)
    key=uuid.uuid4();payload=dict(source_kind='FOUND_AT_OPNAME',product_id=product,location_id=chain.base.LOCATION,qty_pcs=2,physical_at=at.isoformat(),reason='auditor replay')
    first=axp.post(cur,payload,key);again=axp.post(cur,payload,key)
    lots=cur.execute("select count(*) from erp.fg_lots where product_id=%s and lot_origin<>'PRODUCTION'",(product,)).fetchone()[0]
    _,changed=axp.attempt_post(cur,dict(payload,qty_pcs=4),key)
    back=axp.reverse(cur,first['receipt_id'],'auditor reverse')
    after=ledger(cur);stock_after=axp.counts(cur)
    _,again_rev=r1.peer.attempt(cur,lambda:axp.reverse(cur,first['receipt_id'],'auditor reverse twice'))
    checks=dict(replay_same_uuid_identical=first==again,one_lot_only=lots==1,changed_payload_same_uuid_refused=changed is not None,
                reversal_restores_ledger_exactly=before==after,reversal_restores_counts=stock_before==stock_after,second_reversal_refused=again_rev is not None)
    return dict(status='PASS' if all(checks.values()) else 'COUNTEREXAMPLE',checks=checks,changed_msg=(changed or {}).get('message'),second_reversal_msg=(again_rev or {}).get('message'),
                expected='same UUID posts once; different payload with same UUID refused; reversal restores ledger and counts exactly; second reversal refused')

def fg_refusals(cur,today):
    f=axp.stocked_product(cur,today);product=str(f['product']);at=r1.now(cur)-timedelta(minutes=10)
    base=dict(source_kind='FOUND_AT_OPNAME',product_id=product,location_id=chain.base.LOCATION,qty_pcs=1,physical_at=at.isoformat(),reason='auditor refusal')
    expect={'qty_zero':(dict(qty_pcs=0),'FG_UNSOURCED_QTY_INVALID'),'qty_fraction':(dict(qty_pcs=1.5),'FG_UNSOURCED_QTY_INVALID'),'qty_nan':(dict(qty_pcs='NaN'),'FG_UNSOURCED_QTY_INVALID'),
            'value_without_reason':(dict(owner_unit_value='5'),'FG_UNSOURCED_VALUE_REASON_REQUIRED'),'value_negative':(dict(owner_unit_value='-1',owner_value_reason='x'),'FG_UNSOURCED_VALUE_INVALID'),
            'future':(dict(physical_at=(r1.now(cur)+timedelta(days=1)).isoformat()),'FG_UNSOURCED_PHYSICAL_AT_FUTURE'),'no_reason':(dict(reason=' '),'FG_UNSOURCED_REASON_REQUIRED'),
            'unknown_kind':(dict(source_kind='WHATEVER'),'FG_UNSOURCED_KIND_INVALID'),'grade_b':(dict(quality_grade='GRADE_B'),'FG_UNSOURCED_GRADE_INVALID')}
    before=ledger(cur);out={}
    for name,(patch,exp) in expect.items():
        _,err=axp.attempt_post(cur,dict(base,**patch))
        msg=(err or {}).get('message') or ''
        out[name]=dict(refused=err is not None,message=msg[:160],exact=msg.startswith(exp))
    after=ledger(cur)
    ok=all(v['refused'] and v['exact'] for v in out.values()) and before==after
    return dict(status='PASS' if ok else 'COUNTEREXAMPLE',results=out,ledger_unchanged=before==after,expected='each invalid input refused with the exact AX message; ledger unchanged')

def fg_zero_with_reason(cur,today):
    f=axp.stocked_product(cur,today);product=str(f['product']);at=r1.now(cur)-timedelta(minutes=10)
    before=ledger(cur)
    r=axp.post(cur,dict(source_kind='FOUND_AT_OPNAME',product_id=product,location_id=chain.base.LOCATION,qty_pcs=2,physical_at=at.isoformat(),reason='auditor zero',owner_unit_value='0',owner_value_reason='Owner: sample without value'))
    after=ledger(cur);jl=lines(cur,r['journal_entry_id']) if r.get('journal_entry_id') else []
    hv=cur.execute('select cost_state,total_cost from erp.hpp_versions where lot_id=%s and is_current',(r['lot_id'],)).fetchone()
    checks=dict(explicit_zero_accepted=D(r['unit_value'])==0,ledger_unchanged_by_zero_value=before==after,lot_cost_state_recorded=hv is not None)
    return dict(status='PASS' if all(checks.values()) else 'COUNTEREXAMPLE',checks=checks,receipt=r,journal=jl,hpp=[str(x) for x in hv] if hv else None,
                expected='an explicit owner zero WITH reason is accepted and visibly zero (not guessed); without reason refused (fg_refusals)')

def fg_closed_period(cur,today):
    f=r1.production(cur,today);day=f['day']
    source=r1.receipt(cur,f,chain.production.at(day,13),0);r1.final(cur,f,source,chain.production.at(day,14),10)
    api.admin(cur);product=str(f['product']);at=chain.production.at(day,16)
    avg,_=my_average(cur,product,at)
    boundary.historical.prior.set_open_period(cur,day)
    closed=cur.execute('select closed_through from erp.accounting_period_control where singleton_id=1').fetchone()[0]
    r=axp.post(cur,dict(source_kind='FOUND_AT_OPNAME',product_id=product,location_id=chain.base.LOCATION,qty_pcs=2,physical_at=at.isoformat(),reason='auditor closed period'))
    je=cur.execute('select economic_date,transaction_date from erp.journal_entries where id=%s',(r['journal_entry_id'],)).fetchone()
    checks=dict(unit_equals_average_at_physical_instant=avg is not None and D(r['unit_value'])==avg,economic_date_is_physical_day=je[0]==day,gl_date_after_closed_through=je[1]>closed,closed_through_unchanged=cur.execute('select closed_through from erp.accounting_period_control where singleton_id=1').fetchone()[0]==closed)
    return dict(status='PASS' if all(checks.values()) else 'COUNTEREXAMPLE',checks=checks,economic=str(je[0]),transaction=str(je[1]),closed_through=str(closed),unit=str(r['unit_value']),auditor_average=str(avg),
                expected='M:1061 closed period: controlled adjustment; economic date = physical day, GL posting date in the open period; closed_through unchanged')

def acc_seven_pcs(cur,today):
    f=acc.fixture(api,cur,today,12);p=f['payload'];before=api.production.ledger(cur);api.admin(cur)
    master=cur.execute('select to_jsonb(p) from erp.contractor_accessory_price_versions p where id=%s',(f['price'],)).fetchone()[0]
    p['items'][0]['qty']='5';saved=acc.call(api,cur,'SAVE_DRAFT',p)
    p.update(id=saved['id'],expected_version=saved['row_version']);p['items'][0]['qty']='7';p['items'][0]['manual_price']='3.25'
    key=uuid.uuid4();posted=acc.call(api,cur,'POST',p,key);replay=acc.call(api,cur,'POST',p,key)
    api.admin(cur)
    stock=cur.execute('select cached_stock_qty from erp.materials where id=%s',(f['material'],)).fetchone()[0]
    item=cur.execute('select qty,transaction_qty,unit_sale_price_snapshot,total_receivable from erp.contractor_material_issue_items where issue_id=%s',(posted['id'],)).fetchone()
    charge=cur.execute("select coalesce(sum(l.debit),0) from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id where j.source_id=%s and j.source_type='CONTRACTOR_MATERIAL_RECEIVABLE'",(posted['id'],)).fetchone()[0]
    master_after=cur.execute('select to_jsonb(p) from erp.contractor_accessory_price_versions p where id=%s',(f['price'],)).fetchone()[0]
    rev=acc.call(api,cur,'REVERSE',dict(id=posted['id'],expected_version=posted['row_version'],reason='auditor undo'),uuid.uuid4())
    api.admin(cur)
    stock_after=cur.execute('select cached_stock_qty from erp.materials where id=%s',(f['material'],)).fetchone()[0]
    item_after=cur.execute('select qty,transaction_qty,unit_sale_price_snapshot,total_receivable from erp.contractor_material_issue_items where issue_id=%s',(posted['id'],)).fetchone()
    after=api.production.ledger(cur)
    checks=dict(posted_status=posted.get('status')=='POSTED',replay_identical=replay==posted,qty_exactly_7=item is not None and D(item[0])==7 and D(item[1])==7,
                unit_price_manual_3_25=item is not None and D(item[2])==D('3.25'),receivable_22_75=item is not None and D(item[3])==D('22.75') and D(charge)==D('22.75'),
                stock_300_to_293=D(stock)==293,master_price_unchanged=master==master_after and D(master['selling_price'])==36,
                reverse_restores_stock_300=D(stock_after)==300,reverse_restores_every_account=before==after,posted_detail_immutable=item_after==item,reversed_status=rev.get('status')=='REVERSED')
    return dict(status='PASS' if all(checks.values()) else 'COUNTEREXAMPLE',checks=checks,item=[str(x) for x in item] if item else None,charge=str(charge),stock=str(stock),stock_after=str(stock_after),
                expected='M:94 / ACC-DEC02: 7 PCS at manual 3.25 -> 22.75, stock 300->293, master 36.00/dozen unchanged, replay once, linked cancel restores 300 and all accounts, posted detail stays 7 PCS')

def acc_refusals(cur,today):
    out={}
    for name,patch in {'fraction_pcs':dict(qty='7.5'),'manual_without_price':dict(manual_price=None),'nan_price':dict(manual_price='NaN'),'negative_price':dict(manual_price='-3.25'),'zero_qty':dict(qty='0')}.items():
        f=acc.fixture(api,cur,today,12);p=f['payload'];before=api.production.ledger(cur);api.admin(cur)
        p['items'][0].update(patch)
        res,err=r1.peer.attempt(cur,lambda:acc.call(api,cur,'POST',p,uuid.uuid4()))
        api.admin(cur)
        stock=cur.execute('select cached_stock_qty from erp.materials where id=%s',(f['material'],)).fetchone()[0]
        out[name]=dict(refused=err is not None,message=((err or {}).get('message') or '')[:160],stock_unchanged=D(stock)==300,ledger_unchanged=api.production.ledger(cur)==before)
    ok=all(v['refused'] and v['stock_unchanged'] and v['ledger_unchanged'] for v in out.values())
    return dict(status='PASS' if ok else 'COUNTEREXAMPLE',results=out,expected='ACC-DEC02: fractional PCS never posted (M:1405 guard must not accept fractional qty); invalid money refused; stock and ledger unchanged; messages recorded verbatim')

def cases(cur,today):
    def wrap(fn):
        def run():
            try:return fn(cur,today)
            except Exception as exc:return dict(status='INCOMPLETE',error=str(exc)[:900],traceback=traceback.format_exc()[-1200:])
        return run
    return [('FG:FOUND_AT_OPNAME_CONSERVATION',wrap(fg_found)),('FG:REPLAY_AND_REVERSE',wrap(fg_replay_and_reverse)),('FG:EXACT_REFUSALS',wrap(fg_refusals)),
            ('FG:EXPLICIT_ZERO_WITH_REASON',wrap(fg_zero_with_reason)),('FG:CLOSED_PERIOD_PHYSICAL_DATE',wrap(fg_closed_period)),
            ('ACC:SEVEN_PCS_RETAIL_LIFECYCLE',wrap(acc_seven_pcs)),('ACC:REFUSALS_FRACTION_AND_INVALID_PRICE',wrap(acc_refusals))]
