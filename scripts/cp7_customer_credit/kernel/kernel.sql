-- ISOLATED ARITHMETIC PROPOSAL. This file is NOT a product migration/installer.
-- No tables, source collector, posting authority, clock, account, or Native RPC.
-- PostgreSQL >= 14; built-in sha256(bytea), jsonb, numeric, and PL/pgSQL only.
CREATE SCHEMA IF NOT EXISTS ow04_pure_kernel;

CREATE OR REPLACE FUNCTION ow04_pure_kernel.canonical_date_v1(p_value text)
RETURNS text
LANGUAGE plpgsql IMMUTABLE SECURITY INVOKER
SET search_path = ''
AS $function$
BEGIN
  IF p_value IS NULL OR p_value !~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'
     OR pg_catalog.substr(p_value, 1, 4) = '0000' THEN
    RAISE EXCEPTION USING ERRCODE = '22023', MESSAGE = 'CANONICAL_DATE_REQUIRED';
  END IF;
  BEGIN
    PERFORM pg_catalog.make_date(
      pg_catalog.substr(p_value, 1, 4)::integer,
      pg_catalog.substr(p_value, 6, 2)::integer,
      pg_catalog.substr(p_value, 9, 2)::integer
    );
  EXCEPTION WHEN datetime_field_overflow OR invalid_datetime_format THEN
    RAISE EXCEPTION USING ERRCODE = '22023', MESSAGE = 'CANONICAL_DATE_REQUIRED';
  END;
  RETURN p_value;
END;
$function$;

CREATE OR REPLACE FUNCTION ow04_pure_kernel.exact_amount_v1(p_value jsonb)
RETURNS text
LANGUAGE plpgsql IMMUTABLE SECURITY INVOKER
SET search_path = ''
AS $function$
DECLARE
  v_text text;
  v_number numeric;
BEGIN
  IF pg_catalog.jsonb_typeof(p_value) IS DISTINCT FROM 'string' THEN
    RAISE EXCEPTION USING ERRCODE = '22023', MESSAGE = 'EXACT_CENTS_REQUIRED';
  END IF;
  v_text := p_value #>> '{}';
  -- No exponent, non-finite value, whitespace, leading zero, or fractional cent.
  IF v_text !~ '^[+-]?(0|[1-9][0-9]*)([.][0-9]{1,2})?$' THEN
    RAISE EXCEPTION USING ERRCODE = '22023', MESSAGE = 'EXACT_CENTS_REQUIRED';
  END IF;
  BEGIN
    v_number := v_text::numeric;
  EXCEPTION WHEN numeric_value_out_of_range OR invalid_text_representation THEN
    RAISE EXCEPTION USING ERRCODE = '22023', MESSAGE = 'EXACT_CENTS_REQUIRED';
  END;
  RETURN pg_catalog.round(v_number, 2)::text;
END;
$function$;

CREATE OR REPLACE FUNCTION ow04_pure_kernel.normalize_events_v1(
  p_events jsonb,
  p_source_events boolean
)
RETURNS jsonb
LANGUAGE plpgsql IMMUTABLE SECURITY INVOKER
SET search_path = ''
AS $function$
DECLARE
  v_event jsonb;
  v_normalized jsonb := '[]'::jsonb;
  v_fields text[];
  v_required text[];
  v_id text;
  v_economic text;
  v_transaction text;
  v_amount text;
  v_sha256 text;
  v_item jsonb;
