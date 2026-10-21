create function cp7_credit.pg_jsonb_sha256(p jsonb) returns text
language sql immutable security invoker set search_path='' as $$
 select encode(pg_catalog.sha256(convert_to(p::text,'UTF8')),'hex')
$$;