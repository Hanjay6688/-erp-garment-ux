grant usage on schema cp7_request_context to "cp7_installment_read";
grant execute on function cp7_request_context."jwt"() to "cp7_installment_read";
grant execute on function cp7_request_context."uid"() to "cp7_installment_read";
CREATE OR REPLACE FUNCTION cp7_installment.access_now(p_action text DEFAULT NULL::text)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO ''
AS $function$
declare a jsonb;
begin
 if cp7_request_context.uid()is null or coalesce(cp7_request_context.jwt()->>'role','')<>'authenticated' then raise exception using errcode='42501',message='CP7_INSTALLMENT_ACCESS_DENIED';end if;
 a:=erp.get_my_access_v1();
 if a->'allowed'is distinct from 'true'::jsonb or not erp.has_permission('finance.payroll.view')
  or(p_action is not null and(p_action not in('PAY','REVERSE_PAYMENT','REVERSE_PAYROLL')or not erp.has_permission('finance.payroll.pay')))
  or(p_action='REVERSE_PAYROLL'and not erp.has_permission('finance.payroll.approve'))then raise exception using errcode='42501',message='CP7_INSTALLMENT_ACCESS_DENIED';end if;
 return a;
end $function$;
CREATE OR REPLACE FUNCTION cp7_installment.guard_journal()
 RETURNS trigger
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
declare p_id uuid;entry erp.journal_entries;c cp7_installment.command_context;
begin
 if tg_op='DELETE'then entry:=old;else entry:=new;end if;
 if tg_op='INSERT'and entry.source_type='PAYROLL_INSTALLMENT'then
  select * into c from cp7_installment.command_context where backend_pid=pg_backend_pid()and transaction_id=txid_current()and actor=cp7_request_context.uid()and action='PAY'and native_payment_id=entry.source_id;
  if c.actor is null then raise exception using errcode='42501',message='CP7_INSTALLMENT_PRIVATE_CONTEXT_REQUIRED';end if;
  p_id:=(c.payload->>'payroll_id')::uuid;
 else
  select p.payroll_id into p_id from cp7_installment.payments p where entry.id in(p.journal_id,p.reversal_journal_id)or entry.reversal_of_id=p.journal_id;
  if p_id is null and entry.source_type like 'PAYROLL_%'then select payroll_id into p_id from cp7_installment.accounts where payroll_id=entry.source_id;end if;
  if p_id is null and entry.reversal_of_id is not null then
   select a.payroll_id into p_id from erp.journal_entries original join cp7_installment.accounts a on a.payroll_id=original.source_id where original.id=entry.reversal_of_id and original.source_type like 'PAYROLL_%';
  end if;
 end if;
 if p_id is not null then perform cp7_installment.require_context(p_id);end if;
 if tg_op='DELETE'then return old;end if;return new;
end $function$;
CREATE OR REPLACE FUNCTION cp7_installment.guard_line()
 RETURNS trigger
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
declare p_id uuid;j erp.journal_entries;c cp7_installment.command_context;
begin
 select * into j from erp.journal_entries where id=case when tg_op='DELETE'then old.journal_entry_id else new.journal_entry_id end;
 select p.payroll_id into p_id from cp7_installment.payments p where j.id in(p.journal_id,p.reversal_journal_id)or j.reversal_of_id=p.journal_id;
 if p_id is null and j.source_type like 'PAYROLL_%'then select payroll_id into p_id from cp7_installment.accounts where payroll_id=j.source_id;end if;
 if p_id is null and j.source_type='PAYROLL_INSTALLMENT'then
  select * into c from cp7_installment.command_context where backend_pid=pg_backend_pid()and transaction_id=txid_current()and actor=cp7_request_context.uid()and action='PAY'and native_payment_id=j.source_id;
  p_id:=(c.payload->>'payroll_id')::uuid;
 end if;
 if p_id is null and j.reversal_of_id is not null then select a.payroll_id into p_id from erp.journal_entries original join cp7_installment.accounts a on a.payroll_id=original.source_id where original.id=j.reversal_of_id and original.source_type like 'PAYROLL_%';end if;
 if p_id is not null then
  if tg_op<>'INSERT'then raise exception 'CP7_INSTALLMENT_NATIVE_JOURNAL_IMMUTABLE';end if;
  perform cp7_installment.require_context(p_id);
 end if;
 if tg_op='DELETE'then return old;end if;return new;
end $function$;
CREATE OR REPLACE FUNCTION cp7_installment.require_context(p_id uuid)
 RETURNS void
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO ''
AS $function$
declare c cp7_installment.command_context;
begin
 select * into c from cp7_installment.command_context where backend_pid=pg_backend_pid()and transaction_id=txid_current()and actor=cp7_request_context.uid()and(payload->>'payroll_id')::uuid=p_id;
 if c.actor is null or not exists(select 1 from cp7_installment.requests r where r.actor=c.actor and r.request_id=c.request_id and r.action=c.action and r.payload=c.payload and r.expected_version=c.expected_version and r.response is null)then raise exception using errcode='42501',message='CP7_INSTALLMENT_PRIVATE_CONTEXT_REQUIRED';end if;
 perform cp7_installment.access_now(c.action);
