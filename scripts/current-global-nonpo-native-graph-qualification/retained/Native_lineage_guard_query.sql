-- Exact Native final EXISTS query body; SELECT EXISTS envelope only. No writer execution.
select exists(
    with recursive reachable(lot_id,path,depth) as(
      select fl.id,array[fl.id],0
      from erp.fg_lots fl
      where fl.po_id is null and fl.lot_origin not in('CONVERSION','VOIDED_PRODUCTION')
      union all
      select a.destination_lot_id,x.path||a.destination_lot_id,x.depth+1
      from reachable x
      join erp.product_conversion_allocations a on a.source_lot_id=x.lot_id
      join erp.product_conversions c on c.id=a.conversion_id and c.status='POSTED'
      where a.destination_lot_id is not null
        and not a.destination_lot_id=any(x.path) and x.depth<128
    )
    select 1
    from erp.product_conversion_allocations a
    join erp.product_conversions c on c.id=a.conversion_id and c.status='POSTED'
    join erp.fg_lots s on s.id=a.source_lot_id and s.po_id is null
    join erp.fg_lots d on d.id=a.destination_lot_id
    where not exists(select 1 from reachable x where x.lot_id=a.destination_lot_id)
       or not erp.be_nonpo_admitted_v1(c.id) or d.po_id is distinct from s.po_id
       or d.lot_origin<>'CONVERSION' or d.source_lot_id is distinct from s.id
       or a.qty_pcs<=0
) as native_guard_refuses;
