-- ISOLATED PURE PROPOSAL. Not an ERP migration, source collector, or installer.
-- Load only in an isolated database after the unchanged kernel/kernel.sql.
-- Supplied vectors are NOT proven complete/current/authorized Native facts.
CREATE SCHEMA IF NOT EXISTS ow04_ordinal_wrapper;

CREATE OR REPLACE FUNCTION ow04_ordinal_wrapper._id_v1(p_value jsonb, p_reason text)
RETURNS text LANGUAGE plpgsql IMMUTABLE SECURITY INVOKER SET search_path = ''
AS $function$
DECLARE v text;
BEGIN
  v := p_value #>> '{}';
  IF pg_catalog.jsonb_typeof(p_value) IS DISTINCT FROM 'string'
     OR pg_catalog.btrim(v) = '' OR pg_catalog.length(v) > 512 THEN
    RAISE EXCEPTION USING ERRCODE = '22023', MESSAGE = p_reason;
  END IF;
  RETURN v;
END;
$function$;

CREATE OR REPLACE FUNCTION ow04_ordinal_wrapper.normalize_input_v1(p_input jsonb)
RETURNS jsonb LANGUAGE plpgsql IMMUTABLE SECURITY INVOKER SET search_path = ''
AS $function$
DECLARE
  v_keys text[]; v_root text; v_family jsonb; v_families jsonb := '[]';
  v_base jsonb; v_events jsonb; v_i jsonb; v_c jsonb; v_all_source jsonb;
  v_all_movements jsonb := '[]'; v_id text; v_first text; v_ordinal text;
  v_ordinal_number bigint; v_registration text;
