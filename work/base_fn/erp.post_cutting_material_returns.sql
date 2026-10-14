-- bootstrap lines 12708-12755
CREATE OR REPLACE FUNCTION erp.post_cutting_material_returns(p_cutting_group_id uuid, p_location_id uuid)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare
  g erp.cutting_groups%rowtype;
  r record;
  v_value numeric(24,6);
begin
  perform erp.require_internal();
  select * into g from erp.cutting_groups where id=p_cutting_group_id for update;
  if g.id is null or not g.material_issue_posted then raise exception 'Cutting issue must be posted first'; end if;
  if g.material_return_posted then raise exception 'Cutting return already posted'; end if;
  if p_location_id is null or not exists(select 1 from erp.locations where id=p_location_id and is_active=true and location_type='RAW_MATERIAL_WAREHOUSE') then
    raise exception 'Lokasi return cutting harus gudang bahan aktif';
  end if;
  if exists(select 1 from erp.cutting_group_rolls where cutting_group_id=p_cutting_group_id and qty_physically_returned>0 and coalesce(return_destination,'NONE')<>'WAREHOUSE') then
    raise exception 'Positive cutting returns with destination other than WAREHOUSE require a dedicated supplier/scrap flow; they cannot be silently posted as warehouse returns';
  end if;
  if exists(select 1 from erp.cutting_group_rolls where cutting_group_id=p_cutting_group_id and qty_physically_returned>0 and return_destination='WAREHOUSE' and returned_at is null) then
    raise exception 'Tanggal/jam fisik return cutting wajib diisi untuk setiap roll yang kembali ke gudang';
  end if;

  for r in
    select cgr.*,mr.material_id
    from erp.cutting_group_rolls cgr join erp.material_rolls mr on mr.id=cgr.roll_id
    where cgr.cutting_group_id=p_cutting_group_id and cgr.qty_physically_returned>0 and cgr.return_destination='WAREHOUSE'
    order by cgr.returned_at,cgr.id
  loop
    insert into erp.material_stock_movements(material_id,roll_id,location_id,movement_type,qty_signed,input_unit_cost,source_type,source_id,physical_at,created_by)
    values(r.material_id,r.roll_id,p_location_id,'CUTTING_RETURN',r.qty_physically_returned,r.unit_cost_snapshot,'CUTTING_GROUP_RETURN',p_cutting_group_id,r.returned_at,erp.current_app_user_id());
    perform erp.recalculate_material_cost(r.material_id);
    v_value:=r.qty_physically_returned*coalesce(r.unit_cost_snapshot,0);
    if abs(v_value)>0.005 then
      perform erp.post_journal('CUTTING_MATERIAL_RETURN_LINE',r.id,r.returned_at::date,'Unused cutting material physically returned',jsonb_build_array(
        jsonb_build_object('mapping_key','MATERIAL_INVENTORY','debit',round(v_value,2),'credit',0,'po_id',g.po_id),
        jsonb_build_object('mapping_key','WIP','debit',0,'credit',round(v_value,2),'po_id',g.po_id)
      ));
    end if;
  end loop;
  update erp.cutting_groups set material_return_posted=true where id=p_cutting_group_id;
end;
$function$;

alter function "erp"."post_cutting_material_returns"(p_cutting_group_id uuid, p_location_id uuid) owner to "postgres";
