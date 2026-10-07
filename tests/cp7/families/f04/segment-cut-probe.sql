-- Diagnostic only. Not installed by any ERP bundle, and never called by an RPC.
-- Compare the original code-point cut, current tail-copy loop, and a bounded
-- UTF8 byte-window prototype. No business tables, grants, or limits change.
create function public.f04_segment_probe(p_body text,p_n integer,p_method text)
returns jsonb language plpgsql volatile set search_path='' as $$
declare
 started timestamptz:=clock_timestamp();
 parts jsonb:='[]'; part text; rest text;
 data bytea; total_bytes integer; pos integer:=0; finish integer;
 chars integer; idx integer:=0; tail_copied bigint:=0; windows_decoded bigint:=0;
begin
 if p_n is null or p_n<1 or p_n>2000000 then raise exception 'PROBE_BAD_CHUNK';end if;
 if p_method not in('REFERENCE','CURRENT','WINDOW','BAD_SIZE','SKIP_LAST')then raise exception 'PROBE_BAD_METHOD';end if;
 if p_body is null then return null;end if;
 chars:=length(p_body);total_bytes:=octet_length(p_body);
 if p_method='CURRENT'then rest:=p_body;
 elsif p_method in('WINDOW','BAD_SIZE','SKIP_LAST')then data:=convert_to(p_body,'UTF8');end if;
 while case when p_method='REFERENCE'then idx*p_n<chars
            when p_method='CURRENT'then rest<>''else pos<total_bytes end loop
  if p_method='REFERENCE'then part:=substr(p_body,idx*p_n+1,p_n);
  elsif p_method='CURRENT'then
   part:=left(rest,p_n);rest:=right(rest,-p_n);
   -- Actual bytes copied by text_right's cstring_to_text_with_len; this is
   -- separate from character scanning, and is NOT included in parity data.
   tail_copied:=tail_copied+octet_length(rest);
  else
   -- UTF8 needs at most four bytes per code point. Byte offsets do not recount
   -- previous characters or copy the entire remaining tail. Trim at most
   -- three continuation bytes so convert_from sees a complete UTF8 prefix.
   finish:=least(total_bytes,pos+4*p_n);
   while finish<total_bytes and get_byte(data,finish)between 128 and 191 loop finish:=finish-1;end loop;
   windows_decoded:=windows_decoded+finish-pos;
   part:=left(convert_from(substr(data,pos+1,finish-pos),'UTF8'),p_n+case when p_method='BAD_SIZE'then 1 else 0 end);
   pos:=pos+octet_length(part);
   if p_method='SKIP_LAST'and pos=total_bytes then exit;end if;
  end if;
  if part=''then raise exception 'PROBE_NO_PROGRESS';end if;
  parts:=parts||jsonb_build_array(jsonb_build_object('idx',idx,'characters',length(part),
   'utf8_bytes',octet_length(part),'sha256',encode(pg_catalog.sha256(convert_to(part,'UTF8')),'hex')));
  idx:=idx+1;
 end loop;
 return jsonb_build_object('parts',parts,'characters',chars,'utf8_bytes',total_bytes,
  'ms',extract(epoch from(clock_timestamp()-started))*1000,
  'tail_bytes_copied',tail_copied,'window_bytes_decoded',windows_decoded);
end $$;