BEGIN
  IF pg_catalog.jsonb_typeof(p_input) IS DISTINCT FROM 'object' THEN
    RAISE EXCEPTION USING ERRCODE = '22023', MESSAGE = 'ORDINAL_INPUT_FIELDS_REQUIRED';
  END IF;
  SELECT pg_catalog.array_agg(key ORDER BY key COLLATE "C") INTO v_keys
    FROM pg_catalog.jsonb_object_keys(p_input) AS k(key);
  IF v_keys IS DISTINCT FROM ARRAY['base_events','contract_version','families','family_root_sale_id'] THEN
    RAISE EXCEPTION USING ERRCODE = '22023', MESSAGE = 'ORDINAL_INPUT_FIELDS_REQUIRED';
  END IF;
  IF p_input ->> 'contract_version' IS DISTINCT FROM 'ow04.ordinal-input.v1' THEN
    RAISE EXCEPTION USING ERRCODE = '22023', MESSAGE = 'ORDINAL_INPUT_CONTRACT_REQUIRED';
  END IF;
  v_root := ow04_ordinal_wrapper._id_v1(p_input -> 'family_root_sale_id', 'ROOT_SALE_ID_REQUIRED');
  v_base := ow04_pure_kernel.normalize_events_v1(p_input -> 'base_events', true);
  v_all_source := v_base;
  IF pg_catalog.jsonb_typeof(p_input -> 'families') IS DISTINCT FROM 'array' THEN
    RAISE EXCEPTION USING ERRCODE = '22023', MESSAGE = 'FAMILY_ARRAY_REQUIRED';
  END IF;
  FOR v_family IN SELECT value FROM pg_catalog.jsonb_array_elements(p_input -> 'families') LOOP
    IF pg_catalog.jsonb_typeof(v_family) IS DISTINCT FROM 'object' THEN
      RAISE EXCEPTION USING ERRCODE = '22023', MESSAGE = 'FAMILY_FIELDS_REQUIRED';
    END IF;
    SELECT pg_catalog.array_agg(key ORDER BY key COLLATE "C") INTO v_keys
      FROM pg_catalog.jsonb_object_keys(v_family) AS k(key);
    IF v_keys IS DISTINCT FROM ARRAY['consumptions','events','family_id','first_return_id','ordinal','registration_sha256','retained_recognition'] THEN
      RAISE EXCEPTION USING ERRCODE = '22023', MESSAGE = 'FAMILY_FIELDS_REQUIRED';
    END IF;
    v_id := ow04_ordinal_wrapper._id_v1(v_family -> 'family_id', 'FAMILY_ID_REQUIRED');
    v_first := ow04_ordinal_wrapper._id_v1(v_family -> 'first_return_id', 'FIRST_RETURN_ID_REQUIRED');
    v_ordinal := v_family ->> 'ordinal';
    IF pg_catalog.jsonb_typeof(v_family -> 'ordinal') IS DISTINCT FROM 'string'
       OR v_ordinal !~ '^[1-9][0-9]*$' THEN
      RAISE EXCEPTION USING ERRCODE = '22023', MESSAGE = 'CANONICAL_FAMILY_ORDINAL_REQUIRED';
    END IF;
    BEGIN
      v_ordinal_number := v_ordinal::bigint;
    EXCEPTION WHEN numeric_value_out_of_range OR invalid_text_representation THEN
      RAISE EXCEPTION USING ERRCODE = '22023', MESSAGE = 'CANONICAL_FAMILY_ORDINAL_REQUIRED';
    END;
    v_registration := v_family ->> 'registration_sha256';
    IF pg_catalog.jsonb_typeof(v_family -> 'registration_sha256') IS DISTINCT FROM 'string'
       OR v_registration !~ '^[0-9a-f]{64}$' THEN
      RAISE EXCEPTION USING ERRCODE = '22023', MESSAGE = 'REGISTRATION_SHA256_REQUIRED';
    END IF;
    v_events := ow04_pure_kernel.normalize_events_v1(v_family -> 'events', true);
    IF EXISTS (SELECT 1 FROM pg_catalog.jsonb_array_elements(v_events) AS t(event)
      WHERE event ->> 'kind' <> 'NET') THEN
      RAISE EXCEPTION USING ERRCODE = '22023', MESSAGE = 'FAMILY_NET_EVENTS_REQUIRED';
    END IF;
    v_i := ow04_pure_kernel.normalize_events_v1(v_family -> 'retained_recognition', false);
    v_c := ow04_pure_kernel.normalize_events_v1(v_family -> 'consumptions', false);
    v_families := v_families || pg_catalog.jsonb_build_array(pg_catalog.jsonb_build_object(
      'family_id', v_id, 'ordinal', v_ordinal_number::text, 'first_return_id', v_first,
      'registration_sha256', v_registration, 'events', v_events,
      'retained_recognition', v_i, 'consumptions', v_c
    ));
    v_all_source := v_all_source || v_events;
    v_all_movements := v_all_movements || v_i || v_c;
  END LOOP;
  IF EXISTS (SELECT 1 FROM pg_catalog.jsonb_array_elements(v_families) AS t(f)
    GROUP BY (f ->> 'family_id') COLLATE "C" HAVING pg_catalog.count(*) > 1) THEN
    RAISE EXCEPTION USING ERRCODE = '22023', MESSAGE = 'DUPLICATE_FAMILY_ID';
  END IF;
  IF EXISTS (SELECT 1 FROM pg_catalog.jsonb_array_elements(v_families) AS t(f)
    GROUP BY f ->> 'ordinal' HAVING pg_catalog.count(*) > 1) THEN
    RAISE EXCEPTION USING ERRCODE = '22023', MESSAGE = 'DUPLICATE_FAMILY_ORDINAL';
  END IF;
  IF EXISTS (SELECT 1 FROM pg_catalog.jsonb_array_elements(v_families) AS t(f)
    GROUP BY (f ->> 'first_return_id') COLLATE "C" HAVING pg_catalog.count(*) > 1) THEN
    RAISE EXCEPTION USING ERRCODE = '22023', MESSAGE = 'DUPLICATE_FIRST_RETURN_ID';
  END IF;
  PERFORM ow04_pure_kernel.normalize_events_v1(v_all_source, true);
  IF EXISTS (SELECT 1 FROM pg_catalog.jsonb_array_elements(v_all_movements) AS t(event)
    GROUP BY (event ->> 'id') COLLATE "C" HAVING pg_catalog.count(*) > 1) THEN
    RAISE EXCEPTION USING ERRCODE = '22023', MESSAGE = 'DUPLICATE_MOVEMENT_ID';
  END IF;
  SELECT COALESCE(pg_catalog.jsonb_agg(f ORDER BY (f ->> 'ordinal')::bigint), '[]'::jsonb)
    INTO v_families FROM pg_catalog.jsonb_array_elements(v_families) AS t(f);
  RETURN pg_catalog.jsonb_build_object('contract_version','ow04.ordinal-input.v1',
    'family_root_sale_id',v_root,'base_events',v_base,'families',v_families);
