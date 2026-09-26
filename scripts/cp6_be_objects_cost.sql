-- Actual accessory use and approved recovery are native BC documents. BE moves
-- that exact sourced value into/out of conversion HPP; it never accepts manual HPP.
create table erp.be_conversion_cost_sources_v1(
  document_id uuid primary key references erp.bc_documents_v1(id),
  conversion_id uuid not null references erp.product_conversions(id),
  kind text not null check(kind in('USAGE','RECOVERY')),
  created_at timestamptz not null default statement_timestamp()
);
create table erp.be_conversion_cost_events_v1(
  id uuid primary key default gen_random_uuid(),
  document_id uuid not null references erp.be_conversion_cost_sources_v1(document_id),
  adjustment_id uuid not null references erp.material_adjustments(id),
  previous_amount numeric(20,2) not null,target_amount numeric(20,2) not null,
  journal_id uuid not null references erp.journal_entries(id),
  economic_date date not null,created_at timestamptz not null default statement_timestamp(),created_by uuid
);
create trigger be_conversion_cost_sources_fact before insert or update or delete on erp.be_conversion_cost_sources_v1
 for each row execute function erp.be_guard_fact_v1();
create trigger be_conversion_cost_events_fact before insert or update or delete on erp.be_conversion_cost_events_v1
 for each row execute function erp.be_guard_fact_v1();

CREATE OR REPLACE FUNCTION erp.be_conversion_extra_v1(p_conversion uuid)
 RETURNS numeric LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
 select coalesce(sum(e.target_amount-e.previous_amount),0) from erp.be_conversion_cost_sources_v1 s
 join erp.be_conversion_cost_events_v1 e on e.document_id=s.document_id where s.conversion_id=p_conversion
$function$;

CREATE OR REPLACE FUNCTION erp.be_allocation_extra_v1(p_allocation uuid)
 RETURNS numeric LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
 select a.conversion_cost_allocated+erp.be_conversion_extra_v1(a.conversion_id)
 from erp.product_conversion_allocations a where a.id=p_allocation
$function$;

CREATE OR REPLACE FUNCTION erp.be_po_extra_v1(p_po uuid)
 RETURNS numeric LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
 select coalesce(sum(erp.be_conversion_extra_v1(c.id)),0) from erp.product_conversions c
 join erp.be_conversion_sources_v1 s on s.conversion_id=c.id join erp.fg_lots l on l.id=s.source_lot_id
 where c.status='POSTED' and l.po_id=p_po
$function$;

CREATE OR REPLACE FUNCTION erp.be_conversion_revision_v1(p_conversion uuid)
 RETURNS text LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
 select md5(jsonb_build_object('id',c.id,'status',c.status,
   'cost_events',coalesce((select jsonb_agg(e.id order by e.id) from erp.be_conversion_cost_events_v1 e
     join erp.be_conversion_cost_sources_v1 s on s.document_id=e.document_id where s.conversion_id=c.id),'[]'::jsonb))::text)
 from erp.product_conversions c where c.id=p_conversion
$function$;

CREATE OR REPLACE FUNCTION erp.be_reconcile_cost_document_v1(p_document uuid,p_date date)
 RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare s erp.be_conversion_cost_sources_v1%rowtype;c erp.product_conversions%rowtype;l erp.fg_lots%rowtype;
 r record;v_target numeric;v_before numeric;v_delta numeric;v_journal uuid;v_own boolean;v_event uuid;
begin
 perform erp.require_internal();
 select * into s from erp.be_conversion_cost_sources_v1 where document_id=p_document;
 if s.document_id is null then return;end if;
 perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
 select * into c from erp.product_conversions where id=s.conversion_id for update;
 select * into l from erp.fg_lots where id=(select source_lot_id from erp.be_conversion_sources_v1 where conversion_id=c.id);
 if c.status<>'POSTED' then raise exception 'BE_COST_SOURCE_NOT_POSTED';end if;
 v_own:=not erp.be_in_context_v1();
 if v_own then insert into erp.be_execution_context_v1 values(pg_backend_pid(),txid_current(),gen_random_uuid());end if;
 for r in select p.adjustment_id,p.account_id,d.status from erp.bc_adjustment_purposes_v1 p
    join erp.bc_documents_v1 d on d.id=p.document_id where p.document_id=p_document order by p.adjustment_id loop
   v_target:=case when r.status='POSTED' then -(erp._cp6_material_adjustment_revaluation_state(r.adjustment_id)->>'current_value')::numeric else 0 end;
   if (s.kind='USAGE' and v_target<0) or (s.kind='RECOVERY' and v_target>0) then raise exception 'BE_COST_DIRECTION';end if;
   select coalesce(sum(target_amount-previous_amount),0) into v_before from erp.be_conversion_cost_events_v1 where adjustment_id=r.adjustment_id;
   v_delta:=v_target-v_before;
   if v_delta<>0 then
     v_event:=gen_random_uuid();
     v_journal:=erp.post_journal('BE_CONVERSION_SOURCED_COST',v_event,p_date,'Biaya/pemulihan konversi dari dokumen '||p_document::text,
       jsonb_build_array(jsonb_build_object('mapping_key',case when l.po_id is null then 'FG_INVENTORY' else 'WIP' end,
         'po_id',l.po_id,'product_id',case when l.po_id is null then c.to_product_id end,'debit',greatest(v_delta,0),'credit',greatest(-v_delta,0)),
         jsonb_build_object('account_id',r.account_id,'debit',greatest(-v_delta,0),'credit',greatest(v_delta,0))));
     insert into erp.be_conversion_cost_events_v1(id,document_id,adjustment_id,previous_amount,target_amount,journal_id,economic_date,created_by)
     values(v_event,p_document,r.adjustment_id,v_before,v_target,v_journal,p_date,erp.current_app_user_id());
   end if;
 end loop;
 if l.po_id is null then
   perform erp.be_nonpo_sync_all_v1(p_date,'BE_COST_SOURCE',p_document,'Biaya/pemulihan konversi non-PO');
 else
   perform erp.propagate_conversion_hpp_for_po(l.po_id);
   perform erp.sync_po_hpp_to_gl(l.po_id,p_date);
   perform erp.assert_po_hpp_target_book_v2620e(l.po_id);
 end if;
 if v_own then delete from erp.be_execution_context_v1 where backend_pid=pg_backend_pid() and transaction_id=txid_current();end if;
