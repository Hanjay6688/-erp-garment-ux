-- Paid BS redye is its own real service attempt, never a synthetic production receipt.
create table erp.be_redye_services_v1(
 id uuid primary key references erp.rework_orders(id),vendor_id uuid not null references erp.laundry_vendors(id),
 wash_process_id uuid not null references erp.wash_processes(id),po_id uuid not null references erp.production_orders(id),
 sent_at timestamptz not null,qty integer not null check(qty>0),rate_version_id uuid references erp.laundry_vendor_rate_versions(id),
 initial_rate numeric(18,6) check(initial_rate>=0),created_by uuid,created_at timestamptz not null default statement_timestamp()
);
create table erp.be_redye_price_events_v1(
 id uuid primary key default gen_random_uuid(),service_id uuid not null unique references erp.be_redye_services_v1(id),
 rate numeric(18,6) not null check(rate>=0),reason text not null,created_by uuid,created_at timestamptz not null default statement_timestamp()
);
create trigger be_redye_service_fact before insert or update or delete on erp.be_redye_services_v1 for each row execute function erp.be_guard_fact_v1();
create trigger be_redye_price_fact before insert or update or delete on erp.be_redye_price_events_v1 for each row execute function erp.be_guard_fact_v1();
alter table erp.bd_laundry_invoice_lines_v1 add column rework_service_id uuid references erp.be_redye_services_v1(id);
do $source_check$
declare n text;
begin
 select conname into strict n from pg_constraint where conrelid='erp.bd_laundry_invoice_lines_v1'::regclass
   and contype='c' and pg_get_constraintdef(oid) like '%num_nonnulls(receipt_line_id, opening_uninvoiced_id)%';
 execute format('alter table erp.bd_laundry_invoice_lines_v1 drop constraint %I',n);
end;$source_check$;
alter table erp.bd_laundry_invoice_lines_v1 add constraint be_invoice_one_source check(num_nonnulls(receipt_line_id,opening_uninvoiced_id,rework_service_id)=1);
create index be_invoice_redye_source on erp.bd_laundry_invoice_lines_v1(rework_service_id);

CREATE OR REPLACE FUNCTION erp.be_redye_rate_v1(p_service uuid)
 RETURNS numeric LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$ select coalesce(e.rate,s.initial_rate) from erp.be_redye_services_v1 s left join erp.be_redye_price_events_v1 e on e.service_id=s.id where s.id=p_service $function$;
CREATE OR REPLACE FUNCTION erp.be_redye_estimate_v1(p_service uuid)
 RETURNS numeric LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$ select round(s.qty*erp.be_redye_rate_v1(s.id),2) from erp.be_redye_services_v1 s join erp.rework_orders r on r.id=s.id where s.id=p_service and r.status<>'CANCELLED' $function$;
CREATE OR REPLACE FUNCTION erp.be_redye_cost_v1(p_service uuid)
 RETURNS numeric LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$ select coalesce(erp.be_redye_estimate_v1(p_service),0)+coalesce((select sum(l.product_variance) from erp.bd_laundry_invoice_lines_v1 l join erp.bd_laundry_invoices_v1 i on i.id=l.invoice_id where l.rework_service_id=p_service and i.status='POSTED'),0) $function$;
CREATE OR REPLACE FUNCTION erp.be_redye_po_cost_v1(p_po uuid)
 RETURNS numeric LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$ select coalesce(sum(erp.be_redye_cost_v1(s.id)),0) from erp.be_redye_services_v1 s join erp.rework_orders r on r.id=s.id where s.po_id=p_po and r.status<>'CANCELLED' $function$;
CREATE OR REPLACE FUNCTION erp.be_redye_accrual_v1(p_po uuid)
 RETURNS numeric LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$ select coalesce(sum(coalesce(erp.be_redye_estimate_v1(s.id),0)-coalesce((select sum(l.released_estimate) from erp.bd_laundry_invoice_lines_v1 l join erp.bd_laundry_invoices_v1 i on i.id=l.invoice_id where i.status='POSTED' and l.rework_service_id=s.id),0)),0)
 from erp.be_redye_services_v1 s join erp.rework_orders r on r.id=s.id where s.po_id=p_po and r.status<>'CANCELLED' $function$;
