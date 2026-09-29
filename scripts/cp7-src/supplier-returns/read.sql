create function cp7_supplier_return.location_qty(p_material uuid,p_roll uuid,p_location uuid) returns numeric
language sql stable security invoker set search_path='' as $$
 select case when p_location is null then null else coalesce(sum(qty_signed),0) end
 from erp.material_stock_movements where material_id=p_material and roll_id is not distinct from p_roll
 and location_id=p_location and physical_at<=statement_timestamp()
$$;
create function cp7_supplier_return.document(p_id uuid,p_purchase uuid,p_value boolean) returns jsonb
language sql stable security invoker set search_path='' as $$
 select jsonb_build_object('id',h.id,'number',h.return_number,'supplier_id',h.supplier_id,'location_id',h.location_id,
  'location_name',loc.location_name,'physical_at',h.physical_at,'status',h.status,'row_version',h.row_version::text,'reason',h.reason,
  'line_count',(select count(*)::text from erp.material_supplier_return_items where return_id=h.id),
  'single_receipt',not exists(select 1 from erp.material_supplier_return_items r left join erp.material_purchase_items i on i.id=r.purchase_item_id where r.return_id=h.id and i.purchase_id is distinct from p_purchase),
  'lines',(select coalesce(jsonb_agg(jsonb_build_object('id',r.id,'purchase_item_id',r.purchase_item_id,'purchase_id',i.purchase_id,'purchase_number',ph.purchase_number,
   'material_id',r.material_id,'material_name',m.material_name,'unit_code',m.unit_code,'roll_id',r.roll_id,'roll_number',mr.roll_number,'qty',r.qty::text,'notes',r.notes)
   ||case when p_value then jsonb_build_object('finance',jsonb_build_object('credit_unit_price',r.supplier_credit_unit_price::text,
    'ap_relief_qty',r.ap_relief_qty_snapshot::text,'grni_relief_qty',r.grni_relief_qty_snapshot::text,
    'ap_relief_amount',r.ap_relief_amount_snapshot::text,'grni_relief_amount',r.grni_relief_amount_snapshot::text)) else '{}'::jsonb end order by r.id),'[]'::jsonb)
   from erp.material_supplier_return_items r left join erp.material_purchase_items i on i.id=r.purchase_item_id
   left join erp.material_purchase_headers ph on ph.id=i.purchase_id join erp.materials m on m.id=r.material_id left join erp.material_rolls mr on mr.id=r.roll_id where r.return_id=h.id))
  ||case when p_value then jsonb_build_object('finance',jsonb_build_object('basis','SOURCE_VALUATION_SNAPSHOTS_NOT_AVAILABLE_CREDIT',
   'ap_relief_amount',(select case when bool_and(ap_relief_amount_snapshot is not null) then sum(ap_relief_amount_snapshot)::text end from erp.material_supplier_return_items where return_id=h.id),
   'grni_relief_amount',(select case when bool_and(grni_relief_amount_snapshot is not null) then sum(grni_relief_amount_snapshot)::text end from erp.material_supplier_return_items where return_id=h.id))) else '{}'::jsonb end
 from erp.material_supplier_returns h left join erp.locations loc on loc.id=h.location_id where h.id=p_id
