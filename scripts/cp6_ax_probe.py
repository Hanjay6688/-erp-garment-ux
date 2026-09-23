"""AX T1_FAMILY probe: finished goods entering without a production source (owner §15.1-FG, §19.2).

Label T1_FAMILY (owner decision A+B): targeted family evidence on the disposable chain AN -> AS/AT -> AU -> AV -> AW,
never release evidence. Phase 'before' observes AU + AV + AW without AX; phase 'after' also installs
supabase/dev/cp6_ax_t1_family.sql and replays the same cases. Expected outcomes come from the owner decisions:
average HPP only for goods without an origin value, valued at the physical date, frozen at posting, a separate
non-PO lot, never Rp0 unless the owner enters it with a reason, credit OTHER_INCOME; GOOD from an ordinary BS stays
on rework (2A). Every business action uses the ordinary authenticated owner session through the public facades;
administrative fixtures are labelled. Every case is rolled back inside the group (r1.group).
"""
from collections import Counter
from datetime import timedelta
from decimal import Decimal,ROUND_HALF_UP
from pathlib import Path
import argparse,hashlib,json,os,subprocess,sys,traceback,uuid
import psycopg

AUDITOR=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(Path.cwd()/'scripts'))
sys.path.append(str(AUDITOR/'scripts'))
import cp6_aw_probe as awp
r1,api,boundary,prior,chain=awp.r1,awp.api,awp.boundary,awp.prior,awp.chain

OUT=AUDITOR/'cp6-proof/ax'
AX_SQL=AUDITOR/'supabase/dev/cp6_ax_t1_family.sql'
LABEL='T1_FAMILY'


def ax_installed(cur):
    return cur.execute("select to_regprocedure('erp.post_fg_unsourced_receipt_v1(jsonb,uuid)') is not null").fetchone()[0]


def ax_verified(cur):
    base=awp.aw_verified(cur)
    assert cur.execute("select count(*) from erp.schema_migrations where version='v2.6.20ax'").fetchone()[0]==1,'AX_T1_MARKER'
    coverage=cur.execute('select erp.assert_new_stock_cutoff_coverage_v1()').fetchone()[0]
    return dict(base,stage='AV_PLUS_AW_PLUS_AX_T1',ax_sql_sha256=hashlib.sha256(AX_SQL.read_bytes()).hexdigest(),av_coverage=coverage)


def install_ax():
    with psycopg.connect(boundary.PG,autocommit=True) as conn,conn.cursor() as cur:cur.execute(AX_SQL.read_text(),prepare=False)
    with psycopg.connect(boundary.ADMIN) as conn,conn.cursor() as cur:
        result=ax_verified(cur);conn.rollback()
    return result


def post(cur,payload,request=None):
    api.ordinary(cur)
    r=cur.execute('select public.erp_post_fg_unsourced_receipt_v1(%s::jsonb,%s)',(json.dumps(payload,default=str),request or uuid.uuid4())).fetchone()[0]
    api.admin(cur);return r


def attempt_post(cur,payload,request=None):
    result,error=r1.peer.attempt(cur,lambda:post(cur,payload,request))
    return result,error


def preview(cur,product,at):
    api.ordinary(cur)
    r=cur.execute('select public.erp_preview_fg_unsourced_value_v1(%s,%s)',(product,at)).fetchone()[0]
    api.admin(cur);return r


def reverse(cur,receipt,reason='AX reversal',request=None):
    api.ordinary(cur)
    r=cur.execute('select public.erp_reverse_fg_unsourced_receipt_v1(%s,%s,%s)',(receipt,reason,request or uuid.uuid4())).fetchone()[0]
    api.admin(cur);return r


def counts(cur):
    api.admin(cur)
    return dict(lots=cur.execute("select count(*) from erp.fg_lots where lot_origin in('OTHER','VOIDED_PRODUCTION')").fetchone()[0],
                receipts=cur.execute('select count(*) from erp.fg_unsourced_receipts_v1').fetchone()[0] if ax_installed(cur) else None,
                journals=cur.execute("select count(*) from erp.journal_entries where source_type='FG_UNSOURCED_RECEIPT'").fetchone()[0])


def stocked_product(cur,today):
    """A SKU with real FG stock and HPP from the production chain (QC final 10 good)."""
    f=r1.used_product(cur,today) if hasattr(r1,'used_product') else None
    if f is None:
        f=r1.production(cur,today)
        source=r1.receipt(cur,f,r1.now(cur)-timedelta(minutes=30),0)
        r1.final(cur,f,source,r1.now(cur)-timedelta(minutes=20),10)
    api.admin(cur)
    return f


def expected_average(cur,product,at):
    """Independent computation of the stock-on-hand weighted average (probe side, not the function under test)."""
    rows=cur.execute("""select fl.id,hv.hpp_per_pcs,coalesce((select sum(m.qty_signed) from erp.fg_stock_movements m
        where m.lot_id=fl.id and m.physical_at<=%s),0) from erp.fg_lots fl join erp.hpp_versions hv on hv.lot_id=fl.id and hv.is_current
        join erp.products p on p.id=fl.product_id join erp.products t on t.id=%s
        where coalesce(p.identity_root_id,p.id)=coalesce(t.identity_root_id,t.id) and fl.produced_at<=%s
          and fl.lot_origin in('PRODUCTION','OPENING','CONVERSION','RETURN')""",(at,product,at)).fetchall()
    qty=sum(Decimal(q) for _,_,q in rows if q>0);value=sum(Decimal(q)*Decimal(h) for _,h,q in rows if q>0)
    return (value/qty).quantize(Decimal('0.01'),ROUND_HALF_UP) if qty else None