CREATE OR REPLACE FUNCTION erp.be_redye_capacity_v1(p_service uuid,p_category text)
 RETURNS integer LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$ select case when r.status<>'COMPLETED' or not r.cost_posted then 0 when p_category='GOOD' then r.qty_good_returned when p_category='BS' then r.qty_bs_returned else 0 end from erp.rework_orders r where r.id=p_service $function$;
CREATE OR REPLACE FUNCTION erp.be_redye_billed_v1(p_service uuid,p_category text)
 RETURNS integer LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$ select coalesce(sum(l.qty),0)::int from erp.bd_laundry_invoice_lines_v1 l join erp.bd_laundry_invoices_v1 i on i.id=l.invoice_id where i.status='POSTED' and l.rework_service_id=p_service and l.line_kind='BILL' and l.category=p_category $function$;
CREATE OR REPLACE FUNCTION erp.be_redye_resync_v1(p_service uuid,p_date date)
 RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare v_po uuid;
begin
 select po_id into v_po from erp.be_redye_services_v1 where id=p_service;
 if v_po is null then return;end if;
 perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
 perform erp.sync_laundry_accrual(v_po,p_date);
 if exists(select 1 from erp.fg_lots where po_id=v_po) then
   perform erp.rebuild_po_hpp(v_po,'BE celup ulang: sumber jasa/invoice');perform erp.propagate_conversion_hpp_for_po(v_po);perform erp.sync_po_hpp_to_gl(v_po,p_date);
 end if;
end;$function$;

CREATE OR REPLACE FUNCTION erp.be_save_redye_v1(p_payload jsonb,p_request uuid)
 RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare v_result jsonb;v_id uuid;r erp.rework_orders%rowtype;b erp.bs_cases%rowtype;v_process uuid;v_n int;v_rate numeric;v_version uuid;
begin
 perform erp.require_owner_admin();perform erp.require_permission('production.bs_rework.create');perform erp.require_permission('finance.hpp.manage');
 perform erp._cp3_assert_closed_json_object(p_payload,array['order','target_product_id','wash_process_id','price_status','reason'],array['order','target_product_id','wash_process_id','price_status','reason'],'celup ulang berbayar');
 if p_payload->'order'->>'destination_type' is distinct from 'LAUNDRY' then raise exception 'BE_REDYE_VENDOR_REQUIRED';end if;
 v_process:=erp.bd_uuid_v1(p_payload,'wash_process_id',true);
 if not exists(select 1 from erp.wash_processes where id=v_process and is_active) then raise exception 'BE_PROCESS_INACTIVE';end if;
 -- The ordinary binding helper is called with its own closed payload; no arbitrary conversion cost is accepted.
 v_result:=erp.be_save_rework_v1(p_payload-'wash_process_id'-'price_status',p_request,true);v_id:=(v_result->>'rework_id')::uuid;
 select * into r from erp.rework_orders where id=v_id;select * into b from erp.bs_cases where id=r.bs_case_id;
 if b.po_id is null then raise exception 'BE_REDYE_PO_SOURCE_REQUIRED';end if;
 select count(*)::int into v_n from erp.laundry_vendor_rate_versions where vendor_id=r.vendor_id and wash_process_id=v_process
   and effective_from<=r.physical_sent_at and (effective_to is null or effective_to>r.physical_sent_at);
 if p_payload->>'price_status' not in('KNOWN','UNKNOWN') then raise exception 'BE_PRICE_STATUS_REQUIRED';end if;
 if v_n=0 and p_payload->>'price_status'<>'UNKNOWN' then raise exception 'BD_RATE_NOT_EXACT';end if;
 if v_n=1 and p_payload->>'price_status'='UNKNOWN' then raise exception 'BE_PRICE_ALREADY_KNOWN';end if;
 if v_n>1 then raise exception 'BD_RATE_NOT_EXACT: tarif vendor/proses bertumpuk';end if;
 if v_n=1 then select id,rate_per_pcs into v_version,v_rate from erp.laundry_vendor_rate_versions where vendor_id=r.vendor_id and wash_process_id=v_process
   and effective_from<=r.physical_sent_at and (effective_to is null or effective_to>r.physical_sent_at);end if;
 insert into erp.be_redye_services_v1(id,vendor_id,wash_process_id,po_id,sent_at,qty,rate_version_id,initial_rate,created_by)
 values(r.id,r.vendor_id,v_process,b.po_id,r.physical_sent_at,r.qty_sent,v_version,v_rate,erp.current_app_user_id());
 perform erp.be_redye_resync_v1(r.id,erp._cp3_business_date(r.physical_sent_at));
 return v_result||jsonb_build_object('service_id',r.id,'price_status',case when v_rate is null then 'UNKNOWN' else 'KNOWN' end,'rate',v_rate::text);