end $function$;
grant usage on schema cp7_request_context to "cp7_misc_read";
grant execute on function cp7_request_context."jwt"() to "cp7_misc_read";
grant execute on function cp7_request_context."uid"() to "cp7_misc_read";
grant create on schema "cp7_misc" to postgres;
CREATE OR REPLACE FUNCTION cp7_misc.access_now()
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO ''
AS $function$
declare a jsonb;
begin
 if cp7_request_context.uid() is null or coalesce(cp7_request_context.jwt()->>'role','')<>'authenticated' then raise exception using errcode='42501',message='CP7_MISC_ACCESS_DENIED';end if;
 a:=erp.get_my_access_v1();
 if a->'allowed' is distinct from 'true'::jsonb or not erp.has_permission('finance.journal.view') or not erp.has_permission('finance.cash.view') then raise exception using errcode='42501',message='CP7_MISC_ACCESS_DENIED';end if;
 -- The accepted native writer is OWNER/ADMIN only. View permissions cannot
 -- turn a custom role into a financial writer.
 if coalesce(a->'profile'->>'role_code','') not in('OWNER','ADMIN') then raise exception using errcode='42501',message='CP7_MISC_OWNER_ADMIN_REQUIRED';end if;
 return a;
end $function$;
revoke create on schema "cp7_misc" from postgres;
grant usage on schema cp7_request_context to "cp7_sales_write";
grant execute on function cp7_request_context."uid"() to "cp7_sales_write";
CREATE OR REPLACE FUNCTION cp7_payment_correction.command(p jsonb, p_request uuid, p_expected text)
 RETURNS jsonb
 LANGUAGE plpgsql
 SET search_path TO ''
AS $function$
declare a jsonb;saved cp7_payment_correction.requests;r jsonb;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_payment_correction.access_now();perform cp7_payment_correction.validate(p);
 if p_request is null or p_expected is null or p_expected!~'^[1-9][0-9]{0,18}$'then raise exception 'CP7_SALES_COMMAND_FIELDS';end if;
 insert into cp7_payment_correction.requests values(cp7_request_context.uid(),p_request,p,p_expected,null)on conflict do nothing;
 select *into saved from cp7_payment_correction.requests where actor=cp7_request_context.uid()and request_id=p_request for update;
 if cp7_payment_correction.access_now()is distinct from a then raise exception using errcode='42501',message='CP7_SALES_ACCESS_CHANGED';end if;
 if saved.payload is distinct from p or saved.expected_version is distinct from p_expected then raise exception 'CP7_SALES_REQUEST_CHANGED';end if;
 if saved.response is not null then return saved.response;end if;
 insert into cp7_payment_correction.context values(pg_backend_pid(),txid_current(),cp7_request_context.uid(),p_request,p,p_expected);
 r:=cp7_payment_correction.apply(p,p_request,p_expected);
 delete from cp7_payment_correction.context where backend_pid=pg_backend_pid()and transaction_id=txid_current();
 if cp7_payment_correction.access_now()is distinct from a then raise exception using errcode='42501',message='CP7_SALES_ACCESS_CHANGED';end if;
 r:=r||jsonb_build_object('contract_version','cp7.sales-payment-correction.v1','kind','COMMITTED_OUTCOME','action','PAYMENT_CORRECT','request_id',p_request);
 update cp7_payment_correction.requests set response=r where actor=cp7_request_context.uid()and request_id=p_request;return r;
end $function$;
grant usage on schema cp7_request_context to "cp7_period_read";
grant execute on function cp7_request_context."jwt"() to "cp7_period_read";
grant execute on function cp7_request_context."uid"() to "cp7_period_read";
grant create on schema "cp7_period" to postgres;
CREATE OR REPLACE FUNCTION cp7_period.access_now()
 RETURNS void
 LANGUAGE plpgsql
 STABLE
 SET search_path TO ''
AS $function$
declare a jsonb;
begin
 if cp7_request_context.uid() is null or coalesce(cp7_request_context.jwt()->>'role','')<>'authenticated' then raise exception using errcode='42501',message='CP7_PERIOD_ACCESS_DENIED';end if;
 a:=erp.get_my_access_v1();
 if a->'allowed' is distinct from 'true'::jsonb or not erp.has_permission('finance.reports.view') or not erp.has_permission('finance.period_close.manage') then raise exception using errcode='42501',message='CP7_PERIOD_ACCESS_DENIED';end if;
 if coalesce(a->'profile'->>'role_code','') not in('OWNER','ADMIN') then raise exception using errcode='42501',message='CP7_PERIOD_OWNER_ADMIN_REQUIRED';end if;
end $function$;
revoke create on schema "cp7_period" from postgres;
grant usage on schema cp7_request_context to "cp7_period_write";
grant execute on function cp7_request_context."jwt"() to "cp7_period_write";
grant execute on function cp7_request_context."uid"() to "cp7_period_write";
grant create on schema "cp7_period" to postgres;
CREATE OR REPLACE FUNCTION cp7_period.command(p_action text, p_payload jsonb, p_request uuid)
 RETURNS jsonb
 LANGUAGE plpgsql
 SET search_path TO ''