END;
$function$;

CREATE OR REPLACE FUNCTION ow04_ordinal_wrapper._family_net_nonpositive_v1(p_events jsonb)
RETURNS boolean LANGUAGE sql IMMUTABLE SECURITY INVOKER SET search_path = ''
AS $function$
  WITH events AS (
    SELECT event ->> 'economic_date' AS e, event ->> 'transaction_date' AS b,
      (event ->> 'amount')::numeric AS amount
    FROM pg_catalog.jsonb_array_elements(p_events) AS t(event)
  ), ea AS (SELECT DISTINCT e FROM events), ba AS (SELECT DISTINCT b FROM events),
  cells AS (SELECT e,b,pg_catalog.sum(amount) AS amount FROM events GROUP BY e,b),
  economic_scan AS (
    SELECT ea.e,ba.b,pg_catalog.sum(COALESCE(c.amount,0)) OVER (
      PARTITION BY ba.b ORDER BY ea.e COLLATE "C" ROWS UNBOUNDED PRECEDING
    ) AS amount FROM ea CROSS JOIN ba LEFT JOIN cells c ON c.e=ea.e AND c.b=ba.b
  ), prefixes AS (
    SELECT pg_catalog.sum(amount) OVER (
      PARTITION BY e ORDER BY b COLLATE "C" ROWS UNBOUNDED PRECEDING
    ) AS amount FROM economic_scan
  ) SELECT COALESCE(pg_catalog.bool_and(amount<=0),true) FROM prefixes;
$function$;