BEGIN
  IF pg_catalog.jsonb_typeof(p_events) IS DISTINCT FROM 'array' THEN
    RAISE EXCEPTION USING ERRCODE = '22023', MESSAGE = 'SOURCE_EVENT_ARRAY_REQUIRED';
  END IF;
  IF p_source_events IS NULL THEN
    RAISE EXCEPTION USING ERRCODE = '22023', MESSAGE = 'EVENT_SHAPE_REQUIRED';
  END IF;
  v_required := CASE WHEN p_source_events
    THEN ARRAY['amount', 'economic_date', 'id', 'kind', 'source_sha256', 'transaction_date']
    ELSE ARRAY['amount', 'economic_date', 'id', 'source_sha256', 'transaction_date']
  END;
  FOR v_event IN SELECT value FROM pg_catalog.jsonb_array_elements(p_events)
  LOOP
    IF pg_catalog.jsonb_typeof(v_event) IS DISTINCT FROM 'object' THEN
      RAISE EXCEPTION USING ERRCODE = '22023', MESSAGE = 'SOURCE_EVENT_FIELDS_REQUIRED';
    END IF;
    SELECT pg_catalog.array_agg(key ORDER BY key COLLATE "C")
      INTO v_fields FROM pg_catalog.jsonb_object_keys(v_event) AS fields(key);
    IF v_fields IS DISTINCT FROM v_required THEN
      RAISE EXCEPTION USING ERRCODE = '22023', MESSAGE = 'SOURCE_EVENT_FIELDS_REQUIRED';
    END IF;
    v_id := v_event ->> 'id';
    IF pg_catalog.jsonb_typeof(v_event -> 'id') IS DISTINCT FROM 'string'
       OR pg_catalog.btrim(v_id) = '' OR pg_catalog.length(v_id) > 512 THEN
      RAISE EXCEPTION USING ERRCODE = '22023', MESSAGE = 'EVENT_ID_REQUIRED';
    END IF;
    IF p_source_events AND (
      pg_catalog.jsonb_typeof(v_event -> 'kind') IS DISTINCT FROM 'string'
      OR v_event ->> 'kind' NOT IN ('NET', 'FUNDING')
    ) THEN
      RAISE EXCEPTION USING ERRCODE = '22023', MESSAGE = 'SOURCE_KIND_REQUIRED';
    END IF;
    v_sha256 := v_event ->> 'source_sha256';
    IF pg_catalog.jsonb_typeof(v_event -> 'source_sha256') IS DISTINCT FROM 'string'
       OR v_sha256 !~ '^[0-9a-f]{64}$' THEN
      RAISE EXCEPTION USING ERRCODE = '22023', MESSAGE = 'SOURCE_SHA256_REQUIRED';
    END IF;
    IF pg_catalog.jsonb_typeof(v_event -> 'economic_date') IS DISTINCT FROM 'string'
       OR pg_catalog.jsonb_typeof(v_event -> 'transaction_date') IS DISTINCT FROM 'string' THEN
      RAISE EXCEPTION USING ERRCODE = '22023', MESSAGE = 'CANONICAL_DATE_REQUIRED';
    END IF;
    v_economic := ow04_pure_kernel.canonical_date_v1(v_event ->> 'economic_date');
    v_transaction := ow04_pure_kernel.canonical_date_v1(v_event ->> 'transaction_date');
    IF (v_transaction COLLATE "C") < (v_economic COLLATE "C") THEN
      RAISE EXCEPTION USING ERRCODE = '22023', MESSAGE = 'BOOK_BEFORE_ECONOMIC';
    END IF;
    v_amount := ow04_pure_kernel.exact_amount_v1(v_event -> 'amount');
    v_item := pg_catalog.jsonb_build_object(
      'id', v_id, 'amount', v_amount,
      'economic_date', v_economic, 'transaction_date', v_transaction,
      'source_sha256', v_sha256
    );
    IF p_source_events THEN
      v_item := v_item || pg_catalog.jsonb_build_object('kind', v_event ->> 'kind');
    END IF;
    v_normalized := v_normalized || pg_catalog.jsonb_build_array(v_item);
  END LOOP;
  IF EXISTS (
    SELECT 1 FROM pg_catalog.jsonb_array_elements(v_normalized) AS t(event)
    GROUP BY event ->> 'id' HAVING pg_catalog.count(*) > 1
  ) THEN
    RAISE EXCEPTION USING ERRCODE = '22023', MESSAGE = 'DUPLICATE_EVENT_ID';
  END IF;
  SELECT COALESCE(pg_catalog.jsonb_agg(event ORDER BY (event ->> 'id') COLLATE "C"), '[]'::jsonb)
    INTO v_normalized FROM pg_catalog.jsonb_array_elements(v_normalized) AS t(event);
  RETURN v_normalized;