def journal_lines(cur,journal):
    return [dict(key=k,debit=str(d),credit=str(c),product=str(p) if p else None) for k,d,c,p in cur.execute("""select case l.account_id
          when erp.account_id('FG_INVENTORY') then 'FG_INVENTORY' when erp.account_id('OTHER_INCOME') then 'OTHER_INCOME' else l.account_id::text end,
          l.debit,l.credit,l.product_id
        from erp.journal_lines l where l.journal_entry_id=%s order by l.debit desc""",(journal,)).fetchall()]


def owner_only_model_product(cur,is_active=True,effective_from=None):
    """A SKU of a brand-new model with no lots anywhere: no reference HPP exists (administrative master fixture)."""
    api.admin(cur);model=uuid.uuid4();product=uuid.uuid4()
    cur.execute('insert into erp.product_models(id,model_code,model_name,is_active) values(%s,%s,%s,true)',(model,'AX-'+model.hex[:10],'AX no reference model'))
    cur.execute("""insert into erp.products(id,sku,model_id,brand_id,color_name,size_id,product_name,identity_root_id,effective_from,is_active,is_portal_visible)
        select %s,%s,%s,brand_id,'AX-NEW',size_id,'AX no reference',%s,coalesce(%s,effective_from),%s,true from erp.products where id=%s""",
        (product,'AX-'+product.hex[:10],model,product,effective_from,is_active,chain.base.BASE_PRODUCT))
    cur.execute("""insert into erp.accessory_bom_versions(product_id,version_label,effective_from,is_active,notes)
        values(%s,'AX-EMPTY','2026-01-01',true,'Explicit empty BOM')""",(product,))
    return str(product),None


# ---------------------------------------------------------------- cases

def found_stock_on_hand(cur,today):
    if not ax_installed(cur):return dict(status='NOT_APPLICABLE',reason='AX not installed (no path creates a non-PO lot today)')
    f=stocked_product(cur,today);product=str(f['product']);at=r1.now(cur)-timedelta(minutes=10)
    expected=expected_average(cur,product,at)
    view=preview(cur,product,at)
    po_hpp_before=cur.execute("select coalesce(sum(hv.total_cost),0) from erp.fg_lots fl join erp.hpp_versions hv on hv.lot_id=fl.id and hv.is_current where fl.product_id=%s and fl.lot_origin='PRODUCTION'",(product,)).fetchone()[0]
    r=post(cur,dict(source_kind='FOUND_AT_OPNAME',product_id=product,location_id=chain.base.LOCATION,qty_pcs=3,physical_at=at.isoformat(),reason='AX found at opname'))
    lot=cur.execute('select lot_origin,po_id,initial_qty_pcs,produced_at from erp.fg_lots where id=%s',(r['lot_id'],)).fetchone()
    hv=cur.execute('select cost_state,qty_basis_pcs,total_cost from erp.hpp_versions where lot_id=%s and is_current',(r['lot_id'],)).fetchone()
    lines=journal_lines(cur,r['journal_entry_id'])
    po_hpp_after=cur.execute("select coalesce(sum(hv.total_cost),0) from erp.fg_lots fl join erp.hpp_versions hv on hv.lot_id=fl.id and hv.is_current where fl.product_id=%s and fl.lot_origin='PRODUCTION'",(product,)).fetchone()[0]
    check=cur.execute("select coalesce(sum(issue_count),0) from erp.run_v268_financial_report_checks() where check_name='V2620F_NON_PO_PRODUCT_HPP_BOOK_MISMATCH'").fetchone()[0]
    total=(Decimal(str(r['unit_value']))*3).quantize(Decimal('0.01'))
    ok=(expected is not None and Decimal(str(r['unit_value']))==expected and view['tier']=='SKU' and view['method']=='STOCK_ON_HAND_WEIGHTED'
        and lot[0]=='OTHER' and lot[1] is None and lot[2]==3 and hv[0]=='ADJUSTED' and Decimal(hv[2]).quantize(Decimal('0.01'))==total
        and lines==[dict(key='FG_INVENTORY',debit=str(total),credit='0.00',product=product),dict(key='OTHER_INCOME',debit='0.00',credit=str(total),product=None)]
        and po_hpp_before==po_hpp_after and check==0)
    return dict(status='PASS' if ok else 'FAIL',expected_unit=str(expected),receipt=r,preview_tier=view['tier'],preview_method=view['method'],
                lot=[str(x) for x in lot],hpp=[str(x) for x in hv],journal=lines,production_lot_hpp_unchanged=po_hpp_before==po_hpp_after,
                non_po_book_check_issues=check,
                expected='Average of stock on hand at the physical instant; OTHER lot, no PO; Dr FG (product) / Cr OTHER_INCOME (no product); PO lot HPP unchanged')


