-- Diagnostic only. Capture the same canonical chunk digests with the report's
-- STABLE statement snapshot. No row xmin or commit-time inference is involved.
create function cp7_finance_capture.report_book_diagnostic_v1(p_as_of date,p_chunk_rows integer)
returns jsonb language plpgsql stable security definer
set search_path='' set TimeZone='UTC' set jit=off as $book$
declare family text; last_key text; part jsonb; n bigint; total bigint; unit integer:=1;
 pieces text[]:=array[]::text[]; counts jsonb:='{}';
begin
 if p_as_of is null or p_chunk_rows is null or p_chunk_rows<=0 then
  raise exception 'CP7_FINANCE_CAPTURE_QUERY';
 end if;
 foreach family in array array['journal','line','book','cash'] loop
  last_key:=null;total:=0;
  loop
   part:=cp7_finance_capture.book_chunk(family,p_as_of,last_key,p_chunk_rows,null);
   n:=(part->>'rows')::bigint;
   if n=0 then exit;end if;
   if n is null or n<0 or n>p_chunk_rows or part->>'last_key' is null
    or part->>'digest' is null or (part->>'digest')!~'^[0-9a-f]{64}$'
    or part->>'last_key' is not distinct from last_key then
    raise exception 'CP7_FINANCE_CAPTURE_INVARIANT';
   end if;
   pieces:=array_append(pieces,family||':'||unit||':'||n||':'||(part->>'digest'));
   total:=total+n;unit:=unit+1;last_key:=part->>'last_key';
   if n<p_chunk_rows then exit;end if;
  end loop;
  counts:=counts||jsonb_build_object(family,total);
 end loop;
 return jsonb_build_object('rows',counts,'signature',
  encode(pg_catalog.sha256(convert_to(coalesce(array_to_string(pieces,E'\n'),''),'UTF8')),'hex'));
end
$book$;
alter function cp7_finance_capture.report_book_diagnostic_v1(date,integer) owner to cp7_finance_read;
revoke all on function cp7_finance_capture.report_book_diagnostic_v1(date,integer)
 from public,anon,authenticated,service_role,cp7_capture;
