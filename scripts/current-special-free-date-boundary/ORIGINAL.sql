CREATE OR REPLACE FUNCTION erp.bc_free_basis_v1(p_material uuid, p_contractor uuid, p_at timestamp with time zone)
 RETURNS jsonb
 LANGUAGE sql
 STABLE SECURITY DEFINER
 SET search_path TO ''
AS $function$
  select jsonb_build_object('category_id',m.accessory_category_id,'policy_version',erp.bc_policy_version_v1('ERP_DEC02')::text)
  from erp.materials m
  where m.id=p_material and m.material_type='ACCESSORY'
    and coalesce(erp.bc_policy_v1('ERP_DEC02')->'special_free_category_ids','[]'::jsonb) ? m.accessory_category_id::text
    and exists(select 1 from erp.contractor_hpp_policy_versions v where v.contractor_id=p_contractor and v.is_special
      and v.effective_from<=p_at and (v.effective_to is null or v.effective_to>p_at))
$function$
