-- Exact source navigation only. No stock, money, cost, or document writer.
create role cp7_transaction_source_read nologin noinherit nosuperuser nocreatedb nocreaterole noreplication bypassrls;
create schema cp7_transaction_source authorization cp7_transaction_source_read;
revoke all on schema cp7_transaction_source from public,anon,authenticated,service_role;
grant usage on schema erp,auth to cp7_transaction_source_read;
grant execute on function auth.uid(),auth.jwt(),erp.get_my_access_v1(),erp.has_permission(text) to cp7_transaction_source_read;
grant select on erp.material_purchase_headers,erp.material_purchase_items,erp.material_rolls,
 erp.material_supplier_invoices,erp.material_supplier_invoice_lines,erp.supplier_payments,
 erp.material_transfers,erp.material_transfer_items,erp.material_adjustments,erp.material_adjustment_items,
 erp.fg_adjustments,erp.fg_adjustment_items,erp.sales_headers,erp.sales_items,erp.sales_payments,
 erp.sales_returns,erp.sales_return_items,erp.misc_finance_transactions,erp.journal_entries
 to cp7_transaction_source_read;

create function cp7_transaction_source.authority()returns jsonb
language plpgsql stable security invoker set search_path=''as $$
declare a jsonb;
begin
 if auth.uid()is null or coalesce(auth.jwt()->>'role','')<>'authenticated'then
  raise exception using errcode='42501',message='CP7_TRANSACTION_SOURCE_ACCESS_DENIED';end if;
 a:=erp.get_my_access_v1();
 -- Native active custom roles use their own role_code. Their current domain
 -- permissions below are authoritative for reads; a STAFF-code whitelist
 -- would reject an otherwise authorized owning workspace. Financial owner
 -- restrictions remain at their specific domains and never grant a writer.
 if a->'allowed'is distinct from'true'::jsonb then
  raise exception using errcode='42501',message='CP7_TRANSACTION_SOURCE_ACCESS_DENIED';end if;
 return a;
end $$;

create function cp7_transaction_source.resolve(p jsonb)returns jsonb
language plpgsql stable security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb;kind text;ident uuid;domain text;route text;permission text;
 parent_id uuid;doc jsonb;focus jsonb:='null';hops integer:=0;visited uuid[]:='{}';label text;focus_offset bigint;