AS $function$
declare v_actor uuid;saved cp7_period.requests;state jsonb;after_state jsonb;target date;review_day date;outcome jsonb;
begin
 perform cp7_period.access_now();v_actor:=cp7_request_context.uid();
 if p_request is null or p_action not in('CLOSE','REOPEN') or p_action is null or jsonb_typeof(p_payload) is distinct from 'object'
  or not p_payload ?& array['through','review_through','review_token','reason']
  or exists(select 1 from jsonb_object_keys(p_payload)k where k not in('through','review_through','review_token','reason'))
  or jsonb_typeof(p_payload->'through') not in('string','null')
  or exists(select 1 from jsonb_each(p_payload)e where e.key in('review_through','review_token','reason') and jsonb_typeof(e.value)<>'string')
  or (p_payload->>'review_through')!~'^[0-9]{4}-[0-9]{2}-[0-9]{2}$'
  or(p_payload->>'through' is not null and(p_payload->>'through')!~'^[0-9]{4}-[0-9]{2}-[0-9]{2}$')
  or(p_payload->>'review_token')!~'^[a-f0-9]{32}$' or length(btrim(p_payload->>'reason')) not between 1 and 1000 then raise exception 'CP7_PERIOD_COMMAND';end if;
 target:=(p_payload->>'through')::date;review_day:=(p_payload->>'review_through')::date;
 if p_action='CLOSE' and(target is null or target<>review_day) then raise exception 'CP7_PERIOD_CLOSE_REVIEW_DATE';end if;
 perform pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended('cp7.period.request:'||v_actor::text||':'||p_request::text,0));
 perform cp7_period.access_now();
 select * into saved from cp7_period.requests where requests.actor=v_actor and request_id=p_request;
 if found then
  if saved.action<>p_action or saved.payload<>p_payload then raise exception 'CP7_PERIOD_REQUEST_CHANGED';end if;
  if saved.response is null then raise exception 'CP7_PERIOD_REQUEST_INCOMPLETE';end if;
  return saved.response;
 end if;
 perform cp7_period.lock_current();perform cp7_period.access_now();
 state:=cp7_period.workspace(review_day);
 if state->>'review_token'<>p_payload->>'review_token' then raise exception 'CP7_PERIOD_REVIEW_CHANGED';end if;
 insert into cp7_period.requests(actor,request_id,action,payload) values(v_actor,p_request,p_action,p_payload);
 if p_action='CLOSE' then perform erp.close_accounting_through(target,p_payload->>'reason');
 else
  if state->'control'->>'closed_through' is null then raise exception 'CP7_PERIOD_NOT_CLOSED';end if;
  perform erp.reopen_accounting_through(target,p_payload->>'reason');
 end if;
 perform cp7_period.access_now();after_state:=cp7_period.workspace(review_day);
 if (after_state->'control'->>'closed_through')::date is distinct from target then raise exception 'CP7_PERIOD_OUTCOME_MISMATCH';end if;
 outcome:=jsonb_build_object('contract_version','cp7.period-outcome.v1','kind','COMMITTED_OUTCOME','action',p_action,'request_id',p_request,'closed_through',target,
  'version_token',after_state->'control'->>'version_token','filing_id',case when p_action='CLOSE' then after_state->'current_filing'->'id' else 'null'::jsonb end);
 if p_action='CLOSE' and outcome->>'filing_id' is null then raise exception 'CP7_PERIOD_FILING_MISSING';end if;
 update cp7_period.requests set response=outcome where requests.actor=v_actor and request_id=p_request;
 return outcome;
end $function$;
revoke create on schema "cp7_period" from postgres;
CREATE OR REPLACE FUNCTION cp7_reminder_native.accessory_target_now(p_run uuid, p_target text, p_material text, p_index integer)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
 SET "TimeZone" TO 'UTC'
AS $function$
declare a jsonb;j uuid;r jsonb;root uuid;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_schedule_native.access_now(false);
 if p_target!~'^[0-9a-f-]{36}:[0-9a-f-]{36}$'or p_material is not null and p_material!~'^[A-Za-z0-9_:-]{1,200}$'then raise exception 'CP7_REMINDER_V2_PAYLOAD';end if;
 select x.id into j from cp7_analysis_stage.jobs x where x.run_id=p_run and x.actor=cp7_request_context.uid()and x.state='DONE';
 perform cp7_analysis_stage.require_kept(j);
 if j is null or(select count(*)from cp7_analysis_stage.plan_targets t where t.job_id=j and t.target_key=p_target)<>1 then
  raise exception using errcode='42501',message='CP7_REMINDER_V2_CONDITION_UNAVAILABLE';end if;
 root:=split_part(p_target,':',1)::uuid;
 perform pg_advisory_xact_lock_shared(hashtextextended('FG_HPP_SALES_V2620C',0));
 perform pg_advisory_xact_lock_shared(hashtextextended('BF:COMMERCIAL_SKUS',0));
 perform pg_advisory_xact_lock_shared(hashtextextended('CP7:PROFILE:ROOT:'||root::text,0));
 perform pg_advisory_xact_lock_shared(hashtextextended('CP7:SCHEDULE:GLOBAL',0));
 perform pg_advisory_xact_lock_shared(hashtextextended('CP7:RULE_POLICY:ACCESSORY_NEED:GLOBAL:*',0));
 perform pg_advisory_xact_lock_shared(hashtextextended('CP7:RULE_POLICY:ACCESSORY_NEED:TARGET:'||p_target,0));
 perform cp7_reminder_native.accessory_category_locks(p_run,p_target);
 if cp7_schedule_native.access_now(false)is distinct from a then raise exception using errcode='42501',message='CP7_REMINDER_ACCESS_CHANGED';end if;
 select cp7_reminder_native.accessory_capture(j,p_target,p_material,p_index,clock_timestamp())into r;
 if cp7_schedule_native.access_now(false)is distinct from a then raise exception using errcode='42501',message='CP7_REMINDER_ACCESS_CHANGED';end if;
 return r;
end $function$;
CREATE OR REPLACE FUNCTION cp7_reminder_native.original_authority(p_run uuid)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
 SET "TimeZone" TO 'UTC'
