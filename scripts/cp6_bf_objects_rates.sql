CREATE OR REPLACE FUNCTION erp.bf_validate_rates_v1(p_sku uuid,p_settings jsonb)
 RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare j jsonb; k text; ref uuid; vendor uuid; amount numeric; seen text[]:='{}'; key text;
begin
 for j in select value from jsonb_array_elements(p_settings->'work_rates') loop
   perform erp._cp3_assert_closed_json_object(j,array['work_component_id','rate'],array['contractor_id','work_component_id','rate','special'],'SKU work rate');
   vendor:=erp.bd_uuid_v1(j,'contractor_id',false);ref:=erp.bd_uuid_v1(j,'work_component_id',true);
   if (vendor is not null and not exists(select 1 from erp.contractors where id=vendor and is_active))
     or not exists(select 1 from erp.work_components where id=ref and is_active) then raise exception 'BF_WORK_RATE_REFERENCE';end if;
   if j ? 'special' and jsonb_typeof(j->'special') is distinct from 'boolean' then raise exception 'BF_SPECIAL_FLAG';end if;
   perform erp.bd_amount_v1(j->'rate','rate',true);key:=coalesce(vendor::text,'*')||':'||ref::text||':'||coalesce(j->>'special','false');
   if key=any(seen) then raise exception 'BF_DUPLICATE_RATE';end if;seen:=seen||key;
 end loop;
 seen:='{}';
 for j in select value from jsonb_array_elements(p_settings->'laundry_rates') loop
   perform erp._cp3_assert_closed_json_object(j,array['vendor_id','kind','ref_id','rate_status'],
     array['vendor_id','kind','ref_id','rate_status','rate','reason'],'SKU laundry rate');
   if not(j ?& array['rate','reason']) then raise exception 'BF_RATE_FIELDS';end if;
   k:=j->>'kind';ref:=erp.bd_uuid_v1(j,'ref_id',true);vendor:=erp.bd_uuid_v1(j,'vendor_id',true);
   if not exists(select 1 from erp.laundry_vendors where id=vendor and is_active) then raise exception 'BF_VENDOR';end if;
   if k='PROCESS' then
     if not exists(select 1 from erp.wash_processes where id=ref and is_active) then raise exception 'BF_PROCESS';end if;
   elsif k='COMPONENT' then
     if not exists(select 1 from erp.bd_laundry_components_v1 where id=ref and vendor_id=vendor and is_active) then raise exception 'BF_COMPONENT';end if;
   elsif k='PACKAGE' then
     if not exists(select 1 from erp.bd_laundry_packages_v1 where id=ref and vendor_id=vendor and is_active) then raise exception 'BF_PACKAGE';end if;
   else raise exception 'BF_RATE_KIND';end if;
   if j->>'rate_status' not in('KNOWN','UNKNOWN','FREE','WAIVED') or j->>'rate_status' is null then raise exception 'BF_RATE_STATUS';end if;
   if k<>'COMPONENT' and j->>'rate_status'<>'KNOWN' then raise exception 'BF_COMPONENT_MODE_REQUIRED: gunakan komponen untuk UNKNOWN/FREE/WAIVED';end if;
   if j->>'rate_status'='UNKNOWN' then
     if j->'rate'<>'null'::jsonb then raise exception 'BF_UNKNOWN_RATE';end if;
   else
     amount:=erp.bd_amount_v1(j->'rate','rate',true);
     if j->>'rate_status'='KNOWN' and amount<=0 then raise exception 'BF_ZERO_USE_FREE';end if;
     if j->>'rate_status' in('FREE','WAIVED') and (amount<>0 or nullif(btrim(j->>'reason'),'') is null) then raise exception 'BF_FREE_REASON';end if;
   end if;
   key:=vendor::text||':'||k||':'||ref::text;
   if key=any(seen) then raise exception 'BF_DUPLICATE_RATE';end if;seen:=seen||key;
 end loop;
end;$function$;

-- SKU base rate applies to every member size. Optional contractor/special overrides are still per SKU.
CREATE OR REPLACE FUNCTION erp.bf_work_rate_v1(p_version uuid,p_contractor uuid,p_component uuid,p_at timestamptz)
 RETURNS numeric LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
 select (r->>'rate')::numeric from erp.bf_sku_versions_v1 v cross join lateral jsonb_array_elements(v.settings->'work_rates') r
 where v.id=p_version and r->>'work_component_id'=p_component::text
   and (r->>'contractor_id' is null or r->>'contractor_id'=p_contractor::text)
   and (not coalesce((r->>'special')::boolean,false) or exists(select 1 from erp.contractor_hpp_policy_versions pol
     where pol.contractor_id=p_contractor and pol.is_special and pol.effective_from<=erp._cp3_business_date(p_at)
       and (pol.effective_to is null or pol.effective_to>=erp._cp3_business_date(p_at))))
 order by (r->>'contractor_id' is not null) desc,coalesce((r->>'special')::boolean,false) desc limit 1
$function$;

CREATE OR REPLACE FUNCTION erp.bf_context_rate_v1(p_kind text,p_ref uuid,p_vendor uuid DEFAULT NULL)
 RETURNS jsonb LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
 select r||jsonb_build_object('version_id',v.id) from erp.bf_context_v1 c
 join erp.bf_sku_versions_v1 v on v.id=c.version_id cross join lateral jsonb_array_elements(v.settings->'laundry_rates') r
 where c.backend_pid=pg_backend_pid() and c.transaction_id=txid_current() and r->>'kind'=p_kind and r->>'ref_id'=p_ref::text and(p_vendor is null or r->>'vendor_id'=p_vendor::text)
$function$;

CREATE OR REPLACE FUNCTION erp.bf_bom_for_lot_v1(p_lot uuid)
 RETURNS uuid LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare l erp.fg_lots%rowtype; vid uuid; pinned uuid; sid uuid; root uuid; bom uuid;
begin
 select * into l from erp.fg_lots where id=p_lot;
 vid:=erp.bf_version_at_v1(l.product_id,l.produced_at);
 if vid is null then return null;end if;
 select sku_id into sid from erp.bf_sku_versions_v1 where id=vid;
 select identity_root_id into root from erp.products where id=l.product_id;
 select version_id into pinned from erp.bf_po_boms_v1 where po_id=l.po_id and sku_id=sid;
 if pinned is null then
   -- A pre-adoption PO has already committed its old recipe. Never silently mix a new group recipe into that PO.
   if exists(select 1 from erp.po_accessory_bom_commitments c join erp.products p on p.id=c.product_id
     join erp.bf_sku_members_v1 m on m.product_root=p.identity_root_id and m.version_id=vid where c.po_id=l.po_id) then
     raise exception 'BF_PO_LEGACY_BOM: PO sudah memakai resep lama; selesaikan memakai komitmen lama sebelum adopsi SKU';end if;
   insert into erp.bf_po_boms_v1 values(l.po_id,sid,vid);pinned:=vid;
 end if;
 select bom_version_id into bom from erp.bf_sku_members_v1 where version_id=pinned and product_root=root;
 if bom is null then
   if exists(select 1 from erp.bf_sku_members_v1 where version_id=pinned and product_root=root) then
     raise exception 'BF_BOM_UNCONFIGURED: tentukan resep SKU (termasuk tanpa aksesori bila benar) sebelum penggunaan biaya';
   end if;
   raise exception 'BF_PO_NEW_MEMBER: ukuran baru tidak termasuk resep PO yang telah disepakati';
 end if;
 return bom;
end;$function$;
