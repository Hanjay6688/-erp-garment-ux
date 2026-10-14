-- bootstrap lines 18033-18054
CREATE OR REPLACE FUNCTION erp.reverse_journal(p_journal_entry_id uuid, p_reason text)
 RETURNS uuid
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public', 'pg_temp'
AS $function$
declare v_source_type text;
begin
  perform erp.require_internal();
  if nullif(btrim(p_reason),'') is null then raise exception 'Journal reversal reason is required'; end if;
  select source_type into v_source_type
  from erp.journal_entries where id=p_journal_entry_id for update;
  if v_source_type is null then raise exception 'Journal entry not found'; end if;
  if v_source_type in ('ATTENDANCE_HPP_POOL','PAYROLL_ATTENDANCE_ACCRUAL') then
    raise exception 'Protected journal source type % cannot be reversed through generic reverse_journal. Use the owning attendance HPP pool or payroll cancellation/reversal flow.',v_source_type;
  end if;
  return erp._cp3_r4_reverse_journal_internal(p_journal_entry_id,p_reason);
end
$function$;

alter function "erp"."reverse_journal"(p_journal_entry_id uuid, p_reason text) owner to "postgres";
