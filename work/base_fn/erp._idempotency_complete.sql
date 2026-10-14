-- bootstrap lines 5402-5425
CREATE OR REPLACE FUNCTION erp._idempotency_complete(p_operation_name text, p_client_request_id uuid, p_response jsonb)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public', 'pg_temp'
AS $function$
declare
  v_actor text := erp._idempotency_actor_key();
begin
  update erp.idempotency_requests
  set status = 'COMPLETED', response_payload = p_response, updated_at = now()
  where actor_key = v_actor
    and operation_name = p_operation_name
    and client_request_id = p_client_request_id
    and status = 'IN_PROGRESS';
  if not found then
    raise exception 'Idempotency request is missing or already completed';
  end if;
  return p_response;
end;
$function$;

alter function "erp"."_idempotency_complete"(p_operation_name text, p_client_request_id uuid, p_response jsonb) owner to "postgres";