begin
 if jsonb_typeof(p)is distinct from'object'or not(p?&array['source_type','source_id'])
  or(select count(*)from jsonb_object_keys(p))<>2 or jsonb_typeof(p->'source_type')is distinct from'string'
  or jsonb_typeof(p->'source_id')is distinct from'string'or p->>'source_type'!~'^[A-Z][A-Z0-9_]{0,79}$'
  or p->>'source_id'!~'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'then
  raise exception using errcode='22023',message='CP7_TRANSACTION_SOURCE_FIELDS';end if;
 a:=cp7_transaction_source.authority();kind:=p->>'source_type';ident:=(p->>'source_id')::uuid;
 -- Journal inverses point at journals, not at business documents. Follow
 -- only actual immutable journal links; never guess a document from a UUID.
 while kind='JOURNAL_REVERSAL'loop
  if not erp.has_permission('finance.journal.view')or a->'profile'->>'role_code'not in('OWNER','ADMIN')then
   raise exception using errcode='42501',message='CP7_TRANSACTION_SOURCE_ACCESS_DENIED';end if;
  hops:=hops+1;
  if hops>16 or ident=any(visited)then raise exception 'CP7_TRANSACTION_SOURCE_CHAIN_INVALID';end if;
  visited:=array_append(visited,ident);
  select j.source_type,j.source_id into kind,ident from erp.journal_entries j where j.id=ident;
  if not found or ident is null then raise exception 'CP7_TRANSACTION_SOURCE_UNAVAILABLE';end if;
 end loop;
 case
 when kind in('MATERIAL_PURCHASE','MATERIAL_PURCHASE_GRNI_RECLASS','MATERIAL_PURCHASE_REVERSAL','MATERIAL_PURCHASE_ITEM','MATERIAL_PURCHASE_ROLL','MATERIAL_SUPPLIER_INVOICE','MATERIAL_SUPPLIER_INVOICE_LINE','SUPPLIER_PAYMENT')then
  domain:='RECEIPT';route:='procurement';permission:='warehouse.procurement.view';
 when kind in('MATERIAL_TRANSFER','MATERIAL_TRANSFER_ITEM')then
  domain:='MATERIAL_TRANSFER';route:='materials-rolls';permission:='warehouse.material.view';
 when kind in('MATERIAL_ADJUSTMENT','MATERIAL_ADJUSTMENT_ITEM')then
  domain:='MATERIAL_COUNT';route:='stock-adjustment';permission:='warehouse.material.view';
 when kind in('FG_ADJUSTMENT','FG_ADJUSTMENT_ITEM')then
  domain:='FG_ADJUSTMENT';route:='stock-adjustment';permission:='warehouse.fg.view';
 when kind in('SALE','SALE_ITEM','SALES_ITEM','SALES_PAYMENT','SALES_RETURN','SALES_RETURN_ITEM')then
  domain:='SALE';route:=case when kind='SALES_PAYMENT'then'sales-payments'when kind in('SALES_RETURN','SALES_RETURN_ITEM')then'sales-returns'else'sales-invoice'end;
  permission:='sales.invoice.view';
 when kind='MISC_FINANCE'then
  domain:='MISC_FINANCE';route:='finance-journal';permission:='finance.journal.view';
 else
  return jsonb_build_object('contract_version','cp7.transaction-source.v1','actor_scope_id',auth.uid(),
   'source',p,'status','UNSUPPORTED_SOURCE','document',null,'read_at',statement_timestamp(),'business_DML',false);
 end case;
 -- Check the owner's current view permission before resolving child IDs or
 -- returning any Native document number/version. No finance is returned.
 if not erp.has_permission(permission)or(domain in('MATERIAL_COUNT','FG_ADJUSTMENT')and not erp.has_permission('warehouse.stock.adjust'))
  or(kind in('MATERIAL_SUPPLIER_INVOICE','MATERIAL_SUPPLIER_INVOICE_LINE','SUPPLIER_PAYMENT')and not erp.has_permission('finance.ap.view'))
  or(domain='MISC_FINANCE'and(not erp.has_permission('finance.cash.view')or a->'profile'->>'role_code'not in('OWNER','ADMIN')))
  or(kind='SALES_PAYMENT'and(not erp.has_permission('sales.payment.view')or not erp.has_permission('finance.ar.view')))
  or(kind in('SALES_RETURN','SALES_RETURN_ITEM')and(not erp.has_permission('sales.return.view')or not erp.has_permission('finance.ar.view')))then
  raise exception using errcode='42501',message='CP7_TRANSACTION_SOURCE_ACCESS_DENIED';end if;
 parent_id:=ident;
 case kind
 when'MATERIAL_PURCHASE_ITEM'then select i.purchase_id into parent_id from erp.material_purchase_items i where i.id=ident;
 when'MATERIAL_PURCHASE_ROLL'then select i.purchase_id into parent_id from erp.material_rolls r join erp.material_purchase_items i on i.id=r.purchase_item_id where r.id=ident;
 when'MATERIAL_SUPPLIER_INVOICE'then
  select i.purchase_id into parent_id from erp.material_supplier_invoice_lines l join erp.material_purchase_items i on i.id=l.purchase_item_id where l.invoice_id=ident order by i.purchase_id,l.id limit 1;
  focus:=jsonb_build_object('kind','PURCHASE_INVOICE','id',ident);
 when'MATERIAL_SUPPLIER_INVOICE_LINE'then
  select i.purchase_id,jsonb_build_object('kind','PURCHASE_INVOICE','id',l.invoice_id)into parent_id,focus
   from erp.material_supplier_invoice_lines l join erp.material_purchase_items i on i.id=l.purchase_item_id where l.id=ident;
 when'SUPPLIER_PAYMENT'then select s.purchase_id into parent_id from erp.supplier_payments s where s.id=ident;
 when'MATERIAL_TRANSFER_ITEM'then select i.transfer_id into parent_id from erp.material_transfer_items i where i.id=ident;
 when'MATERIAL_ADJUSTMENT_ITEM'then select i.adjustment_id into parent_id from erp.material_adjustment_items i where i.id=ident;
 when'FG_ADJUSTMENT_ITEM'then select i.adjustment_id into parent_id from erp.fg_adjustment_items i where i.id=ident;
 when'SALE_ITEM','SALES_ITEM'then select i.sale_id into parent_id from erp.sales_items i where i.id=ident;
 when'SALES_PAYMENT'then
  select i.sale_id into parent_id from erp.sales_payments i where i.id=ident;
  focus:=jsonb_build_object('kind','SALES_PAYMENT','id',ident);
 when'SALES_RETURN'then
  select i.sale_id into parent_id from erp.sales_returns i where i.id=ident;
  focus:=jsonb_build_object('kind','SALES_RETURN','id',ident);
 when'SALES_RETURN_ITEM'then
  select i.sale_id,jsonb_build_object('kind','SALES_RETURN','id',i.id)into parent_id,focus
   from erp.sales_return_items l join erp.sales_returns i on i.id=l.return_id where l.id=ident;
 else null;
 end case;
 if parent_id is null then raise exception 'CP7_TRANSACTION_SOURCE_UNAVAILABLE';end if;
 case domain
 when'RECEIPT'then select to_jsonb(h),h.purchase_number into doc,label from erp.material_purchase_headers h where h.id=parent_id;
 when'MATERIAL_TRANSFER'then select to_jsonb(h),h.transfer_number into doc,label from erp.material_transfers h where h.id=parent_id;
 when'MATERIAL_COUNT'then select to_jsonb(h),h.adjustment_number into doc,label from erp.material_adjustments h where h.id=parent_id;
 when'FG_ADJUSTMENT'then select to_jsonb(h),h.adjustment_number into doc,label from erp.fg_adjustments h where h.id=parent_id;
 when'SALE'then select to_jsonb(h),h.sale_number into doc,label from erp.sales_headers h where h.id=parent_id;
 when'MISC_FINANCE'then select to_jsonb(h),h.transaction_number into doc,label from erp.misc_finance_transactions h where h.id=parent_id;
 end case;
 if doc is null or coalesce(label,'')=''then raise exception 'CP7_TRANSACTION_SOURCE_UNAVAILABLE';end if;
 -- Position the exact child within its owning reader's unchanged 25-row
 -- ordering. The owner re-reads the page and checks identity; no client scan.
 if focus is not null and focus<>'null'::jsonb then
  case focus->>'kind'
  when'SALES_PAYMENT'then
   select ((n-1)/25)*25 into focus_offset from(select id,row_number()over(order by payment_date desc,id)n from erp.sales_payments where sale_id=parent_id)x where id=(focus->>'id')::uuid;
  when'SALES_RETURN'then
   select ((n-1)/25)*25 into focus_offset from(select id,row_number()over(order by physical_at desc,id)n from erp.sales_returns where sale_id=parent_id)x where id=(focus->>'id')::uuid;
  when'PURCHASE_INVOICE'then
   select ((n-1)/25)*25 into focus_offset from(select ih.id,row_number()over(order by ih.received_at desc,ih.id)n from erp.material_supplier_invoices ih where exists(select 1 from erp.material_supplier_invoice_lines l join erp.material_purchase_items i on i.id=l.purchase_item_id where l.invoice_id=ih.id and i.purchase_id=parent_id))x where id=(focus->>'id')::uuid;
  end case;
  if focus_offset is null or focus_offset>1000000 then raise exception 'CP7_TRANSACTION_SOURCE_FOCUS_UNAVAILABLE';end if;
  focus:=focus||jsonb_build_object('page_offset',focus_offset);
 end if;
 if cp7_transaction_source.authority()is distinct from a or not erp.has_permission(permission)then
  raise exception using errcode='42501',message='CP7_TRANSACTION_SOURCE_ACCESS_CHANGED';end if;
 return jsonb_build_object('contract_version','cp7.transaction-source.v1','actor_scope_id',auth.uid(),'source',p,
  'status','AVAILABLE','document',jsonb_build_object('domain',domain,'route',route,'id',parent_id,'number',label,
   'status',doc->'status','revision',doc->>'row_version','focus',focus),
  'read_at',statement_timestamp(),'business_DML',false);
end $$;

alter function cp7_transaction_source.authority()owner to cp7_transaction_source_read;
alter function cp7_transaction_source.resolve(jsonb)owner to cp7_transaction_source_read;
revoke all on function cp7_transaction_source.authority(),cp7_transaction_source.resolve(jsonb)from public,anon,authenticated,service_role;
grant create on schema public to cp7_transaction_source_read;
create function public.erp_cp7_resolve_transaction_source_v1(p_source jsonb)returns jsonb
language sql stable security definer set search_path=''as $$select cp7_transaction_source.resolve(p_source)$$;
alter function public.erp_cp7_resolve_transaction_source_v1(jsonb)owner to cp7_transaction_source_read;
revoke create on schema public from cp7_transaction_source_read;
revoke all on function public.erp_cp7_resolve_transaction_source_v1(jsonb)from public,anon,authenticated,service_role;
grant execute on function public.erp_cp7_resolve_transaction_source_v1(jsonb)to authenticated;