def idempotent(cur,today):
    if not ax_installed(cur):return dict(status='NOT_APPLICABLE')
    f=stocked_product(cur,today);product=str(f['product']);at=r1.now(cur)-timedelta(minutes=10);req=uuid.uuid4()
    payload=dict(source_kind='FOUND_AT_OPNAME',product_id=product,location_id=chain.base.LOCATION,qty_pcs=2,physical_at=at.isoformat(),reason='AX replay')
    first=post(cur,payload,req);before=counts(cur)
    replay=post(cur,payload,req);after=counts(cur)
    changed=dict(payload,qty_pcs=4)
    _,error=attempt_post(cur,changed,req)
    ok=first==replay and before==after and error is not None
    return dict(status='PASS' if ok else 'FAIL',same_response=first==replay,no_second_lot=before==after,changed_payload_refusal=error)


def invalid_numbers(cur,today):
    if not ax_installed(cur):return dict(status='NOT_APPLICABLE')
    f=stocked_product(cur,today);product=str(f['product']);at=(r1.now(cur)-timedelta(minutes=10)).isoformat()
    base=dict(source_kind='FOUND_AT_OPNAME',product_id=product,location_id=chain.base.LOCATION,qty_pcs=1,physical_at=at,reason='AX invalid')
    variants={'qty_0':dict(qty_pcs=0),'qty_negative':dict(qty_pcs=-1),'qty_fraction':dict(qty_pcs=1.5),'qty_nan':dict(qty_pcs='NaN'),
              'qty_infinity':dict(qty_pcs='Infinity'),'value_nan':dict(owner_unit_value='NaN',owner_value_reason='x'),
              'value_infinity':dict(owner_unit_value='Infinity',owner_value_reason='x'),'value_negative':dict(owner_unit_value='-1',owner_value_reason='x'),
              'value_scale':dict(owner_unit_value='1.005',owner_value_reason='x'),'value_overflow':dict(owner_unit_value='10000000000000000',owner_value_reason='x'),
              'value_without_reason':dict(owner_unit_value='5'),'future_date':dict(physical_at=(r1.now(cur)+timedelta(days=1)).isoformat()),
              'no_reason':dict(reason=' '),'unknown_kind':dict(source_kind='WHATEVER')}
    before=counts(cur);refused={}
    for name,change in variants.items():
        _,error=attempt_post(cur,dict(base,**change))
        refused[name]=error and (error.get('message') or '')[:80]
    after=counts(cur)
    ok=all(refused.values()) and before==after
    return dict(status='PASS' if ok else 'FAIL',refused=refused,no_residue=before==after)


def no_reference(cur,today):
    """Never Rp0 by default: without any reference lot the owner must enter a value with a reason; explicit 0 is allowed."""
    if not ax_installed(cur):return dict(status='NOT_APPLICABLE')
    product,_=owner_only_model_product(cur);at=(r1.now(cur)-timedelta(minutes=10)).isoformat()
    view=preview(cur,product,at)
    base=dict(source_kind='FOUND_AT_OPNAME',product_id=product,location_id=chain.base.LOCATION,qty_pcs=2,physical_at=at,reason='AX no reference')
    _,refusal=attempt_post(cur,base)
    zero=post(cur,dict(base,owner_unit_value='0',owner_value_reason='Owner: barang contoh tanpa nilai'))
    valued=post(cur,dict(base,owner_unit_value='12500.50',owner_value_reason='Owner: harga pokok taksiran'))
    ok=(view['tier']=='OWNER_INPUT_REQUIRED' and refusal and 'FG_UNSOURCED_VALUE_REQUIRED' in (refusal.get('message') or '')
        and Decimal(str(zero['total_value']))==0 and zero['journal_entry_id'] is None
        and Decimal(str(valued['total_value']))==Decimal('25001.00') and valued['valuation']['tier']=='OWNER_VALUE')
    return dict(status='PASS' if ok else 'FAIL',preview=view,refusal=refusal,explicit_zero=zero,owner_value=valued)


def owner_value_with_reference(cur,today):
    """Owner decision: when a reference average exists the receipt takes that average; an owner value is refused."""
    if not ax_installed(cur):return dict(status='NOT_APPLICABLE')
    f=stocked_product(cur,today);product=str(f['product']);before=counts(cur)
    _,error=attempt_post(cur,dict(source_kind='FOUND_AT_OPNAME',product_id=product,location_id=chain.base.LOCATION,qty_pcs=1,
        physical_at=(r1.now(cur)-timedelta(minutes=5)).isoformat(),reason='AX owner value with reference',owner_unit_value='99999',owner_value_reason='AX'))
    after=counts(cur)
    ok=error is not None and 'OWNER_VALUE_NOT_ALLOWED' in (error.get('message') or '') and before==after
    return dict(status='PASS' if ok else 'FAIL',refusal=error,no_residue=before==after)


def manual_bs(cur,product,kind,qty,at):
    return chain.bs_action(cur,'CREATE_MANUAL_BS',dict(untracked_type=kind,legacy_reference='AX-'+uuid.uuid4().hex[:12],
        change_reason='AX '+kind+' BS',physical_at=at.isoformat(),qty_pcs=qty,product_id=str(product)))