AS $function$
declare a jsonb;k text;original jsonb;financial boolean;close_required boolean;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 if cp7_request_context.uid()is null or coalesce(cp7_request_context.jwt()->>'role','')<>'authenticated'then raise exception using errcode='42501',message='CP7_REMINDER_ACCESS_DENIED';end if;
 a:=erp.get_my_access_v1();
 if a->'allowed'is distinct from'true'::jsonb then raise exception using errcode='42501',message='CP7_REMINDER_ACCESS_DENIED';end if;
 if coalesce(a->'profile'->>'role_code','')not in('OWNER','ADMIN','STAFF')then raise exception using errcode='42501',message='CP7_REMINDER_INTERNAL_ROLE_REQUIRED';end if;
 foreach k in array array['master.product.view','production.wip.view','warehouse.stock.view','sales.invoice.view']loop
  if not erp.has_permission(k)then raise exception using errcode='42501',message='CP7_REMINDER_ACCESS_DENIED';end if;
 end loop;
 select jsonb_build_object('run_id',r.id,'analysis',jsonb_build_object(
   'snapshot',jsonb_build_object('source_hash',r.result->'snapshot'->'source_hash'),
   'semantic_hash',r.result->'semantic_hash',
   'scope',jsonb_build_object('actor_scope_id',r.actor),
   'recommendations',coalesce((select jsonb_agg(jsonb_build_object('target',jsonb_build_object('key',x.value->'target'->'key'))order by x.n)
    from jsonb_array_elements(r.result->'recommendations')with ordinality x(value,n)),'[]'::jsonb))),
  coalesce(r.facts->'financial_source','null')<>'null'::jsonb,
  coalesce(r.facts->'financial_source'->'report'->'close_preflight','null')<>'null'::jsonb
 into original,financial,close_required from cp7_analysis_native.runs r where r.id=p_run and r.actor=cp7_request_context.uid();
 if original is null then raise exception using errcode='42501',message='CP7_ANALYSIS_RUN_UNAVAILABLE';end if;
 if financial and(a->'profile'->>'role_code'not in('OWNER','ADMIN')or not erp.has_permission('finance.reports.view'))
  or close_required and not erp.has_permission('finance.period_close.manage')then raise exception using errcode='42501',message='CP7_ANALYSIS_FINANCE_ACCESS_DENIED';end if;
 -- Presence flags suffice for the post-wait capability guard. No financial
 -- amounts, cached condition rows or presumed freshness leave this helper.
 original:=original||jsonb_build_object('financial_source',case when financial then
  jsonb_build_object('report',jsonb_build_object('close_preflight',case when close_required then'{}'::jsonb else null end))else null end);
 foreach k in array array['master.product.view','production.wip.view','warehouse.stock.view','sales.invoice.view']loop
  if not erp.has_permission(k)then raise exception using errcode='42501',message='CP7_REMINDER_ACCESS_DENIED';end if;
 end loop;
 if financial and not erp.has_permission('finance.reports.view')or close_required and not erp.has_permission('finance.period_close.manage')
  then raise exception using errcode='42501',message='CP7_ANALYSIS_FINANCE_ACCESS_DENIED';end if;
 if erp.get_my_access_v1()is distinct from a then raise exception using errcode='42501',message='CP7_REMINDER_ACCESS_CHANGED';end if;
 return jsonb_build_object('access',a,'analysis',original);
end $function$;
grant usage on schema cp7_request_context to "cp7_payable_read";
grant execute on function cp7_request_context."jwt"() to "cp7_payable_read";
grant execute on function cp7_request_context."uid"() to "cp7_payable_read";
CREATE OR REPLACE FUNCTION cp7_reminder_native.payable_source()
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO ''
 SET "TimeZone" TO 'UTC'
AS $function$
declare a jsonb;index jsonb;vendor jsonb;native jsonb;balances jsonb:='[]';rows jsonb;suppliers jsonb;
 total bigint;posted bigint;at date:=(statement_timestamp()at time zone'Asia/Jakarta')::date;
begin
 if cp7_request_context.uid()is null or coalesce(cp7_request_context.jwt()->>'role','')<>'authenticated'then
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
end $function$;
grant usage on schema cp7_request_context to "cp7_sales_read";
grant execute on function cp7_request_context."jwt"() to "cp7_sales_read";
grant execute on function cp7_request_context."uid"() to "cp7_sales_read";
CREATE OR REPLACE FUNCTION cp7_sales.access_now()
 RETURNS boolean
 LANGUAGE plpgsql
 STABLE
 SET search_path TO ''
AS $function$
declare a jsonb;
begin
 if cp7_request_context.uid() is null or coalesce(cp7_request_context.jwt()->>'role','')<>'authenticated' then raise exception using errcode='42501',message='CP7_SALES_ACCESS_DENIED';end if;
 a:=erp.get_my_access_v1();
 if a->'allowed' is distinct from 'true'::jsonb or not erp.has_permission('sales.invoice.view') then raise exception using errcode='42501',message='CP7_SALES_ACCESS_DENIED';end if;
 return erp.has_permission('finance.ar.view');
end $function$;
CREATE OR REPLACE FUNCTION cp7_sales.command(p_action text, p_payload jsonb, p_request uuid, p_expected text)
 RETURNS jsonb
 LANGUAGE plpgsql
 SET search_path TO ''