CREATE OR REPLACE FUNCTION ow04_ordinal_wrapper._component_difference_v1(p_target jsonb,p_retained jsonb)
RETURNS jsonb LANGUAGE sql IMMUTABLE SECURITY INVOKER SET search_path = ''
AS $function$
  WITH source_axes AS (
    SELECT event ->> 'economic_date' AS e,event ->> 'transaction_date' AS b
    FROM pg_catalog.jsonb_array_elements((p_target -> 'before_events') || (p_target -> 'added_events')) AS t(event)
    UNION SELECT event ->> 'economic_date',event ->> 'transaction_date'
    FROM pg_catalog.jsonb_array_elements(p_retained) AS t(event)
  ), ea AS (
    SELECT e,pg_catalog.lag(e) OVER (ORDER BY e COLLATE "C") AS previous_e
    FROM (SELECT DISTINCT e FROM source_axes) AS d
  ), ba AS (
    SELECT b,pg_catalog.lag(b) OVER (ORDER BY b COLLATE "C") AS previous_b
    FROM (SELECT DISTINCT b FROM source_axes) AS d
  ), entries AS (
    SELECT event ->> 'economic_date' AS e,event ->> 'transaction_date' AS b,
      (event ->> 'amount')::numeric AS amount,true AS target
    FROM pg_catalog.jsonb_array_elements(p_target -> 'components') AS t(event)
    UNION ALL SELECT event ->> 'economic_date',event ->> 'transaction_date',
      (event ->> 'amount')::numeric,false FROM pg_catalog.jsonb_array_elements(p_retained) AS t(event)
  ), cells AS (
    SELECT e,b,COALESCE(pg_catalog.sum(amount) FILTER (WHERE target),0) AS target_amount,
      COALESCE(pg_catalog.sum(amount) FILTER (WHERE NOT target),0) AS retained_amount
    FROM entries GROUP BY e,b
  ), economic_scan AS (
    SELECT ea.e,ba.b,ea.previous_e,ba.previous_b,COALESCE(c.target_amount,0) AS target_amount,
      COALESCE(c.retained_amount,0) AS retained_amount,
      pg_catalog.sum(COALESCE(c.target_amount,0)-COALESCE(c.retained_amount,0)) OVER (
        PARTITION BY ba.b ORDER BY ea.e COLLATE "C" ROWS UNBOUNDED PRECEDING
      ) AS amount FROM ea CROSS JOIN ba LEFT JOIN cells c ON c.e=ea.e AND c.b=ba.b
  ), prefixes AS (
    SELECT *,pg_catalog.sum(amount) OVER (
      PARTITION BY e ORDER BY b COLLATE "C" ROWS UNBOUNDED PRECEDING
    ) AS d FROM economic_scan
  ), first_lags AS (
    SELECT *,COALESCE(pg_catalog.lag(d) OVER (PARTITION BY b ORDER BY e COLLATE "C"),0) AS d_prev_e,
      COALESCE(pg_catalog.lag(d) OVER (PARTITION BY e ORDER BY b COLLATE "C"),0) AS d_prev_b
    FROM prefixes
  ), corners AS (
    SELECT *,COALESCE(pg_catalog.lag(d_prev_e) OVER (PARTITION BY e ORDER BY b COLLATE "C"),0) AS d_prev_both
    FROM first_lags
  ) SELECT COALESCE(pg_catalog.jsonb_agg(pg_catalog.jsonb_build_object(
    'amount',pg_catalog.round(target_amount-retained_amount,2)::text,
    'economic_date',e,'transaction_date',b,
    'target_amount',pg_catalog.round(target_amount,2)::text,
    'retained_amount',pg_catalog.round(retained_amount,2)::text,
    'previous_economic_date',previous_e,'previous_transaction_date',previous_b,
    'corners',pg_catalog.jsonb_build_object('d_here',pg_catalog.round(d,2)::text,
      'd_prev_economic',pg_catalog.round(d_prev_e,2)::text,
      'd_prev_transaction',pg_catalog.round(d_prev_b,2)::text,
      'd_prev_both',pg_catalog.round(d_prev_both,2)::text)
  ) ORDER BY e COLLATE "C",b COLLATE "C"),'[]'::jsonb)
  FROM corners WHERE target_amount-retained_amount<>0;
$function$;

-- Role-namespaced derived IDs prevent source IDs from colliding with target atoms.
-- The output hashes of the capacity kernel concern these derived movements;
-- wrapper hashes separately bind the complete supplied original vectors.
CREATE OR REPLACE FUNCTION ow04_ordinal_wrapper._capacity_movements_v1(p_events jsonb,p_role text,p_family text)
RETURNS jsonb LANGUAGE sql IMMUTABLE SECURITY INVOKER SET search_path = ''
AS $function$
  SELECT COALESCE(pg_catalog.jsonb_agg(pg_catalog.jsonb_build_object(
    'id',p_role || ':' || ordinality::text || ':' ||
      ow04_pure_kernel.vector_sha256_v1(pg_catalog.jsonb_build_array(p_family,event ->> 'id')),
    'amount',event ->> 'amount','economic_date',event ->> 'economic_date',
    'transaction_date',event ->> 'transaction_date','source_sha256',
      CASE WHEN p_role='TARGET' THEN ow04_pure_kernel.vector_sha256_v1(event)
        ELSE event ->> 'source_sha256' END
  ) ORDER BY ordinality),'[]'::jsonb)
  FROM pg_catalog.jsonb_array_elements(p_events) WITH ORDINALITY AS t(event,ordinality);
$function$;

