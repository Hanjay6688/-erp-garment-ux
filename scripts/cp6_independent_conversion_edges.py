"""Auditor-owned conversion edge probes on the unchanged revised BF package."""
from datetime import timedelta
import json
import cp6_bf_combined_probe as p


def protected_conversion_edge(cur,today,source_side=False,reversed_doc=False):
    """Independently check the source branch and a reversed target, including atomic refusal."""
    import copy
    f=p.fixture(cur,today)
    washed=p.wash(cur,f,range(4),11)
    p.finish(cur,f,[washed],range(4),13)
    source=p.lots(cur,f)[1]
    label='INDEP-EDGE-'+p.uuid.uuid4().hex[:8]
    target=p.b.sized_product(cur,f['size_ids'][1],label)
    sibling=p.b.sized_product(cur,f['size_ids'][2],label)
    a=p.bf.group(cur,[target],f['when'](14))
    z=p.bf.group(cur,[sibling],f['when'](14))
    p.bf.save(cur,[a,z],f['when'](14))
    posted=p.bf.be.be(cur,'POST',dict(source_lot_id=source,target_product_id=target,
        location_id=p.base.LOCATION,qty_pcs=1,physical_at=f['when'](15).isoformat(),
        reason='Independent source/reversal edge',expected_version=p.one(cur,
        'select erp.be_source_revision_v1(%s,%s)',source,p.base.LOCATION)))
    if reversed_doc:
        p.bf.be.be(cur,'REVERSE',dict(conversion_id=posted['conversion_id'],
            reason='Independent reversed-history edge'))
    destination=posted['destination_lot_id']
    stamp=f['when'](15)
    def document():
        p.prod.owner(cur)
        data=p.one(cur,'select public.erp_get_product_conversion_workspace_v1(%s::jsonb)',json.dumps({}))
        p.b.api.admin(cur)
        return next(d for d in data['documents'] if d['id']==posted['conversion_id'])
    before_doc=document()
    before_src=p.one(cur,'select erp.bf_commercial_sku_at_v1(%s,%s)',f['roots'][1],stamp)
    before_tgt=p.one(cur,'select erp.bf_commercial_sku_at_v1(%s,%s)',target,stamp)
    assert before_src==f['a']['sku'] and before_tgt==a['sku'], ('EDGE_PRECONDITION',before_src,before_tgt)
    before_hpp=(p.report(cur,f['a']['sku'],stamp+timedelta(seconds=1))['groups'],
        p.report(cur,a['sku'],stamp+timedelta(seconds=1))['groups'])
    before_books=p.books(cur)
    before_stock=p.stock(cur,destination)
    def groups(at):
        if source_side:
            keep=p.bf.group(cur,[f['roots'][0],f['roots'][2]],at,sku=f['a']['sku'],
                gid=f['a']['id'],revision=1,settings=copy.deepcopy(f['a']['settings']))
            add=p.bf.group(cur,[f['roots'][3],f['roots'][1]],at,sku=f['z']['sku'],
                gid=f['z']['id'],revision=1,settings=copy.deepcopy(f['z']['settings']))
        else:
            keep=p.bf.group(cur,[target],at,sku=a['sku'],gid=a['id'],revision=1)
            keep.update(members=[],legacy_basis=[])
            add=p.bf.group(cur,[sibling,target],at,sku=z['sku'],gid=z['id'],revision=1)
        return [keep,add]
    at=f['when'](14,30)
    p.b.api.admin(cur)
    cur.execute('savepoint independent_edge_backdate')
    try:
        p.bf.save(cur,groups(at),at)
    except Exception as exc:
        cur.execute('rollback to savepoint independent_edge_backdate')
        cur.execute('release savepoint independent_edge_backdate')
        p.b.api.admin(cur)
        guard=str(exc).splitlines()[0][:500]
        after_doc=document()
        after_hpp=(p.report(cur,f['a']['sku'],stamp+timedelta(seconds=1))['groups'],
            p.report(cur,a['sku'],stamp+timedelta(seconds=1))['groups'])
        stable=(before_doc.get('source_sku')==after_doc.get('source_sku')
            and before_doc.get('target_sku')==after_doc.get('target_sku')
            and p.one(cur,'select erp.bf_commercial_sku_at_v1(%s,%s)',f['roots'][1],stamp)==before_src
            and p.one(cur,'select erp.bf_commercial_sku_at_v1(%s,%s)',target,stamp)==before_tgt
            and after_hpp==before_hpp and p.books(cur)==before_books
            and p.stock(cur,destination)==before_stock)
        future_ok=False
        if 'BF_TARIFF_HISTORY' in guard and stable:
            later=f['when'](16)
            cur.execute('savepoint independent_edge_future')
            try:
                p.bf.save(cur,groups(later),later)
                after_later=document()
                moved=p.one(cur,'select erp.bf_commercial_sku_at_v1(%s,%s)',
                    f['roots'][1] if source_side else target,f['when'](17))
                expected=f['z']['sku'] if source_side else z['sku']
                future_ok=(moved==expected
                    and after_later.get('source_sku')==before_doc.get('source_sku')
                    and after_later.get('target_sku')==before_doc.get('target_sku')
                    and p.books(cur)==before_books
                    and p.report(cur,f['a']['sku'],stamp+timedelta(seconds=1))['groups']==before_hpp[0]
                    and p.report(cur,a['sku'],stamp+timedelta(seconds=1))['groups']==before_hpp[1])
                cur.execute('release savepoint independent_edge_future')
            except Exception as future_exc:
                cur.execute('rollback to savepoint independent_edge_future')
                cur.execute('release savepoint independent_edge_future')
                return dict(status='INCOMPLETE',guard=guard,history_intact=stable,
                    forward_error=str(future_exc).splitlines()[0][:300])
        return dict(status='PASS' if 'BF_TARIFF_HISTORY' in guard and stable and future_ok else 'INCOMPLETE',
            conversion_id=posted['conversion_id'],guard=guard,history_intact=stable,
            later_move_ok=future_ok,reversed_doc=reversed_doc,source_side=source_side,
            destination_stock_pcs=before_stock)
    after_doc=document()
    changed=(before_doc.get('source_sku')!=after_doc.get('source_sku') if source_side
        else before_doc.get('target_sku')!=after_doc.get('target_sku'))
    cur.execute('rollback to savepoint independent_edge_backdate')
    cur.execute('release savepoint independent_edge_backdate')
    return dict(status='COUNTEREXAMPLE' if changed else 'INCOMPLETE',
        reason='Backdated edit accepted after recorded conversion',source_side=source_side,
        reversed_doc=reversed_doc,document_changed=changed)

def cases(cur,today):
    return [
        ('INDEPENDENT:SOURCE_AFTER_POSTED_CONVERSION',lambda:protected_conversion_edge(cur,today,source_side=True)),
        ('INDEPENDENT:TARGET_AFTER_REVERSED_CONVERSION',lambda:protected_conversion_edge(cur,today,reversed_doc=True)),
    ]
