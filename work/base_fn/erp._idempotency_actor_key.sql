-- bootstrap lines 28801-28815
CREATE OR REPLACE FUNCTION erp._idempotency_actor_key()
 RETURNS text
 LANGUAGE sql
 STABLE SECURITY DEFINER
 SET search_path TO 'erp', 'public', 'auth', 'pg_temp'
AS $function$
  select coalesce(
    erp.current_app_user_id()::text,
    auth.uid()::text,
    'database:' || session_user
  )
$function$;

alter function "erp"."_idempotency_actor_key"() owner to "postgres";