def good_from_found_bs(cur,today):
    """Partial rework of a found BS: 3 of 5 become GOOD, then 3 more is refused, then the last 2 resolve the case."""
    if not ax_installed(cur):return dict(status='NOT_APPLICABLE')
    f=stocked_product(cur,today);product=str(f['product']);found_at=r1.now(cur)-timedelta(minutes=15)
    case=manual_bs(cur,product,'OUT_OF_NOWHERE',5,found_at)['result']['bs_case_id']
    api.admin(cur)
    base=dict(source_kind='GOOD_FROM_UNSOURCED_BS',bs_case_id=case,location_id=chain.base.LOCATION,physical_at=(r1.now(cur)-timedelta(minutes=5)).isoformat(),reason='AX BS found reworked')
    first=post(cur,dict(base,qty_pcs=3))
    status1=cur.execute('select status from erp.bs_cases where id=%s',(case,)).fetchone()[0]
    _,over=attempt_post(cur,dict(base,qty_pcs=3))
    second=post(cur,dict(base,qty_pcs=2))
    status2=cur.execute('select status from erp.bs_cases where id=%s',(case,)).fetchone()[0]
    resolved=cur.execute("select coalesce(sum(qty_pcs),0) from erp.bs_resolutions where bs_case_id=%s and resolution_type='OTHER'",(case,)).fetchone()[0]
    ok=first['qty_pcs']==3 and over and 'QTY_EXCEEDS_OPEN' in (over.get('message') or '') and second['qty_pcs']==2 and resolved==5 and status2=='RESOLVED'
    return dict(status='PASS' if ok else 'FAIL',first=first,status_after_first=status1,over_refusal=over,second=second,status_after_second=status2,resolved_qty=resolved)


def ordinary_bs_refused(cur,today):
    """GOOD from a BS that has an origin value stays on rework (2A): LEGACY manual BS is refused by AX."""
    if not ax_installed(cur):return dict(status='NOT_APPLICABLE')
    f=stocked_product(cur,today);product=str(f['product'])
    case=manual_bs(cur,product,'LEGACY',2,r1.now(cur)-timedelta(minutes=15))['result']['bs_case_id']
    api.admin(cur)
    _,error=attempt_post(cur,dict(source_kind='GOOD_FROM_UNSOURCED_BS',bs_case_id=case,location_id=chain.base.LOCATION,qty_pcs=1,
        physical_at=(r1.now(cur)-timedelta(minutes=5)).isoformat(),reason='AX legacy BS'))
    ok=error is not None and 'HAS_ORIGIN_VALUE' in (error.get('message') or '')
    return dict(status='PASS' if ok else 'FAIL',refusal=error)


def reversal(cur,today):
    """Reverse an unused receipt (BS open again, journal reversed, lot voided); a used lot cannot be reversed."""
    if not ax_installed(cur):return dict(status='NOT_APPLICABLE')
    f=stocked_product(cur,today);product=str(f['product'])
    case=manual_bs(cur,product,'OUT_OF_NOWHERE',2,r1.now(cur)-timedelta(minutes=15))['result']['bs_case_id']
    api.admin(cur)
    r=post(cur,dict(source_kind='GOOD_FROM_UNSOURCED_BS',bs_case_id=case,location_id=chain.base.LOCATION,qty_pcs=2,
        physical_at=(r1.now(cur)-timedelta(minutes=5)).isoformat(),reason='AX to reverse'))
    back=reverse(cur,r['receipt_id'])
    state=cur.execute("""select rc.status,fl.lot_origin,(select status from erp.bs_cases where id=%s),
        (select count(*) from erp.bs_resolutions where id=rc.bs_resolution_id),
        (select count(*) from erp.journal_entries where reversal_of_id=rc.journal_entry_id)
        from erp.fg_unsourced_receipts_v1 rc join erp.fg_lots fl on fl.id=rc.lot_id where rc.id=%s""",(case,r['receipt_id'])).fetchone()
    _,again=r1.peer.attempt(cur,lambda:reverse(cur,r['receipt_id']))
    # A lot sold after posting cannot be reversed: sale through the ordinary RPCs on a SKU whose only lot is the AX lot.
    solo,_=owner_only_model_product(cur)
    sold=post(cur,dict(source_kind='FOUND_AT_OPNAME',product_id=solo,location_id=chain.base.LOCATION,qty_pcs=1,
        physical_at=(r1.now(cur)-timedelta(minutes=5)).isoformat(),reason='AX to sell',owner_unit_value='10000',owner_value_reason='AX sale fixture'))
    sale=chain.production.rpc(cur,'erp.save_sale_draft_v2',dict(sale_number='AX-'+uuid.uuid4().hex[:10],customer_id=chain.base.create_customer(cur,'AX'+uuid.uuid4().hex[:6]),
        source_location_id=chain.base.LOCATION,sale_date=(r1.now(cur)-timedelta(minutes=2)).isoformat(),reason='AX sale',
        items=[dict(product_id=solo,qty_pcs=1,unit_price_snapshot=15000,discount_amount=0)]),uuid.uuid4(),None)
    api.admin(cur)
    sale_id=sale['sale_id']
    chain.production.owner(cur);cur.execute('select erp.post_sale_v2(%s,%s,%s)',(sale_id,uuid.uuid4(),int(sale['row_version'])));api.admin(cur)
    cogs=cur.execute("""select coalesce(sum(l.debit-l.credit),0) from erp.journal_lines l join erp.journal_entries e on e.id=l.journal_entry_id
        where l.product_id=%s and l.account_id=erp.account_id('COGS') and e.status in('POSTED','REVERSED')""",(solo,)).fetchone()[0]
    _,used=r1.peer.attempt(cur,lambda:reverse(cur,sold['receipt_id']))
    ok=(state[0]=='REVERSED' and state[1]=='VOIDED_PRODUCTION' and state[2]=='OPEN' and state[3]==0 and state[4]==1 and again is not None
        and used is not None and 'LOT_IN_USE' in (used.get('message') or '') and Decimal(cogs)==Decimal('10000'))
    return dict(status='PASS' if ok else 'FAIL',reversal=back,state=[str(x) for x in state],second_reversal=again,used_lot_refusal=used,
                sold_unit_cogs=str(cogs),expected='Unused receipt reverses fully; sold lot refused; COGS of the sold unit equals the frozen value once')


