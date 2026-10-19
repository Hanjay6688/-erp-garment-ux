create or replace function erp.pocket_fabric_checks_v1()
returns table(check_name text,severity text,issue_count bigint,details text) language sql stable security definer set search_path='' set TimeZone='UTC' as $function$
 with docs as (
  select u.*,h.status,h.physical_at,h.reason_code,to_jsonb(h)-'status'-'row_version'-'updated_at' header,
   (erp._cp6_material_adjustment_revaluation_state(h.id)->>'current_value')::numeric signed_value
  from erp.pocket_fabric_usage u join erp.material_adjustments h on h.id=u.adjustment_id
 ), original_journals as (
  select u.adjustment_id,j.id from docs u join erp.journal_entries j on j.source_type='MATERIAL_ADJUSTMENT' and j.source_id=u.adjustment_id
  union select u.adjustment_id,f.journal_entry_id from docs u join erp.material_adjustment_revaluation_facts f on f.adjustment_id=u.adjustment_id
 ), all_journals as (
  select * from original_journals union select o.adjustment_id,j.id from original_journals o join erp.journal_entries j on j.reversal_of_id=o.id
 )
 select 'AP_POCKET_SOURCE'::text,'CRITICAL'::text,count(*),'Pocket outflow preserves the original roll, quantity and posted source'::text from docs u where u.header<>u.posted_header or u.reason_code<>'INTERNAL_FACTORY_USE'
  or u.status not in('POSTED','REVERSED') or (select count(*) from erp.material_adjustment_items where adjustment_id=u.adjustment_id)<>1
  or not exists(select 1 from erp.material_adjustment_items i where i.adjustment_id=u.adjustment_id and to_jsonb(i)=u.posted_item
    and i.material_id=u.material_id and i.roll_id=u.roll_id and i.qty_signed=-u.issued_quantity)
 union all select 'AP_POCKET_EXPENSE_LEDGER','CRITICAL',count(*),'Current outflow value reconciles to inventory and period expense including corrections and inverses' from docs u where
  erp._cp6_supplier_cent_ledger((select array_agg(j.id) from all_journals j where j.adjustment_id=u.adjustment_id))
  is distinct from case when u.signed_value=0 then '{}'::jsonb else jsonb_build_object(
   erp.account_id('MATERIAL_INVENTORY')::text,u.signed_value,erp.account_id('OTHER_EXPENSE')::text,-u.signed_value) end
 union all select 'AP_POCKET_NO_CUTTING','CRITICAL',count(*),'Pocket fabric does not create sized cutting output' from erp.cutting_group_rolls c join erp.material_rolls r on r.id=c.roll_id
  join erp.pocket_fabric_materials p on p.material_id=r.material_id;
$function$;
