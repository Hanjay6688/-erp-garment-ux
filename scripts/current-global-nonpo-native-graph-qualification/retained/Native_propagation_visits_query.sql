-- Exact Native ordered visit query; no loop/writer executed.
    with recursive rooted(lot_id,depth,path) as(
      select fl.id,0,array[fl.id]
      from erp.fg_lots fl
      where fl.po_id is null and fl.lot_origin not in('CONVERSION','VOIDED_PRODUCTION')
      union all
      select a.destination_lot_id,x.depth+1,x.path||a.destination_lot_id
      from rooted x
      join erp.product_conversion_allocations a on a.source_lot_id=x.lot_id
      join erp.product_conversions c on c.id=a.conversion_id and c.status='POSTED'
      where a.destination_lot_id is not null
        and not a.destination_lot_id=any(x.path)
        and x.depth<128
    )
    select a.*,x.depth source_depth
    from rooted x
    join erp.product_conversion_allocations a on a.source_lot_id=x.lot_id
    join erp.product_conversions c on c.id=a.conversion_id and c.status='POSTED'
    where a.destination_lot_id is not null
    order by x.depth,a.id;
