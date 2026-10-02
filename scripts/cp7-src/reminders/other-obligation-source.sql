-- Draft extension: authoritative readers for the remaining obligation domains.
-- Loaded only by the disposable Native269 candidate; qualification pending.
-- No money formula or business writer. Delegated Native helpers are unchanged.
create role cp7_obligation_read nologin noinherit nosuperuser nocreatedb nocreaterole noreplication bypassrls;
grant usage on schema erp,auth,public to cp7_obligation_read;
grant usage,create on schema cp7_reminder_native to cp7_obligation_read;
grant select on erp.opening_subledger_balances,erp.opening_balance_items,erp.opening_balance_headers,
 erp.initial_import_financial_sources,erp.customers,erp.suppliers,erp.contractors,erp.laundry_vendors,
 erp.bc_lot_events_v1,erp.bc_documents_v1,erp.payroll_reimbursements,erp.payroll_settlements,erp.vendor_invoices,
 erp.laundry_receipt_lines,erp.laundry_receipts,erp.laundry_delivery_lines,erp.laundry_deliveries,
 erp.bd_opening_laundry_uninvoiced_v1,erp.bd_laundry_invoice_lines_v1,erp.bd_laundry_invoices_v1
 to cp7_obligation_read;
grant execute on function auth.uid(),auth.jwt(),erp.get_my_access_v1(),erp.has_permission(text),
 erp.bb_financial_workspace_v1(uuid),erp.bb_opening_balance_context_v1(uuid),erp.bd_vendor_payables_v1(uuid),
 erp.bc_carry_remaining_v1(uuid),erp.bd_receipt_page_v1(uuid,uuid,timestamptz),erp.bd_receipt_invoiced_v1(uuid),
 erp.bd_opening_invoiced_v1(uuid),erp.bd_opening_billed_v1(uuid),erp.bd_opening_released_v1(uuid),
 public.erp_cp7_get_payroll_workspace_v1(text,jsonb),
 public.erp_cp7_get_payroll_installments_v1(jsonb),cp7_reminder_native.exact_numbers(jsonb)to cp7_obligation_read;

create function cp7_reminder_native.other_access()returns jsonb
language plpgsql stable security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb;
begin
 if auth.uid()is null or coalesce(auth.jwt()->>'role','')<>'authenticated'then raise exception using errcode='42501',message='CP7_OTHER_OBLIGATION_ACCESS_DENIED';end if;
 a:=erp.get_my_access_v1();
 if a->'allowed'is distinct from'true'::jsonb or a->'profile'->>'role_code'not in('OWNER','ADMIN','STAFF')then
  raise exception using errcode='42501',message='CP7_OTHER_OBLIGATION_ACCESS_DENIED';end if;
 return a;
end $$;

create function cp7_reminder_native.other_money(p text,p_id uuid,p_kind text)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
begin
 if p is null then return jsonb_build_object('state','UNKNOWN','unit','IDR','reason','ACCEPTED_NATIVE_REMAINING_NOT_AVAILABLE',
  'refs',jsonb_build_array(jsonb_build_object('kind',p_kind,'id',p_id)));end if;
 if p!~'^-?(0|[1-9][0-9]{0,23})(\.[0-9]{1,12})?$'then raise exception 'CP7_OTHER_NATIVE_AMOUNT_INVALID';end if;
 -- Preserve the exact Native decimal string. Never reconstruct its formula.
 return jsonb_build_object('state','KNOWN','unit','IDR','value',p,'refs',jsonb_build_array(jsonb_build_object('kind',p_kind,'id',p_id)));
end $$;

create function cp7_reminder_native.other_document(p_domain text,p_id uuid,p_label text,p_due date,p_amount jsonb,
 p_state text,p_raw jsonb,p_at date)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare state text;reason text;resolved boolean:=false;days jsonb;economic text;refs jsonb;
 document jsonb:=cp7_reminder_native.exact_numbers(p_raw);document_hash text:=encode(pg_catalog.sha256(convert_to(p_raw::text,'UTF8')),'hex');
 rule text:=case when p_domain='OPENING_AR'then'AR_DUE'else'AP_DUE'end;
