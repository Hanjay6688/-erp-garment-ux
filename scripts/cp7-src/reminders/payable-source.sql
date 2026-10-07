-- Current supplier material liabilities only. Opening AP, payroll and other
-- obligations are outside this declared source; no second AP/cash/HPP engine.
create role cp7_payable_read nologin noinherit nosuperuser nocreatedb nocreaterole noreplication bypassrls;
grant usage on schema erp,auth to cp7_payable_read;
grant execute on function auth.uid(),auth.jwt(),erp.get_my_access_v1(),erp.has_permission(text),
 public.erp_get_supplier_credit_v1(jsonb),erp.material_purchase_final_ap_total(uuid),
 erp.material_purchase_grni_total(uuid),erp.material_purchase_total_liability(uuid),
 erp.material_purchase_invoice_capacity(uuid),erp.material_purchase_posted_invoice_qty(uuid),
 erp.material_purchase_current_unit_cost(uuid)to cp7_payable_read;
grant select on erp.v_material_purchase_liability_status,erp.material_purchase_headers,
 erp.material_purchase_items,erp.suppliers,erp.supplier_payments,
 erp.material_supplier_invoices,erp.material_supplier_invoice_lines to cp7_payable_read;
grant usage,create on schema cp7_reminder_native to cp7_payable_read;

create function cp7_reminder_native.payable_exact_numbers(p jsonb)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare r jsonb;
begin
 case jsonb_typeof(p)
 when'number'then return to_jsonb(p::text);
 when'object'then select coalesce(jsonb_object_agg(k,cp7_reminder_native.payable_exact_numbers(v)),'{}')into r from jsonb_each(p)e(k,v);return r;
 when'array'then select coalesce(jsonb_agg(cp7_reminder_native.payable_exact_numbers(v)order by n),'[]')into r from jsonb_array_elements(p)with ordinality e(v,n);return r;
 else return p;
 end case;
end $$;

-- AP-5 (owner decision 7 Oct 2026). Native records a supplier payment against
-- a receipt (supplier_payments.purchase_id), never against an invoice, so no
-- recorded invoice allocation exists to use first. For the reminder only, the
-- receipt's posted payments are applied to its payable portions oldest due
-- first: each posted invoice's lines on this receipt (the same net amounts the
-- Native final AP sums) and the receipt's DIRECT_FINAL items (due on the
-- receipt header). The first portion not covered gives the due date. This is a
-- rule result, labelled as such, never per-invoice payment evidence; no
-- journal, payment or balance is read differently or changed. Return relief
-- and credit moves are receipt-level and not attributed to an invoice, so they
-- never move the due date later. Rounding follows the facade (2 decimals).
create function cp7_reminder_native.payable_due_rule(p_portions jsonb,p_paid text,p_remaining text)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare paid numeric;running numeric:=0;n integer:=0;portion jsonb;
begin
 if p_remaining is null or p_paid is null or p_remaining::numeric<=0 or jsonb_array_length(p_portions)=0 then
  return jsonb_build_object('outcome','NOT_APPLICABLE','open_portion',null);end if;
 paid:=p_paid::numeric;
 for portion in select value from jsonb_array_elements(p_portions)loop
  running:=running+(portion->>'amount')::numeric;
  if round(running,2)>paid then
   return jsonb_build_object('outcome',case when portion->>'due_date'is null then'OPEN_PORTION_DUE_MISSING'else'OPEN_PORTION'end,'open_portion',n);
  end if;
  n:=n+1;
 end loop;
 -- Every portion is covered yet a balance remains: it belongs to no invoice.
 return jsonb_build_object('outcome','UNATTRIBUTED','open_portion',null);
end $$;
create function cp7_reminder_native.payable_source()returns jsonb
language plpgsql stable security definer set search_path=''set TimeZone='UTC'as $$
declare a jsonb;index jsonb;vendor jsonb;native jsonb;balances jsonb:='[]';rows jsonb;suppliers jsonb;
 total bigint;posted bigint;at date:=(statement_timestamp()at time zone'Asia/Jakarta')::date;
