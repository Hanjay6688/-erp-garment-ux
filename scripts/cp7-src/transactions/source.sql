-- Exact source navigation only. No stock, money, cost, or document writer.
create role cp7_transaction_source_read nologin noinherit nosuperuser nocreatedb nocreaterole noreplication bypassrls;
create schema cp7_transaction_source authorization cp7_transaction_source_read;
revoke all on schema cp7_transaction_source from public,anon,authenticated,service_role;
grant usage on schema erp,auth to cp7_transaction_source_read;
grant usage on schema cp7_installment to cp7_transaction_source_read;
grant select on cp7_installment.payments to cp7_transaction_source_read;
grant usage on schema cp7_payment_correction to cp7_transaction_source_read;
grant select on cp7_payment_correction.links to cp7_transaction_source_read;
grant usage on schema cp7_supplier_payment_correction to cp7_transaction_source_read;
grant select on cp7_supplier_payment_correction.links to cp7_transaction_source_read;
grant usage on schema cp7_sales_return_correction to cp7_transaction_source_read;
grant select on cp7_sales_return_correction.links,cp7_sales_return_correction.journal_restatements to cp7_transaction_source_read;
grant execute on function auth.uid(),auth.jwt(),erp.get_my_access_v1(),erp.has_permission(text) to cp7_transaction_source_read;
grant select on erp.material_purchase_headers,erp.material_purchase_items,erp.material_rolls,
 erp.material_supplier_invoices,erp.material_supplier_invoice_lines,erp.supplier_payments,
 erp.material_transfers,erp.material_transfer_items,erp.material_adjustments,erp.material_adjustment_items,
 erp.fg_adjustments,erp.fg_adjustment_items,erp.sales_headers,erp.sales_items,erp.sales_payments,
 erp.sales_returns,erp.sales_return_items,erp.misc_finance_transactions,erp.journal_entries,erp.payroll_settlements,
 erp.contractor_material_issues,erp.contractor_material_issue_items,erp.materials,erp.uom_definitions,
 erp.bs_cases,erp.rework_orders,erp.qc_inspections,erp.qc_inspection_items,erp.fg_stock_movements,
 erp.laundry_deliveries,erp.laundry_delivery_lines,erp.laundry_delivery_batch_size_lines,
 erp.laundry_receipts,erp.laundry_receipt_lines,erp.laundry_receipt_batch_size_lines,
 erp.cutting_groups,erp.production_orders,erp.product_models
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
 -- Economic-date entries belong to the exact ordinary payment correction.
 -- Require both the immutable correction FK and the actual Native journal;
 -- an arbitrary payment UUID cannot masquerade as a correction source.
 if kind in('PAYMENT_CORRECTION_TIME_NEUTRAL','PAYMENT_CORRECTION_EFFECTIVE')then
  if not erp.has_permission('finance.journal.view')or a->'profile'->>'role_code'not in('OWNER','ADMIN')then
   raise exception using errcode='42501',message='CP7_TRANSACTION_SOURCE_ACCESS_DENIED';end if;
  if not exists(select 1 from cp7_payment_correction.links l join erp.journal_entries j
   on j.id=case when kind='PAYMENT_CORRECTION_TIME_NEUTRAL'then l.time_neutral_id else l.effective_inverse_id end
   where l.original_id=ident and j.source_type=kind and j.source_id=ident and j.status='POSTED')then
   raise exception 'CP7_TRANSACTION_SOURCE_UNAVAILABLE';end if;
  kind:='SALES_PAYMENT';
 end if;
 if kind in('SUPPLIER_PAYMENT_CORRECTION_TIME_NEUTRAL','SUPPLIER_PAYMENT_CORRECTION_EFFECTIVE')then
  if not erp.has_permission('finance.journal.view')or a->'profile'->>'role_code'not in('OWNER','ADMIN')then
   raise exception using errcode='42501',message='CP7_TRANSACTION_SOURCE_ACCESS_DENIED';end if;
  if not exists(select 1 from cp7_supplier_payment_correction.links l join erp.journal_entries j
   on j.id=case when kind='SUPPLIER_PAYMENT_CORRECTION_TIME_NEUTRAL'then l.time_neutral_id else l.effective_inverse_id end
   where l.original_id=ident and j.source_type=kind and j.source_id=ident and j.status='POSTED')then
   raise exception 'CP7_TRANSACTION_SOURCE_UNAVAILABLE';end if;
  kind:='SUPPLIER_PAYMENT';
 end if;
 if kind in('RETURN_CORRECTION_TIME_NEUTRAL','RETURN_CORRECTION_EFFECTIVE')then
  if not erp.has_permission('finance.journal.view')or a->'profile'->>'role_code'not in('OWNER','ADMIN')then
   raise exception using errcode='42501',message='CP7_TRANSACTION_SOURCE_ACCESS_DENIED';end if;
  select r.original_return_id into ident from cp7_sales_return_correction.journal_restatements r
   join cp7_sales_return_correction.links l on l.original_id=r.original_return_id
   join erp.journal_entries j on j.id=case when kind='RETURN_CORRECTION_TIME_NEUTRAL'then r.neutral_journal_id else r.effective_journal_id end
   where r.inverse_journal_id=ident and j.source_type=kind and j.source_id=r.inverse_journal_id and j.status='POSTED';
  if not found then raise exception 'CP7_TRANSACTION_SOURCE_UNAVAILABLE';end if;
  kind:='SALES_RETURN';
 end if;
 -- A Native FG inverse references the original movement UUID, not a QC
 -- inspection. Follow that actual immutable link only for the qualified QC
 -- source family. Other FG inverse families stay explicitly unsupported.
 if kind='FG_MOVEMENT_REVERSAL' then
  if not(erp.has_permission('warehouse.stock.view')or erp.has_permission('warehouse.movement.view'))then
   raise exception using errcode='42501',message='CP7_TRANSACTION_SOURCE_ACCESS_DENIED';end if;
  select m.source_type,m.source_id into kind,ident from erp.fg_stock_movements m where m.id=ident and m.reversal_of_id is null;
  if not found or ident is null then raise exception 'CP7_TRANSACTION_SOURCE_UNAVAILABLE';end if;
  if kind<>'QC_ITEM'and not(kind='SALES_RETURN_ITEM'and exists(select 1 from erp.sales_return_items i
   join cp7_sales_return_correction.links l on l.original_id=i.return_id where i.id=ident))then
   return jsonb_build_object('contract_version','cp7.transaction-source.v1','actor_scope_id',auth.uid(),'source',p,
    'status','UNSUPPORTED_SOURCE','document',null,'read_at',statement_timestamp(),'business_DML',false);
  end if;
 end if;
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
 when kind in('MISC_FINANCE','MISC_CORRECTION_TIME_NEUTRAL','MISC_CORRECTION_EFFECTIVE')then
  domain:='MISC_FINANCE';route:='finance-journal';permission:='finance.journal.view';
 when kind in('PAYROLL_ATTENDANCE_ACCRUAL','PAYROLL_EXTRA_ACCRUAL','PAYROLL_MANUAL_REDUCTION','PAYROLL_MATERIAL_DEDUCTION','PAYROLL_CASH_ADVANCE_DEDUCTION','PAYROLL_OTHER_DEDUCTION','PAYROLL_PAYMENT','PAYROLL_INSTALLMENT')then
  domain:='PAYROLL';route:='finance-payroll';permission:='finance.payroll.view';
 when kind in('CONTRACTOR_ACCESSORY_STOCK_COST','CONTRACTOR_MATERIAL_RECEIVABLE','CONTRACTOR_MATERIAL_ISSUE_ITEM')then
  domain:='ACCESSORY_ISSUE';route:='contractor-issue';permission:='finance.contractor_accessory.view';
 when kind in('REWORK_ORDER','REWORK_COMPLETION')then
  domain:='BS_REWORK';route:='bs-rework';permission:='production.bs_rework.view';
 when kind in('QC_INSPECTION','QC_ITEM')then
  domain:='QC';route:='qc';permission:='production.final_sku.view';
 when kind in('LAUNDRY_DELIVERY','LAUNDRY_DELIVERY_LINE','LAUNDRY_DELIVERY_BATCH_SIZE_LINE',
  'LAUNDRY_RECEIPT','LAUNDRY_RECEIPT_LINE','LAUNDRY_RECEIPT_BATCH_SIZE_LINE')then
  domain:='LAUNDRY';route:='laundry';permission:='production.laundry.view';
 when kind in('CUTTING_GROUP','CUTTING_MATERIAL_ISSUE')then
  -- Posted cutting is read by the existing Native ALL distribution queue,
  -- never by the unposted cutting-draft selector. Its current view right is
  -- production.distribution.view; cutting.view alone cannot open that reader.
  domain:='CUTTING';route:='mandor-wip';permission:='production.distribution.view';
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
 when'SUPPLIER_PAYMENT'then
  select s.purchase_id into parent_id from erp.supplier_payments s where s.id=ident;
  focus:=jsonb_build_object('kind','SUPPLIER_PAYMENT','id',ident);
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
 when'PAYROLL_INSTALLMENT'then
  select i.payroll_id into parent_id from cp7_installment.payments i where i.id=ident;
  focus:=jsonb_build_object('kind','PAYROLL_INSTALLMENT','id',ident);
 when'CONTRACTOR_MATERIAL_ISSUE_ITEM'then
  select i.issue_id into parent_id from erp.contractor_material_issue_items i where i.id=ident;
 when'REWORK_ORDER','REWORK_COMPLETION'then
  select r.bs_case_id into parent_id from erp.rework_orders r where r.id=ident;
  focus:=jsonb_build_object('kind','REWORK_ORDER','id',ident);
 when'QC_ITEM'then
  select i.inspection_id into parent_id from erp.qc_inspection_items i where i.id=ident;
 when'LAUNDRY_DELIVERY_LINE'then
  select l.delivery_id into parent_id from erp.laundry_delivery_lines l where l.id=ident;
 when'LAUNDRY_DELIVERY_BATCH_SIZE_LINE'then
  select l.delivery_id into parent_id from erp.laundry_delivery_batch_size_lines s
   join erp.laundry_delivery_lines l on l.id=s.delivery_line_id where s.id=ident;
 when'LAUNDRY_RECEIPT'then
  select r.delivery_id into parent_id from erp.laundry_receipts r where r.id=ident;
  focus:=jsonb_build_object('kind','LAUNDRY_RECEIPT','id',ident);
 when'LAUNDRY_RECEIPT_LINE'then
  select r.delivery_id,jsonb_build_object('kind','LAUNDRY_RECEIPT','id',r.id)into parent_id,focus
   from erp.laundry_receipt_lines l join erp.laundry_receipts r on r.id=l.receipt_id where l.id=ident;
 when'LAUNDRY_RECEIPT_BATCH_SIZE_LINE'then
  select r.delivery_id,jsonb_build_object('kind','LAUNDRY_RECEIPT','id',r.id)into parent_id,focus
   from erp.laundry_receipt_batch_size_lines s join erp.laundry_receipt_lines l on l.id=s.receipt_line_id
   join erp.laundry_receipts r on r.id=l.receipt_id where s.id=ident;
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
 when'PAYROLL'then select to_jsonb(h),h.payroll_number into doc,label from erp.payroll_settlements h where h.id=parent_id;
 when'ACCESSORY_ISSUE'then select to_jsonb(h),h.issue_number into doc,label from erp.contractor_material_issues h where h.id=parent_id;
 when'BS_REWORK'then select to_jsonb(h),h.bs_number into doc,label from erp.bs_cases h where h.id=parent_id;
 when'QC'then select to_jsonb(h),h.inspection_number into doc,label from erp.qc_inspections h where h.id=parent_id;
 when'LAUNDRY'then select to_jsonb(h),h.delivery_number into doc,label from erp.laundry_deliveries h where h.id=parent_id;
 when'CUTTING'then
  select to_jsonb(g),g.group_number into doc,label from erp.cutting_groups g
   join erp.production_orders po on po.id=g.po_id
   join erp.product_models pm on pm.id=po.model_id where g.id=parent_id;
 end case;
 if doc is null or coalesce(label,'')=''then raise exception 'CP7_TRANSACTION_SOURCE_UNAVAILABLE';end if;
 if domain='CUTTING'then
  if doc->'material_issue_posted'is distinct from'true'::jsonb then
   return jsonb_build_object('contract_version','cp7.transaction-source.v1','actor_scope_id',auth.uid(),
    'source',p,'status','UNSUPPORTED_SOURCE','document',null,'read_at',statement_timestamp(),'business_DML',false);
  end if;
  focus:=jsonb_build_object('kind','CUTTING_GROUP','id',parent_id,'parent_id',doc->>'po_id');
 end if;
 -- The existing CP6 owner reads complete Native laundry-linked QC only.
 -- Legacy/import outputs are distinct sources, never guessed into this form.
 if domain='QC'and(not exists(select 1 from erp.qc_inspection_items i where i.inspection_id=parent_id)
  or exists(select 1 from erp.qc_inspection_items i where i.inspection_id=parent_id and i.source_laundry_receipt_batch_size_line_id is null))then
  return jsonb_build_object('contract_version','cp7.transaction-source.v1','actor_scope_id',auth.uid(),
   'source',p,'status','UNSUPPORTED_SOURCE','document',null,'read_at',statement_timestamp(),'business_DML',false);
 end if;
 -- The unchanged owning Laundry workspace reads batch-linked deliveries.
 -- Receipt numbers are not searched by that reader: use its actual delivery
 -- number and recheck the embedded receipt UUID inside that exact parent.
 if domain='LAUNDRY'and(not exists(select 1 from erp.laundry_delivery_lines l where l.delivery_id=parent_id)
  or exists(select 1 from erp.laundry_delivery_lines l where l.delivery_id=parent_id
   and not exists(select 1 from erp.laundry_delivery_batch_size_lines s where s.delivery_line_id=l.id)))then
  return jsonb_build_object('contract_version','cp7.transaction-source.v1','actor_scope_id',auth.uid(),
   'source',p,'status','UNSUPPORTED_SOURCE','document',null,'read_at',statement_timestamp(),'business_DML',false);
 end if;
 -- The current owner is specifically a counted-PCS accessory workspace.
 -- A mixed or fabric issue is a different Native document and cannot be
 -- redirected into that editor merely because its receivable has this kind.
 if domain='ACCESSORY_ISSUE'and exists(
  select 1 from erp.contractor_material_issue_items i
   left join erp.materials m on m.id=i.material_id
   left join erp.uom_definitions u on u.unit_code=m.unit_code
  where i.issue_id=parent_id and(m.material_type is distinct from'ACCESSORY'
   or upper(m.unit_code)is distinct from'PCS'or u.dimension is distinct from'COUNT'))then
  return jsonb_build_object('contract_version','cp7.transaction-source.v1','actor_scope_id',auth.uid(),
   'source',p,'status','UNSUPPORTED_SOURCE','document',null,'read_at',statement_timestamp(),'business_DML',false);
 end if;
 -- Match each unchanged owning reader's pagination and exact ordering.
 -- BS uses ALL/BS, no query or pattern, and 50 rows; other children use 25.
 -- The owner re-reads the page and checks both identities; no client scan.
 if focus is not null and focus<>'null'::jsonb then
  case focus->>'kind'
  when'CUTTING_GROUP'then
   -- Exactly Native get_cutting_pickup_queue_v1(ALL,NULL,NULL,100,offset):
   -- all posted groups including picked-up/finished PO history, same inner
   -- joins and cut_at/group_number/id order. No query scan or first-row guess.
   select ((n-1)/100)*100 into focus_offset from(
    select g.id,row_number()over(order by g.cut_at,g.group_number,g.id)n
    from erp.cutting_groups g join erp.production_orders po on po.id=g.po_id
    join erp.product_models pm on pm.id=po.model_id where g.material_issue_posted
   )x where id=parent_id;
  when'LAUNDRY_RECEIPT'then
   -- Embedded child, not an independently paginated list. Zero is the closed
   -- focus position; the owner re-reads and checks this receipt's actual FK.
   if exists(select 1 from erp.laundry_receipts r where r.id=(focus->>'id')::uuid and r.delivery_id=parent_id)then
    focus_offset:=0;
   end if;
  when'SALES_PAYMENT'then
   select ((n-1)/25)*25 into focus_offset from(select id,row_number()over(order by payment_date desc,id)n from erp.sales_payments where sale_id=parent_id)x where id=(focus->>'id')::uuid;
  when'SALES_RETURN'then
   select ((n-1)/25)*25 into focus_offset from(select id,row_number()over(order by physical_at desc,id)n from erp.sales_returns where sale_id=parent_id)x where id=(focus->>'id')::uuid;
  when'PURCHASE_INVOICE'then
   select ((n-1)/25)*25 into focus_offset from(select ih.id,row_number()over(order by ih.received_at desc,ih.id)n from erp.material_supplier_invoices ih where exists(select 1 from erp.material_supplier_invoice_lines l join erp.material_purchase_items i on i.id=l.purchase_item_id where l.invoice_id=ih.id and i.purchase_id=parent_id))x where id=(focus->>'id')::uuid;
  when'SUPPLIER_PAYMENT'then
   select ((n-1)/25)*25 into focus_offset from(select p.id,row_number()over(order by p.payment_date,p.created_at,p.id)n from erp.supplier_payments p where p.purchase_id=parent_id)x where id=(focus->>'id')::uuid;
  when'PAYROLL_INSTALLMENT'then
   -- Match the existing installment source loop, including reversed history.
   select ((n-1)/25)*25 into focus_offset from(select i.id,row_number()over(order by i.payment_date,i.created_at,i.id)n from cp7_installment.payments i where i.payroll_id=parent_id)x where id=(focus->>'id')::uuid;
  when'REWORK_ORDER'then
   -- Native get_bs_resolution_workspace_v1 orders open cases before closed,
   -- then physical_at DESC, bs_number, id. Status comes from the same header;
   -- the Native owning reader remains authoritative for quantities and history.
   select ((n-1)/50)*50 into focus_offset from(select b.id,row_number()over(
    order by(b.status in('RESOLVED','SCRAPPED','WRITTEN_OFF','CANCELLED')),
     b.physical_at desc,b.bs_number,b.id)n from erp.bs_cases b)x where id=parent_id;
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
grant execute on function public.erp_cp7_resolve_transaction_source_v1(jsonb)to postgres;
