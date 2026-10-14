-- bootstrap lines 5359-5401
CREATE OR REPLACE FUNCTION erp._idempotency_begin(p_operation_name text, p_client_request_id uuid, p_request_hash text)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public', 'pg_temp'
AS $function$
declare
  v_actor text := erp._idempotency_actor_key();
  v_row erp.idempotency_requests%rowtype;
begin
  if p_client_request_id is null then
    raise exception 'client_request_id is required';
  end if;
  if coalesce(btrim(p_operation_name), '') = '' then
    raise exception 'operation_name is required';
  end if;

  insert into erp.idempotency_requests(
    actor_key, operation_name, client_request_id, request_hash
  ) values (
    v_actor, p_operation_name, p_client_request_id, p_request_hash
  )
  on conflict do nothing;

  select * into v_row
  from erp.idempotency_requests
  where actor_key = v_actor
    and operation_name = p_operation_name
    and client_request_id = p_client_request_id
  for update;

  if v_row.request_hash <> p_request_hash then
    raise exception 'client_request_id was already used with a different payload';
  end if;
  if v_row.status = 'COMPLETED' then
    return v_row.response_payload;
  end if;
  return null;
end;
$function$;

alter function "erp"."_idempotency_begin"(p_operation_name text, p_client_request_id uuid, p_request_hash text) owner to "postgres";
