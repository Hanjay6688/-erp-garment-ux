-- bootstrap lines 6743-6758
CREATE OR REPLACE FUNCTION erp.assert_laundry_receipt_reversal_payroll_safe(p_receipt_id uuid)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public', 'pg_temp'
AS $function$
begin
  -- Kept as a compatibility hook for the existing laundry reversal path.
  -- Laundry receipt reversal cannot retract component work already completed,
  -- so it no longer requires reversal of an otherwise valid payroll Nota.
  return;
end;
$function$;

alter function "erp"."assert_laundry_receipt_reversal_payroll_safe"(p_receipt_id uuid) owner to "postgres";