CREATE OR REPLACE FUNCTION ow04_ordinal_wrapper.reconcile_v1(p_input jsonb)
RETURNS jsonb LANGUAGE plpgsql IMMUTABLE SECURITY INVOKER SET search_path = ''
AS $function$
DECLARE
  v_input jsonb; v_base jsonb; v_family jsonb; v_prior jsonb; v_target jsonb;
  v_diff jsonb; v_i jsonb; v_c jsonb; v_target_moves jsonb; v_i_moves jsonb; v_c_moves jsonb;
  v_capacity jsonb; v_retained_capacity jsonb; v_families jsonb := '[]'; v_registrations jsonb;
  v_source_view jsonb; v_i_view jsonb; v_c_view jsonb; v_input_sha text; v_source_sha text;
  v_i_sha text; v_c_sha text; v_cohort_binding jsonb; v_cohort_sha text; v_result jsonb;
  v_earliest text; v_supported boolean; v_all_supported boolean := true;
  v_i_net numeric; v_diff_net numeric; v_registration jsonb;
BEGIN
  v_input := ow04_ordinal_wrapper.normalize_input_v1(p_input);
  v_input_sha := ow04_pure_kernel.vector_sha256_v1(v_input);
  v_base := ow04_pure_kernel.recognition_plan_v1('[]',v_input -> 'base_events');
  IF (v_base ->> 'has_recognition_effect')::boolean THEN
    RAISE EXCEPTION USING ERRCODE='22023',MESSAGE='BASE_OVERFLOW_NONZERO';
  END IF;
  SELECT COALESCE(pg_catalog.jsonb_agg(pg_catalog.jsonb_build_object(
    'family_id',f ->> 'family_id','ordinal',f ->> 'ordinal',
    'first_return_id',f ->> 'first_return_id','registration_sha256',f ->> 'registration_sha256'
  ) ORDER BY (f ->> 'ordinal')::bigint),'[]'::jsonb) INTO v_registrations
    FROM pg_catalog.jsonb_array_elements(v_input -> 'families') AS t(f);
  SELECT pg_catalog.jsonb_build_object('family_root_sale_id',v_input ->> 'family_root_sale_id',
    'base_events',v_input -> 'base_events','families',COALESCE(pg_catalog.jsonb_agg(
      (f - 'retained_recognition' - 'consumptions') ORDER BY (f ->> 'ordinal')::bigint),'[]'::jsonb)),
    COALESCE(pg_catalog.jsonb_agg(pg_catalog.jsonb_build_object('family_id',f ->> 'family_id',
      'ordinal',f ->> 'ordinal','events',f -> 'retained_recognition') ORDER BY (f ->> 'ordinal')::bigint),'[]'::jsonb),
    COALESCE(pg_catalog.jsonb_agg(pg_catalog.jsonb_build_object('family_id',f ->> 'family_id',
      'ordinal',f ->> 'ordinal','events',f -> 'consumptions') ORDER BY (f ->> 'ordinal')::bigint),'[]'::jsonb)
    INTO v_source_view,v_i_view,v_c_view FROM pg_catalog.jsonb_array_elements(v_input -> 'families') AS t(f);
  v_source_sha := ow04_pure_kernel.vector_sha256_v1(v_source_view);
  v_i_sha := ow04_pure_kernel.vector_sha256_v1(v_i_view);
  v_c_sha := ow04_pure_kernel.vector_sha256_v1(v_c_view);
  v_prior := v_input -> 'base_events';
  FOR v_family IN SELECT value FROM pg_catalog.jsonb_array_elements(v_input -> 'families') LOOP
    IF NOT ow04_ordinal_wrapper._family_net_nonpositive_v1(v_family -> 'events') THEN
      RAISE EXCEPTION USING ERRCODE='22023',MESSAGE='FAMILY_NET_PREFIX_POSITIVE';
    END IF;
    v_target := ow04_pure_kernel.recognition_plan_v1(v_prior,v_family -> 'events');
    v_i := v_family -> 'retained_recognition'; v_c := v_family -> 'consumptions';
    v_diff := ow04_ordinal_wrapper._component_difference_v1(v_target,v_i);
    IF EXISTS (SELECT 1 FROM pg_catalog.jsonb_array_elements(v_diff) AS t(x)
      WHERE (x ->> 'amount')::numeric IS DISTINCT FROM
        ((x -> 'corners' ->> 'd_here')::numeric-(x -> 'corners' ->> 'd_prev_economic')::numeric
        -(x -> 'corners' ->> 'd_prev_transaction')::numeric+(x -> 'corners' ->> 'd_prev_both')::numeric)) THEN
      RAISE EXCEPTION 'ORDINAL_RECONCILIATION_CORNER_MISMATCH';
    END IF;
    v_target_moves := ow04_ordinal_wrapper._capacity_movements_v1(v_target -> 'components','TARGET',v_family ->> 'family_id');
    v_i_moves := ow04_ordinal_wrapper._capacity_movements_v1(v_i,'RETAINED',v_family ->> 'family_id');
    v_c_moves := ow04_ordinal_wrapper._capacity_movements_v1(v_c,'CONSUMPTION',v_family ->> 'family_id');
    SELECT COALESCE(pg_catalog.min(event ->> 'economic_date'),'0001-01-01') INTO v_earliest
      FROM pg_catalog.jsonb_array_elements(v_target_moves || v_i_moves || v_c_moves) AS t(event);
    v_capacity := ow04_pure_kernel.credit_capacity_v1(v_target_moves,v_c_moves,v_earliest,v_earliest);
    v_retained_capacity := ow04_pure_kernel.credit_capacity_v1(v_i_moves,v_c_moves,v_earliest,v_earliest);
    v_supported := (v_capacity ->> 'source_prefixes_nonnegative')::boolean
      AND (v_retained_capacity ->> 'source_prefixes_nonnegative')::boolean;
    v_all_supported := v_all_supported AND v_supported;
    SELECT COALESCE(pg_catalog.sum((event ->> 'amount')::numeric),0) INTO v_i_net
      FROM pg_catalog.jsonb_array_elements(v_i) AS t(event);
    SELECT COALESCE(pg_catalog.sum((event ->> 'amount')::numeric),0) INTO v_diff_net
      FROM pg_catalog.jsonb_array_elements(v_diff) AS t(event);
    IF v_diff_net IS DISTINCT FROM (v_target ->> 'net_current_k')::numeric-v_i_net THEN
      RAISE EXCEPTION 'ORDINAL_RECONCILIATION_CURRENT_MISMATCH';
    END IF;
    v_registration := v_family - 'events' - 'retained_recognition' - 'consumptions';
    v_cohort_binding := pg_catalog.jsonb_build_object(
      'wrapper_version','ow04-ordinal-wrapper-v1','input_sha256',v_input_sha,
      'family_root_sale_id',v_input ->> 'family_root_sale_id','registration',v_registration,
      'source_target',v_target,'retained_recognition',v_i,'consumptions',v_c,
      'reconciliation_components',v_diff
    );
    v_cohort_sha := ow04_pure_kernel.vector_sha256_v1(v_cohort_binding);
    v_families := v_families || pg_catalog.jsonb_build_array(pg_catalog.jsonb_build_object(
      'registration',v_registration,'registration_required',true,
      'plan_kind',CASE WHEN pg_catalog.jsonb_array_length(v_i)=0 THEN 'INITIAL' ELSE 'ADJUSTMENT' END,
      'supplied_retained_history_present',pg_catalog.jsonb_array_length(v_i)>0,
      'cohort_input_sha256',v_cohort_sha,
      'source_target',v_target,'source_target_sha256',ow04_pure_kernel.vector_sha256_v1(v_target),
      'retained_recognition_sha256',ow04_pure_kernel.vector_sha256_v1(v_i),
      'consumptions_sha256',ow04_pure_kernel.vector_sha256_v1(v_c),
      'component_basis','FAMILY_TARGET_MINUS_ALL_SUPPLIED_RETAINED_RECOGNITION',
      'reconciliation_components',v_diff,'reconciliation_sha256',ow04_pure_kernel.vector_sha256_v1(v_diff),
      'target_net_current',v_target ->> 'net_current_k',
      'retained_net_current',pg_catalog.round(v_i_net,2)::text,
      'reconciliation_net_current',pg_catalog.round(v_diff_net,2)::text,
      'has_reconciliation_effect',pg_catalog.jsonb_array_length(v_diff)>0,
      'needs_cohort_configuration',pg_catalog.jsonb_array_length(v_i)=0 AND (v_target ->> 'has_recognition_effect')::boolean,
      'target_full_prefix_capacity',v_capacity,'retained_full_prefix_capacity',v_retained_capacity,
      'arithmetic_supported',v_supported,'source_authority_proven',false
    ));
    v_prior := v_prior || (v_family -> 'events');
  END LOOP;
  v_result := pg_catalog.jsonb_build_object(
    'contract_version','ow04.ordinal-reconciliation.v1','wrapper_version','ow04-ordinal-wrapper-v1',
    'kernel_version','ow04-2d-difference-v1','evidence_class','PURE_ARITHMETIC_FROM_SUPPLIED_VECTORS',
    'source_authority_proven',false,'input',v_input,'input_sha256',v_input_sha,
    'source_input_sha256',v_source_sha,'retained_recognition_input_sha256',v_i_sha,
    'consumption_input_sha256',v_c_sha,'family_registrations',v_registrations,
    'families',v_families,'arithmetic_supported',v_all_supported
  );
  RETURN v_result || pg_catalog.jsonb_build_object('result_sha256',ow04_pure_kernel.vector_sha256_v1(v_result));
