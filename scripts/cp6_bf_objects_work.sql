-- A wave can contain several ranges. Its reference chooses rates, never final FG identity.
alter table erp.rework_component_lines add column bf_sku_version_id uuid references erp.bf_sku_versions_v1(id);
alter table erp.rework_component_lines drop constraint rework_component_lines_rate_basis_check;
alter table erp.rework_component_lines add constraint rework_component_lines_rate_basis_check
 check(rate_basis in('CONTRACTOR_RATE','PO_SNAPSHOT','LAUNDRY_ZERO','LEGACY_CLIENT','SKU_RATE'));

CREATE OR REPLACE FUNCTION erp.bf_bind_wave_v1(p_payload jsonb,p_request uuid)
 RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare g erp.cutting_groups%rowtype; r jsonb; sid uuid; v_sku uuid; vid uuid; model uuid; seen uuid[]:='{}'; before_hash text;
begin
 perform erp._cp3_assert_closed_json_object(p_payload,array['cutting_group_id','references','expected_version'],array['cutting_group_id','references','expected_version'],'wave SKU references');
 perform pg_advisory_xact_lock(hashtextextended('BF:COMMERCIAL_SKUS',0));
 select * into g from erp.cutting_groups where id=erp.bd_uuid_v1(p_payload,'cutting_group_id',true) for update;
 if g.id is null then raise exception 'BF_WAVE_MISSING';end if;
 select model_id into model from erp.production_orders where id=g.po_id;
 before_hash:=erp.bf_wave_revision_v1(g.id);
 if p_payload->>'expected_version' is distinct from before_hash then raise exception 'STALE_VERSION';end if;
 if exists(select 1 from erp.work_completion_events where cutting_group_id=g.id and status='POSTED')
   or exists(select 1 from erp.fg_lots where cutting_group_id=g.id)
   or exists(select 1 from erp.laundry_deliveries d join erp.laundry_delivery_lines l on l.delivery_id=d.id
     where l.cutting_group_id=g.id and d.status not in('DRAFT','REVERSED')) then
   raise exception 'BF_WAVE_USED: referensi pekerjaan yang sudah dipakai terkunci';end if;
 if jsonb_typeof(p_payload->'references') is distinct from 'array' then raise exception 'BF_REFERENCES';end if;
 delete from erp.bf_wave_skus_v1 where cutting_group_id=g.id;
 for r in select value from jsonb_array_elements(p_payload->'references') loop
   perform erp._cp3_assert_closed_json_object(r,array['sku_id','size_id'],array['sku_id','size_id'],'wave size SKU');
   v_sku:=erp.bd_uuid_v1(r,'sku_id',true);sid:=erp.bd_uuid_v1(r,'size_id',true);
   if sid=any(seen) then raise exception 'BF_DUPLICATE_SIZE';end if;seen:=seen||sid;
   if not exists(select 1 from erp.cutting_group_size_slots where cutting_group_id=g.id and size_id=sid) then raise exception 'BF_SIZE_NOT_IN_WAVE';end if;
   select v.id into vid from erp.bf_sku_versions_v1 v join erp.bf_skus_v1 s on s.id=v.sku_id
     join erp.bf_sku_members_v1 m on m.version_id=v.id join erp.products p on p.id=m.product_root
     where s.id=v_sku and s.model_id=model and p.size_id=sid and v.effective_from<=statement_timestamp() and(v.effective_to is null or v.effective_to>statement_timestamp());
   if vid is null then raise exception 'BF_SKU_SIZE_MODEL: SKU referensi harus memuat ukuran/model saat dipilih';end if;
   insert into erp.bf_wave_skus_v1 values(g.id,sid,v_sku,clock_timestamp(),erp.current_app_user_id(),p_request);
 end loop;
 if cardinality(seen)>0 and exists(select 1 from erp.cutting_group_size_slots where cutting_group_id=g.id and not(size_id=any(seen))) then
   raise exception 'BF_WAVE_COVERAGE: tentukan SKU referensi setiap ukuran wave';end if;
 insert into erp.audit_logs(entity_type,entity_id,action,new_data,changed_by,change_reason)
   values('cutting_groups',g.id,'UPDATE',p_payload,erp.current_app_user_id(),'Referensi tarif SKU per ukuran wave; bukan identitas FG');
 return jsonb_build_object('cutting_group_id',g.id,'revision',erp.bf_wave_revision_v1(g.id));
end;$function$;

CREATE OR REPLACE FUNCTION erp.bf_work_capacity_v1(p_group uuid,p_snapshot uuid,p_default bigint)
 RETURNS bigint LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
 select case when s.bf_sku_version_id is null then p_default else coalesce((
   select sum(y.qty_pcs)::bigint from erp.cutting_roll_yields y join erp.cutting_group_rolls r on r.id=y.cutting_group_roll_id
   join erp.cutting_group_size_slots slot on slot.id=y.size_slot_id
   join erp.bf_wave_skus_v1 w on w.cutting_group_id=r.cutting_group_id and w.size_id=slot.size_id
   where r.cutting_group_id=p_group and w.sku_id=v.sku_id),0) end
 from erp.po_work_component_snapshots s left join erp.bf_sku_versions_v1 v on v.id=s.bf_sku_version_id where s.id=p_snapshot
$function$;