def backdated(cur,today):
    """Valuation at the physical date in a closed period: stock as of that instant, GL date moved to the open period."""
    if not ax_installed(cur):return dict(status='NOT_APPLICABLE')
    f=stocked_product(cur,today);product=str(f['product'])
    boundary.historical.prior.set_open_period(cur,today-timedelta(days=1))
    at=r1.now(cur)-timedelta(minutes=10)
    r=post(cur,dict(source_kind='FOUND_AT_OPNAME',product_id=product,location_id=chain.base.LOCATION,qty_pcs=1,physical_at=at.isoformat(),reason='AX backdated'))
    je=cur.execute('select economic_date,transaction_date from erp.journal_entries where id=%s',(r['journal_entry_id'],)).fetchone()
    return dict(status='OBSERVED',receipt=r,economic_date=str(je[0]),transaction_date=str(je[1]),
                note='Physical date today (open) here; a closed physical date needs stock before the close, covered in the next iteration')


def backdated_closed(cur,today):
    """Physical date inside a closed period (owner: value at the physical date). A PO lot produced two days ago is the
    only stock of the SKU; the period is then closed through that day. The receipt must be valued from the stock as of
    the physical instant, the journal keeps the physical day as economic date and moves only the GL date into the open
    period; a preview before the lot existed must not use that lot."""
    if not ax_installed(cur):return dict(status='NOT_APPLICABLE')
    f=r1.production(cur,today);day=f['day']
    source=r1.receipt(cur,f,chain.production.at(day,13),0)
    r1.final(cur,f,source,chain.production.at(day,14),10)
    api.admin(cur);product=str(f['product'])
    lot=str(cur.execute("select id from erp.fg_lots where product_id=%s and lot_origin='PRODUCTION'",(product,)).fetchone()[0])
    before_lot=preview(cur,product,chain.production.at(day,12))
    at=chain.production.at(day,16)
    expected=expected_average(cur,product,at)
    view=preview(cur,product,at)
    boundary.historical.prior.set_open_period(cur,day)
    r=post(cur,dict(source_kind='FOUND_AT_OPNAME',product_id=product,location_id=chain.base.LOCATION,qty_pcs=2,physical_at=at.isoformat(),reason='AX backdated closed'))
    je=cur.execute('select economic_date,transaction_date from erp.journal_entries where id=%s',(r['journal_entry_id'],)).fetchone()
    closed=cur.execute('select closed_through from erp.accounting_period_control where singleton_id=1').fetchone()[0]
    mv=cur.execute('select physical_at from erp.fg_stock_movements where lot_id=%s',(r['lot_id'],)).fetchall()
    ok=(expected is not None and Decimal(str(r['unit_value']))==expected and view['tier']=='SKU' and lot in json.dumps(view)
        and lot not in json.dumps(before_lot) and je[0]==day and je[1]>closed and closed==day
        and len(mv)==1 and mv[0][0]==at)
    return dict(status='PASS' if ok else 'FAIL',expected_unit=str(expected),receipt=r,preview_before_lot=before_lot,preview_at=view,
                economic_date=str(je[0]),transaction_date=str(je[1]),closed_through=str(closed),movement_physical_at=[str(m[0]) for m in mv],
                expected='Unit = stock-on-hand average at the physical instant; economic date = physical day (closed); GL date in the open period')


def new_stock_inactive(cur,today):
    """NEW_STOCK (owner decision 1C): an inactive SKU, or a SKU version not yet effective at the physical instant,
    cannot receive a new lot, even with an owner value; nothing is left behind."""
    if not ax_installed(cur):return dict(status='NOT_APPLICABLE')
    before=counts(cur)
    inactive,_=owner_only_model_product(cur,is_active=False)
    later,_=owner_only_model_product(cur,effective_from=r1.now(cur)-timedelta(hours=1))
    results={}
    for name,product,at in (('inactive',inactive,r1.now(cur)-timedelta(minutes=5)),('not_yet_effective',later,r1.now(cur)-timedelta(days=1))):
        _,error=attempt_post(cur,dict(source_kind='FOUND_AT_OPNAME',product_id=product,location_id=chain.base.LOCATION,qty_pcs=1,
            physical_at=at.isoformat(),reason='AX NEW_STOCK '+name,owner_unit_value='1000',owner_value_reason='AX owner value'))
        results[name]=error
    after=counts(cur)
    ok=(results['inactive'] is not None and 'tidak aktif' in (results['inactive'].get('message') or '')
        and results['not_yet_effective'] is not None and 'belum berlaku' in (results['not_yet_effective'].get('message') or '')
        and before==after)
    return dict(status='PASS' if ok else 'FAIL',refusals=results,no_residue=before==after)