begin
 -- Some Native tables have no row_version. The reference is their actual
 -- document content hash, explicitly labelled; never fabricate version 1.
 select jsonb_agg(x||jsonb_build_object('revision',document_hash))into refs from jsonb_array_elements(p_amount->'refs')x;
 p_amount:=p_amount||jsonb_build_object('refs',refs);
 if p_state in('DRAFT_ONLY','INACTIVE_DOCUMENT','VALUE_PENDING','ALLOCATION_NOT_SETTLEMENT','SOURCE_REVIEW','INVOICED_LIABILITY_SEE_NATIVE_DOCUMENT')then
  state:=case when p_state in('DRAFT_ONLY','INACTIVE_DOCUMENT')then'NO_CURRENT_GAP'else'DATA_REVIEW'end;reason:=p_state;
 elsif p_amount->>'state'<>'KNOWN'then state:='DATA_REVIEW';reason:='UNKNOWN_NATIVE_REMAINING';
 elsif(p_amount->>'value')::numeric<0 then state:='DATA_REVIEW';reason:='NATIVE_CREDIT_REVIEW';
 elsif(p_amount->>'value')::numeric=0 then state:='RESOLVED';reason:='ZERO_NATIVE_REMAINING';resolved:=true;
 elsif p_due is null then state:='DATA_REVIEW';reason:='MISSING_RECORDED_DUE_DATE';
 elsif p_due>p_at then state:='NO_CURRENT_GAP';reason:='NOT_DUE_YET';
 else state:='ACTIVE';reason:=case when p_due=p_at then'DUE_TODAY'else'OVERDUE'end;end if;
 economic:=case when p_state in('DRAFT_ONLY','INACTIVE_DOCUMENT')then'INACTIVE'
  when resolved then'SETTLED'when p_state in('VALUE_PENDING','ALLOCATION_NOT_SETTLEMENT','SOURCE_REVIEW','INVOICED_LIABILITY_SEE_NATIVE_DOCUMENT')or p_amount->>'state'<>'KNOWN'then'UNKNOWN'
  when(p_amount->>'value')::numeric>0 then'OPEN'else'UNKNOWN'end;
 days:=jsonb_build_object('state',case when p_due is null or state='DATA_REVIEW'then'UNKNOWN'else'KNOWN'end,
  'unit','DAY','refs',p_amount->'refs');
 if days->>'state'='KNOWN'then days:=days||jsonb_build_object('value',greatest(0,p_at-p_due)::text);
 else days:=days||jsonb_build_object('reason',reason);end if;
 return jsonb_build_object('domain',p_domain,'key',rule||':'||p_domain||':'||p_id::text,'rule_id',rule,
  'target_key',null,'source_id',p_id,'material_key',null,'state',state,'reason',reason,'value',days,
  'production_state',null,'business_resolved',resolved,'economic_state',economic,'scope','CURRENT_ACCEPTED_NATIVE_'||p_domain,
  'label',p_label,'financial_source',jsonb_build_object('remaining',p_amount,'recorded_due_date',p_due,'document',document,
   'document_sha256',document_hash,'revision_basis','NATIVE_DOCUMENT_CONTENT_SHA256'),
  'source_hash',encode(pg_catalog.sha256(convert_to(jsonb_build_object('domain',p_domain,'id',p_id,'state',p_state,
   'due',p_due,'remaining',p_amount,'document',p_raw,'as_of',p_at)::text,'UTF8')),'hex'));
end $$;

create function cp7_reminder_native.other_opening(p_ar boolean,p_ap boolean,p_at date)returns jsonb
language plpgsql stable security invoker set search_path=''set TimeZone='UTC'as $$
declare documents jsonb:='[]';native_rows jsonb:='[]';native jsonb;item jsonb;balance record;batch uuid;
 domain text;amount jsonb;label text;due date;state text;vendor jsonb;