END;
$function$;

CREATE OR REPLACE FUNCTION ow04_pure_kernel.vector_sha256_v1(p_normalized_vector jsonb)
RETURNS text
LANGUAGE sql IMMUTABLE STRICT SECURITY INVOKER
SET search_path = ''
AS $function$
  SELECT pg_catalog.encode(
    pg_catalog.sha256(pg_catalog.convert_to(p_normalized_vector::text, 'UTF8')), 'hex'
  );
$function$;

CREATE OR REPLACE FUNCTION ow04_pure_kernel.recognition_plan_v1(
  p_before jsonb,
  p_added jsonb
)
RETURNS jsonb
LANGUAGE plpgsql IMMUTABLE SECURITY INVOKER
SET search_path = ''
AS $function$
DECLARE
  v_before jsonb;
  v_added jsonb;
  v_after jsonb;
  v_grid jsonb;
  v_components jsonb;
  v_support jsonb;
  v_net numeric := 0;
BEGIN
  v_before := ow04_pure_kernel.normalize_events_v1(p_before, true);
  v_added := ow04_pure_kernel.normalize_events_v1(p_added, true);
  -- Uniqueness includes before/added together; an inverse has its own event ID.
  v_after := ow04_pure_kernel.normalize_events_v1(v_before || v_added, true);
  WITH events AS (
    SELECT event ->> 'kind' AS kind, (event ->> 'amount')::numeric AS amount,
      event ->> 'economic_date' AS e, event ->> 'transaction_date' AS b, false AS added
    FROM pg_catalog.jsonb_array_elements(v_before) AS t(event)
    UNION ALL
    SELECT event ->> 'kind', (event ->> 'amount')::numeric,
      event ->> 'economic_date', event ->> 'transaction_date', true
    FROM pg_catalog.jsonb_array_elements(v_added) AS t(event)
  ), economic_axis AS (
    SELECT e, pg_catalog.lag(e) OVER (ORDER BY e COLLATE "C") AS previous_e
    FROM (SELECT DISTINCT e FROM events) AS axis
  ), transaction_axis AS (
    SELECT b, pg_catalog.lag(b) OVER (ORDER BY b COLLATE "C") AS previous_b
    FROM (SELECT DISTINCT b FROM events) AS axis
  ), cells AS (
    SELECT e, b,
      COALESCE(pg_catalog.sum(amount) FILTER (WHERE kind = 'NET' AND NOT added), 0) AS before_net,
      COALESCE(pg_catalog.sum(amount) FILTER (WHERE kind = 'FUNDING' AND NOT added), 0) AS before_funding,
      COALESCE(pg_catalog.sum(amount) FILTER (WHERE kind = 'NET'), 0) AS after_net,
      COALESCE(pg_catalog.sum(amount) FILTER (WHERE kind = 'FUNDING'), 0) AS after_funding
    FROM events GROUP BY e, b
  ), economic_scan AS (
    SELECT ea.e, ba.b, ea.previous_e, ba.previous_b,
      pg_catalog.sum(COALESCE(c.before_net, 0)) OVER w AS before_net,
      pg_catalog.sum(COALESCE(c.before_funding, 0)) OVER w AS before_funding,
      pg_catalog.sum(COALESCE(c.after_net, 0)) OVER w AS after_net,
      pg_catalog.sum(COALESCE(c.after_funding, 0)) OVER w AS after_funding
    FROM economic_axis ea CROSS JOIN transaction_axis ba
    LEFT JOIN cells c ON c.e = ea.e AND c.b = ba.b
    WINDOW w AS (PARTITION BY ba.b ORDER BY ea.e COLLATE "C" ROWS UNBOUNDED PRECEDING)
  ), prefixes AS (
    SELECT e, b, previous_e, previous_b,
      pg_catalog.sum(before_net) OVER w AS before_net,
      pg_catalog.sum(before_funding) OVER w AS before_funding,
      pg_catalog.sum(after_net) OVER w AS after_net,
      pg_catalog.sum(after_funding) OVER w AS after_funding
    FROM economic_scan
    WINDOW w AS (PARTITION BY e ORDER BY b COLLATE "C" ROWS UNBOUNDED PRECEDING)
  ), differences AS (
    SELECT *, GREATEST(after_funding - after_net, 0)
      - GREATEST(before_funding - before_net, 0) AS d
    FROM prefixes
  ), first_lags AS (
    SELECT *, COALESCE(pg_catalog.lag(d) OVER (PARTITION BY b ORDER BY e COLLATE "C"), 0) AS d_prev_e,
      COALESCE(pg_catalog.lag(d) OVER (PARTITION BY e ORDER BY b COLLATE "C"), 0) AS d_prev_b
    FROM differences
  ), corners AS (
    SELECT *, COALESCE(pg_catalog.lag(d_prev_e) OVER (PARTITION BY e ORDER BY b COLLATE "C"), 0) AS d_prev_both
    FROM first_lags
  )
  SELECT COALESCE(pg_catalog.jsonb_agg(pg_catalog.jsonb_build_object(
    'economic_date', e, 'transaction_date', b,
    'previous_economic_date', previous_e, 'previous_transaction_date', previous_b,
    'before_net', before_net::text, 'before_funding', before_funding::text,
    'after_net', after_net::text, 'after_funding', after_funding::text,
    'd_here', pg_catalog.round(d, 2)::text,
    'd_prev_economic', pg_catalog.round(d_prev_e, 2)::text,
    'd_prev_transaction', pg_catalog.round(d_prev_b, 2)::text,
    'd_prev_both', pg_catalog.round(d_prev_both, 2)::text,
    'amount', pg_catalog.round(d - d_prev_e - d_prev_b + d_prev_both, 2)::text
  ) ORDER BY e COLLATE "C", b COLLATE "C"), '[]'::jsonb) INTO v_grid FROM corners;

  -- These are source-prefix constraints, not a ban on overflow recognition.
  -- Validate BOTH complete snapshots; an added repair cannot conceal bad before.
  IF EXISTS (
    SELECT 1 FROM pg_catalog.jsonb_array_elements(v_grid) AS t(cell)
    WHERE (cell ->> 'before_net')::numeric < 0 OR (cell ->> 'after_net')::numeric < 0
  ) THEN
    RAISE EXCEPTION USING ERRCODE = '22023', MESSAGE = 'SOURCE_NET_BEFORE_SALE';
  END IF;
  IF EXISTS (
    SELECT 1 FROM pg_catalog.jsonb_array_elements(v_grid) AS t(cell)
    WHERE (cell ->> 'before_funding')::numeric < 0 OR (cell ->> 'after_funding')::numeric < 0
  ) THEN
    RAISE EXCEPTION USING ERRCODE = '22023', MESSAGE = 'NEGATIVE_SOURCE_FUNDING';
  END IF;
  IF EXISTS (
    SELECT 1 FROM pg_catalog.jsonb_array_elements(v_grid) AS t(cell)
    WHERE (cell ->> 'amount')::numeric <> 0
      AND (cell ->> 'transaction_date') COLLATE "C" < (cell ->> 'economic_date') COLLATE "C"
  ) THEN
    RAISE EXCEPTION USING ERRCODE = '22023', MESSAGE = 'COMPONENT_BOOK_BEFORE_ECONOMIC';
  END IF;
  SELECT COALESCE(pg_catalog.jsonb_agg(pg_catalog.jsonb_build_object(
    'economic_date', cell ->> 'economic_date', 'transaction_date', cell ->> 'transaction_date',
    'previous_economic_date', cell -> 'previous_economic_date',
    'previous_transaction_date', cell -> 'previous_transaction_date',
    'amount', cell ->> 'amount',
    'corners', pg_catalog.jsonb_build_object(
      'd_here', cell ->> 'd_here', 'd_prev_economic', cell ->> 'd_prev_economic',
      'd_prev_transaction', cell ->> 'd_prev_transaction', 'd_prev_both', cell ->> 'd_prev_both'
    )
  ) ORDER BY (cell ->> 'economic_date') COLLATE "C", (cell ->> 'transaction_date') COLLATE "C"), '[]'::jsonb)
    INTO v_components FROM pg_catalog.jsonb_array_elements(v_grid) AS t(cell)
    WHERE (cell ->> 'amount')::numeric <> 0;
  SELECT COALESCE(pg_catalog.sum((cell ->> 'amount')::numeric), 0) INTO v_net
    FROM pg_catalog.jsonb_array_elements(v_components) AS t(cell);
  SELECT COALESCE(pg_catalog.jsonb_agg(pg_catalog.jsonb_build_object(
    'id', event ->> 'id', 'source_sha256', event ->> 'source_sha256'
  ) ORDER BY (event ->> 'id') COLLATE "C"), '[]'::jsonb)
    INTO v_support FROM pg_catalog.jsonb_array_elements(v_after) AS t(event);
  RETURN pg_catalog.jsonb_build_object(
    'contract_version', 'ow04.pure-recognition-plan.v1',
    'kernel_version', 'ow04-2d-difference-v1',
    'before_source_sha256', ow04_pure_kernel.vector_sha256_v1(v_before),
    'after_source_sha256', ow04_pure_kernel.vector_sha256_v1(v_after),
    'before_events', v_before, 'added_events', v_added, 'support', v_support,
    'components', v_components, 'net_current_k', pg_catalog.round(v_net, 2)::text,
    'has_recognition_effect', pg_catalog.jsonb_array_length(v_components) > 0
  );
