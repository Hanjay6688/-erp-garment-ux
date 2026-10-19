CREATE OR REPLACE FUNCTION erp.expected_mapping_account_type(p_mapping_key text)
 RETURNS text
 LANGUAGE sql
 IMMUTABLE
 SET search_path TO 'erp', 'public', 'pg_temp'
AS $function$
select case upper(p_mapping_key)
  when 'CASH' then 'ASSET' when 'BANK' then 'ASSET' when 'AR_CUSTOMER' then 'ASSET'
  when 'MATERIAL_INVENTORY' then 'ASSET' when 'WIP' then 'ASSET'
  when 'FG_INVENTORY' then 'ASSET' when 'CONTRACTOR_RECEIVABLE' then 'ASSET'
  when 'AP_VENDOR' then 'LIABILITY' when 'AP_SUPPLIER' then 'LIABILITY'
  when 'GRNI_MATERIAL' then 'LIABILITY'
  when 'ACCRUED_MANUFACTURING' then 'LIABILITY' when 'CONTRACTOR_PAYABLE' then 'LIABILITY'
  when 'OPENING_EQUITY' then 'EQUITY'
  when 'SALES_REVENUE' then 'REVENUE' when 'OTHER_INCOME' then 'REVENUE'
  when 'MATERIAL_RECOVERY' then 'REVENUE'
  when 'COGS' then 'EXPENSE' when 'LAUNDRY_COST' then 'EXPENSE'
  when 'LABOR_COST' then 'EXPENSE' when 'OTHER_EXPENSE' then 'EXPENSE'
  when 'HPP_ADJUSTMENT_CLEARING' then 'EXPENSE'
  when 'ACCESSORY_RECOVERY_COGS' then 'EXPENSE'
  when 'ACCESSORY_REIMBURSE_VARIANCE' then 'EXPENSE'
  when 'MATERIAL_PURCHASE_VARIANCE' then 'EXPENSE'
  else null end
$function$;
