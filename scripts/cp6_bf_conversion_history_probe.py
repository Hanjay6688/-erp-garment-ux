"""Writer regressions for the independent conversion-history counterexample.

Native posting and two-session races only; fixtures run on disposable PostgreSQL.
The auditor's original probe lives separately and is retained byte-for-byte.
"""
import copy
import json
import uuid
from datetime import datetime, timedelta, timezone
import cp6_bf_combined_probe as p

b, bf, one = p.b, p.bf, p.one


def fixture(cur,today):
    f=p.fixture(cur,today)
    w=p.wash(cur,f,range(4),11)
    p.finish(cur,f,[w],range(4),13)
    label='BF-HISTORY-'+uuid.uuid4().hex[:8]
    target=b.sized_product(cur,f['size_ids'][1],label)
    sibling=b.sized_product(cur,f['size_ids'][2],label)
    a=bf.group(cur,[target],f['when'](14))
    z=bf.group(cur,[sibling],f['when'](14))
    bf.save(cur,[a,z],f['when'](14))
    source=p.lots(cur,f)[1]
    f.update(target=target,sibling=sibling,target_a=a,target_z=z,source=source,
        conversion_request=str(uuid.uuid4()),conversion_payload=dict(source_lot_id=source,target_product_id=target,
        location_id=p.base.LOCATION,qty_pcs=1,physical_at=f['when'](15).isoformat(),
        reason='Posted conversion identity must retain its original commercial range',
        expected_version=one(cur,'select erp.be_source_revision_v1(%s,%s)',source,p.base.LOCATION)))
    return f


def post(cur,f):
    return bf.be.be(cur,'POST',f['conversion_payload'],f['conversion_request'])


def move_payload(cur,f,hour=14,minute=30,source=False):
    at=f['when'](hour,minute)
    if source:
        a,z=f['a'],f['z'];remaining=[f['roots'][0],f['roots'][2]];incoming=[f['roots'][3],f['roots'][1]]
    else:
        a,z=f['target_a'],f['target_z'];remaining=[];incoming=[f['sibling'],f['target']]
    ga=bf.group(cur,remaining or a['members'],at,sku=a['sku'],gid=a['id'],revision=1,settings=copy.deepcopy(a['settings']))
    if not remaining:ga.update(members=[],legacy_basis=[])
    gz=bf.group(cur,incoming,at,sku=z['sku'],gid=z['id'],revision=1,settings=copy.deepcopy(z['settings']))
    return dict(groups=[ga,gz],effective_from=at.isoformat(),reason='Range history regression')


def move(cur,payload):
    return bf.call(cur,'SAVE_GROUPS',payload)


def document(cur,f):
    p.prod.owner(cur)
    result=cur.execute('select public.erp_get_product_conversion_workspace_v1(%s::jsonb)',(json.dumps({}),)).fetchone()[0]
    b.api.admin(cur)
    row=next(row for row in result['documents'] if row['id']==f['conversion_request'])
    # The reader serializes timestamptz in the caller's session timezone.
    # Compare the exact instant, retaining precision, rather than its offset
    # spelling; finance fixture helpers can switch Asia/Jakarta to UTC.
    row['physical_at']=datetime.fromisoformat(row['physical_at']).astimezone(timezone.utc).isoformat()
    return row


def history(cur,today,source=False,reversed_=False):
    f=fixture(cur,today);posted=post(cur,f)
    if reversed_:
        bf.be.be(cur,'REVERSE',dict(conversion_id=posted['conversion_id'],reason='History remains after reversal'))
    before=document(cur,f);books=p.books(cur)
    target=f['target_a']['sku'];stamp=f['when'](15)+timedelta(seconds=1)
    historical=p.report(cur,target,stamp)['groups']
    checks={}
    for label,hour,minute in [('backdated',14,30),('same_instant',15,0)]:
        payload=move_payload(cur,f,hour,minute,source)
        checks[label]=b.refused(cur,lambda:move(cur,payload),'BF_TARIFF_HISTORY')['ok']
        checks[label+'_atomic']=document(cur,f)==before and p.books(cur)==books and p.report(cur,target,stamp)['groups']==historical
    # A legitimate later move remains allowed, including after a reversal.
    move(cur,move_payload(cur,f,16,source=source))
    after=document(cur,f)
    product=f['roots'][1] if source else f['target']
    expected=f['z']['sku'] if source else f['target_z']['sku']
    checks.update(old_document=after==before,old_hpp_group=p.report(cur,target,stamp)['groups']==historical,
        later_identity=one(cur,'select erp.bf_commercial_sku_at_v1(%s,%s)',product,f['when'](17))==expected,
        balances_unchanged=p.books(cur)==books,
        destination_stock=p.stock(cur,posted['destination_lot_id'])==(0 if reversed_ else 1))
    return b.verdict(checks,source=source,reversed=reversed_,document_before=before,document_after=after,
        historical_hpp=historical,books_before=books,books_after=p.books(cur))


