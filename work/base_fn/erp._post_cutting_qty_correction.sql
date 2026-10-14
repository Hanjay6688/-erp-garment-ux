-- bootstrap lines 5426-5575
CREATE OR REPLACE FUNCTION erp._post_cutting_qty_correction(p_cutting_batch_id uuid, p_correction_type text, p_reason_code text, p_reason text, p_lines jsonb, p_physical_at timestamp with time zone, p_reversal_of_id uuid DEFAULT NULL::uuid)
 RETURNS uuid
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
DECLARE
  v_id uuid;
  v_po_id uuid;
  v_number text;
  v_total_delta bigint;
  v_line_count integer;
  v_current bigint;
  v_committed bigint;
  v_new bigint;
  v_group_batch uuid;
  r record;
BEGIN
  PERFORM erp.require_internal();

  SELECT po_id INTO v_po_id
  FROM erp.cutting_batches
  WHERE id=p_cutting_batch_id
  FOR UPDATE;
  IF v_po_id IS NULL THEN
    RAISE EXCEPTION 'Cutting batch not found';
  END IF;

  IF p_correction_type NOT IN ('RECOUNT','REDISTRIBUTION','REVERSAL','OTHER') THEN
    RAISE EXCEPTION 'Invalid cutting correction type';
  END IF;
  IF COALESCE(btrim(p_reason_code),'')='' OR COALESCE(btrim(p_reason),'')='' THEN
    RAISE EXCEPTION 'Correction reason code and reason are required';
  END IF;
  IF jsonb_typeof(p_lines) <> 'array' OR jsonb_array_length(p_lines)=0 THEN
    RAISE EXCEPTION 'Correction requires at least one line';
  END IF;

  IF p_reversal_of_id IS NULL AND p_correction_type='REVERSAL' THEN
    RAISE EXCEPTION 'REVERSAL requires a source correction';
  END IF;
  IF p_reversal_of_id IS NOT NULL THEN
    IF p_correction_type <> 'REVERSAL' THEN
      RAISE EXCEPTION 'reversal_of_id is only valid for REVERSAL';
    END IF;
    IF NOT EXISTS (
      SELECT 1 FROM erp.cutting_qty_corrections c
      WHERE c.id=p_reversal_of_id AND c.cutting_batch_id=p_cutting_batch_id
    ) THEN
      RAISE EXCEPTION 'Source correction not found in this cutting batch';
    END IF;
    IF EXISTS (SELECT 1 FROM erp.cutting_qty_corrections c WHERE c.reversal_of_id=p_reversal_of_id) THEN
      RAISE EXCEPTION 'Correction has already been reversed';
    END IF;
  END IF;

  WITH parsed AS (
    SELECT
      NULLIF(x->>'cutting_group_id','')::uuid AS group_id,
      NULLIF(x->>'size_slot_id','')::uuid AS size_slot_id,
      (x->>'qty_delta_pcs')::integer AS delta
    FROM jsonb_array_elements(p_lines) x
  )
  SELECT COALESCE(SUM(delta),0)::bigint, COUNT(*)::integer
  INTO v_total_delta,v_line_count
  FROM parsed
  WHERE group_id IS NOT NULL AND delta <> 0;

  IF v_line_count=0 THEN
    RAISE EXCEPTION 'Correction contains no valid non-zero lines';
  END IF;
  IF p_correction_type='REDISTRIBUTION' AND v_total_delta<>0 THEN
    RAISE EXCEPTION 'REDISTRIBUTION must net to zero across groups';
  END IF;

  FOR r IN
    WITH parsed AS (
      SELECT NULLIF(x->>'cutting_group_id','')::uuid AS group_id,
             (x->>'qty_delta_pcs')::integer AS delta
      FROM jsonb_array_elements(p_lines) x
    )
    SELECT group_id,SUM(delta)::bigint AS delta
    FROM parsed
    WHERE group_id IS NOT NULL AND delta<>0
    GROUP BY group_id
  LOOP
    SELECT cutting_batch_id INTO v_group_batch
    FROM erp.cutting_groups
    WHERE id=r.group_id
    FOR UPDATE;
    IF v_group_batch IS NULL OR v_group_batch<>p_cutting_batch_id THEN
      RAISE EXCEPTION 'Cutting group % does not belong to correction batch',r.group_id;
    END IF;

    SELECT total_pcs INTO v_current
    FROM erp.v_cutting_group_totals
    WHERE cutting_group_id=r.group_id;
    v_current:=COALESCE(v_current,0);
    v_new:=v_current+r.delta;
    v_committed:=erp.cutting_group_downstream_committed_qty(r.group_id);

    IF v_new<0 THEN
      RAISE EXCEPTION 'Correction would make cutting group % negative: % pcs',r.group_id,v_new;
    END IF;
    IF v_new<v_committed THEN
      RAISE EXCEPTION 'Correction would reduce group % to % pcs, but % pcs are already committed downstream',r.group_id,v_new,v_committed;
    END IF;
  END LOOP;

  v_number:='CQC-'||to_char(COALESCE(p_physical_at,now()) AT TIME ZONE 'Asia/Jakarta','YYYYMMDD')||'-'||lpad(nextval('erp.cutting_qty_correction_seq')::text,6,'0');

  INSERT INTO erp.cutting_qty_corrections(
    correction_number,cutting_batch_id,correction_type,reason_code,reason,physical_at,reversal_of_id,posted_by
  ) VALUES (
    v_number,p_cutting_batch_id,p_correction_type,p_reason_code,p_reason,COALESCE(p_physical_at,now()),p_reversal_of_id,erp.current_app_user_id()
  ) RETURNING id INTO v_id;

  INSERT INTO erp.cutting_qty_correction_lines(correction_id,cutting_group_id,size_slot_id,qty_delta_pcs,notes)
  WITH parsed AS (
    SELECT NULLIF(x->>'cutting_group_id','')::uuid AS group_id,
           NULLIF(x->>'size_slot_id','')::uuid AS size_slot_id,
           (x->>'qty_delta_pcs')::integer AS delta,
           NULLIF(x->>'notes','') AS notes
    FROM jsonb_array_elements(p_lines) x
  )
  SELECT v_id,group_id,size_slot_id,SUM(delta)::integer,MAX(notes)
  FROM parsed
  WHERE group_id IS NOT NULL AND delta<>0
  GROUP BY group_id,size_slot_id
  HAVING SUM(delta)<>0;

  INSERT INTO erp.audit_logs(entity_type,entity_id,action,new_data,changed_by,change_reason)
  VALUES (
    'cutting_qty_corrections',v_id,'POST',
    jsonb_build_object('correction_number',v_number,'type',p_correction_type,'batch_id',p_cutting_batch_id,'net_delta_pcs',v_total_delta,'lines',p_lines),
    erp.current_app_user_id(),p_reason
  );

  IF EXISTS (SELECT 1 FROM erp.fg_lots WHERE po_id=v_po_id AND lot_origin='PRODUCTION') THEN
    PERFORM erp.rebuild_po_hpp(v_po_id,'Cutting quantity correction '||v_number);
    PERFORM erp.propagate_conversion_hpp_for_po(v_po_id);
    PERFORM erp.sync_po_hpp_to_gl(v_po_id,COALESCE(p_physical_at,now())::date);
  END IF;

  RETURN v_id;
END;
$function$;

alter function "erp"."_post_cutting_qty_correction"(p_cutting_batch_id uuid, p_correction_type text, p_reason_code text, p_reason text, p_lines jsonb, p_physical_at timestamp with time zone, p_reversal_of_id uuid) owner to "postgres";