begin
 if auth.uid()is null or coalesce(auth.jwt()->>'role','')<>'authenticated'then
  raise exception using errcode='42501',message='CP7_REMINDER_AP_ACCESS_DENIED';end if;
 a:=erp.get_my_access_v1();
 if a->'allowed'is distinct from'true'::jsonb or not erp.has_permission('finance.ap.view')then
  raise exception using errcode='42501',message='CP7_REMINDER_AP_ACCESS_DENIED';end if;
 select count(*),count(*)filter(where status='POSTED')into total,posted from erp.v_material_purchase_liability_status;
 if total>5000 then raise exception 'CP7_REMINDER_AP_SOURCE_INCOMPLETE';end if;
 -- The accepted BF facade returns the entire posted-purchase list per supplier.
 -- Its credit-event page is not reused or claimed as a complete credit ledger.
 index:=public.erp_get_supplier_credit_v1(jsonb_build_object('supplier_id',null,'page',1));suppliers:=index->'suppliers';
 if jsonb_typeof(suppliers)is distinct from'array'or jsonb_array_length(suppliers)>5000
  or(select count(distinct x->>'id')from jsonb_array_elements(suppliers)x)<>jsonb_array_length(suppliers)then raise exception 'CP7_REMINDER_AP_SOURCE_INCOMPLETE';end if;
 for vendor in select value from jsonb_array_elements(suppliers)loop
  native:=public.erp_get_supplier_credit_v1(jsonb_build_object('supplier_id',vendor->>'id','page',1));
  if native->>'supplier_id'is distinct from vendor->>'id'or jsonb_typeof(native->'purchases')is distinct from'array'
   or native->'suppliers'is distinct from suppliers then raise exception 'CP7_REMINDER_AP_SOURCE_INCOMPLETE';end if;
  balances:=balances||coalesce((select jsonb_agg(jsonb_build_object('supplier_id',vendor->>'id','native_purchase',x)order by n)
   from jsonb_array_elements(native->'purchases')with ordinality e(x,n)),'[]');
 end loop;
 if jsonb_array_length(balances)<>posted or(select count(distinct x->'native_purchase'->>'id')from jsonb_array_elements(balances)x)<>posted
  or exists(select 1 from erp.v_material_purchase_liability_status l where l.status='POSTED'and not exists(
   select 1 from jsonb_array_elements(balances)x where x->'native_purchase'->>'id'=l.purchase_id::text and x->>'supplier_id'=l.supplier_id::text))then raise exception 'CP7_REMINDER_AP_SOURCE_INCOMPLETE';end if;
 with source as materialized(
  select cp7_reminder_native.payable_exact_numbers(to_jsonb(l))liability,
   (select x->'native_purchase'from jsonb_array_elements(balances)x where x->'native_purchase'->>'id'=l.purchase_id::text)balance,
   h.due_date receipt_due_date,coalesce(l.earliest_due_date,h.due_date)recorded_due_date,
   case when l.earliest_due_date is not null then'NATIVE_POSTED_INVOICE_EARLIEST'when h.due_date is not null then'NATIVE_RECEIPT_HEADER'else'MISSING'end recorded_due_basis,
   coalesce((select jsonb_agg(jsonb_build_object('kind',x.kind,'invoice_id',x.invoice_id,'invoice_number',x.invoice_number,
     'invoice_date',x.invoice_date,'due_date',x.due_date,'amount',x.amount::text)
    order by x.due_date nulls last,x.invoice_date nulls last,x.invoice_number collate "C" nulls last,x.invoice_id nulls last)
    from(select'POSTED_INVOICE'kind,ih.id invoice_id,ih.invoice_number::text invoice_number,ih.invoice_date,ih.due_date,sum(il.net_amount)amount
      from erp.material_supplier_invoice_lines il join erp.material_supplier_invoices ih on ih.id=il.invoice_id
      join erp.material_purchase_items pi on pi.id=il.purchase_item_id
      where pi.purchase_id=l.purchase_id and ih.status='POSTED'and pi.invoice_match_state<>'DIRECT_FINAL'group by ih.id
     union all
     select'RECEIPT_DIRECT_FINAL',null,null,null,h.due_date,sum(pi.qty*erp.material_purchase_current_unit_cost(pi.id))
      from erp.material_purchase_items pi where pi.purchase_id=l.purchase_id and pi.invoice_match_state='DIRECT_FINAL'having count(*)>0)x),'[]')portions,
   coalesce((select jsonb_agg(jsonb_build_object('id',i.id,'price_state',i.price_state,'invoice_match_state',i.invoice_match_state,
    'capacity',erp.material_purchase_invoice_capacity(i.id)::text,'invoiced_qty',erp.material_purchase_posted_invoice_qty(i.id)::text)order by i.id)
    from erp.material_purchase_items i where i.purchase_id=l.purchase_id),'[]')coverage,
   l.physical_at,l.purchase_id from erp.v_material_purchase_liability_status l join erp.material_purchase_headers h on h.id=l.purchase_id),
 ruled as materialized(select *,case when liability->>'status'='POSTED'then cp7_reminder_native.payable_due_rule(portions,balance->>'paid',balance->>'remaining')
  else jsonb_build_object('outcome','NOT_APPLICABLE','open_portion',null)end rule from source),
 dated as(select *,case rule->>'outcome'when'OPEN_PORTION'then(portions->((rule->>'open_portion')::integer)->>'due_date')::date
   when'OPEN_PORTION_DUE_MISSING'then null else recorded_due_date end due_date,
  case rule->>'outcome'when'OPEN_PORTION'then'RULE_OLDEST_DUE_FIRST_WITHIN_RECEIPT'when'OPEN_PORTION_DUE_MISSING'then'RULE_OPEN_PORTION_DUE_MISSING'
   else recorded_due_basis end due_basis,
  jsonb_build_object('rule','OLDEST_DUE_FIRST_WITHIN_RECEIPT','evidence','RULE_RESULT_NOT_PER_INVOICE_PAYMENT_EVIDENCE',
   'recorded_invoice_allocation','NONE_IN_NATIVE_PAYMENTS_ARE_RECEIPT_BOUND','payments_applied',balance->>'paid',
   'recorded_due_date',recorded_due_date,'recorded_due_basis',recorded_due_basis,'portions',portions)||rule due_rule from ruled),
 pending as(select *,liability->>'status'='POSTED'and(coalesce((liability->>'grni_estimated_amount')::numeric>0,false)or exists(
  select 1 from jsonb_array_elements(coverage)x where x->>'invoice_match_state'<>'DIRECT_FINAL'
   and(x->>'capacity')::numeric>(x->>'invoiced_qty')::numeric))invoice_pending from dated),
 observed as(select *,case when liability->>'status'='DRAFT'then'DRAFT_ONLY'
  when liability->>'status'<>'POSTED'then'INACTIVE_DOCUMENT'
  when balance->>'remaining'is null then'UNKNOWN_BALANCE'
  when(balance->>'remaining')::numeric<0 then'CREDIT_REVIEW'
  when(balance->>'remaining')::numeric=0 and invoice_pending then'INVOICE_PENDING'
  when(balance->>'remaining')::numeric=0 then'ZERO_BALANCE'
  when due_date is null then'MISSING_DUE_DATE'when due_date<at then'OVERDUE'when due_date=at then'DUE_TODAY'else'NOT_DUE_YET'end state from pending)
 select coalesce(jsonb_agg(jsonb_build_object('liability',liability,'balance',balance,'receipt_due_date',receipt_due_date,'due_date',due_date,'due_basis',due_basis,'due_rule',due_rule,'invoice_coverage',coverage,
  'condition',jsonb_build_object('key','AP_MATERIAL:'||purchase_id::text,'source_revision',liability->>'row_version',
   'native_source_hash',encode(pg_catalog.sha256(convert_to(jsonb_build_object('liability',liability,'balance',balance,'receipt_due_date',receipt_due_date,'due_date',due_date,'due_basis',due_basis,'due_rule',due_rule,'invoice_coverage',coverage)::text,'UTF8')),'hex'),
   'state',state,'invoice_pending',invoice_pending,'business_resolved',state='ZERO_BALANCE'))
  order by physical_at desc,purchase_id),'[]')into rows from observed;
 if jsonb_array_length(rows)<>total or octet_length(rows::text)>4000000 or exists(
  select 1 from jsonb_array_elements(rows)x where x->'liability'->>'status'='POSTED'and(jsonb_array_length(x->'invoice_coverage')=0
   or exists(select 1 from jsonb_array_elements(x->'invoice_coverage')c where c->>'capacity'is null or c->>'invoiced_qty'is null)))then raise exception 'CP7_REMINDER_AP_SOURCE_INCOMPLETE';end if;
 return jsonb_build_object('contract_version','cp7.native-material-ap-source.v2','basis','ACCEPTED_BF_SIGNED_BALANCE_NATIVE_LIABILITY_AND_OLDEST_DUE_FIRST_RULE',
  'as_of',at,'read_at',statement_timestamp(),'rows',rows,'suppliers',suppliers,'page_complete',true,'total',total::text,
  'source_hash',encode(pg_catalog.sha256(convert_to(jsonb_build_object('as_of',at,'rows',rows,'suppliers',suppliers)::text,'UTF8')),'hex'));