begin
 if not p_ar and not p_ap then return documents;end if;
 if p_ar is distinct from erp.has_permission('finance.ar.view')or p_ap is distinct from erp.has_permission('finance.ap.view')then
  raise exception using errcode='42501',message='CP7_OTHER_OBLIGATION_DOMAIN_CHANGED';end if;
 for batch in select distinct f.batch_id from erp.initial_import_financial_sources f join erp.opening_subledger_balances b on b.opening_item_id=f.opening_item_id
  where f.source_kind<>'CONTRACTOR_CASH_ADVANCE'and(p_ar and b.direction='RECEIVABLE'or p_ap and b.direction='PAYABLE')loop
  native:=erp.bb_financial_workspace_v1(batch);
  if jsonb_typeof(native->'opening_balances')is distinct from'array'then raise exception 'CP7_OTHER_OPENING_SOURCE_INCOMPLETE';end if;
  native_rows:=native_rows||(native->'opening_balances');
 end loop;
 if(select count(distinct x->>'balance_id')from jsonb_array_elements(native_rows)x)<>jsonb_array_length(native_rows)then
  raise exception 'CP7_OTHER_OPENING_SOURCE_INCOMPLETE';end if;
 for balance in select b.*,i.balance_type,h.opening_date,h.status opening_status,f.id imported_source_id,f.source_kind,
  coalesce(c.customer_name,s.supplier_name,v.vendor_name,k.contractor_name)party_name
  from erp.opening_subledger_balances b join erp.opening_balance_items i on i.id=b.opening_item_id
  join erp.opening_balance_headers h on h.id=i.opening_id
  left join erp.initial_import_financial_sources f on f.opening_item_id=b.opening_item_id
  left join erp.customers c on c.id=b.customer_id left join erp.suppliers s on s.id=b.supplier_id
  left join erp.laundry_vendors v on v.id=b.vendor_id left join erp.contractors k on k.id=b.contractor_id
  where f.source_kind is distinct from'CONTRACTOR_CASH_ADVANCE'and(p_ar and b.direction='RECEIVABLE'or p_ap and b.direction='PAYABLE')order by b.id loop
  domain:=case when balance.direction='RECEIVABLE'then'OPENING_AR'else'OPENING_AP'end;
  select x into item from jsonb_array_elements(native_rows)x where x->>'balance_id'=balance.id::text;
  if balance.imported_source_id is not null and item is null then raise exception 'CP7_OTHER_OPENING_SOURCE_INCOMPLETE';end if;
  if item is not null then
   amount:=cp7_reminder_native.other_money(item->>'remaining_amount',balance.id,'ACCEPTED_BB_OPENING_BALANCE');due:=(item->>'due_date')::date;
  else
   native:=jsonb_build_object('header',to_jsonb(balance),'context',erp.bb_opening_balance_context_v1(balance.id));due:=null;
   -- A legacy vendor opening can reuse the complete Native BD balance reader.
   -- Imported and legacy opening identities remain one canonical row each.
   if balance.vendor_id is not null then
    vendor:=erp.bd_vendor_payables_v1(balance.vendor_id);
    select x into item from jsonb_array_elements(vendor->'documents')x where x->>'kind'='OPENING_PAYABLE'and x->>'id'=balance.id::text;
    if item is not null then native:=native||jsonb_build_object('native_vendor_document',item,'native_vendor_ledger',vendor->'ledger');end if;
   end if;
   amount:=cp7_reminder_native.other_money(case when item is not null then item->>'remaining'
    when balance.status='SETTLED'and balance.original_amount=balance.settled_amount then'0'end,balance.id,'ACCEPTED_NATIVE_LEGACY_OPENING_BALANCE');
   item:=native;
  end if;
  state:=case when balance.opening_status<>'POSTED'then'INACTIVE_DOCUMENT'else'CURRENT_NATIVE_DOCUMENT'end;
  label:=coalesce(item->>'document_number','Saldo awal')||' · '||coalesce(balance.party_name,'Pihak saldo awal');
  documents:=documents||jsonb_build_array(cp7_reminder_native.other_document(domain,balance.id,label,due,amount,state,item,p_at));
 end loop;
 return documents;
end $$;

create function cp7_reminder_native.other_payroll(p_at date)returns jsonb
language plpgsql stable security invoker set search_path=''set TimeZone='UTC'as $$
declare documents jsonb:='[]';page jsonb;payroll jsonb;native jsonb;off integer:=0;total bigint;seen bigint:=0;
 amount jsonb;state text;financial jsonb;
