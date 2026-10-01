"""Fable round 14 (CP6 finisher): BF — commercial SKU ranges and portable supplier credit — auditor's own oracles.
Fixtures reuse the writer's helpers (cp6_bf_combined_probe, cp6_bf_supplier_probe); every check below is the auditor's.
Oracles (M: SKU reference is commercial grouping, not physical identity — M:1971, A:147; owner rule quoted by the writer
28 Sep 14:59 WIB, UNVERIFIED_OWNER_DECISION until confirmed: membership changes never touch ledger/stock/posted docs):
  XA14:RANGE_MOVE_WRITES_NO_PHYSICAL   moving size 34 from SKU z into SKU a (after the lots exist) leaves fg movements, lots,
                                       products, journals and GL books byte-identical; membership differs only by time.
  XA14:SKU_AT_TIMELINE_NO_GAP          erp.bf_commercial_sku_at_v1 is total and contiguous over the fixture window: every
                                       sampled instant resolves, z before the move / a from the move on, and the version
                                       rows of each SKU chain effective_to -> effective_from without gap or overlap.
  XA14:HPP_VALUE_CONSERVED_ACROSS_GROUPING  the HPP report's remaining qty/value summed over SKUs is invariant under the
                                       regrouping (20 PCS; same value), with 4 lots in a after the move.
  XA14:SUPPLIER_CREDIT_AP_CONSERVED    the sum of final AP over the supplier's purchases is invariant under any credit
                                       allocation; AP_SUPPLIER GL and material stock/values unchanged by reallocation;
                                       a negative amount and an over-allocation across two targets are refused with no change;
                                       an empty allocation restores the original split.
"""
import json
from datetime import timedelta
from decimal import Decimal as D
import cp6_bf_probe as bf
import cp6_bf_combined_probe as p
import cp6_bf_supplier_probe as supplier
INSTALL_BF=True
b,one=bf.b,bf.one

def physical(cur,roots):
    return dict(
        movements=cur.execute("select count(*),md5(coalesce(string_agg(m::text,'|' order by m.id::text),'')) from erp.fg_stock_movements m join erp.fg_lots l on l.id=m.lot_id where l.product_id=any(%s::uuid[])",(roots,)).fetchone(),
        lots=cur.execute("select count(*),md5(coalesce(string_agg(l::text,'|' order by l.id::text),'')) from erp.fg_lots l where l.product_id=any(%s::uuid[])",(roots,)).fetchone(),
        products=cur.execute("select md5(string_agg(x::text,'|' order by x.id::text)) from erp.products x where id=any(%s::uuid[])",(roots,)).fetchone()[0],
        journals=one(cur,'select count(*) from erp.journal_entries'),
        books=p.books(cur))

def report_totals(cur,skus):
    qty=D(0);value=D(0);lots=0;groups=0
    for sku in skus:
        for g in (p.report(cur,sku).get('groups') or []):
            groups+=1;qty+=D(str(g['qty']));value+=D(str(g['value']));lots+=len(g.get('lots') or [])
    return dict(qty=str(qty),value=str(value),lots=lots,groups=groups)

def built(cur,today):
    f=p.fixture(cur,today);w=p.wash(cur,f,range(4),11);p.finish(cur,f,[w],range(4),13);return f

def range_move_no_physical(cur,today):
    f=built(cur,today);roots=f['roots'];before=physical(cur,roots)
    sku_before=[one(cur,'select erp.bf_commercial_sku_at_v1(%s,%s)',r,f['when'](14)) for r in roots]
    p.move34(cur,f,16);after=physical(cur,roots)
    sku_after=[one(cur,'select erp.bf_commercial_sku_at_v1(%s,%s)',r,f['when'](17)) for r in roots]
    sku_hist=[one(cur,'select erp.bf_commercial_sku_at_v1(%s,%s)',r,f['when'](14)) for r in roots]
    return b.verdict(dict(stock_present=before['movements'][0]>0 and before['lots'][0]==4,
        movements_identical=before['movements']==after['movements'],lots_identical=before['lots']==after['lots'],
        products_identical=before['products']==after['products'],no_new_journal=before['journals']==after['journals'],
        books_identical=before['books']==after['books'],
        membership_before=sku_before==[f['a']['sku']]*3+[f['z']['sku']],membership_after=sku_after==[f['a']['sku']]*4,
        history_kept=sku_hist==sku_before),before=before,after=after,sku_before=sku_before,sku_after=sku_after)

