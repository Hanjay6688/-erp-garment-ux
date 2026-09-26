-- Rework keeps the native BS lifecycle. Only the GOOD lot produced by COMPLETE
-- is converted; partial saves never make stock or payable. Both facts commit atomically.
create table erp.be_rework_targets_v1(
 rework_id uuid primary key references erp.rework_orders(id),
 target_product_id uuid not null references erp.products(id),
 mode text not null check(mode in('REWORK_SKU','REDYE_SKU')),
 reason text not null,created_by uuid,created_at timestamptz not null default statement_timestamp()
);
create trigger be_rework_targets_fact before insert or update or delete on erp.be_rework_targets_v1
 for each row execute function erp.be_guard_fact_v1();

CREATE OR REPLACE FUNCTION erp.be_guard_rework_source_v1()
 RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
begin
 if exists(select 1 from erp.be_rework_targets_v1 where rework_id=old.id) then
   if TG_OP='DELETE' then raise exception 'BE_REWORK_SOURCE_IMMUTABLE';end if;
   if (new.bs_case_id,new.destination_type,new.contractor_id,new.vendor_id,new.qty_sent,new.physical_sent_at)
      is distinct from (old.bs_case_id,old.destination_type,old.contractor_id,old.vendor_id,old.qty_sent,old.physical_sent_at) then
     raise exception 'BE_REWORK_SOURCE_IMMUTABLE: sumber/tujuan kiriman sudah terikat; batalkan lalu buat dokumen baru';end if;
 end if;
 if TG_OP='DELETE' then return old;end if;return new;
end;$function$;
create trigger be_rework_source_immutable before update or delete on erp.rework_orders
 for each row execute function erp.be_guard_rework_source_v1();

CREATE OR REPLACE FUNCTION erp.be_save_rework_v1(p_payload jsonb,p_request uuid,p_redye boolean default false)
 RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare b erp.bs_cases%rowtype;s erp.products%rowtype;t erp.products%rowtype;v_order uuid;v_result jsonb;v_payload jsonb;
begin
 perform erp.require_permission('production.bs_rework.create');
 perform erp._cp3_assert_closed_json_object(p_payload,array['order','target_product_id','reason'],array['order','target_product_id','reason'],'rework SKU baru');
 if jsonb_typeof(p_payload->'order') is distinct from 'object' or nullif(p_payload->'order'->>'id','') is not null then
   raise exception 'BE_NEW_REWORK_REQUIRED: target SKU ditentukan pada order baru';end if;
 v_payload:=(p_payload->'order')||jsonb_build_object('change_reason',p_payload->>'reason');
 select * into b from erp.bs_cases where id=erp.bd_uuid_v1(v_payload,'bs_case_id',true) for update;
 select * into s from erp.products where id=b.product_id;
 select * into t from erp.products where id=erp.bd_uuid_v1(p_payload,'target_product_id',true);
 if b.id is null or s.id is null then raise exception 'BE_REWORK_SOURCE_IDENTITY_UNKNOWN';end if;
 if t.id is null or not t.is_active or t.id=s.id or t.model_id<>s.model_id or t.size_id<>s.size_id then
   raise exception 'BE_DIMENSION_MISMATCH: SKU baru harus berbeda, dengan model konstruksi dan ukuran sumber';end if;
 v_result:=erp.save_bs_resolution_action_v1('SAVE_REWORK',v_payload,p_request,null);
 v_order:=(v_result->'result'->>'rework_order_id')::uuid;
 if v_order is null then raise exception 'BE_NATIVE_REWORK_RESPONSE_INVALID';end if;
 insert into erp.be_rework_targets_v1(rework_id,target_product_id,mode,reason,created_by)
 values(v_order,t.id,case when p_redye then 'REDYE_SKU' else 'REWORK_SKU' end,erp.bc_text_v1(p_payload,'reason',true,1000),erp.current_app_user_id());
 return jsonb_build_object('rework_id',v_order,'target_product_id',t.id,'status','IN_PROGRESS','native',v_result);
end;$function$;

CREATE OR REPLACE FUNCTION erp.be_complete_rework_target_v1(p_rework uuid)
 RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare b erp.be_rework_targets_v1%rowtype;r erp.rework_orders%rowtype;v_own boolean;v_result jsonb;
