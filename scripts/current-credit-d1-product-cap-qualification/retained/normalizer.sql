CREATE FUNCTION erp.normalize_sales_return_item_from_allocation() RETURNS trigger
    LANGUAGE plpgsql
    SET search_path TO 'erp', 'public', 'pg_temp'
    AS $$
declare
  v_return_sale uuid;
  v_return_customer uuid;
  v_alloc_sale uuid;
  v_alloc_customer uuid;
  v_product uuid;
  v_lot uuid;
  v_hpp numeric(18,6);
  v_alloc_qty integer;
  v_sale_item_qty integer;
  v_sale_line_total numeric(24,6);
  v_max_refund numeric(24,6);
begin
  select sr.sale_id,sr.customer_id into v_return_sale,v_return_customer
  from erp.sales_returns sr where sr.id=new.return_id;
  if v_return_sale is null then raise exception 'Sales return must reference an original sale'; end if;

  select si.sale_id,sh.customer_id,si.product_id,ssa.lot_id,ssa.unit_hpp_snapshot,ssa.qty_pcs,si.qty_pcs,si.line_total
  into v_alloc_sale,v_alloc_customer,v_product,v_lot,v_hpp,v_alloc_qty,v_sale_item_qty,v_sale_line_total
  from erp.sale_stock_allocations ssa
  join erp.sales_items si on si.id=ssa.sale_item_id
  join erp.sales_headers sh on sh.id=si.sale_id
  where ssa.id=new.sale_stock_allocation_id;

  if v_alloc_sale is null then raise exception 'Original sale stock allocation not found'; end if;
  if v_alloc_sale<>v_return_sale then raise exception 'Return allocation does not belong to the selected original sale'; end if;
  if v_alloc_customer is distinct from v_return_customer then raise exception 'Return customer does not match original sale customer'; end if;
  if new.qty_pcs>v_alloc_qty then raise exception 'Return qty % exceeds qty % sold from this lot allocation',new.qty_pcs,v_alloc_qty; end if;
  if not exists (select 1 from erp.locations l where l.id=new.location_id and l.is_active=true and l.location_type='FG_WAREHOUSE') then
    raise exception 'Sales return destination must be an active FG warehouse';
  end if;

  v_max_refund:=case when v_sale_item_qty>0 then (v_sale_line_total/v_sale_item_qty)*new.qty_pcs else 0 end;
  if new.refund_amount>v_max_refund+0.01 then
    raise exception 'Refund amount % exceeds original net sales value % for returned qty',new.refund_amount,round(v_max_refund,2);
  end if;

  select coalesce(ch.hpp_per_pcs,v_hpp) into v_hpp
  from (select 1) x
  left join erp.v_current_hpp ch on ch.lot_id=v_lot;

  new.product_id:=v_product;
  new.lot_id:=v_lot;
  new.unit_hpp_snapshot:=v_hpp;
  return new;
end;
$$;