begin
 if not erp.has_permission('finance.ap.view')or not erp.has_permission('finance.payroll.view')then raise exception using errcode='42501',message='CP7_OTHER_PAYROLL_DOMAIN_DENIED';end if;
 loop
  page:=public.erp_cp7_get_payroll_workspace_v1('PAYROLLS',jsonb_build_object('limit',100,'offset',off));
  if page->>'section'<>'PAYROLLS'or jsonb_typeof(page->'page'->'rows')is distinct from'array'then raise exception 'CP7_OTHER_PAYROLL_SOURCE_INCOMPLETE';end if;
  if total is null then total:=(page->'page'->>'total')::bigint;elsif(page->'page'->>'total')::bigint<>total then raise exception 'CP7_OTHER_PAYROLL_SOURCE_INCOMPLETE';end if;
  if total>15000 then raise exception 'CP7_OTHER_PAYROLL_SOURCE_INCOMPLETE';end if;
  for payroll in select value from jsonb_array_elements(page->'page'->'rows')loop
   native:=public.erp_cp7_get_payroll_installments_v1(jsonb_build_object('payroll_id',payroll->>'id'));
   financial:=native->'document';
   if financial->>'payroll_id'<>payroll->>'id'or financial->>'row_version'<>payroll->>'row_version'or financial->>'native_status'<>payroll->>'status'then
    raise exception 'CP7_OTHER_PAYROLL_SOURCE_INCOMPLETE';end if;
   state:=case when payroll->>'status'='REVERSED'then'INACTIVE_DOCUMENT'when payroll->>'status'not in('APPROVED','PAID')then'DRAFT_ONLY'else'CURRENT_NATIVE_DOCUMENT'end;
   amount:=cp7_reminder_native.other_money(financial->>'remaining_amount',(payroll->>'id')::uuid,'ACCEPTED_E05_NATIVE_PAYROLL_INSTALLMENT');
   documents:=documents||jsonb_build_array(cp7_reminder_native.other_document('PAYROLL_AP',(payroll->>'id')::uuid,
    payroll->>'payroll_number'||' · '||(payroll->>'contractor_name'),null,amount,state,jsonb_build_object('payroll',payroll,'native_installment',financial),p_at));
   seen:=seen+1;
  end loop;
  exit when page->'page'->'next_offset'='null'::jsonb;
  if(page->'page'->>'next_offset')::integer<>off+jsonb_array_length(page->'page'->'rows')or jsonb_array_length(page->'page'->'rows')=0 then raise exception 'CP7_OTHER_PAYROLL_SOURCE_INCOMPLETE';end if;
  off:=(page->'page'->>'next_offset')::integer;
 end loop;
 if seen<>total or(select count(distinct x->>'source_id')from jsonb_array_elements(documents)x)<>seen then raise exception 'CP7_OTHER_PAYROLL_SOURCE_INCOMPLETE';end if;
 return documents;
end $$;

create function cp7_reminder_native.other_accessory(p_at date)returns jsonb
language plpgsql stable security invoker set search_path=''set TimeZone='UTC'as $$
declare documents jsonb:='[]';event record;links jsonb;amount jsonb;state text;native_remaining text;
begin
 if not erp.has_permission('finance.ap.view')or not erp.has_permission('warehouse.accessory.view')
  or not(erp.has_permission('finance.hpp.view')or erp.has_permission('finance.hpp.manage'))then raise exception using errcode='42501',message='CP7_OTHER_ACCESSORY_DOMAIN_DENIED';end if;
 for event in select e.*,d.document_number,d.status document_status from erp.bc_lot_events_v1 e join erp.bc_documents_v1 d on d.id=e.document_id
  where e.event_kind='CREDIT'and e.amount_carry>0 order by e.id loop
  native_remaining:=erp.bc_carry_remaining_v1(event.id)::text;
  select coalesce(jsonb_agg(jsonb_build_object('native_allocation',to_jsonb(r),'native_payroll',to_jsonb(p))order by r.id),'[]')into links
   from erp.payroll_reimbursements r join erp.payroll_settlements p on p.id=r.payroll_id
   where r.bc_credit_event_id=event.id and r.source_type='BC_RETURN_CARRY'and p.status<>'REVERSED';
  state:=case when event.document_status<>'POSTED'then'INACTIVE_DOCUMENT'else'ALLOCATION_NOT_SETTLEMENT'end;
  -- Native carry_remaining measures what is still allocatable, not what was
  -- paid. Never treat its zero or APPROVED payroll allocation as settlement.
  -- All linked allocations must have the actual Native PAID transition before
  -- their complete zero allocatable balance proves this entitlement settled.
  amount:=cp7_reminder_native.other_money(null,event.id,'ACCEPTED_BC_ACCESSORY_RETURN_CARRY');
  if event.document_status='POSTED'and native_remaining is not null
   and(native_remaining::numeric>0 or jsonb_array_length(links)>0)
   and not exists(select 1 from jsonb_array_elements(links)x where x->'native_payroll'->>'status'<>'PAID')then
   -- With no unpaid allocation, the accepted unallocated remainder is the
   -- unpaid remainder. Copy it; never subtract or distribute installments.
   state:='CURRENT_NATIVE_DOCUMENT';amount:=cp7_reminder_native.other_money(native_remaining,event.id,'ACCEPTED_BC_NATIVE_UNPAID_CARRY');
  end if;
  documents:=documents||jsonb_build_array(cp7_reminder_native.other_document('ACCESSORY_AP',event.id,'Retur aksesori · '||event.document_number,
   null,amount,state,jsonb_build_object('event',to_jsonb(event),'native_allocatable_remaining',native_remaining,'payroll_allocations',links,
    'meaning','ALLOCATABLE_REMAINDER_IS_NOT_UNPAID_BALANCE'),p_at));
 end loop;
 return documents;