def access(cur,today):
    if not ax_installed(cur):return dict(status='NOT_APPLICABLE')
    def stranger():
        api.admin(cur)
        cur.execute("select set_config('request.jwt.claims',%s,true)",(json.dumps({'sub':str(uuid.uuid4()),'role':'authenticated'}),))
        cur.execute('set local session authorization authenticated')
        return cur.execute('select public.erp_post_fg_unsourced_receipt_v1(%s::jsonb,%s)',(json.dumps(dict(source_kind='FOUND_AT_OPNAME')),uuid.uuid4())).fetchone()[0]
    def anon():
        api.admin(cur);cur.execute('set local role anon')
        return cur.execute('select public.erp_preview_fg_unsourced_value_v1(%s,now())',(uuid.uuid4(),)).fetchone()[0]
    def direct_table():
        api.admin(cur);cur.execute('set local role authenticated')
        return cur.execute('select count(*) from erp.fg_unsourced_receipts_v1').fetchone()[0]
    results={}
    for name,op in (('stranger_post',stranger),('anon_preview',anon),('authenticated_table',direct_table)):
        _,error=r1.peer.attempt(cur,op);results[name]=dict(refused=error is not None,sqlstate=error and error.get('sqlstate'))
    ok=all(v['refused'] for v in results.values())
    return dict(status='PASS' if ok else 'FAIL',results=results)


def engine_after(cur,today):
    """After AX postings the AW engine sees no new integrity blocker for the product."""
    if not ax_installed(cur):return dict(status='NOT_APPLICABLE')
    f=stocked_product(cur,today);product=str(f['product']);at=r1.now(cur)-timedelta(minutes=10)
    post(cur,dict(source_kind='FOUND_AT_OPNAME',product_id=product,location_id=chain.base.LOCATION,qty_pcs=2,physical_at=at.isoformat(),reason='AX engine'))
    pre=awp.preflight(cur,today)
    integrity=[b['code'] for b in pre['blockers'] if b['family']=='INTEGRITY']
    return dict(status='PASS' if not integrity else 'FAIL',integrity_blockers=integrity,all_codes=awp.codes(pre))


def cases(cur,today):
    return [('AX:FOUND_STOCK_ON_HAND',lambda:found_stock_on_hand(cur,today)),('AX:IDEMPOTENT_REPLAY',lambda:idempotent(cur,today)),
            ('AX:INVALID_NUMBERS',lambda:invalid_numbers(cur,today)),('AX:NO_REFERENCE_OWNER_VALUE',lambda:no_reference(cur,today)),
            ('AX:OWNER_VALUE_WITH_REFERENCE_REFUSED',lambda:owner_value_with_reference(cur,today)),
            ('AX:GOOD_FROM_FOUND_BS_PARTIAL',lambda:good_from_found_bs(cur,today)),('AX:ORDINARY_BS_STAYS_2A',lambda:ordinary_bs_refused(cur,today)),
            ('AX:REVERSAL_AND_USED_LOT',lambda:reversal(cur,today)),('AX:BACKDATED_OBSERVATION',lambda:backdated(cur,today)),
            ('AX:BACKDATED_CLOSED_PERIOD',lambda:backdated_closed(cur,today)),('AX:NEW_STOCK_INACTIVE_SKU',lambda:new_stock_inactive(cur,today)),
            ('AX:ACCESS',lambda:access(cur,today)),('AX:ENGINE_CONSISTENCY',lambda:engine_after(cur,today))]


# ---------------------------------------------------------------- two-session races (committed, fresh copy per schedule)

def race_fixture(admin,with_sale):
    """Committed in the race copy: a SKU with no reference (owner value), a found BS of 5 and, for the sale races, an AX
    lot of 1 piece and a customer. The sale draft is saved inside the race: a saved draft already reserves the lot, and
    the reversal rightly refuses a reserved lot (iteration 2, run 35905188855, saved the draft in the fixture)."""
    with psycopg.connect(admin) as conn,conn.cursor() as cur:
        product,_=owner_only_model_product(cur)
        case=manual_bs(cur,product,'OUT_OF_NOWHERE',5,r1.now(cur)-timedelta(minutes=30))['result']['bs_case_id']
        api.admin(cur);f=dict(product=product,case=str(case),good_at=(r1.now(cur)-timedelta(minutes=5)).isoformat())
        if with_sale:
            lot=post(cur,dict(source_kind='FOUND_AT_OPNAME',product_id=product,location_id=chain.base.LOCATION,qty_pcs=1,
                physical_at=(r1.now(cur)-timedelta(minutes=20)).isoformat(),reason='AX race lot',owner_unit_value='10000',owner_value_reason='AX race'))
            api.admin(cur)
            f.update(receipt=lot['receipt_id'],lot=lot['lot_id'],customer=str(chain.base.create_customer(cur,'AXR'+uuid.uuid4().hex[:6])),
                     sale_at=(r1.now(cur)-timedelta(minutes=10)).isoformat())
        conn.commit()
    return f


