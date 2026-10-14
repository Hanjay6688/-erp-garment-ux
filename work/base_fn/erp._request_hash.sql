-- bootstrap lines 26435-26445
CREATE OR REPLACE FUNCTION erp._request_hash(p_payload jsonb)
 RETURNS text
 LANGUAGE sql
 IMMUTABLE SECURITY DEFINER
 SET search_path TO 'erp', 'public', 'extensions', 'pg_temp'
AS $function$
  select encode(extensions.digest(convert_to(coalesce(p_payload, '{}'::jsonb)::text, 'UTF8'), 'sha256'), 'hex')
$function$;

alter function "erp"."_request_hash"(p_payload jsonb) owner to "postgres";