AS $function$
declare a jsonb;old cp7_sales.requests;r jsonb;
begin
 if current_setting('transaction_isolation')<>'read committed' then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_sales.command_access(p_action);
 if p_request is null or (p_action='CREATE' and p_expected is not null) or(p_action<>'CREATE' and(p_expected is null or p_expected!~'^[1-9][0-9]{0,18}$')) then raise exception 'CP7_SALES_COMMAND_FIELDS';end if;
 if p_action in('CREATE','EDIT') then
  perform cp7_sales.validate_draft(p_payload,p_action='EDIT');
 elsif p_action in('PAYMENT','PAYMENT_REVERSE') then
  perform cp7_sales.validate_payment(p_payload,p_action='PAYMENT_REVERSE');
 elsif p_action in('RETURN','RETURN_REVERSE') then
  perform cp7_sales.validate_return(p_payload,p_action='RETURN_REVERSE');
 else
  if jsonb_typeof(p_payload) is distinct from 'object' or not p_payload ?& array['sale_id','review_token','change_reason']
   or exists(select 1 from jsonb_each(p_payload) e where e.key not in('sale_id','review_token','change_reason') or jsonb_typeof(e.value)<>'string')
   or coalesce(p_payload->>'sale_id','')!~*'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
   or coalesce(p_payload->>'review_token','')!~'^[a-f0-9]{32}$'
   or length(btrim(p_payload->>'change_reason')) not between 5 and 1000 then raise exception 'CP7_SALES_COMMAND_FIELDS';end if;
 end if;
 insert into cp7_sales.requests values(cp7_request_context.uid(),p_request,p_action,p_payload,p_expected,null) on conflict do nothing;
 select * into old from cp7_sales.requests where actor=cp7_request_context.uid() and request_id=p_request for update;
 if old.action<>p_action or old.payload is distinct from p_payload or old.expected_version is distinct from p_expected then raise exception 'CP7_SALES_REQUEST_CHANGED';end if;
 if cp7_sales.command_access(p_action) is distinct from a then raise exception using errcode='42501',message='CP7_SALES_ACCESS_CHANGED';end if;
 if old.response is not null then return old.response;end if;
 insert into cp7_sales.command_context values(pg_backend_pid(),txid_current(),cp7_request_context.uid(),(p_payload->>'sale_id')::uuid,p_action);
 r:=cp7_sales.apply_command(p_action,p_payload,p_request,p_expected);
 delete from cp7_sales.command_context where backend_pid=pg_backend_pid() and transaction_id=txid_current();
 if cp7_sales.command_access(p_action) is distinct from a then raise exception using errcode='42501',message='CP7_SALES_ACCESS_CHANGED';end if;
 r:=r||jsonb_build_object('contract_version','cp7.sales-outcome.v1','kind','COMMITTED_OUTCOME','action',p_action,'request_id',p_request);
 update cp7_sales.requests set response=r where actor=cp7_request_context.uid() and request_id=p_request;
 return r;
end $function$;
CREATE OR REPLACE FUNCTION cp7_sales.command_access(p_action text)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO ''
AS $function$
declare a jsonb;
begin
 -- Read the complete current access once per invocation. access_now() already
 -- obtains that same document; invoking it here and then reading it again
 -- multiplies full permission-list reads in each native account/HPP guard.
 -- This is never a command/transaction cache: every post-wait guard invocation
 -- still reads current authority and calls the native fine permission checks.
 if cp7_request_context.uid() is null or coalesce(cp7_request_context.jwt()->>'role','')<>'authenticated' then raise exception using errcode='42501',message='CP7_SALES_ACCESS_DENIED';end if;
 a:=erp.get_my_access_v1();
 if a->'allowed' is distinct from 'true'::jsonb or not erp.has_permission('sales.invoice.view') then raise exception using errcode='42501',message='CP7_SALES_ACCESS_DENIED';end if;
 if not erp.has_permission('finance.ar.view') or p_action is null or p_action not in('CREATE','EDIT','POST','CANCEL','PAYMENT','PAYMENT_REVERSE','RETURN','RETURN_REVERSE','SALE_REVERSE')
  or not erp.has_permission(case when p_action='POST' then 'sales.invoice.post' when p_action='CREATE' then 'sales.invoice.create' when p_action='PAYMENT' then 'sales.payment.create' when p_action='PAYMENT_REVERSE' then 'sales.payment.reverse' when p_action='RETURN' then 'sales.return.create' when p_action='RETURN_REVERSE' then 'sales.return.reverse' when p_action='SALE_REVERSE' then 'sales.invoice.reverse' else 'sales.invoice.edit_draft' end)
  or(p_action in('PAYMENT','PAYMENT_REVERSE') and not erp.has_permission('sales.payment.view'))
  or(p_action='PAYMENT' and not erp.has_permission('sales.payment.post'))
  or(p_action in('RETURN','RETURN_REVERSE') and not erp.has_permission('sales.return.view'))
  or(p_action='RETURN' and not erp.has_permission('sales.return.post'))
 then raise exception using errcode='42501',message='CP7_SALES_WRITE_DENIED';end if;
 if p_action in('PAYMENT_REVERSE','RETURN_REVERSE','SALE_REVERSE') and coalesce(a->'profile'->>'role_code','') not in('OWNER','ADMIN') then raise exception using errcode='42501',message='CP7_SALES_OWNER_ADMIN_REQUIRED';end if;
 return a;
end $function$;
CREATE OR REPLACE FUNCTION cp7_sales.command_allowed(p_action text)
 RETURNS boolean
 LANGUAGE plpgsql
 STABLE
 SET search_path TO ''