end;$function$;

CREATE OR REPLACE FUNCTION erp.be_set_redye_price_v1(p_payload jsonb,p_request uuid)
 RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare s erp.be_redye_services_v1%rowtype;v_rate numeric;
begin
 perform erp.require_owner_admin();perform erp.require_permission('finance.hpp.manage');
 perform erp._cp3_assert_closed_json_object(p_payload,array['service_id','rate','reason'],array['service_id','rate','reason'],'harga jasa celup');
 select * into s from erp.be_redye_services_v1 where id=erp.bd_uuid_v1(p_payload,'service_id',true) for update;
 if s.id is null then raise exception 'BE_SERVICE_NOT_FOUND';end if;
 if erp.be_redye_rate_v1(s.id) is not null then raise exception 'BE_PRICE_ALREADY_KNOWN: koreksi harga memakai invoice sumber';end if;
 v_rate:=erp.bd_amount_v1(p_payload->'rate','rate',false);
 insert into erp.be_redye_price_events_v1(service_id,rate,reason,created_by) values(s.id,v_rate,erp.bc_text_v1(p_payload,'reason',true,1000),erp.current_app_user_id());
 perform erp.be_redye_resync_v1(s.id,erp._cp3_business_date(statement_timestamp()));
 return jsonb_build_object('service_id',s.id,'rate',v_rate::text,'price_status','KNOWN');
end;$function$;

-- Called under the invoice's source locks, before any invoice journal is posted.
CREATE OR REPLACE FUNCTION erp.be_invoice_redye_line_v1(p_line uuid,p_billable jsonb,p_dec06 jsonb)
 RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare l erp.bd_laundry_invoice_lines_v1%rowtype;i erp.bd_laundry_invoices_v1%rowtype;s erp.be_redye_services_v1%rowtype;
 v_billed int;v_cap int;v_complete bool;v_prior numeric;v_pool numeric;v_rel numeric;v_net numeric;v_paid bool;v_floor numeric;