END;
$function$;

CREATE OR REPLACE FUNCTION ow04_pure_kernel.credit_capacity_v1(
  p_components jsonb,
  p_consumptions jsonb,
  p_economic_date text,
  p_transaction_date text
)
RETURNS jsonb
LANGUAGE plpgsql IMMUTABLE SECURITY INVOKER
SET search_path = ''
AS $function$
DECLARE
  v_components jsonb;
  v_consumptions jsonb;
  v_economic text;
  v_transaction text;
  v_grid jsonb;
  v_requested numeric := 0;
  v_current numeric := 0;
  v_minimum numeric := 0;
  v_limiting jsonb;
  v_nonnegative boolean;
BEGIN
  v_components := ow04_pure_kernel.normalize_events_v1(p_components, false);
  v_consumptions := ow04_pure_kernel.normalize_events_v1(p_consumptions, false);
  -- A signed inverse must have a new ID, and source binding remains the caller's.
  PERFORM ow04_pure_kernel.normalize_events_v1(v_components || v_consumptions, false);
  v_economic := ow04_pure_kernel.canonical_date_v1(p_economic_date);
  v_transaction := ow04_pure_kernel.canonical_date_v1(p_transaction_date);
  IF (v_transaction COLLATE "C") < (v_economic COLLATE "C") THEN
    RAISE EXCEPTION USING ERRCODE = '22023', MESSAGE = 'BOOK_BEFORE_ECONOMIC';
  END IF;
  WITH movements AS (
    SELECT event ->> 'economic_date' AS e, event ->> 'transaction_date' AS b,
      (event ->> 'amount')::numeric AS balance_change
    FROM pg_catalog.jsonb_array_elements(v_components) AS t(event)
    UNION ALL
    SELECT event ->> 'economic_date', event ->> 'transaction_date',
      -(event ->> 'amount')::numeric
    FROM pg_catalog.jsonb_array_elements(v_consumptions) AS t(event)
  ), economic_axis AS (
    SELECT e FROM movements UNION SELECT v_economic
  ), transaction_axis AS (
    SELECT b FROM movements UNION SELECT v_transaction
  ), cells AS (
    SELECT e, b, pg_catalog.sum(balance_change) AS amount FROM movements GROUP BY e, b
  ), economic_scan AS (
    SELECT ea.e, ba.b, pg_catalog.sum(COALESCE(c.amount, 0)) OVER (
      PARTITION BY ba.b ORDER BY ea.e COLLATE "C" ROWS UNBOUNDED PRECEDING
    ) AS amount
    FROM economic_axis ea CROSS JOIN transaction_axis ba
    LEFT JOIN cells c ON c.e = ea.e AND c.b = ba.b
  ), prefixes AS (
    SELECT e, b, pg_catalog.sum(amount) OVER (
      PARTITION BY e ORDER BY b COLLATE "C" ROWS UNBOUNDED PRECEDING
    ) AS balance FROM economic_scan
  )
  SELECT pg_catalog.jsonb_agg(pg_catalog.jsonb_build_object(
    'economic_date', e, 'transaction_date', b, 'balance', pg_catalog.round(balance, 2)::text
  ) ORDER BY e COLLATE "C", b COLLATE "C") INTO v_grid FROM prefixes;
  SELECT (cell ->> 'balance')::numeric INTO v_requested
    FROM pg_catalog.jsonb_array_elements(v_grid) AS t(cell)
    WHERE cell ->> 'economic_date' = v_economic AND cell ->> 'transaction_date' = v_transaction;
  SELECT (cell ->> 'balance')::numeric INTO v_current
    FROM pg_catalog.jsonb_array_elements(v_grid) AS t(cell)
    ORDER BY (cell ->> 'economic_date') COLLATE "C" DESC,
      (cell ->> 'transaction_date') COLLATE "C" DESC LIMIT 1;
  SELECT pg_catalog.min((cell ->> 'balance')::numeric) INTO v_minimum
    FROM pg_catalog.jsonb_array_elements(v_grid) AS t(cell)
    WHERE (cell ->> 'economic_date') COLLATE "C" >= v_economic COLLATE "C"
      AND (cell ->> 'transaction_date') COLLATE "C" >= v_transaction COLLATE "C";
  SELECT pg_catalog.jsonb_agg(pg_catalog.jsonb_build_object(
    'economic_date', cell ->> 'economic_date', 'transaction_date', cell ->> 'transaction_date'
  ) ORDER BY (cell ->> 'economic_date') COLLATE "C", (cell ->> 'transaction_date') COLLATE "C")
    INTO v_limiting FROM pg_catalog.jsonb_array_elements(v_grid) AS t(cell)
    WHERE (cell ->> 'economic_date') COLLATE "C" >= v_economic COLLATE "C"
      AND (cell ->> 'transaction_date') COLLATE "C" >= v_transaction COLLATE "C"
      AND (cell ->> 'balance')::numeric = v_minimum;
  SELECT COALESCE(pg_catalog.bool_and((cell ->> 'balance')::numeric >= 0), true)
    INTO v_nonnegative FROM pg_catalog.jsonb_array_elements(v_grid) AS t(cell);
  RETURN pg_catalog.jsonb_build_object(
    'contract_version', 'ow04.pure-credit-capacity.v1',
    'kernel_version', 'ow04-2d-difference-v1',
    'components_sha256', ow04_pure_kernel.vector_sha256_v1(v_components),
    'consumptions_sha256', ow04_pure_kernel.vector_sha256_v1(v_consumptions),
    'economic_date', v_economic, 'transaction_date', v_transaction,
    'requested_pair_balance', pg_catalog.round(v_requested, 2)::text,
    'current_balance', pg_catalog.round(v_current, 2)::text,
    'minimum_available', pg_catalog.round(v_minimum, 2)::text,
    'source_prefixes_nonnegative', v_nonnegative,
    'limiting_pairs', v_limiting
  );
END;
$function$;