end;$function$;

CREATE OR REPLACE FUNCTION erp.be_sync_material_cost_v1(p_material uuid)
 RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare d uuid;
begin
 for d in select distinct s.document_id from erp.be_conversion_cost_sources_v1 s join erp.bc_adjustment_purposes_v1 p on p.document_id=s.document_id
   join erp.material_adjustment_items i on i.adjustment_id=p.adjustment_id where i.material_id=p_material order by s.document_id loop
   perform erp.be_reconcile_cost_document_v1(d,coalesce(erp.invoice_recost_economic_date_v1(),erp._cp3_business_date(current_timestamp)));
 end loop;
end;$function$;

CREATE OR REPLACE FUNCTION erp.be_link_recovery_v1(p_document uuid,p_return_lot uuid,p_date date)
 RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare v_conversion uuid;v_own boolean;
begin
 select s.conversion_id into v_conversion from erp.be_conversion_returns_v1 s join erp.bc_return_lots_v1 l on l.outstanding_id=s.outstanding_id
 where l.id=p_return_lot;
 if v_conversion is null then return;end if;
 v_own:=not erp.be_in_context_v1();
 if v_own then insert into erp.be_execution_context_v1 values(pg_backend_pid(),txid_current(),gen_random_uuid());end if;
 insert into erp.be_conversion_cost_sources_v1(document_id,conversion_id,kind) values(p_document,v_conversion,'RECOVERY');
 perform erp.be_reconcile_cost_document_v1(p_document,p_date);
 if v_own then delete from erp.be_execution_context_v1 where backend_pid=pg_backend_pid() and transaction_id=txid_current();end if;
end;$function$;

CREATE OR REPLACE FUNCTION erp.be_post_usage_v1(p_payload jsonb,p_request uuid)
 RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare c erp.product_conversions%rowtype;v_result jsonb;v_at timestamptz;v_items jsonb;v_doc uuid:=gen_random_uuid();
begin
 perform erp.require_permission('warehouse.stock.adjust');
 perform erp._cp3_assert_closed_json_object(p_payload,array['conversion_id','expected_version','location_id','items','physical_at','reason'],
   array['conversion_id','expected_version','location_id','items','physical_at','reason'],'aksesori konversi');
 perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
 select * into c from erp.product_conversions where id=erp.bd_uuid_v1(p_payload,'conversion_id',true) for update;
 if c.id is null or c.status<>'POSTED' or not exists(select 1 from erp.be_conversion_sources_v1 where conversion_id=c.id) then
   raise exception 'BE_DOCUMENT_NOT_POSTED';end if;
 if p_payload->>'expected_version' is distinct from erp.be_conversion_revision_v1(c.id) then raise exception 'STALE_VERSION';end if;
 v_at:=erp.bd_at_v1(p_payload->>'physical_at','physical_at');
 if v_at<c.physical_at then raise exception 'BE_BEFORE_CONVERSION';end if;
 v_items:=erp.bc_lines_v1(p_payload);
 select jsonb_agg((x-'line_number')||jsonb_build_object('purpose','OWN_FG_REPAIR','physical_at',v_at) order by (x->>'line_number')::int)
 into v_items from jsonb_array_elements(v_items) x;
 v_result:=erp.save_accessory_service_action_v1('INTERNAL_USE',jsonb_build_object('location_id',p_payload->>'location_id',
   'items',v_items,'reason',p_payload->>'reason','reference','Konversi '||c.conversion_number),v_doc);
 insert into erp.be_conversion_cost_sources_v1(document_id,conversion_id,kind) values(v_doc,c.id,'USAGE');
 perform erp.be_reconcile_cost_document_v1(v_doc,erp._cp3_business_date(v_at));
 return jsonb_build_object('conversion_id',c.id,'cost_document_id',v_doc,'status','POSTED','source',v_result,
   'expected_version',erp.be_conversion_revision_v1(c.id));
end;$function$;