def timeline_no_gap(cur,today):
    f=built(cur,today);root=f['roots'][3];move_at=f['when'](16);p.move34(cur,f,16)
    samples=[(h,m) for h in range(0,30) for m in (0,30)]
    resolved=[(h,m,one(cur,'select erp.bf_commercial_sku_at_v1(%s,%s)',root,f['when'](h,m))) for h,m in samples]
    expected=[(h,m,f['z']['sku'] if f['when'](h,m)<move_at else f['a']['sku']) for h,m in samples]
    exact=[one(cur,'select erp.bf_commercial_sku_at_v1(%s,%s)',root,move_at),one(cur,'select erp.bf_commercial_sku_at_v1(%s,%s)',root,move_at-timedelta(microseconds=1))]
    def chain(sku_id):
        rows=cur.execute('select effective_from,effective_to,revision from erp.bf_sku_versions_v1 where sku_id=%s order by revision',(sku_id,)).fetchall()
        contiguous=all(rows[i][1]==rows[i+1][0] for i in range(len(rows)-1));open_tail=rows[-1][1] is None
        return dict(rows=[(str(a),str(c),r) for a,c,r in rows],raw=rows,contiguous=contiguous,open_tail=open_tail)
    ca,cz=chain(f['a']['id']),chain(f['z']['id'])
    return b.verdict(dict(total=all(s is not None for _,_,s in resolved),sampled=resolved==expected,
        boundary=exact==[f['a']['sku'],f['z']['sku']],a_contiguous=ca['contiguous'] and ca['open_tail'],z_contiguous=cz['contiguous'] and cz['open_tail'],
        z_closed_at_move=len(cz['raw'])==2 and cz['raw'][0][1]==move_at),a_chain={k:v for k,v in ca.items() if k!='raw'},z_chain={k:v for k,v in cz.items() if k!='raw'},move_at=str(move_at))

def hpp_conserved(cur,today):
    f=built(cur,today);skus=[f['a']['sku'],f['z']['sku']];before=report_totals(cur,skus);a_before=report_totals(cur,skus[:1])
    p.move34(cur,f,16);after=report_totals(cur,skus);a_after=report_totals(cur,skus[:1]);z_after=report_totals(cur,skus[1:])
    return b.verdict(dict(qty_20=before['qty']=='20' and after['qty']=='20',value_conserved=before['value']==after['value'] and D(before['value'])>0,
        lots_4=before['lots']==4 and after['lots']==4,all_in_a=a_after['qty']=='20' and a_after['lots']==4 and z_after['qty'] in('0',) ,
        a_grew=D(a_after['value'])>D(a_before['value'])),before=before,after=after,a_before=a_before,a_after=a_after,z_after=z_after)

def supplier_credit_conserved(cur,today):
    f=supplier.fixture(cur,today);a,z,k=f['purchases'];s0=supplier.state(cur,f);total=lambda s:sum(D(x) for x in s['ap'])
    supplier.call(cur,supplier.payload(cur,f,[(z,'5.00')]));s1=supplier.state(cur,f)
    neg=b.refused(cur,lambda:supplier.call(cur,supplier.payload(cur,f,[(z,'-5.00')])),'ANY');s_neg=supplier.state(cur,f)
    over=b.refused(cur,lambda:supplier.call(cur,supplier.payload(cur,f,[(z,'15.00'),(k,'6.00')])),'ANY');s_over=supplier.state(cur,f)
    supplier.call(cur,supplier.payload(cur,f,[(z,'20.00')]));s2=supplier.state(cur,f)
    supplier.call(cur,supplier.payload(cur,f,[]));s3=supplier.state(cur,f)
    same_books=lambda x,y:x['ledger']==y['ledger'] and x['stock']==y['stock'] and x['values']==y['values']
    return b.verdict(dict(original=s0['ap']==['80.00','100.00','60.00'],split5=s1['ap']==['85.00','95.00','60.00'],full=s2['ap']==['100.00','80.00','60.00'],
        sum_invariant=total(s0)==total(s1)==total(s2)==total(s3)==D('240.00'),
        negative_refused=neg['refusal'] is not None and s_neg==s1,over_refused=over['refusal'] is not None and s_over==s1,
        gl_and_stock_untouched=same_books(s0,s1) and same_books(s0,s2) and same_books(s0,s3),restored=s3==s0),
        refusals=dict(negative=str(neg['refusal'])[:200],over=str(over['refusal'])[:200]),states=dict(s0=s0['ap'],s1=s1['ap'],s2=s2['ap'],s3=s3['ap']))

def cases(cur,today):
    return [('XA14:RANGE_MOVE_WRITES_NO_PHYSICAL',lambda:range_move_no_physical(cur,today)),
        ('XA14:SKU_AT_TIMELINE_NO_GAP',lambda:timeline_no_gap(cur,today)),
        ('XA14:HPP_VALUE_CONSERVED_ACROSS_GROUPING',lambda:hpp_conserved(cur,today)),
        ('XA14:SUPPLIER_CREDIT_AP_CONSERVED',lambda:supplier_credit_conserved(cur,today))]
