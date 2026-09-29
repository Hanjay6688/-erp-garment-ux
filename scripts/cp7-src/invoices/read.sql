create function cp7_invoice.workspace(p_purchase uuid,p_offset integer,p_limit integer) returns jsonb
language plpgsql stable security invoker set search_path='' as $$
declare a jsonb;h erp.material_purchase_headers;lines jsonb;docs jsonb;total bigint;
begin
 a:=cp7_invoice.access_now();
 if p_purchase is null or p_offset is null or p_offset not between 0 and 1000000 or p_limit is null or p_limit not between 1 and 25 then raise exception 'CP7_INVOICE_QUERY';end if;
 select * into h from erp.material_purchase_headers where id=p_purchase;
 if not found then raise exception 'CP7_INVOICE_RECEIPT_NOT_FOUND';end if;
 if (select count(*) from erp.material_purchase_items where purchase_id=p_purchase)>100 then raise exception 'CP7_INVOICE_COMPLETE_DOCUMENT_REQUIRED';end if;
 select coalesce(jsonb_agg(jsonb_build_object('id',i.id,'material_id',i.material_id,'material_name',m.material_name,'unit_code',m.unit_code,
  'receipt_qty',i.qty::text,'estimate_unit_price',i.unit_price::text,'price_state',i.price_state,'invoice_match_state',i.invoice_match_state,
  'capacity',erp.material_purchase_invoice_capacity(i.id)::text,'invoiced_qty',erp.material_purchase_posted_invoice_qty(i.id)::text,
  'remaining_qty',case when i.invoice_match_state='DIRECT_FINAL' then '0' else (erp.material_purchase_invoice_capacity(i.id)-erp.material_purchase_posted_invoice_qty(i.id))::text end)
  order by i.id),'[]'::jsonb) into lines from erp.material_purchase_items i join erp.materials m on m.id=i.material_id where i.purchase_id=p_purchase;
 select count(*) into total from erp.material_supplier_invoices ih where exists(select 1 from erp.material_supplier_invoice_lines l join erp.material_purchase_items i on i.id=l.purchase_item_id where l.invoice_id=ih.id and i.purchase_id=p_purchase);
 -- Every returned invoice is complete, including lines from other receipts.
 -- Such a legacy multi-receipt document is readable, but the bounded single-
 -- receipt reverse command refuses it instead of undoing unseen allocations.
 if exists(select 1 from (select ih.id from erp.material_supplier_invoices ih where exists(select 1 from erp.material_supplier_invoice_lines l join erp.material_purchase_items i on i.id=l.purchase_item_id where l.invoice_id=ih.id and i.purchase_id=p_purchase)
  order by ih.received_at desc,ih.id limit p_limit offset p_offset) selected where (select count(*) from erp.material_supplier_invoice_lines where invoice_id=selected.id)>100) then raise exception 'CP7_INVOICE_COMPLETE_DOCUMENT_REQUIRED';end if;
 select coalesce(jsonb_agg(jsonb_build_object('id',ih.id,'number',ih.invoice_number,'invoice_date',ih.invoice_date,'received_at',ih.received_at,'due_date',ih.due_date,
  'status',ih.status,'row_version',ih.row_version::text,'notes',ih.notes,'line_count',(select count(*)::text from erp.material_supplier_invoice_lines where invoice_id=ih.id),
  'document_net_amount',(select sum(net_amount)::text from erp.material_supplier_invoice_lines where invoice_id=ih.id),
  'single_receipt',not exists(select 1 from erp.material_supplier_invoice_lines l join erp.material_purchase_items i on i.id=l.purchase_item_id where l.invoice_id=ih.id and i.purchase_id<>p_purchase),
  'lines',coalesce((select jsonb_agg(jsonb_build_object('id',l.id,'purchase_item_id',l.purchase_item_id,'purchase_id',i.purchase_id,'purchase_number',ph.purchase_number,
    'material_name',m.material_name,'unit_code',m.unit_code,'qty',l.qty_invoiced::text,'unit_price',l.unit_price::text,'discount',l.discount_amount::text,'net_amount',l.net_amount::text) order by l.id)
    from erp.material_supplier_invoice_lines l join erp.material_purchase_items i on i.id=l.purchase_item_id join erp.material_purchase_headers ph on ph.id=i.purchase_id join erp.materials m on m.id=i.material_id where l.invoice_id=ih.id),'[]'::jsonb)) order by ih.received_at desc,ih.id),'[]'::jsonb)
 into docs from (select x.* from erp.material_supplier_invoices x where exists(select 1 from erp.material_supplier_invoice_lines l join erp.material_purchase_items i on i.id=l.purchase_item_id where l.invoice_id=x.id and i.purchase_id=p_purchase)
  order by x.received_at desc,x.id limit p_limit offset p_offset) ih;
 return jsonb_build_object('contract_version','cp7.purchase-invoices.v1','read_at',statement_timestamp(),'purchase_id',p_purchase,'purchase_number',h.purchase_number,'purchase_status',h.status,
  'purchase_version',h.row_version::text,'supplier_id',h.supplier_id,'capabilities',jsonb_build_object('finalize',a->'finalize','reverse',a->'reverse'),
  'basis','INVOICE_DOCUMENTS_NOT_PAYMENT_OUTSTANDING','receipt_line_count',jsonb_array_length(lines)::text,'receipt_lines',lines,
  'page',jsonb_build_object('rows',docs,'total',total::text,'offset',p_offset,'limit',p_limit,'next_offset',case when p_offset+jsonb_array_length(docs)<total then p_offset+jsonb_array_length(docs) else null end));
end $$;
create function public.erp_cp7_get_purchase_invoices_v1(p_purchase uuid,p_offset integer,p_limit integer) returns jsonb
language sql stable security definer set search_path='' as $$select cp7_invoice.workspace(p_purchase,p_offset,p_limit)$$;