begin
 select * into l from erp.bd_laundry_invoice_lines_v1 where id=p_line;select * into i from erp.bd_laundry_invoices_v1 where id=l.invoice_id;
 select * into s from erp.be_redye_services_v1 where id=l.rework_service_id for update;
 if s.id is null or s.vendor_id<>i.vendor_id then raise exception 'BD_INVOICE_VENDOR';end if;
 if i.invoice_date<erp._cp3_business_date((select completed_at from erp.rework_orders where id=s.id)) then raise exception 'BE_INVOICE_BEFORE_SERVICE';end if;
 v_pool:=erp.be_redye_estimate_v1(s.id);
 if v_pool is null then raise exception 'BE_PRICE_UNKNOWN_SET_FIRST';end if;
 if not p_billable @> to_jsonb(l.category) then raise exception 'BD_CATEGORY_NOT_BILLABLE';end if;
 select coalesce(sum(x.released_estimate),0) into v_prior from erp.bd_laundry_invoice_lines_v1 x join erp.bd_laundry_invoices_v1 y on y.id=x.invoice_id
   where x.rework_service_id=s.id and (y.status='POSTED' or (y.id=i.id and x.line_no<l.line_no));
 if l.line_kind='BILL' then
   v_cap:=erp.be_redye_capacity_v1(s.id,l.category);
   v_billed:=erp.be_redye_billed_v1(s.id,l.category)+coalesce((select sum(x.qty) from erp.bd_laundry_invoice_lines_v1 x where x.invoice_id=i.id and x.rework_service_id=s.id and x.category=l.category and x.line_kind='BILL' and x.line_no<l.line_no),0);
   if v_billed+l.qty>v_cap then raise exception 'BD_INVOICE_CAPACITY';end if;
   select bool_and(erp.be_redye_billed_v1(s.id,c)+coalesce((select sum(x.qty) from erp.bd_laundry_invoice_lines_v1 x where x.invoice_id=i.id and x.rework_service_id=s.id and x.category=c and x.line_kind='BILL' and x.line_no<=l.line_no),0)>=erp.be_redye_capacity_v1(s.id,c))
     into v_complete from jsonb_array_elements_text(p_billable) c;
   v_rel:=case when v_complete then v_pool-v_prior else least(round(v_pool*l.qty/s.qty,2),v_pool-v_prior) end;
 else
   if not exists(select 1 from erp.bd_laundry_invoice_lines_v1 x join erp.bd_laundry_invoices_v1 y on y.id=x.invoice_id where x.rework_service_id=s.id and x.line_kind='BILL' and y.status='POSTED') then raise exception 'BD_CORRECTION_WITHOUT_BILL';end if;
   select exists(select 1 from erp.bd_laundry_invoice_lines_v1 x join erp.bd_laundry_invoices_v1 y on y.id=x.invoice_id join erp.vendor_payments p on p.vendor_invoice_id=y.id and p.status='POSTED' where x.rework_service_id=s.id and y.status='POSTED') into v_paid;
   if v_paid and p_dec06->>'after_payment'<>'CORRECTION_DOCUMENT' then raise exception 'BD_PAID_CORRECTION_REFUSED';end if;
   select coalesce(sum(x.net_amount),0) into v_floor from erp.bd_laundry_invoice_lines_v1 x join erp.bd_laundry_invoices_v1 y on y.id=x.invoice_id where x.rework_service_id=s.id and y.status='POSTED';
   v_floor:=v_floor+coalesce((select sum(x.amount) from erp.bd_laundry_invoice_lines_v1 x where x.invoice_id=i.id and x.rework_service_id=s.id and x.line_no<=l.line_no),0);
   if v_floor<0 then raise exception 'BD_CORRECTION_BELOW_ZERO';end if;
   v_rel:=0;v_complete:=false;
 end if;
 v_net:=l.amount-l.discount_share+l.rounding_share;
 if v_rel<0 then raise exception 'BE_NEGATIVE_RELEASE';end if;
 update erp.bd_laundry_invoice_lines_v1 set net_amount=v_net,released_estimate=v_rel,variance=v_net-v_rel,
  product_variance=case when p_dec06->>'variance_mode'='PRODUCT_COST' then v_net-v_rel else 0 end,completes_source=v_complete where id=l.id;
end;$function$;

CREATE OR REPLACE FUNCTION erp.be_redye_status_change_v1()
 RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
begin
 if new.status='CANCELLED' and old.status is distinct from new.status and exists(select 1 from erp.be_redye_services_v1 where id=new.id) then
   if exists(select 1 from erp.bd_laundry_invoice_lines_v1 l join erp.bd_laundry_invoices_v1 i on i.id=l.invoice_id where l.rework_service_id=new.id and i.status='POSTED') then
     raise exception 'BE_REDYE_INVOICED: batalkan dahulu invoice sumber dan dependensinya';end if;
   perform erp.be_redye_resync_v1(new.id,erp._cp3_business_date(statement_timestamp()));
 end if;
 return new;
end;$function$;
create trigger be_redye_status after update of status on erp.rework_orders for each row execute function erp.be_redye_status_change_v1();

CREATE OR REPLACE FUNCTION erp.be_redye_workspace_v1(p_vendor uuid,p_money boolean)
 RETURNS jsonb LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
 select coalesce(jsonb_agg(jsonb_build_object('id',s.id,'number',r.rework_number,'vendor_id',s.vendor_id,'po_number',p.po_number,
   'status',r.status,'qty',s.qty,'good',r.qty_good_returned,'bs',r.qty_bs_returned,
   'billed_good',erp.be_redye_billed_v1(s.id,'GOOD'),'billed_bs',erp.be_redye_billed_v1(s.id,'BS'),
   'process',w.process_name,'price_known',erp.be_redye_rate_v1(s.id) is not null,
   'rate',case when p_money then erp.be_redye_rate_v1(s.id)::text end,
   'cost',case when p_money then erp.be_redye_cost_v1(s.id)::text end) order by s.sent_at desc,s.id),'[]'::jsonb)
 from erp.be_redye_services_v1 s join erp.rework_orders r on r.id=s.id join erp.production_orders p on p.id=s.po_id join erp.wash_processes w on w.id=s.wash_process_id
 where p_vendor is not null and s.vendor_id=p_vendor
$function$;