end $$;

create function cp7_reminder_native.other_laundry(p_at date)returns jsonb
language plpgsql stable security invoker set search_path=''set TimeZone='UTC'as $$
declare documents jsonb:='[]';vendor record;native jsonb;doc jsonb;header erp.vendor_invoices%rowtype;amount jsonb;state text;expected bigint;seen bigint:=0;
begin
 if not erp.has_permission('finance.ap.view')or not erp.has_permission('production.laundry.view')
  or not(erp.has_permission('finance.hpp.view')or erp.has_permission('finance.hpp.manage'))then raise exception using errcode='42501',message='CP7_OTHER_LAUNDRY_DOMAIN_DENIED';end if;
 select count(*)into expected from erp.vendor_invoices;
 for vendor in select distinct v.id,v.vendor_name from erp.laundry_vendors v join erp.vendor_invoices i on i.vendor_id=v.id
  order by v.id loop
  native:=erp.bd_vendor_payables_v1(vendor.id);
  if native->>'vendor_id'<>vendor.id::text or jsonb_typeof(native->'documents')is distinct from'array'then raise exception 'CP7_OTHER_LAUNDRY_SOURCE_INCOMPLETE';end if;
  for doc in select value from jsonb_array_elements(native->'documents')where value->>'kind'='VENDOR_INVOICE'loop
   select *into header from erp.vendor_invoices h where h.id=(doc->>'id')::uuid and h.vendor_id=vendor.id;
   if header.id is null or header.status<>doc->>'status'then raise exception 'CP7_OTHER_LAUNDRY_SOURCE_INCOMPLETE';end if;
   amount:=cp7_reminder_native.other_money(doc->>'remaining',header.id,'ACCEPTED_BD_NATIVE_VENDOR_PAYABLE');
   state:=case when native->'ledger'->'matches'is distinct from'true'::jsonb then'SOURCE_REVIEW'else'CURRENT_NATIVE_DOCUMENT'end;
   documents:=documents||jsonb_build_array(cp7_reminder_native.other_document('LAUNDRY_AP',header.id,header.invoice_number||' · '||vendor.vendor_name,
    header.due_date,amount,state,jsonb_build_object('native_document',doc,'native_vendor_ledger',native->'ledger','native_credits',native->'credits',
     'header',to_jsonb(header),'opening_rows_composed_once_in','OPENING_AP'),p_at));seen:=seen+1;
  end loop;
  for header in select h.*from erp.vendor_invoices h where h.vendor_id=vendor.id and h.status not in('POSTED','PARTIAL_PAID','PAID')order by h.id loop
   if exists(select 1 from jsonb_array_elements(native->'documents')x where x->>'kind'='VENDOR_INVOICE'and x->>'id'=header.id::text)then
    raise exception 'CP7_OTHER_LAUNDRY_SOURCE_INCOMPLETE';end if;
   amount:=cp7_reminder_native.other_money(null,header.id,'ACCEPTED_BD_NATIVE_VENDOR_PAYABLE');
   state:=case when header.status='DRAFT'then'DRAFT_ONLY'else'INACTIVE_DOCUMENT'end;
   documents:=documents||jsonb_build_array(cp7_reminder_native.other_document('LAUNDRY_AP',header.id,header.invoice_number||' · '||vendor.vendor_name,
    header.due_date,amount,state,jsonb_build_object('header',to_jsonb(header),'meaning','INACTIVE_NATIVE_DOCUMENT_IS_NOT_HEALTHY_ZERO'),p_at));seen:=seen+1;
  end loop;
 end loop;
 if seen<>expected or(select count(distinct x->>'source_id')from jsonb_array_elements(documents)x)<>seen then raise exception 'CP7_OTHER_LAUNDRY_SOURCE_INCOMPLETE';end if;
 return documents;
