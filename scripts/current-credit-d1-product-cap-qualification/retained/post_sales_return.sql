CREATE FUNCTION erp.post_sales_return(p_return_id uuid) RETURNS void
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'erp', 'public'
    AS $$
declare
  h erp.sales_returns%rowtype;
  s erp.sales_headers%rowtype;
  r record;
  v_refund numeric(24,6):=0;
  v_sold_qty integer;
  v_prior_returned integer;
  v_current_return integer;
  v_product_sale_value numeric(24,6);
  v_prior_product_refund numeric(24,6);
  v_current_product_refund numeric(24,6);
  v_original_hpp numeric(18,6);
  v_unit_hpp numeric(18,6);
  v_net_total numeric(20,2);
  v_paid numeric(20,2);
  v_delta_cogs numeric(24,6);
  v_delta_fg numeric(24,6);
  v_delta_other numeric(24,6);
  v_target_hpp numeric(24,6);
  v_target_other numeric(24,6);
  v_book_hpp numeric(24,6);
  v_book_other numeric(24,6);
  v_lines jsonb:='[]'::jsonb;
begin
  perform erp.require_internal();
  perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
  select * into h from erp.sales_returns where id=p_return_id for update;
  if h.id is null or h.status<>'DRAFT' then raise exception 'Sales return must be DRAFT'; end if;
  if h.sale_id is null then raise exception 'Native sales return must reference the original sale'; end if;
  select * into s from erp.sales_headers where id=h.sale_id for update;
  if s.id is null or s.status not in('POSTED','PARTIAL_PAID','PAID') then raise exception 'Original sale must be active/posted'; end if;
  if s.customer_id is distinct from h.customer_id then raise exception 'Sales return customer does not match original sale customer'; end if;
  if not exists(select 1 from erp.sales_return_items where return_id=h.id) then raise exception 'Sales return has no lines'; end if;

  for r in
    select distinct fl.product_id
    from erp.sales_return_items i
    join erp.fg_lots fl on fl.id=i.lot_id
    where i.return_id=h.id and fl.po_id is null
    order by fl.product_id
  loop
    perform erp.assert_non_po_product_hpp_target_book_v2620f(r.product_id);
  end loop;

  for r in
    select * from erp.sales_return_items where return_id=h.id
    order by product_id,location_id,quality_grade,lot_id,id
  loop
    if r.lot_id is null then raise exception 'Sales return line requires original FG lot'; end if;
    if not exists(select 1 from erp.fg_lots fl where fl.id=r.lot_id and fl.product_id=r.product_id) then raise exception 'Sales return lot does not belong to selected product'; end if;

    insert into erp.fg_inventory_balances(product_id,location_id,quality_grade,cached_qty_pcs)
    values(r.product_id,r.location_id,r.quality_grade,0)
    on conflict(product_id,location_id,quality_grade) do nothing;
    perform 1 from erp.fg_inventory_balances
    where product_id=r.product_id and location_id=r.location_id and quality_grade=r.quality_grade
    for update;
    perform 1 from erp.fg_lots where id=r.lot_id for update;

    select coalesce(sum(a.qty_pcs),0)::integer,
           case when coalesce(sum(a.qty_pcs),0)>0 then sum(a.qty_pcs*a.unit_hpp_snapshot)/sum(a.qty_pcs) else null end
    into v_sold_qty,v_original_hpp
    from erp.sale_stock_allocations a
    join erp.sales_items si on si.id=a.sale_item_id
    where si.sale_id=h.sale_id and si.product_id=r.product_id and a.lot_id=r.lot_id and a.location_id=r.location_id;
    if v_sold_qty<=0 or v_original_hpp is null then raise exception 'Returned product/lot/location was not allocated on the original sale'; end if;

    v_unit_hpp:=coalesce(erp.lock_current_hpp_per_pcs(r.lot_id),v_original_hpp);
    select coalesce(sum(sri.qty_pcs),0)::integer into v_prior_returned
    from erp.sales_return_items sri join erp.sales_returns sr on sr.id=sri.return_id
    where sr.sale_id=h.sale_id and sr.id<>h.id and sr.status='POSTED'
      and sri.product_id=r.product_id and sri.lot_id=r.lot_id and sri.location_id=r.location_id;
    select coalesce(sum(sri.qty_pcs),0)::integer into v_current_return
    from erp.sales_return_items sri
    where sri.return_id=h.id and sri.product_id=r.product_id and sri.lot_id=r.lot_id and sri.location_id=r.location_id;
    if v_prior_returned+v_current_return>v_sold_qty then
      raise exception 'Sales return exceeds quantity originally sold for this lot/location. Sold %, prior returned %, current return %',v_sold_qty,v_prior_returned,v_current_return;
    end if;

    select coalesce(sum(si.line_total),0) into v_product_sale_value
    from erp.sales_items si where si.sale_id=h.sale_id and si.product_id=r.product_id;
    select coalesce(sum(sri.refund_amount),0) into v_prior_product_refund
    from erp.sales_return_items sri join erp.sales_returns sr on sr.id=sri.return_id
    where sr.sale_id=h.sale_id and sr.id<>h.id and sr.status='POSTED' and sri.product_id=r.product_id;
    select coalesce(sum(sri.refund_amount),0) into v_current_product_refund
    from erp.sales_return_items sri where sri.return_id=h.id and sri.product_id=r.product_id;
    if v_prior_product_refund+v_current_product_refund>v_product_sale_value then
      raise exception 'Refund exceeds original net sale value for product. Sold value %, prior refund %, current refund %',v_product_sale_value,v_prior_product_refund,v_current_product_refund;
    end if;

    update erp.sales_return_items set unit_hpp_snapshot=v_unit_hpp where id=r.id;
    perform erp.post_fg_movement(r.product_id,r.lot_id,r.location_id,r.quality_grade,
      'SALE_RETURN',r.qty_pcs,v_unit_hpp,h.customer_id,'SALES_RETURN_ITEM',r.id,
      h.physical_at,'Customer sales return',false);
    v_refund:=v_refund+r.refund_amount;
  end loop;

  select greatest(erp.sale_net_total(h.sale_id)-v_refund,0)::numeric(20,2) into v_net_total;
  select coalesce(sum(sp.amount),0)::numeric(20,2) into v_paid
  from erp.sales_payments sp where sp.sale_id=h.sale_id and sp.status='POSTED';
  if v_paid>v_net_total then
    raise exception 'Retur ini membuat pembayaran customer melebihi nilai penjualan tersisa. Nilai setelah retur %, sudah dibayar %. Reverse/koreksi pembayaran customer dulu agar kelebihan bayar tidak hilang dari pembukuan.',v_net_total,v_paid;
  end if;

  update erp.sales_returns set status='POSTED' where id=h.id;
  if abs(v_refund)>0.005 then
    v_lines:=v_lines||jsonb_build_array(
      jsonb_build_object('mapping_key','SALES_REVENUE','debit',round(v_refund,2),'credit',0,'customer_id',h.customer_id),
      jsonb_build_object('mapping_key','AR_CUSTOMER','debit',0,'credit',round(v_refund,2),'customer_id',h.customer_id));
  end if;

  for r in
    select distinct fl.product_id
    from erp.sales_return_items i
    join erp.fg_lots fl on fl.id=i.lot_id
    where i.return_id=h.id and fl.po_id is null
    order by fl.product_id
  loop
    select round(t.fg_value-b.fg_value,2),
      round(t.cogs_value-b.cogs_value,2),
      round(t.other_out_value-b.other_out_value,2)
    into v_delta_fg,v_delta_cogs,v_delta_other
    from erp.compute_non_po_product_hpp_targets_v2620f(r.product_id) t
    cross join lateral erp.compute_non_po_product_hpp_book_v2620f(r.product_id) b;
    if abs(v_delta_fg+v_delta_cogs+v_delta_other)>0.005 then
      raise exception 'Return non-PO HPP delta does not conserve source value for product %: fg %, cogs %, other %',
        r.product_id,v_delta_fg,v_delta_cogs,v_delta_other;
    end if;
    if abs(v_delta_fg)>0.005 then
      v_lines:=v_lines||jsonb_build_array(case when v_delta_fg>0
        then jsonb_build_object('mapping_key','FG_INVENTORY','debit',v_delta_fg,
          'credit',0,'customer_id',h.customer_id,'product_id',r.product_id)
        else jsonb_build_object('mapping_key','FG_INVENTORY','debit',0,
          'credit',abs(v_delta_fg),'customer_id',h.customer_id,
          'product_id',r.product_id) end);
    end if;
    if abs(v_delta_cogs)>0.005 then
      v_lines:=v_lines||jsonb_build_array(case when v_delta_cogs>0
        then jsonb_build_object('mapping_key','COGS','debit',v_delta_cogs,
          'credit',0,'customer_id',h.customer_id,'product_id',r.product_id)
        else jsonb_build_object('mapping_key','COGS','debit',0,
          'credit',abs(v_delta_cogs),'customer_id',h.customer_id,
          'product_id',r.product_id) end);
    end if;
    if abs(v_delta_other)>0.005 then
      v_lines:=v_lines||jsonb_build_array(case when v_delta_other>0
        then jsonb_build_object('mapping_key','OTHER_EXPENSE','debit',v_delta_other,
          'credit',0,'customer_id',h.customer_id,'product_id',r.product_id)
        else jsonb_build_object('mapping_key','OTHER_INCOME','debit',0,
          'credit',abs(v_delta_other),'customer_id',h.customer_id,
          'product_id',r.product_id) end);
    end if;
  end loop;

  for r in
    select distinct fl.po_id
    from erp.sales_return_items i join erp.fg_lots fl on fl.id=i.lot_id
    where i.return_id=h.id and fl.po_id is not null order by fl.po_id
  loop
    perform erp.refresh_po_hpp_gl_baseline(r.po_id);
    select
      round(coalesce(t.cogs_value,0),2)-st.cogs_value,
      round(coalesce(t.fg_value,0),2)-st.fg_value,
      (round(coalesce(t.hpp_total_cost,0),2)-round(coalesce(t.fg_value,0),2)
        -round(coalesce(t.cogs_value,0),2))-st.other_out_value,
      round(coalesce(t.hpp_total_cost,0),2),
      round(coalesce(t.hpp_total_cost,0),2)-round(coalesce(t.fg_value,0),2)-round(coalesce(t.cogs_value,0),2),
      st.hpp_total_cost,st.other_out_value
    into v_delta_cogs,v_delta_fg,v_delta_other,
      v_target_hpp,v_target_other,v_book_hpp,v_book_other
    from erp.po_hpp_gl_state st
    cross join lateral erp.compute_po_hpp_gl_targets_v2620d(r.po_id) t
    where st.po_id=r.po_id for update of st;
    if v_delta_cogs>0.005 or v_delta_fg<-0.005
       or abs(v_delta_cogs+v_delta_fg+v_delta_other)>0.005
       or v_target_hpp is distinct from v_book_hpp then
      raise exception 'Sales-return cumulative HPP target does not conserve PO value %. dc %, df %, do %, target/book hpp %/%',
        r.po_id,v_delta_cogs,v_delta_fg,v_delta_other,v_target_hpp,v_book_hpp;
    end if;
    if abs(v_delta_cogs)>0.005 then
      v_lines:=v_lines||jsonb_build_array(case when v_delta_cogs>0 then
        jsonb_build_object('mapping_key','COGS','debit',v_delta_cogs,'credit',0,
          'customer_id',h.customer_id,'po_id',r.po_id)
        else jsonb_build_object('mapping_key','COGS','debit',0,'credit',abs(v_delta_cogs),
          'customer_id',h.customer_id,'po_id',r.po_id) end);
    end if;
    if abs(v_delta_fg)>0.005 then
      v_lines:=v_lines||jsonb_build_array(case when v_delta_fg>0 then
        jsonb_build_object('mapping_key','FG_INVENTORY','debit',v_delta_fg,'credit',0,
          'customer_id',h.customer_id,'po_id',r.po_id)
        else jsonb_build_object('mapping_key','FG_INVENTORY','debit',0,'credit',abs(v_delta_fg),
          'customer_id',h.customer_id,'po_id',r.po_id) end);
    end if;
    if abs(v_delta_other)>0.005 then
      v_lines:=v_lines||jsonb_build_array(case when v_delta_other>0 then
        jsonb_build_object('mapping_key','OTHER_EXPENSE','debit',v_delta_other,'credit',0,
          'customer_id',h.customer_id,'po_id',r.po_id)
        else jsonb_build_object('mapping_key','OTHER_INCOME','debit',0,'credit',abs(v_delta_other),
          'customer_id',h.customer_id,'po_id',r.po_id) end);
    end if;
  end loop;
  if jsonb_array_length(v_lines)>=2 then
    perform erp.post_journal('SALES_RETURN',h.id,h.physical_at::date,
      'Sales return from customer · cumulative exact HPP target',v_lines);
  end if;

  for r in
    select distinct fl.product_id
    from erp.sales_return_items i
    join erp.fg_lots fl on fl.id=i.lot_id
    where i.return_id=h.id and fl.po_id is null
    order by fl.product_id
  loop
    perform erp.assert_non_po_product_hpp_target_book_v2620f(r.product_id);
  end loop;

  update erp.sales_headers
  set status=case when v_paid=v_net_total then 'PAID' when v_paid>0 and v_paid<v_net_total then 'PARTIAL_PAID' else 'POSTED' end
  where id=h.sale_id;
  for r in
    select distinct fl.po_id
    from erp.sales_return_items i join erp.fg_lots fl on fl.id=i.lot_id
    where i.return_id=h.id and fl.po_id is not null order by fl.po_id
  loop
    perform erp.refresh_po_hpp_gl_baseline(r.po_id);
    perform erp.assert_po_hpp_target_book_v2620e(r.po_id);
  end loop;
end
$$;