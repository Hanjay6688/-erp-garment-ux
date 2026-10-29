CREATE OR REPLACE FUNCTION erp.save_accessory_bom_edit(p_bom_version_id uuid, p_items jsonb, p_effective_from timestamp with time zone DEFAULT clock_timestamp(), p_notes text DEFAULT NULL::text)
 RETURNS uuid
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public', 'pg_temp'
AS $function$
declare b erp.accessory_bom_versions%rowtype;v_last_commit timestamptz;v_eff timestamptz:=coalesce(p_effective_from,clock_timestamp());v_next timestamptz;v_new_end timestamptz;v_new uuid;j jsonb;
begin
  perform erp.require_owner_admin();
  if jsonb_typeof(p_items)<>'array' then raise exception 'BOM accessory items harus berupa array; gunakan [] untuk deklarasi produk tanpa aksesori'; end if;
  select * into b from erp.accessory_bom_versions where id=p_bom_version_id for update;
  if b.id is null then raise exception 'BOM accessory tidak ditemukan'; end if;
  v_last_commit:=erp.accessory_bom_last_committed_at(b.id);
  if v_last_commit is null and not exists(select 1 from erp.po_accessory_bom_commitments where bom_version_id=b.id) then
    delete from erp.accessory_bom_items where bom_version_id=b.id;
    for j in select value from jsonb_array_elements(p_items) loop
      insert into erp.accessory_bom_items(bom_version_id,category_id,qty_per_good_fg_base,hpp_method,hpp_standard_rate,hpp_uom_code,reimbursement_rate,reimbursement_uom_code,notes)
      values(b.id,(j->>'category_id')::uuid,(j->>'qty_per_good_fg_base')::numeric,coalesce(nullif(j->>'hpp_method',''),'CATEGORY_MOVING_AVG'),nullif(j->>'hpp_standard_rate','')::numeric,nullif(j->>'hpp_uom_code',''),coalesce(nullif(j->>'reimbursement_rate','')::numeric,0),nullif(j->>'reimbursement_uom_code',''),j->>'notes');
    end loop;
    update erp.accessory_bom_versions set notes=coalesce(p_notes,notes) where id=b.id;
    insert into erp.audit_logs(entity_type,entity_id,action,changed_by,change_reason,new_data) values('accessory_bom_versions',b.id,'UPDATE',erp.current_app_user_id(),'BOM accessory edited before financial commitment',jsonb_build_object('item_count',jsonb_array_length(p_items),'in_place',true,'explicit_no_accessory',jsonb_array_length(p_items)=0));
    return b.id;
  end if;
  if v_eff<=coalesce(v_last_commit,b.effective_from) or v_eff<=b.effective_from then raise exception 'Tanggal mulai BOM baru harus setelah penggunaan finansial terakhir dan setelah awal versi lama'; end if;
  if b.effective_to is not null and v_eff>=b.effective_to then raise exception 'Tanggal mulai BOM baru harus sebelum akhir versi lama'; end if;
  select min(x.effective_from) into v_next from erp.accessory_bom_versions x where x.product_id=b.product_id and x.id<>b.id and x.effective_from>v_eff;
  v_new_end:=case when b.effective_to is null then v_next when v_next is null then b.effective_to else least(b.effective_to,v_next) end;
  update erp.accessory_bom_versions set effective_to=v_eff where id=b.id;
  insert into erp.accessory_bom_versions(product_id,version_label,effective_from,effective_to,is_active,notes,created_by)
  values(b.product_id,concat(coalesce(b.version_label,'BOM'),' / ',to_char(v_eff,'YYYYMMDD-HH24MI')),v_eff,v_new_end,true,coalesce(p_notes,'Successor BOM from Edit'),erp.current_app_user_id()) returning id into v_new;
  for j in select value from jsonb_array_elements(p_items) loop
    insert into erp.accessory_bom_items(bom_version_id,category_id,qty_per_good_fg_base,hpp_method,hpp_standard_rate,hpp_uom_code,reimbursement_rate,reimbursement_uom_code,notes)
    values(v_new,(j->>'category_id')::uuid,(j->>'qty_per_good_fg_base')::numeric,coalesce(nullif(j->>'hpp_method',''),'CATEGORY_MOVING_AVG'),nullif(j->>'hpp_standard_rate','')::numeric,nullif(j->>'hpp_uom_code',''),coalesce(nullif(j->>'reimbursement_rate','')::numeric,0),nullif(j->>'reimbursement_uom_code',''),j->>'notes');
  end loop;
  insert into erp.audit_logs(entity_type,entity_id,action,changed_by,change_reason,new_data) values('accessory_bom_versions',b.id,'UPDATE',erp.current_app_user_id(),'Committed BOM edited by creating successor',jsonb_build_object('successor_bom_version_id',v_new,'effective_from',v_eff,'item_count',jsonb_array_length(p_items),'explicit_no_accessory',jsonb_array_length(p_items)=0));
  return v_new;
end;
$function$;
