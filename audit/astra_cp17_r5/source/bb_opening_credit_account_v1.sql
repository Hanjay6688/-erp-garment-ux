CREATE OR REPLACE FUNCTION erp.bb_opening_credit_account_v1(p_settlement_id uuid)
 RETURNS uuid LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
  select case c.credit_kind when 'VENDOR_CLAIM_APPLY' then erp.account_id('AP_VENDOR') when 'VENDOR_CORRECTION_APPLY' then erp.account_id('AP_VENDOR') when 'ACCESSORY_NOTE_RETURN' then erp.account_id('MATERIAL_RECOVERY') when 'CUSTOMER_ALLOWANCE' then erp.account_id('SALES_REVENUE')
    when 'SUPPLIER_ALLOWANCE' then erp.account_id('MATERIAL_PURCHASE_VARIANCE') when 'VENDOR_ALLOWANCE' then erp.account_id('OTHER_INCOME')
    else (select k.coa_account_id from erp.bb_customer_credits_v1 k where k.id=c.customer_credit_id) end
  from erp.bb_opening_credits_v1 c where c.settlement_id=p_settlement_id
$function$;