AS $function$
begin
 if cp7_request_context.uid() is null or coalesce(cp7_request_context.jwt()->>'role','')<>'authenticated' then raise exception using errcode='42501',message='CP7_SALES_ACCESS_DENIED';end if;
 -- Native has_permission(NULL) can only be true for its current active,
 -- protected OWNER universal grant here: service JWTs were refused above and
 -- a SQL NULL cannot equal a stored permission key. Read that Native decision
 -- anew; do not duplicate its role formula or cache authority. Invalid actions
 -- still follow the unchanged exact refusal checks below.
 if p_action in('CREATE','EDIT','POST','CANCEL','PAYMENT','PAYMENT_REVERSE','RETURN','RETURN_REVERSE','SALE_REVERSE') and erp.has_permission(null::text) then return true;end if;
 -- Native has_permission's positive invoice-view result also requires the
 -- same unique active app user and active role as get_my_access.allowed.
 if not erp.has_permission('sales.invoice.view') then raise exception using errcode='42501',message='CP7_SALES_ACCESS_DENIED';end if;
 if not erp.has_permission('finance.ar.view') or p_action is null or p_action not in('CREATE','EDIT','POST','CANCEL','PAYMENT','PAYMENT_REVERSE','RETURN','RETURN_REVERSE','SALE_REVERSE')
  or not erp.has_permission(case when p_action='POST' then 'sales.invoice.post' when p_action='CREATE' then 'sales.invoice.create' when p_action='PAYMENT' then 'sales.payment.create' when p_action='PAYMENT_REVERSE' then 'sales.payment.reverse' when p_action='RETURN' then 'sales.return.create' when p_action='RETURN_REVERSE' then 'sales.return.reverse' when p_action='SALE_REVERSE' then 'sales.invoice.reverse' else 'sales.invoice.edit_draft' end)
  or(p_action in('PAYMENT','PAYMENT_REVERSE') and not erp.has_permission('sales.payment.view'))
  or(p_action='PAYMENT' and not erp.has_permission('sales.payment.post'))
  or(p_action in('RETURN','RETURN_REVERSE') and not erp.has_permission('sales.return.view'))
  or(p_action='RETURN' and not erp.has_permission('sales.return.post'))
 then raise exception using errcode='42501',message='CP7_SALES_WRITE_DENIED';end if;
 if p_action in('PAYMENT_REVERSE','RETURN_REVERSE','SALE_REVERSE') and coalesce(erp.current_app_role(),'') not in('OWNER','ADMIN') then raise exception using errcode='42501',message='CP7_SALES_OWNER_ADMIN_REQUIRED';end if;
 return true;
end $function$;
CREATE OR REPLACE FUNCTION cp7_stock_formula.access_now(p_manage boolean)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
 SET "TimeZone" TO 'UTC'
AS $function$
declare a jsonb;
begin
 if cp7_request_context.uid()is null or coalesce(cp7_request_context.jwt()->>'role','')<>'authenticated'then raise exception using errcode='42501',message='CP7_FORMULA_ACCESS_DENIED';end if;
 a:=erp.get_my_access_v1();
 if a->'allowed'is distinct from'true'::jsonb or erp.has_permission('warehouse.fg.view')is not true
  or(p_manage and coalesce(a->'profile'->>'role_code','')not in('OWNER','ADMIN'))then
  raise exception using errcode='42501',message='CP7_FORMULA_ACCESS_DENIED';end if;
 return a;
end $function$;
CREATE OR REPLACE FUNCTION cp7_stock_formula.material_access_now(p_type text, p_manage boolean)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
 SET "TimeZone" TO 'UTC'
AS $function$
declare a jsonb;
begin
 if cp7_request_context.uid()is null or coalesce(cp7_request_context.jwt()->>'role','')<>'authenticated'then raise exception using errcode='42501',message='CP7_FORMULA_ACCESS_DENIED';end if;
 a:=erp.get_my_access_v1();
 if a->'allowed'is distinct from'true'::jsonb or p_type is null or p_type not in('FABRIC','ACCESSORY')
  or(p_type='FABRIC'and(erp.has_permission('warehouse.material.view')is not true or erp.has_permission('master.fabric.view')is not true))
  or(p_type='ACCESSORY'and erp.has_permission('warehouse.accessory.view')is not true)
  or(p_manage and coalesce(a->'profile'->>'role_code','')not in('OWNER','ADMIN'))then
  raise exception using errcode='42501',message='CP7_FORMULA_ACCESS_DENIED';end if;
 return a;
end $function$;
CREATE OR REPLACE FUNCTION cp7_stock_formula.save_manual(p jsonb, p_request uuid)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
 SET "TimeZone" TO 'UTC'