begin
 select * into b from erp.be_rework_targets_v1 where rework_id=p_rework;
 if b.rework_id is null then return;end if;
 select * into r from erp.rework_orders where id=p_rework for update;
 if not r.cost_posted or r.status<>'COMPLETED' then raise exception 'BE_REWORK_NOT_COMPLETE';end if;
 if r.qty_good_returned=0 then return;end if;
 if r.good_fg_lot_id is null then raise exception 'BE_REWORK_GOOD_LOT_MISSING';end if;
 if exists(select 1 from erp.be_conversion_sources_v1 s join erp.product_conversions c on c.id=s.conversion_id
      where s.rework_id=r.id and s.source_lot_id=r.good_fg_lot_id and c.status='POSTED') then return;end if;
 v_own:=not erp.be_in_context_v1();
 if v_own then insert into erp.be_execution_context_v1(backend_pid,transaction_id,request_id) values(pg_backend_pid(),txid_current(),gen_random_uuid());end if;
 v_result:=erp.be_post_conversion_v1(jsonb_build_object('source_lot_id',r.good_fg_lot_id,'target_product_id',b.target_product_id,
   'location_id',r.return_fg_location_id,'qty_pcs',r.qty_good_returned,'physical_at',r.completed_at,'reason',b.reason,
   'expected_version',erp.be_source_revision_v1(r.good_fg_lot_id,r.return_fg_location_id)),gen_random_uuid(),
   case when b.mode='REDYE_SKU' then 'REDYE' else 'REWORK' end,r.id);
 if v_own then delete from erp.be_execution_context_v1 where backend_pid=pg_backend_pid() and transaction_id=txid_current();end if;
end;$function$;

CREATE OR REPLACE FUNCTION erp.be_reverse_conversion_v1(p_conversion uuid,p_reason text)
 RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
begin
 perform erp.require_permission('warehouse.brand_conversion.reverse');perform erp.require_owner_admin();
 perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
 if not exists(select 1 from erp.be_conversion_sources_v1 where conversion_id=p_conversion) then raise exception 'BE_DOCUMENT_NOT_FOUND';end if;
 if exists(select 1 from erp.be_conversion_cost_sources_v1 s join erp.bc_documents_v1 d on d.id=s.document_id
     where s.conversion_id=p_conversion and d.status='POSTED') then raise exception 'BE_REVERSE_DEPENDANTS: batalkan dahulu sumber biaya/pemulihan';end if;
 if exists(select 1 from erp.be_conversion_returns_v1 s join erp.bc_return_lots_v1 l on l.outstanding_id=s.outstanding_id
     join erp.bc_documents_v1 d on d.id=l.document_id where s.conversion_id=p_conversion and d.status='POSTED') then
   raise exception 'BE_REVERSE_DEPENDANTS: batalkan dahulu penerimaan bongkaran';end if;
 perform erp.reverse_product_conversion(p_conversion,p_reason);
 update erp.bc_outstanding_returns_v1 set status='CANCELLED' where id in(select outstanding_id from erp.be_conversion_returns_v1 where conversion_id=p_conversion);
end;$function$;

CREATE OR REPLACE FUNCTION erp.be_reverse_rework_target_v1(p_rework uuid,p_reason text)
 RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare v uuid;v_own boolean;
begin
 if not exists(select 1 from erp.be_rework_targets_v1 where rework_id=p_rework) then return;end if;
 v_own:=not erp.be_in_context_v1();
 if v_own then insert into erp.be_execution_context_v1(backend_pid,transaction_id,request_id) values(pg_backend_pid(),txid_current(),gen_random_uuid());end if;
 for v in select s.conversion_id from erp.be_conversion_sources_v1 s join erp.product_conversions c on c.id=s.conversion_id
    where s.rework_id=p_rework and c.status='POSTED' order by c.physical_at desc,c.id desc loop
   perform erp.be_reverse_conversion_v1(v,p_reason);
 end loop;
 if v_own then delete from erp.be_execution_context_v1 where backend_pid=pg_backend_pid() and transaction_id=txid_current();end if;
end;$function$;