END;
$function$;

CREATE OR REPLACE FUNCTION ow04_ordinal_wrapper.capacity_v1(
  p_input jsonb,p_family_id text,p_economic_date text,p_transaction_date text
)
RETURNS jsonb LANGUAGE plpgsql IMMUTABLE SECURITY INVOKER SET search_path = ''
AS $function$
DECLARE v_result jsonb;v_family jsonb;v_input_family jsonb;v_capacity jsonb;
BEGIN
  v_result := ow04_ordinal_wrapper.reconcile_v1(p_input);
  SELECT f INTO v_family FROM pg_catalog.jsonb_array_elements(v_result -> 'families') AS t(f)
    WHERE (f -> 'registration' ->> 'family_id') COLLATE "C" = p_family_id COLLATE "C";
  IF v_family IS NULL THEN
    RAISE EXCEPTION USING ERRCODE='22023',MESSAGE='FAMILY_NOT_IN_INPUT';
  END IF;
  SELECT f INTO v_input_family FROM pg_catalog.jsonb_array_elements(v_result -> 'input' -> 'families') AS t(f)
    WHERE (f ->> 'family_id') COLLATE "C" = p_family_id COLLATE "C";
  v_capacity := ow04_pure_kernel.credit_capacity_v1(
    ow04_ordinal_wrapper._capacity_movements_v1(v_family -> 'source_target' -> 'components','TARGET',p_family_id),
    ow04_ordinal_wrapper._capacity_movements_v1(v_input_family -> 'consumptions','CONSUMPTION',p_family_id),
    p_economic_date,p_transaction_date
  );
  RETURN pg_catalog.jsonb_build_object('contract_version','ow04.ordinal-capacity.v1',
    'wrapper_version','ow04-ordinal-wrapper-v1','kernel_version','ow04-2d-difference-v1',
    'evidence_class','PURE_ARITHMETIC_FROM_SUPPLIED_VECTORS','source_authority_proven',false,
    'input_sha256',v_result ->> 'input_sha256','source_input_sha256',v_result ->> 'source_input_sha256',
    'family_id',p_family_id,'cohort_input_sha256',v_family ->> 'cohort_input_sha256',
    'reconciliation_sha256',v_family ->> 'reconciliation_sha256',
    'all_cohorts_arithmetic_supported',v_result -> 'arithmetic_supported',
    'cohort_arithmetic_supported',v_family -> 'arithmetic_supported',
    'capacity_basis','RECONCILED_FAMILY_TARGET_MINUS_SUPPLIED_CONSUMPTIONS',
    'capacity_hash_basis','DERIVED_ROLE_NAMESPACED_MOVEMENTS','capacity',v_capacity);
END;
$function$;