end $$;

-- Include every receipt line, including missing prices, fully invoiced lines
-- and inactive documents. The accepted billable reader is only one subset.
-- A Native zero allocatable/GRNI value is never an unpaid-balance proof.
create function cp7_reminder_native.other_laundry_pending(p_at date)returns jsonb
language plpgsql stable security invoker set search_path=''set TimeZone='UTC'as $$
declare documents jsonb:='[]';native_rows jsonb:='[]';page jsonb;vendor uuid;cursor uuid;old_cursor uuid;
 at timestamptz:=statement_timestamp();receipt record;opening record;item jsonb;links jsonb;amount jsonb;state text;invoiced boolean;
begin
 if not erp.has_permission('finance.ap.view')or not erp.has_permission('production.laundry.view')
  or not(erp.has_permission('finance.hpp.view')or erp.has_permission('finance.hpp.manage'))then raise exception using errcode='42501',message='CP7_OTHER_LAUNDRY_DOMAIN_DENIED';end if;
 for vendor in select distinct d.vendor_id from erp.laundry_deliveries d join erp.laundry_delivery_lines dl on dl.delivery_id=d.id
  join erp.laundry_receipt_lines rl on rl.delivery_line_id=dl.id loop
  cursor:=null;
  loop
   page:=erp.bd_receipt_page_v1(vendor,cursor,at);
   if jsonb_typeof(page->'items')is distinct from'array'or(page->>'limit')::integer<>200 then raise exception 'CP7_OTHER_LAUNDRY_SOURCE_INCOMPLETE';end if;
   native_rows:=native_rows||(page->'items');old_cursor:=cursor;cursor:=(page->>'next_id')::uuid;
   exit when cursor is null;
   if cursor is not distinct from old_cursor or jsonb_array_length(page->'items')<>200 or jsonb_array_length(native_rows)>15000 then raise exception 'CP7_OTHER_LAUNDRY_SOURCE_INCOMPLETE';end if;
  end loop;
 end loop;
 if(select count(distinct x->>'receipt_line_id')from jsonb_array_elements(native_rows)x)<>jsonb_array_length(native_rows)then raise exception 'CP7_OTHER_LAUNDRY_SOURCE_INCOMPLETE';end if;
 for receipt in select rl.*,r.status receipt_status,r.receipt_number,r.row_version receipt_revision,r.physical_at,d.vendor_id,v.vendor_name
  from erp.laundry_receipt_lines rl join erp.laundry_receipts r on r.id=rl.receipt_id
  join erp.laundry_delivery_lines dl on dl.id=rl.delivery_line_id join erp.laundry_deliveries d on d.id=dl.delivery_id
  join erp.laundry_vendors v on v.id=d.vendor_id order by rl.id loop
  select x into item from jsonb_array_elements(native_rows)x where x->>'receipt_line_id'=receipt.id::text;
  invoiced:=erp.bd_receipt_invoiced_v1(receipt.id);
  if receipt.receipt_status='POSTED'and receipt.actual_cost_status='ESTIMATED'and receipt.actual_cost is not null and not invoiced and item is null then raise exception 'CP7_OTHER_LAUNDRY_SOURCE_INCOMPLETE';end if;
  select coalesce(jsonb_agg(jsonb_build_object('invoice_id',i.id,'invoice_number',i.invoice_number,'native_status',h.status,
   'completes_source',l.completes_source)order by l.id),'[]')into links
   from erp.bd_laundry_invoice_lines_v1 l join erp.bd_laundry_invoices_v1 i on i.id=l.invoice_id
   join erp.vendor_invoices h on h.id=i.id where l.receipt_line_id=receipt.id and i.status='POSTED';
  state:=case when receipt.receipt_status<>'POSTED'then'INACTIVE_DOCUMENT'when invoiced then'INVOICED_LIABILITY_SEE_NATIVE_DOCUMENT'else'VALUE_PENDING'end;
  amount:=cp7_reminder_native.other_money(null,receipt.id,'ACCEPTED_BD_LAUNDRY_RECEIPT');
  if receipt.receipt_status='POSTED'and invoiced and jsonb_array_length(links)>0
   and not exists(select 1 from jsonb_array_elements(links)x where x->>'native_status'<>'PAID')then
   state:='CURRENT_NATIVE_DOCUMENT';amount:=cp7_reminder_native.other_money('0',receipt.id,'ACCEPTED_BD_RECEIPT_FULL_NATIVE_INVOICES_PAID');
  end if;
  documents:=documents||jsonb_build_array(cp7_reminder_native.other_document('LAUNDRY_RECEIPT',receipt.id,
   'Penerimaan laundry · '||receipt.receipt_number||' · '||receipt.vendor_name,null,amount,state,
   jsonb_build_object('receipt',to_jsonb(receipt),'native_billable',item,'invoiced',invoiced,'native_invoices',links,
    'meaning','GRNI_ESTIMATE_NOT_FINAL_UNPAID_BALANCE_FINAL_MONEY_REPORTED_ONCE_IN_NATIVE_INVOICE'),p_at));
 end loop;
 for opening in select u.*,v.vendor_name from erp.bd_opening_laundry_uninvoiced_v1 u join erp.laundry_vendors v on v.id=u.vendor_id order by u.id loop
  invoiced:=erp.bd_opening_invoiced_v1(opening.id);
  select coalesce(jsonb_agg(jsonb_build_object('invoice_id',i.id,'invoice_number',i.invoice_number,'native_status',h.status,
   'completes_source',l.completes_source)order by l.id),'[]')into links
   from erp.bd_laundry_invoice_lines_v1 l join erp.bd_laundry_invoices_v1 i on i.id=l.invoice_id
   join erp.vendor_invoices h on h.id=i.id where l.opening_uninvoiced_id=opening.id and i.status='POSTED';
  amount:=cp7_reminder_native.other_money(null,opening.id,'ACCEPTED_BD_OPENING_UNINVOICED');
  state:=case when invoiced then'INVOICED_LIABILITY_SEE_NATIVE_DOCUMENT'else'VALUE_PENDING'end;
  if invoiced and jsonb_array_length(links)>0 and not exists(select 1 from jsonb_array_elements(links)x where x->>'native_status'<>'PAID')then
   state:='CURRENT_NATIVE_DOCUMENT';amount:=cp7_reminder_native.other_money('0',opening.id,'ACCEPTED_BD_OPENING_FULL_NATIVE_INVOICES_PAID');
  end if;
  documents:=documents||jsonb_build_array(cp7_reminder_native.other_document('LAUNDRY_OPENING_UNINVOICED',opening.id,
   'Nota awal laundry · '||opening.document_number||' · '||opening.vendor_name,null,amount,state,
   jsonb_build_object('opening',to_jsonb(opening),'invoiced',invoiced,'billed',erp.bd_opening_billed_v1(opening.id)::text,
    'released',erp.bd_opening_released_v1(opening.id)::text,'native_invoices',links,
    'meaning','ESTIMATE_NOT_FINAL_UNPAID_BALANCE_FINAL_MONEY_REPORTED_ONCE_IN_NATIVE_INVOICE'),p_at));
 end loop;
 if jsonb_array_length(documents)>15000 or octet_length(documents::text)>8000000 then raise exception 'CP7_OTHER_LAUNDRY_SOURCE_INCOMPLETE';end if;
 return documents;