AS $function$
declare a jsonb;h text;prev cp7_stock_formula.manual_points;root uuid;cur_rev integer;prod record;row cp7_stock_formula.manual_points;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_stock_formula.access_now(true);
 if p_request is null then raise exception using errcode='22023',message='CP7_FORMULA_REQUEST_REQUIRED';end if;
 h:=encode(sha256(convert_to(coalesce(p::text,''),'UTF8')),'hex');
 perform pg_advisory_xact_lock(hashtextextended('CP7:FORMULA:FG',0));
 select*into prev from cp7_stock_formula.manual_points x where x.request_id=p_request;
 if found then
  if prev.actor<>cp7_request_context.uid()or prev.request_hash<>h then raise exception using errcode='22023',message='CP7_FORMULA_REQUEST_REUSED';end if;
  return jsonb_build_object('replay',true,'root_id',prev.root_id,'revision',prev.revision,'reorder_point_pcs',prev.reorder_point_pcs);
 end if;
 if jsonb_typeof(p)is distinct from'object'or not p?&array['root_id','expected_revision','reorder_point_pcs','reason']
  or exists(select 1 from jsonb_object_keys(p)k where k not in('root_id','expected_revision','reorder_point_pcs','reason'))
  or jsonb_typeof(p->'root_id')<>'string'or(p->>'root_id')!~'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
  or jsonb_typeof(p->'expected_revision')<>'number'or(p->>'expected_revision')!~'^[0-9]{1,9}$'
  or jsonb_typeof(p->'reorder_point_pcs')not in('number','null')or coalesce(p->>'reorder_point_pcs','0')!~'^[0-9]{1,8}$'
  or jsonb_typeof(p->'reason')<>'string'or length(btrim(p->>'reason'))not between 1 and 500
 then raise exception using errcode='22023',message='CP7_FORMULA_MANUAL_INVALID';end if;
 root:=(p->>'root_id')::uuid;
 select p2.id,p2.size_id into prod from erp.products p2 where coalesce(p2.identity_root_id,p2.id)=root and p2.is_active
  and p2.effective_from<=clock_timestamp()and(p2.effective_to is null or p2.effective_to>clock_timestamp());
 if prod.id is null or(select count(*)from erp.products q where coalesce(q.identity_root_id,q.id)=root and q.effective_from<=clock_timestamp()
  and(q.effective_to is null or q.effective_to>clock_timestamp()))<>1 then raise exception using errcode='22023',message='CP7_FORMULA_ITEM_UNKNOWN';end if;
 select coalesce(max(x.revision),0)into cur_rev from cp7_stock_formula.manual_points x where x.root_id=root;
 if cur_rev<>(p->>'expected_revision')::integer then raise exception using errcode='40001',message='CP7_FORMULA_MANUAL_STALE';end if;
 insert into cp7_stock_formula.manual_points(root_id,revision,size_id,product_version_id,reorder_point_pcs,reason,actor,request_id,request_hash)
 values(root,cur_rev+1,prod.size_id,prod.id,(p->>'reorder_point_pcs')::integer,btrim(p->>'reason'),cp7_request_context.uid(),p_request,h)returning*into row;
 perform cp7_stock_formula.compute(clock_timestamp(),interval'1 second');
 return jsonb_build_object('replay',false,'root_id',row.root_id,'revision',row.revision,'reorder_point_pcs',row.reorder_point_pcs,
  'evaluation',(select to_jsonb(e)from cp7_stock_formula.evaluations e where e.root_id=root));
end $function$;
CREATE OR REPLACE FUNCTION cp7_stock_formula.save_material(p jsonb, p_request uuid)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
 SET "TimeZone" TO 'UTC'
AS $function$
declare a jsonb;h text;prev cp7_stock_formula.material_settings;mat record;cur_rev integer;row cp7_stock_formula.material_settings;lead numeric;manual numeric;
 moq numeric;usage_month numeric;buffer numeric;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 if jsonb_typeof(p)is distinct from'object'or not p?&array['material_id','expected_revision','lead_days','manual_point','reason']
  or exists(select 1 from jsonb_object_keys(p)k where k not in('material_id','expected_revision','lead_days','manual_point','reason','moq',
   'usage_month_qty','buffer_days'))
  or jsonb_typeof(p->'material_id')<>'string'or(p->>'material_id')!~'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
  or jsonb_typeof(p->'expected_revision')<>'number'or(p->>'expected_revision')!~'^[0-9]{1,9}$'
  or jsonb_typeof(p->'lead_days')not in('string','null')or coalesce(p->>'lead_days','1')!~'^[0-9]{1,3}(\.[0-9]{1,2})?$'
  or jsonb_typeof(p->'manual_point')not in('string','null')or coalesce(p->>'manual_point','0')!~'^[0-9]{1,13}(\.[0-9]{1,4})?$'
  or(p?'moq'and(jsonb_typeof(p->'moq')not in('string','null')or coalesce(p->>'moq','1')!~'^[0-9]{1,13}(\.[0-9]{1,4})?$'))
  or(p?'usage_month_qty'and(jsonb_typeof(p->'usage_month_qty')not in('string','null')or coalesce(p->>'usage_month_qty','1')!~'^[0-9]{1,13}(\.[0-9]{1,4})?$'))
  or(p?'buffer_days'and(jsonb_typeof(p->'buffer_days')not in('string','null')or coalesce(p->>'buffer_days','0')!~'^[0-9]{1,3}(\.[0-9]{1,2})?$'))
  or jsonb_typeof(p->'reason')<>'string'or length(btrim(p->>'reason'))not between 1 and 500
 then raise exception using errcode='22023',message='CP7_FORMULA_MATERIAL_INVALID';end if;
 select m.id,m.material_type::text material_type into mat from erp.materials m
  where m.id=(p->>'material_id')::uuid and m.is_active and m.material_type in('FABRIC','ACCESSORY');
 if mat.id is null then raise exception using errcode='22023',message='CP7_FORMULA_ITEM_UNKNOWN';end if;
 a:=cp7_stock_formula.material_access_now(mat.material_type,true);
 if p_request is null then raise exception using errcode='22023',message='CP7_FORMULA_REQUEST_REQUIRED';end if;
 lead:=(p->>'lead_days')::numeric;manual:=(p->>'manual_point')::numeric;
 moq:=(p->>'moq')::numeric;usage_month:=(p->>'usage_month_qty')::numeric;buffer:=(p->>'buffer_days')::numeric;
 if(lead is not null and(lead<=0 or lead>365))or(moq is not null and moq<=0)or(usage_month is not null and usage_month<=0)
  or(buffer is not null and buffer>365)
  or(mat.material_type='FABRIC'and(manual is not null or moq is not null or usage_month is not null or buffer is not null))then
  raise exception using errcode='22023',message='CP7_FORMULA_MATERIAL_INVALID';end if;
 h:=encode(sha256(convert_to(coalesce(p::text,''),'UTF8')),'hex');
 perform pg_advisory_xact_lock(hashtextextended('CP7:FORMULA:FG',0));
 select*into prev from cp7_stock_formula.material_settings x where x.request_id=p_request;
 if found then
  if prev.actor<>cp7_request_context.uid()or prev.request_hash<>h then raise exception using errcode='22023',message='CP7_FORMULA_REQUEST_REUSED';end if;
  return jsonb_build_object('replay',true,'material_id',prev.material_id,'revision',prev.revision);
 end if;
 select coalesce(max(x.revision),0)into cur_rev from cp7_stock_formula.material_settings x where x.material_id=mat.id;
 if cur_rev<>(p->>'expected_revision')::integer then raise exception using errcode='40001',message='CP7_FORMULA_MATERIAL_STALE';end if;
 insert into cp7_stock_formula.material_settings(material_id,revision,lead_days,manual_point,moq,usage_month_qty,buffer_days,reason,actor,request_id,request_hash)
 values(mat.id,cur_rev+1,lead,manual,moq,usage_month,buffer,btrim(p->>'reason'),cp7_request_context.uid(),p_request,h)returning*into row;
 perform cp7_stock_formula.compute(clock_timestamp(),interval'1 second');
 return jsonb_build_object('replay',false,'material_id',row.material_id,'revision',row.revision,
  'evaluation',(select to_jsonb(e)from cp7_stock_formula.material_evaluations e where e.material_id=mat.id));
