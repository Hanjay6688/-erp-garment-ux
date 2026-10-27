
declare
  i erp.opening_balance_items%rowtype;
  v_price numeric(20,6);
  v_hpp numeric(20,6);
  v_asof timestamptz;
begin
  perform erp.require_internal();
  select * into i from erp.opening_balance_items where id=p_item_id for update;
  if i.id is null or i.balance_type<>'FINISHED_GOODS' then raise exception 'Opening FG item tidak ditemukan'; end if;

  -- Opening date is a business date, while versioned SKU identity is timestamped.
  -- Use the first valid instant for this SKU on that opening date so a same-day
  -- effective identity is not incorrectly treated as 'not yet existing at midnight'.
  v_asof:=erp.product_opening_physical_at(i.product_id,p_opening_date);

  if i.hpp_input_method='PRICE_PERCENT' then
    if i.hpp_percent_of_price is null or i.hpp_percent_of_price<=0 or i.hpp_percent_of_price>1000 then
      raise exception 'Persentase HPP dari harga jual wajib >0 dan masuk akal untuk opening FG';
    end if;
    v_price:=erp.resolve_product_price_at(i.product_id,v_asof);
    if v_price is null then
      raise exception 'Harga jual produk belum tersedia pada waktu opening %. Isi harga jual historis/cutover atau gunakan HPP manual.',v_asof;
    end if;
    v_hpp:=round(v_price*i.hpp_percent_of_price/100.0,6);
    update erp.opening_balance_items set reference_sell_price_snapshot=v_price,unit_cost_snapshot=v_hpp where id=i.id;
    return v_hpp;
  end if;

  v_hpp:=coalesce(i.unit_cost_snapshot,0);
  update erp.opening_balance_items set reference_sell_price_snapshot=null where id=i.id;
  return v_hpp;
end;
