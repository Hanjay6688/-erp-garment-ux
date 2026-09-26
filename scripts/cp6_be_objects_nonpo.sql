-- Opening/non-PO conversion has an explicit value source. Current value moves
-- between SKU dimensions; only disposal/sales become expense. Historical sale
-- snapshots and allocation.original_hpp_per_pcs remain immutable.
create table erp.be_nonpo_transfer_events_v1(
 id uuid primary key default gen_random_uuid(),conversion_id uuid not null references erp.product_conversions(id),
 previous_value numeric(20,2) not null,target_value numeric(20,2) not null,
 journal_id uuid not null references erp.journal_entries(id),economic_date date not null,
 created_at timestamptz not null default statement_timestamp()
);
create trigger be_nonpo_transfer_events_fact before insert or update or delete on erp.be_nonpo_transfer_events_v1
 for each row execute function erp.be_guard_fact_v1();

CREATE OR REPLACE FUNCTION erp.be_nonpo_admitted_v1(p_conversion uuid)
 RETURNS boolean LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
 select exists(select 1 from erp.be_conversion_sources_v1 b join erp.product_conversions c on c.id=b.conversion_id
  join erp.fg_lots l on l.id=b.source_lot_id join erp.v_current_hpp h on h.lot_id=l.id
  where b.conversion_id=p_conversion and l.po_id is null and l.product_id=c.from_product_id
   and l.lot_origin<>'VOIDED_PRODUCTION' and h.hpp_per_pcs>=0)
$function$;

CREATE OR REPLACE FUNCTION erp.be_nonpo_in_sync_v1()
 RETURNS boolean LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
 select coalesce((select syncing_nonpo from erp.be_execution_context_v1
   where backend_pid=pg_backend_pid() and transaction_id=txid_current()),false)
$function$;

CREATE OR REPLACE FUNCTION erp.be_nonpo_sync_all_v1(p_date date,p_source_type text,p_source_id uuid,p_reason text)
 RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare r record;v_own boolean;v_old numeric;v_new numeric;v_delta numeric;v_journal uuid;v_event uuid;v_product uuid;
begin
 perform erp.require_internal();
 perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
 if erp.be_nonpo_in_sync_v1() then raise exception 'BE_NON_PO_RECURSION';end if;
 v_own:=not erp.be_in_context_v1();
 if v_own then insert into erp.be_execution_context_v1(backend_pid,transaction_id,request_id) values(pg_backend_pid(),txid_current(),gen_random_uuid());end if;
 update erp.be_execution_context_v1 set syncing_nonpo=true where backend_pid=pg_backend_pid() and transaction_id=txid_current();
 perform erp.be_propagate_nonpo_v1();
 for r in select c.id,c.from_product_id,c.to_product_id,a.id allocation_id,a.qty_pcs,a.original_hpp_per_pcs,
    h.hpp_per_pcs from erp.product_conversions c join erp.product_conversion_allocations a on a.conversion_id=c.id
    join erp.fg_lots l on l.id=a.source_lot_id join erp.v_current_hpp h on h.lot_id=l.id
    where l.po_id is null and c.status='POSTED' order by c.physical_at,c.id loop
   if not erp.be_nonpo_admitted_v1(r.id) then raise exception 'NON_PO_CONVERSION_REQUIRES_SOURCED_HPP_WORKFLOW';end if;
   select round(r.qty_pcs*r.original_hpp_per_pcs,2)+coalesce(sum(target_value-previous_value),0) into v_old
     from erp.be_nonpo_transfer_events_v1 where conversion_id=r.id;
   v_new:=round(r.qty_pcs*r.hpp_per_pcs,2);v_delta:=v_new-v_old;
   if v_delta<>0 then
     v_event:=gen_random_uuid();
     v_journal:=erp.post_journal('BE_NONPO_CONVERSION_RECOST',v_event,p_date,'Nilai sumber terkini konversi '||r.id::text,
       jsonb_build_array(jsonb_build_object('mapping_key','FG_INVENTORY','product_id',r.to_product_id,'debit',greatest(v_delta,0),'credit',greatest(-v_delta,0)),
         jsonb_build_object('mapping_key','FG_INVENTORY','product_id',r.from_product_id,'debit',greatest(-v_delta,0),'credit',greatest(v_delta,0))));
     insert into erp.be_nonpo_transfer_events_v1(id,conversion_id,previous_value,target_value,journal_id,economic_date)
       values(v_event,r.id,v_old,v_new,v_journal,p_date);
   end if;
 end loop;
 for v_product in select distinct product_id from erp.fg_lots where po_id is null order by product_id loop
   perform erp.sync_non_po_product_hpp_to_gl_v2620f(v_product,p_date,p_source_type,p_source_id,p_reason);
 end loop;
 update erp.be_execution_context_v1 set syncing_nonpo=false where backend_pid=pg_backend_pid() and transaction_id=txid_current();
 if v_own then delete from erp.be_execution_context_v1 where backend_pid=pg_backend_pid() and transaction_id=txid_current();end if;
end;$function$;