end $function$;
CREATE OR REPLACE FUNCTION cp7_stock_formula.save_settings(p jsonb, p_request uuid)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
 SET "TimeZone" TO 'UTC'
AS $function$
declare a jsonb;h text;prev cp7_stock_formula.settings;cur_rev bigint;row cp7_stock_formula.settings;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_stock_formula.access_now(true);
 if p_request is null then raise exception using errcode='22023',message='CP7_FORMULA_REQUEST_REQUIRED';end if;
 h:=encode(sha256(convert_to(coalesce(p::text,''),'UTF8')),'hex');
 perform pg_advisory_xact_lock(hashtextextended('CP7:FORMULA:FG',0));
 select*into prev from cp7_stock_formula.settings x where x.request_id=p_request;
 if found then
  if prev.actor<>cp7_request_context.uid()or prev.request_hash<>h then raise exception using errcode='22023',message='CP7_FORMULA_REQUEST_REUSED';end if;
  return jsonb_build_object('replay',true,'settings',cp7_stock_formula.current_settings());
 end if;
 if jsonb_typeof(p)is distinct from'object'or not p?&array['expected_revision','service_level','window_days','reason']
  or exists(select 1 from jsonb_object_keys(p)k where k not in('expected_revision','service_level','window_days','reason'))
  or jsonb_typeof(p->'expected_revision')<>'number'or(p->>'expected_revision')!~'^[0-9]{1,9}$'
  or jsonb_typeof(p->'service_level')<>'string'or p->>'service_level'not in('0.90','0.95','0.99')
  or jsonb_typeof(p->'window_days')<>'number'or(p->>'window_days')!~'^[0-9]{1,3}$'or(p->>'window_days')::integer not between 14 and 365
  or jsonb_typeof(p->'reason')<>'string'or length(btrim(p->>'reason'))not between 1 and 500
 then raise exception using errcode='22023',message='CP7_FORMULA_SETTINGS_INVALID';end if;
 select coalesce(max(x.revision),0)into cur_rev from cp7_stock_formula.settings x;
 if cur_rev<>(p->>'expected_revision')::bigint then raise exception using errcode='40001',message='CP7_FORMULA_SETTINGS_STALE';end if;
 insert into cp7_stock_formula.settings(revision,service_level,window_days,reason,actor,request_id,request_hash)
 values(cur_rev+1,(p->>'service_level')::numeric,(p->>'window_days')::integer,btrim(p->>'reason'),cp7_request_context.uid(),p_request,h)returning*into row;
 perform cp7_stock_formula.compute(clock_timestamp(),interval'1 second');
 return jsonb_build_object('replay',false,'settings',cp7_stock_formula.current_settings());
end $function$;
grant execute on function cp7_analysis_stage.bounds() to postgres;
grant usage on schema "cp7_material" to postgres;
grant select ("backend_pid", "transaction_id", "actor", "action", "permission_key") on table "cp7_material"."execution_context" to postgres;
grant usage on schema "cp7_payroll" to postgres;
grant select ("backend_pid", "transaction_id", "actor", "action", "permission_key") on table "cp7_payroll"."execution_context" to postgres;
grant usage on schema "cp7_supplier_return" to postgres;
grant select ("backend_pid", "transaction_id", "actor", "action", "permission_key") on table "cp7_supplier_return"."execution_context" to postgres;
