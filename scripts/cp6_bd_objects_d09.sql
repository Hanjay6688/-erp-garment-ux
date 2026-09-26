-- ================================================================ D09 (owner 26 Sep 2026, ACC-C12 option a; not laundry, carried by BD
-- as the next unreleased family): every pending item of the opening accessory custody file names its source, either a count
-- sheet with its line/item (count_sheet + sheet_line) or a source lot (source_lot), one form only. The source identity stays
-- with the goods whatever custody key a later request uses: a second row with the same source (same sheet line, or same lot)
-- is refused (BC_C12_SAME_SOURCE), in the same batch or after an earlier post; other lines of the same sheet are accepted (the
-- sheet itself is not locked). Identity: the kind, then the trimmed text lower-cased with inner white space collapsed.
-- The two BC import functions take it through checked substitutions (scripts/cp6_bd_build.py D09_*); this file holds the
-- table and the identity function.

create table erp.bd_custody_sources_v1(
  source_identity text primary key,
  custody_kind text not null check(custody_kind in('PENDING_VALUE','UNRETURNED','CUSTOMER_GARMENT')),
  record_id uuid not null unique,
  batch_id uuid not null references erp.migration_batches(id),
  source_row_id uuid not null unique references erp.migration_staging_rows(id),
  count_sheet text,
  sheet_line text,
  source_lot text,
  created_at timestamptz not null default statement_timestamp(),
  check((count_sheet is not null and sheet_line is not null and source_lot is null)
     or (count_sheet is null and sheet_line is null and source_lot is not null))
);

-- The source identity of one custody payload; p_strict raises on a missing, ambiguous or too long reference, otherwise NULL.
CREATE OR REPLACE FUNCTION erp.bd_custody_source_identity_v1(p jsonb,p_strict boolean DEFAULT true)
 RETURNS text LANGUAGE plpgsql IMMUTABLE SET search_path TO ''
AS $function$
declare
  s text:=nullif(regexp_replace(btrim(coalesce(p->>'count_sheet','')),'\s+',' ','g'),'');
  l text:=nullif(regexp_replace(btrim(coalesce(p->>'sheet_line','')),'\s+',' ','g'),'');
  t text:=nullif(regexp_replace(btrim(coalesce(p->>'source_lot','')),'\s+',' ','g'),'');
begin
  if s is not null and l is not null and t is null then
    if length(s)<=80 and length(l)<=40 then return 'SHEET:'||lower(s)||'#'||lower(l);end if;
    if p_strict then raise exception 'count_sheet/sheet_line: maksimal 80 dan 40 karakter';end if;
    return null;
  elsif t is not null and s is null and l is null then
    if length(t)<=80 then return 'LOT:'||lower(t);end if;
    if p_strict then raise exception 'source_lot: maksimal 80 karakter';end if;
    return null;
  end if;
  if p_strict then
    raise exception 'BC_C12_SOURCE_REQUIRED: item pending wajib rujukan sumber, salah satu saja: lembar hitung + baris (count_sheet, sheet_line) atau lot sumber (source_lot)';
  end if;
  return null;
end;$function$;