end $$;
alter function cp7_reminder_native.payable_exact_numbers(jsonb)owner to cp7_payable_read;
alter function cp7_reminder_native.payable_due_rule(jsonb,text,text)owner to cp7_payable_read;
alter function cp7_reminder_native.payable_source()owner to cp7_payable_read;
revoke create on schema cp7_reminder_native from cp7_payable_read;
revoke all on function cp7_reminder_native.payable_exact_numbers(jsonb),cp7_reminder_native.payable_due_rule(jsonb,text,text),cp7_reminder_native.payable_source()from public,anon,authenticated,service_role;
grant execute on function cp7_reminder_native.payable_source()to cp7_reminder;

create function cp7_reminder_native.payable_conditions(p_run uuid)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb:=cp7_reminder_native.access_now(p_run);source jsonb;
begin
 source:=cp7_reminder_native.payable_source();
 if erp.get_my_access_v1()is distinct from a->'access'or not erp.has_permission('finance.ap.view')then
  raise exception using errcode='42501',message='CP7_REMINDER_AP_ACCESS_CHANGED';end if;
 return jsonb_build_object('contract_version','cp7.native-material-ap-conditions.v1','actor_scope_id',auth.uid(),'analysis',a->'analysis','source',source);
end $$;
alter function cp7_reminder_native.payable_conditions(uuid)owner to cp7_reminder;
revoke all on function cp7_reminder_native.payable_conditions(uuid)from public,anon,authenticated,service_role;
grant create on schema public to cp7_reminder;
create function public.erp_cp7_get_analysis_payable_conditions_v1(p_run uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_reminder_native.payable_conditions(p_run)$$;
alter function public.erp_cp7_get_analysis_payable_conditions_v1(uuid)owner to cp7_reminder;
revoke create on schema public from cp7_reminder;
revoke all on function public.erp_cp7_get_analysis_payable_conditions_v1(uuid)from public,anon,authenticated,service_role;
grant execute on function public.erp_cp7_get_analysis_payable_conditions_v1(uuid)to authenticated;