def race_state(admin,f):
    with psycopg.connect(admin) as conn,conn.cursor() as cur:
        api.admin(cur)
        state=dict(receipts=cur.execute("select count(*) from erp.fg_unsourced_receipts_v1 where bs_case_id=%s and status='POSTED'",(f['case'],)).fetchone()[0],
                   resolved=cur.execute("select coalesce(sum(qty_pcs),0) from erp.bs_resolutions where bs_case_id=%s",(f['case'],)).fetchone()[0],
                   bs_status=cur.execute('select status from erp.bs_cases where id=%s',(f['case'],)).fetchone()[0],
                   ax_lots=cur.execute("select count(*) from erp.fg_lots where product_id=%s and lot_origin='OTHER'",(f['product'],)).fetchone()[0])
        if f.get('receipt'):
            state.update(receipt_status=cur.execute('select status from erp.fg_unsourced_receipts_v1 where id=%s',(f['receipt'],)).fetchone()[0],
                         sales_posted=cur.execute("select count(*) from erp.sales_headers h join erp.sales_items i on i.sale_id=h.id where i.product_id=%s and h.status='POSTED'",(f['product'],)).fetchone()[0],
                         lot_origin=cur.execute('select lot_origin from erp.fg_lots where id=%s',(f['lot'],)).fetchone()[0])
        issues=cur.execute("select coalesce(sum(issue_count),0) from erp.run_v268_financial_report_checks() where check_name='V2620F_NON_PO_PRODUCT_HPP_BOOK_MISMATCH'").fetchone()[0]
        state['non_po_book']='BALANCED' if issues==0 else f'{issues} issues'
        conn.rollback()
    return state


def ax_race(admin,kind,commit):
    f=race_fixture(admin,kind in('REVERSE_FIRST','SALE_FIRST'))
    good=lambda qty,request=None:(lambda cur:post(cur,dict(source_kind='GOOD_FROM_UNSOURCED_BS',bs_case_id=f['case'],location_id=chain.base.LOCATION,
        qty_pcs=qty,physical_at=f['good_at'],reason='AX race GOOD',owner_unit_value='5000',
        owner_value_reason='AX race'),request))
    def do_reverse(cur):return reverse(cur,f['receipt'],'AX race reversal')['status']
    def do_sell(cur):
        sale=chain.production.rpc(cur,'erp.save_sale_draft_v2',dict(sale_number='AXR-'+uuid.uuid4().hex[:10],customer_id=f['customer'],
            source_location_id=chain.base.LOCATION,sale_date=f['sale_at'],reason='AX race sale',
            items=[dict(product_id=f['product'],qty_pcs=1,unit_price_snapshot=15000,discount_amount=0)]),uuid.uuid4(),None)
        f['sale']=sale['sale_id']
        cur.execute('select erp.post_sale_v2(%s,%s,%s)',(sale['sale_id'],uuid.uuid4(),int(sale['row_version'])));api.admin(cur);return 'SOLD'
    if kind=='BS_OVERDRAW':
        first,second=good(3),good(3)
    elif kind=='SAME_REQUEST':
        request=uuid.uuid4();first,second=good(2,request),good(2,request)
    elif kind=='REVERSE_FIRST':
        first,second=do_reverse,do_sell
    else:
        first,second=do_sell,do_reverse
    held,contention,outcome=awp.two_sessions(admin,first,second,commit)
    state=race_state(admin,f)
    msg=outcome.get('message') or ''
    if kind=='BS_OVERDRAW':
        expected=dict(contention='BLOCKED',second='refused QTY_EXCEEDS_OPEN 3 > 2' if commit else 'posted',resolved=3,receipts=1)
        ok=(contention['kind']=='BLOCKED' and state['resolved']==3 and state['receipts']==1
            and ((not outcome['ok'] and 'QTY_EXCEEDS_OPEN' in msg) if commit else outcome['ok']))
    elif kind=='SAME_REQUEST':
        expected=dict(contention='BLOCKED',second='same response as the first' if commit else 'posted once by itself',resolved=2,receipts=1)
        same=outcome['ok'] and outcome['result'] is not None and outcome['result'].get('receipt_id')==held.get('receipt_id')
        ok=contention['kind']=='BLOCKED' and state['resolved']==2 and state['receipts']==1 and (same if commit else outcome['ok'])
    elif kind=='REVERSE_FIRST':
        expected=dict(contention='BLOCKED',sale='refused (lot voided)' if commit else 'SOLD',receipt='REVERSED' if commit else 'POSTED')
        ok=(contention['kind']=='BLOCKED' and state['receipt_status']==('REVERSED' if commit else 'POSTED')
            and (not outcome['ok'] if commit else outcome['ok']) and state['sales_posted']==(0 if commit else 1) and state['non_po_book']=='BALANCED')
    else:
        expected=dict(contention='BLOCKED',reverse='refused LOT_IN_USE' if commit else 'REVERSED',receipt='POSTED' if commit else 'REVERSED')
        ok=(contention['kind']=='BLOCKED' and state['receipt_status']==('POSTED' if commit else 'REVERSED')
            and ((not outcome['ok'] and 'LOT_IN_USE' in msg) if commit else outcome['ok']) and state['sales_posted']==(1 if commit else 0)
            and state['non_po_book']=='BALANCED')
    return dict(status='PASS' if ok else 'FAIL',kind=kind,first_committed=commit,expected=expected,contention=contention,
                held=held,contender=outcome,state=state)


