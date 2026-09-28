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
 if jsonb_array_length(p_settings->'laundry_rates')>0 then
   raise exception 'BF_LAUNDRY_VENDOR_AUTHORITY: harga laundry diatur pada vendor; riwayat SKU hanya referensi pemilihan';
 end if;
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
 -- Legacy context helper cannot supply SKU monetary rates.
 select null::jsonb
$function$;

CREATE OR REPLACE FUNCTION erp.bf_bom_for_lot_v1(p_lot uuid)
 RETURNS uuid LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare l erp.fg_lots%rowtype; vid uuid; pinned uuid; sid uuid; root uuid; bom uuid; frozen_bom uuid;
begin
 select * into l from erp.fg_lots where id=p_lot;
 vid:=erp.bf_version_at_v1(l.product_id,l.produced_at);
 if vid is null then return null;end if;
 select sku_id into sid from erp.bf_sku_versions_v1 where id=vid;
 select identity_root_id into root from erp.products where id=l.product_id;
 select version_id into pinned from erp.bf_po_boms_v1 where po_id=l.po_id and sku_id=sid;
 if pinned is null then
   -- Rework can be the first financial use, before any GOOD lot. Its native commitment already pins a real SKU recipe.
   select v.id into pinned from erp.po_accessory_bom_commitments c
     join erp.bf_sku_members_v1 m on m.bom_version_id=c.bom_version_id join erp.bf_sku_versions_v1 v on v.id=m.version_id
     where c.po_id=l.po_id and v.sku_id=sid order by c.committed_at,c.id limit 1;
   if pinned is not null then insert into erp.bf_po_boms_v1 values(l.po_id,sid,pinned);end if;
 end if;
 if pinned is null then
   select bom_version_id into bom from erp.bf_sku_members_v1 where version_id=vid and product_root=root;
   -- Adoption may continue an existing PO only when every old commitment has the exact same economic recipe.
   if exists(select 1 from erp.po_accessory_bom_commitments c join erp.products p on p.id=c.product_id
     join erp.bf_sku_members_v1 m on m.product_root=p.identity_root_id and m.version_id=vid
     where c.po_id=l.po_id and erp.bf_recipe_basis_v1(c.bom_version_id) is distinct from erp.bf_recipe_basis_v1(bom)) then
     raise exception 'BF_PO_LEGACY_BOM: resep PO lama berbeda; komitmen lama tidak boleh diganti diam-diam';end if;
   insert into erp.bf_po_boms_v1 values(l.po_id,sid,vid);pinned:=vid;
 end if;
 select bom_version_id into bom from erp.bf_sku_members_v1 where version_id=pinned and product_root=root;
 if bom is null then
   if exists(select 1 from erp.bf_sku_members_v1 where version_id=pinned and product_root=root) then
     raise exception 'BF_BOM_UNCONFIGURED: tentukan resep SKU (termasuk tanpa aksesori bila benar) sebelum penggunaan biaya';
   end if;
   -- Adding a size must not force a new price for the other members of a PO already in progress.
   select bom_version_id into frozen_bom from erp.bf_sku_members_v1 where version_id=pinned and bom_version_id is not null order by product_root limit 1;
   select bom_version_id into bom from erp.bf_sku_members_v1 where version_id=vid and product_root=root;
   if bom is null or erp.bf_recipe_basis_v1(bom) is distinct from erp.bf_recipe_basis_v1(frozen_bom) then
     raise exception 'BF_PO_NEW_MEMBER: resep ukuran baru berbeda dari komitmen PO';end if;
 end if;
 return bom;
end;$function$;

CREATE OR REPLACE FUNCTION erp.bf_recipe_basis_v1(p_bom uuid)
 RETURNS jsonb LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
 select case when p_bom is not null then coalesce(jsonb_agg(jsonb_build_object('category',category_id,'qty',qty_per_good_fg_base,
   'method',hpp_method,'standard',case when hpp_method='BOM_STANDARD' then hpp_standard_rate end,
   'unit',case when hpp_method='BOM_STANDARD' then hpp_uom_code end,'reimbursement',reimbursement_rate,'reimbursement_unit',reimbursement_uom_code)
   order by category_id),'[]') end from erp.accessory_bom_items where bom_version_id=p_bom
$function$;