$$;
create function cp7_supplier_return.workspace(p_purchase uuid,p_location uuid,p_offset integer,p_limit integer) returns jsonb
language plpgsql stable security invoker set search_path='' as $$
declare a jsonb;h erp.material_purchase_headers;items jsonb;docs jsonb;total bigint;selected_location jsonb;
begin
 a:=cp7_supplier_return.access_now();
 if p_purchase is null or p_offset is null or p_offset not between 0 and 1000000 or p_limit is null or p_limit not between 1 and 25 then raise exception 'CP7_RETURN_QUERY';end if;
 select * into h from erp.material_purchase_headers where id=p_purchase;if not found then raise exception 'CP7_RETURN_RECEIPT_NOT_FOUND';end if;
 if p_location is not null then
  select jsonb_build_object('id',l.id,'name',l.location_name,'available',l.is_active and l.location_type='RAW_MATERIAL_WAREHOUSE' and not exists(select 1 from erp.bc_accessory_zones_v1 z where z.location_id=l.id)) into selected_location from erp.locations l where l.id=p_location;
  if selected_location is null then raise exception 'CP7_RETURN_LOCATION_NOT_FOUND';end if;
 end if;
 if (select count(*) from erp.material_purchase_items where purchase_id=p_purchase)>100 or
  (select count(*) from erp.material_rolls r join erp.material_purchase_items i on i.id=r.purchase_item_id where i.purchase_id=p_purchase)>2000 then raise exception 'CP7_RETURN_COMPLETE_SOURCE_REQUIRED';end if;
 select coalesce(jsonb_agg(jsonb_build_object('id',i.id,'material_id',i.material_id,'material_name',m.material_name,'material_type',m.material_type,'material_active',m.is_active,'unit_code',m.unit_code,
  'receipt_qty',i.qty::text,'posted_return_qty',coalesce(q.qty,0)::text,'unreturned_qty',(i.qty-coalesce(q.qty,0))::text,
  'location_qty',case when m.material_type<>'FABRIC' then cp7_supplier_return.location_qty(i.material_id,null,p_location)::text end,
  'rolls',coalesce((select jsonb_agg(jsonb_build_object('id',r.id,'number',r.roll_number,'receipt_qty',r.original_qty::text,
    'location_qty',cp7_supplier_return.location_qty(i.material_id,r.id,p_location)::text) order by r.roll_number,r.id) from erp.material_rolls r where r.purchase_item_id=i.id),'[]'::jsonb)) order by i.id),'[]'::jsonb)
 into items from erp.material_purchase_items i join erp.materials m on m.id=i.material_id
 left join lateral(select sum(ri.qty) qty from erp.material_supplier_return_items ri join erp.material_supplier_returns rh on rh.id=ri.return_id where ri.purchase_item_id=i.id and rh.status='POSTED') q on true
 where i.purchase_id=p_purchase;
 select count(*) into total from erp.material_supplier_returns rh where exists(select 1 from erp.material_supplier_return_items r join erp.material_purchase_items i on i.id=r.purchase_item_id where r.return_id=rh.id and i.purchase_id=p_purchase);
 if exists(select 1 from (select rh.id from erp.material_supplier_returns rh where exists(select 1 from erp.material_supplier_return_items r join erp.material_purchase_items i on i.id=r.purchase_item_id where r.return_id=rh.id and i.purchase_id=p_purchase) order by rh.physical_at desc,rh.id limit p_limit offset p_offset) selected
  where (select count(*) from erp.material_supplier_return_items where return_id=selected.id)>100) then raise exception 'CP7_RETURN_COMPLETE_DOCUMENT_REQUIRED';end if;
 select coalesce(jsonb_agg(cp7_supplier_return.document(rh.id,p_purchase,(a->>'view_value')::boolean) order by rh.physical_at desc,rh.id),'[]'::jsonb) into docs
 from (select rh.* from erp.material_supplier_returns rh where exists(select 1 from erp.material_supplier_return_items r join erp.material_purchase_items i on i.id=r.purchase_item_id where r.return_id=rh.id and i.purchase_id=p_purchase) order by rh.physical_at desc,rh.id limit p_limit offset p_offset) rh;
 return jsonb_build_object('contract_version','cp7.supplier-returns.v1','read_at',statement_timestamp(),'purchase_id',p_purchase,'purchase_number',h.purchase_number,'purchase_status',h.status,'purchase_version',h.row_version::text,
  'supplier_id',h.supplier_id,'receipt_location_id',h.location_id,'selected_location',selected_location,'basis','CURRENT_POSTED_STOCK_AND_SOURCE_RETURN_DOCUMENTS',
  'financial_captured',a->'view_value','capabilities',jsonb_build_object('create',a->'create','post',a->'post','reverse',a->'reverse'),
  'source_line_count',jsonb_array_length(items)::text,'source_lines',items,
  'page',jsonb_build_object('rows',docs,'total',total::text,'offset',p_offset,'limit',p_limit,'next_offset',case when p_offset+jsonb_array_length(docs)<total then p_offset+jsonb_array_length(docs) else null end));
end $$;
create function public.erp_cp7_get_supplier_returns_v1(p_purchase uuid,p_location uuid,p_offset integer,p_limit integer) returns jsonb
language sql stable security definer set search_path='' as $$select cp7_supplier_return.workspace(p_purchase,p_location,p_offset,p_limit)$$;