end $$;

create function cp7_reminder_native.other_obligation_source()returns jsonb
language plpgsql stable security definer set search_path=''set TimeZone='UTC'as $$
declare a jsonb:=cp7_reminder_native.other_access();rows jsonb:='[]';coverage jsonb;at date:=(statement_timestamp()at time zone'Asia/Jakarta')::date;
 ar boolean:=erp.has_permission('finance.ar.view');ap boolean:=erp.has_permission('finance.ap.view');
 payroll boolean;accessory boolean;laundry boolean;
begin
 payroll:=ap and erp.has_permission('finance.payroll.view');accessory:=ap and erp.has_permission('warehouse.accessory.view')and(erp.has_permission('finance.hpp.view')or erp.has_permission('finance.hpp.manage'));
 laundry:=ap and erp.has_permission('production.laundry.view')and(erp.has_permission('finance.hpp.view')or erp.has_permission('finance.hpp.manage'));
 rows:=cp7_reminder_native.other_opening(ar,ap,at);
 if payroll then rows:=rows||cp7_reminder_native.other_payroll(at);end if;
 if accessory then rows:=rows||cp7_reminder_native.other_accessory(at);end if;
 if laundry then rows:=rows||cp7_reminder_native.other_laundry(at)||cp7_reminder_native.other_laundry_pending(at);end if;
 if cp7_reminder_native.other_access()is distinct from a then raise exception using errcode='42501',message='CP7_OTHER_OBLIGATION_ACCESS_CHANGED';end if;
 if jsonb_array_length(rows)>15000 or octet_length(rows::text)>8000000 or(select count(distinct x->>'key')from jsonb_array_elements(rows)x)<>jsonb_array_length(rows)then
  raise exception 'CP7_OTHER_OBLIGATION_SOURCE_INCOMPLETE';end if;
 coverage:=jsonb_build_object('opening_ar',case when ar then'COMPLETE_NATIVE_DOCUMENT_SCOPE_CONTRACTOR_CASH_ADVANCE_EXCLUDED'else'EXCLUDED_BY_CURRENT_RIGHTS'end,
  'opening_ap',case when ap then'COMPLETE_NATIVE_DOCUMENT_SCOPE_CONTRACTOR_CASH_ADVANCE_EXCLUDED'else'EXCLUDED_BY_CURRENT_RIGHTS'end,
  'payroll_ap',case when payroll then'COMPLETE_NATIVE_DOCUMENT_SCOPE'else'EXCLUDED_BY_CURRENT_RIGHTS'end,
  'accessory_ap',case when accessory then'COMPLETE_NATIVE_RETURN_CARRY_SCOPE_UNKNOWN_UNALLOCATED_BALANCE_RETAINED'else'EXCLUDED_BY_CURRENT_RIGHTS'end,
  'laundry_ap',case when laundry then'COMPLETE_NATIVE_INVOICE_RECEIPT_AND_OPENING_UNINVOICED_SCOPE_UNKNOWN_PENDING_RETAINED'else'EXCLUDED_BY_CURRENT_RIGHTS'end);
 return jsonb_build_object('contract_version','cp7.native-other-obligations.v1','rows',rows,'coverage',coverage,'as_of',at,
  'source_hash',encode(pg_catalog.sha256(convert_to(jsonb_build_object('rows',rows,'coverage',coverage,'as_of',at)::text,'UTF8')),'hex'),
  'full_family_acceptance',false,'meaning','NATIVE_REMAINING_COPIED_NEVER_RECALCULATED_NO_IMPLICIT_DUE_OR_SETTLEMENT');