CREATE OR REPLACE FUNCTION erp.bf_snapshot_sku_v1(p_snapshot uuid)
 RETURNS uuid LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
 select v.sku_id from erp.po_work_component_snapshots s join erp.bf_sku_versions_v1 v on v.id=s.bf_sku_version_id where s.id=p_snapshot
$function$;

CREATE OR REPLACE FUNCTION erp.bf_wave_revision_v1(p_group uuid)
 RETURNS text LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
 select md5(coalesce((select jsonb_agg(jsonb_build_array(size_id,sku_id,request_id) order by size_id)::text from erp.bf_wave_skus_v1 where cutting_group_id=p_group),'[]'))
$function$;

CREATE OR REPLACE FUNCTION erp.bf_group_sku_v1(p_group uuid,p_product uuid)
 RETURNS uuid LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
 select case when p_product is null then
   (select min(w.sku_id::text)::uuid from erp.bf_wave_skus_v1 w where w.cutting_group_id=p_group having count(distinct w.sku_id)=1)
 else (select w.sku_id from erp.bf_wave_skus_v1 w join erp.products p on p.size_id=w.size_id where w.cutting_group_id=p_group and p.id=p_product) end
$function$;

CREATE OR REPLACE FUNCTION erp.bf_ensure_work_v1(p_po uuid,p_at timestamptz)
 RETURNS integer LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare s record; base record; vid uuid; rate numeric; n integer:=0; contractor uuid;
begin
 perform pg_advisory_xact_lock(hashtextextended('BF:COMMERCIAL_SKUS',0));
 select contractor_id into contractor from erp.production_orders where id=p_po for update;
 for s in select distinct w.sku_id from erp.bf_wave_skus_v1 w join erp.cutting_groups g on g.id=w.cutting_group_id where g.po_id=p_po loop
   -- First financial use pins the SKU version for the PO. Merely cutting/binding does not pin a tariff.
   select x.bf_sku_version_id into vid from erp.po_work_component_snapshots x join erp.bf_sku_versions_v1 v on v.id=x.bf_sku_version_id
     where x.po_id=p_po and v.sku_id=s.sku_id order by x.committed_at,x.id limit 1;
   if vid is not null then continue;end if;
   select id into vid from erp.bf_sku_versions_v1 where sku_id=s.sku_id and effective_from<=p_at and(effective_to is null or effective_to>p_at);
   if vid is null then raise exception 'BF_WORK_VERSION_MISSING';end if;
   -- An unused binding is a choice, not a membership snapshot. Recheck it at
   -- first financial use under the same lock as SAVE_GROUPS. Earlier pins above
   -- retain their original version after a later membership change.
   if exists(select 1 from erp.bf_wave_skus_v1 w join erp.cutting_groups g on g.id=w.cutting_group_id
     where g.po_id=p_po and w.sku_id=s.sku_id and not exists(
       select 1 from erp.bf_sku_members_v1 m join erp.products p on p.id=m.product_root
       where m.version_id=vid and p.size_id=w.size_id)) then
     raise exception 'BF_WAVE_REFERENCE_STALE: keanggotaan ukuran berubah sebelum tarif kerja dipakai; pilih ulang SKU wave';
   end if;
   for base in select * from erp.po_work_component_snapshots where po_id=p_po and bf_sku_version_id is null order by sequence_no,id loop
     rate:=erp.bf_work_rate_v1(vid,contractor,base.work_component_id,p_at);
     insert into erp.po_work_component_snapshots(po_id,work_component_id,source_bom_version_id,sequence_no,rate_per_pcs_snapshot,source_bom_item_id,source_contractor_rate_id,committed_at,bf_sku_version_id)
       values(p_po,base.work_component_id,base.source_bom_version_id,base.sequence_no,coalesce(rate,base.rate_per_pcs_snapshot),base.source_bom_item_id,
         case when rate is null then base.source_contractor_rate_id end,p_at,vid);
     n:=n+1;
   end loop;
 end loop;
 return n;
end;$function$;

CREATE OR REPLACE FUNCTION erp.bf_snapshot_matches_v1(p_snapshot uuid,p_group uuid,p_product uuid)
 RETURNS boolean LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
 select case when erp.bf_group_sku_v1(p_group,p_product) is null then s.bf_sku_version_id is null and not exists(select 1 from erp.bf_wave_skus_v1 w where w.cutting_group_id=p_group)
   else v.sku_id=erp.bf_group_sku_v1(p_group,p_product) end
 from erp.po_work_component_snapshots s left join erp.bf_sku_versions_v1 v on v.id=s.bf_sku_version_id where s.id=p_snapshot
$function$;

CREATE OR REPLACE FUNCTION erp.bf_assert_work_scope_v1(p_completion uuid,p_snapshot uuid)
 RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare e erp.work_completion_events%rowtype; sku uuid; version uuid;
begin
 select * into e from erp.work_completion_events where id=p_completion;
 select s.bf_sku_version_id,v.sku_id into version,sku from erp.po_work_component_snapshots s left join erp.bf_sku_versions_v1 v on v.id=s.bf_sku_version_id where s.id=p_snapshot;
 if version is not null and not exists(select 1 from erp.bf_wave_skus_v1 where cutting_group_id=e.cutting_group_id and sku_id=sku) then raise exception 'BF_WORK_OTHER_SKU';end if;
 if version is null and exists(select 1 from erp.bf_wave_skus_v1 where cutting_group_id=e.cutting_group_id) then raise exception 'BF_WORK_SCOPE_REQUIRED: pilih tarif SKU anggota wave';end if;
end;$function$;