def races(phase,verify):
    admin=boundary.ADMIN.rsplit('/',1)[0]+'/'+awp.RACE_DB
    report=dict(status='INCOMPLETE',database=awp.RACE_DB,schedules={},label=LABEL,copy_per_schedule=True,production_go=False)
    try:
        report['setup']=awp.fresh_race_copy(admin,verify)
        if phase=='after':
            for kind in ('BS_OVERDRAW','SAME_REQUEST','REVERSE_FIRST','SALE_FIRST'):
                for commit in (False,True):
                    key=f'AX_RACE:{kind}:'+('COMMIT' if commit else 'ABORT')
                    try:
                        setup=awp.fresh_race_copy(admin,verify)
                        row=ax_race(admin,kind,commit);row['copy_runtime_stage']=setup['runtime'].get('stage')
                    except Exception as exc:row=dict(status='INCOMPLETE',error=str(exc),traceback=traceback.format_exc())
                    report['schedules'][key]=row;r1.save('RACES_'+phase.upper(),report)
                    print(json.dumps(dict(group='AX_RACES_'+phase.upper(),case=key,**row),default=str),flush=True)
    finally:
        r1.docker('dropdb','-U','supabase_admin','--if-exists','--force','--maintenance-db=template1',awp.RACE_DB)
        with psycopg.connect(boundary.PRIMARY_ADMIN) as conn,conn.cursor() as cur:
            report['race_database_remaining']=cur.execute('select count(*) from pg_database where datname=%s',(awp.RACE_DB,)).fetchone()[0]
    report['counts']=dict(Counter(r['status'] for r in report['schedules'].values()))
    bad=report['counts'].get('INCOMPLETE') or report['counts'].get('FAIL') or report['race_database_remaining']
    report['status']='INCOMPLETE' if bad else 'PASS'
    r1.save('RACES_'+phase.upper(),report);return report


def run(phase):
    assert os.environ.get('CP6_AR_CONFIRM')=='cp6_rollback' and os.environ.get('CP6_DATABASE_CONTAINER')=='supabase_db_cp5-local'
    r1.OUT=OUT
    report=dict(status='INCOMPLETE',label=LABEL,phase=phase,source=r1.source(),production_go=False,independent_acceptance=False,release_evidence=False)
    r1.save('RESULT_'+phase.upper(),report)
    primary=None
    try:
        with psycopg.connect(boundary.PRIMARY_ADMIN) as conn,conn.cursor() as cur:prior.verified(cur,'AN');primary=boundary.snapshot(cur)
        r1.writer.install_at()
        control_url=os.environ['CP6_ADMISSION_CONTROL_PGURL']
        report['au_install']=awp.au_runtime.change('install',boundary.PG,control_url)['status']
        report['av_install']=awp.av_runtime.change('install',boundary.PG,control_url)['status']
        report['aw_install']=awp.install_aw();verify=awp.aw_verified
        if phase=='after':report['ax_install']=install_ax();verify=ax_verified
        r1.save('RESULT_'+phase.upper(),report)
        print(json.dumps(dict(ax_probe_setup={k:report.get(k) for k in ('au_install','av_install','aw_install','ax_install')}),default=str),flush=True)
        group=r1.group('AX_CASES_'+phase.upper(),cases,verify)
        report['ax_cases']={k:group[k] for k in ('status','counts')}
        race=races(phase,verify)
        report['ax_races']={k:race[k] for k in ('status','counts','race_database_remaining')}
        report['status']='REVIEW_COMPLETE' if group['status']!='INCOMPLETE' and race['status']!='INCOMPLETE' else 'INCOMPLETE'
    except Exception as exc:report.update(status='INCOMPLETE',error=str(exc),traceback=traceback.format_exc())
    finally:
        subprocess.run(['docker','exec','supabase_db_cp5-local','dropdb','-U','supabase_admin','--if-exists','--force','--maintenance-db=template1','cp6_rollback'],check=True)
        with psycopg.connect(boundary.PRIMARY_ADMIN) as conn,conn.cursor() as cur:
            prior.verified(cur,'AN');report['primary_unchanged']=primary is not None and boundary.snapshot(cur)==primary
            report['clone_remaining']=cur.execute("select count(*) from pg_database where datname='cp6_rollback'").fetchone()[0]
        if not report['primary_unchanged'] or report['clone_remaining']:report['status']='INCOMPLETE'
        r1.save('RESULT_'+phase.upper(),report)
    print(json.dumps(dict(ax_probe_phase=phase,**report),default=str),flush=True)
    assert report['status']=='REVIEW_COMPLETE',report.get('error','AX_PROBE_INCOMPLETE')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--phase',choices=('before','after'),required=True)
    run(parser.parse_args().phase)