def race(tools,today,first,commit):
    with tools.connect() as conn,conn.cursor() as cur:
        f=fixture(cur,today);payload=move_payload(cur,f);conn.commit()
    ops=dict(CONVERSION=lambda cur:post(cur,f),MOVE=lambda cur:move(cur,payload))
    other='MOVE' if first=='CONVERSION' else 'CONVERSION'
    held,contention,outcome=tools.two_sessions(ops[first],ops[other],commit)
    with tools.connect() as conn,conn.cursor() as cur:
        count=one(cur,'select count(*) from erp.product_conversions where id=%s',f['conversion_request'])
        revision=one(cur,'select revision from erp.bf_skus_v1 where id=%s',f['target_a']['id'])
        label=document(cur,f)['target_sku'] if count else None
        conn.rollback()
    rejected=first=='CONVERSION' and commit
    checks=dict(serialized=contention.get('kind')=='BLOCKED' and contention.get('holder_blocks_worker') is True,
        outcome=(not outcome.get('ok') and 'BF_TARIFF_HISTORY' in (outcome.get('message') or '')) if rejected else outcome.get('ok') is True,
        conversion_count=count==(1 if first=='MOVE' or commit else 0),
        revision=revision==(1 if rejected or (first=='MOVE' and not commit) else 2),
        identity=label==(f['target_z']['sku'] if first=='MOVE' and commit else f['target_a']['sku']) if count else True)
    return b.verdict(checks,first=first,first_committed=commit,contention=contention,second=outcome,
        conversion_count=count,revision=revision,document_target_sku=label)


def grade_b_return(cur,today):
    f=p.fixture(cur,today);w=p.wash(cur,f,range(4),11)
    p.finish(cur,f,[w],range(4),13)
    lot=p.lots(cur,f)[3];unit=b.lot_value(cur,lot)/4
    sale=p.sale(cur,f,3,2,15)
    old=p.report(cur,f['z']['sku'],f['when'](15,30))['groups']
    p.move34(cur,f,16)
    ret=str(uuid.uuid4());p.prod.owner(cur)
    cur.execute("insert into erp.sales_returns(id,return_number,sale_id,customer_id,physical_at,created_by) select %s,%s,id,customer_id,%s,erp.current_app_user_id() from erp.sales_headers where id=%s",(ret,'BFB-'+ret,f['when'](17),sale))
    cur.execute("insert into erp.sales_return_items(return_id,sale_stock_allocation_id,location_id,qty_pcs,refund_amount,quality_grade) select %s,a.id,a.location_id,1,185000,'GRADE_B' from erp.sale_stock_allocations a join erp.sales_items i on i.id=a.sale_item_id where i.sale_id=%s",(ret,sale))
    cur.execute('select erp.post_sales_return(%s)',(ret,));b.api.admin(cur)
    all_=p.report(cur,f['a']['sku'])['groups'][0]
    a=p.report(cur,f['a']['sku'],grade='GRADE_A')['groups'][0]
    grade=p.report(cur,f['a']['sku'],grade='GRADE_B')['groups'][0]
    checks=dict(nonempty=grade['qty']=='1' and len(grade['lots'])==1,
        original_lot=grade['lots'][0]['lot_id']==lot and grade['lots'][0]['product_id']==f['roots'][3],
        exact_grade_value=b.D(grade['value'])==unit,
        partition_qty=b.D(all_['qty'])==b.D(a['qty'])+b.D(grade['qty'])==19,
        partition_value=b.D(all_['value'])==b.D(a['value'])+b.D(grade['value']),
        old_membership=p.report(cur,f['z']['sku'],f['when'](15,30))['groups']==old)
    p.prod.owner(cur);cur.execute('select erp.reverse_sales_return(%s,%s)',(ret,'Grade B report inverse'));b.api.admin(cur)
    checks['inverse_grade_empty']=p.report(cur,f['a']['sku'],grade='GRADE_B')['groups']==[]
    checks['inverse_qty']=p.report(cur,f['a']['sku'])['groups'][0]['qty']=='18'
    return b.verdict(checks,grade_b=grade,grade_a_qty=a['qty'],all_qty=all_['qty'],unit_value=str(unit))