end $$;

alter function cp7_reminder_native.other_access()owner to cp7_obligation_read;
alter function cp7_reminder_native.other_money(text,uuid,text)owner to cp7_obligation_read;
alter function cp7_reminder_native.other_document(text,uuid,text,date,jsonb,text,jsonb,date)owner to cp7_obligation_read;
alter function cp7_reminder_native.other_opening(boolean,boolean,date)owner to cp7_obligation_read;
alter function cp7_reminder_native.other_payroll(date)owner to cp7_obligation_read;
alter function cp7_reminder_native.other_accessory(date)owner to cp7_obligation_read;
alter function cp7_reminder_native.other_laundry(date)owner to cp7_obligation_read;
alter function cp7_reminder_native.other_laundry_pending(date)owner to cp7_obligation_read;
alter function cp7_reminder_native.other_obligation_source()owner to cp7_obligation_read;
revoke all on function cp7_reminder_native.other_access(),cp7_reminder_native.other_money(text,uuid,text),
 cp7_reminder_native.other_document(text,uuid,text,date,jsonb,text,jsonb,date),cp7_reminder_native.other_opening(boolean,boolean,date),
 cp7_reminder_native.other_payroll(date),cp7_reminder_native.other_accessory(date),cp7_reminder_native.other_laundry(date),
 cp7_reminder_native.other_laundry_pending(date),cp7_reminder_native.other_obligation_source()from public,anon,authenticated,service_role;
grant execute on function cp7_reminder_native.other_obligation_source()to cp7_reminder;
revoke create on schema cp7_reminder_native from cp7_obligation_read;
