CREATE TEMP TABLE native_quote_fixture(
    lot_id uuid, version_id uuid, product_id uuid, location_id uuid, po_id uuid,
    units numeric, unit_value numeric, pending integer, laundry_unknown boolean
);
CREATE FUNCTION erp.get_hpp_completeness(uuid) RETURNS TABLE(pending_reason_count integer)
LANGUAGE sql STABLE AS $$ SELECT f.pending FROM pg_temp.native_quote_fixture f WHERE f.po_id=$1 LIMIT 1 $$;
CREATE FUNCTION erp.bd_lot_laundry_unknown_v1(uuid) RETURNS boolean
LANGUAGE sql STABLE AS $$ SELECT COALESCE((SELECT f.laundry_unknown FROM pg_temp.native_quote_fixture f WHERE f.lot_id=$1),false) $$;
CREATE FUNCTION cp7_sku_conversion.pool_components_v2(uuid,uuid,text)
RETURNS TABLE(line_no integer,root_lot_id uuid,po_id uuid,hpp_version_id uuid,component_units numeric,unit_value numeric,value numeric)
LANGUAGE sql STABLE AS $$
    SELECT 1,f.lot_id,f.po_id,f.version_id,f.units,f.unit_value,f.units*f.unit_value
    FROM pg_temp.native_quote_fixture f WHERE f.product_id=$1 AND f.location_id=$2 AND $3='GRADE_A'
$$;
CREATE FUNCTION cp7_sku_conversion.pool_cost_components_v3(uuid,uuid,text)
RETURNS TABLE(line_no integer,root_lot_id uuid,po_id uuid,hpp_version_id uuid,component_units numeric,unit_value numeric,value numeric,source_revision jsonb)
LANGUAGE sql STABLE AS $$ SELECT NULL::integer,NULL::uuid,NULL::uuid,NULL::uuid,NULL::numeric,NULL::numeric,NULL::numeric,NULL::jsonb WHERE false $$;
CREATE FUNCTION cp7_sku_conversion.pool_attribution_v2(uuid,uuid,text)
RETURNS TABLE(line_no integer,po_id uuid,value numeric,base_value numeric,adjustment numeric)
LANGUAGE sql STABLE AS $$
    SELECT 1,f.po_id,f.units*f.unit_value,f.units*f.unit_value,0::numeric
    FROM pg_temp.native_quote_fixture f WHERE f.product_id=$1 AND f.location_id=$2 AND $3='GRADE_A'
$$;
CREATE FUNCTION pg_temp.id(label text) RETURNS uuid LANGUAGE sql IMMUTABLE AS $$ SELECT md5(label)::uuid $$;
CREATE FUNCTION pg_temp.must(ok boolean, check_name text) RETURNS void LANGUAGE plpgsql AS $$
BEGIN
    IF ok IS DISTINCT FROM true THEN RAISE EXCEPTION 'REPLAY_ASSERTION_FAILED:%',check_name; END IF;
END $$;
CREATE FUNCTION pg_temp.expect_error(command text, first_line text) RETURNS void LANGUAGE plpgsql AS $$
BEGIN
    BEGIN
        EXECUTE command;
    EXCEPTION WHEN raise_exception THEN
        PERFORM pg_temp.must(split_part(SQLERRM,':',1)=first_line, 'error '||first_line||' got '||SQLERRM);
        RETURN;
    END;
    RAISE EXCEPTION 'REPLAY_EXPECTED_ERROR:%',first_line;
END $$;
CREATE FUNCTION pg_temp.open_fixture(p_mode text, p_pending integer, p_unknown_cost boolean)
RETURNS void LANGUAGE plpgsql AS $$
BEGIN
    TRUNCATE erp.rework_orders,erp.be_rework_targets_v1,erp.bs_cases,erp.fg_lots,erp.production_orders,
             erp.fg_stock_movements,erp.product_conversions,erp.be_conversion_sources_v1,
             erp.be_execution_context_v1,erp.hpp_versions,cp7_sku_conversion.automatic_context_v5,
             pg_temp.native_quote_fixture;
    INSERT INTO erp.production_orders(id) VALUES(pg_temp.id('po'));
    INSERT INTO erp.bs_cases(id,po_id,product_id) VALUES(pg_temp.id('bs'),pg_temp.id('po'),pg_temp.id('sku-source'));
    INSERT INTO erp.fg_lots(id,po_id,product_id,lot_origin,initial_qty_pcs)
    VALUES(pg_temp.id('lot'),pg_temp.id('po'),pg_temp.id('sku-source'),'PRODUCTION',2);
    INSERT INTO erp.rework_orders(id,bs_case_id,good_fg_lot_id,return_fg_location_id,
                                 qty_good_returned,cost_posted,status,completed_at,created_at,updated_at,physical_sent_at)
    VALUES(pg_temp.id('rw'),pg_temp.id('bs'),pg_temp.id('lot'),pg_temp.id('warehouse'),2,true,'COMPLETED',
           '2026-11-12T10:45:09.127+07','2026-11-11T14:00:02.4+07','2026-11-12T10:45:09.127+07','2026-11-11T14:00:03.414+07');
    INSERT INTO erp.be_rework_targets_v1(rework_id,target_product_id,mode,reason,created_at)
    VALUES(pg_temp.id('rw'),pg_temp.id('sku-target'),p_mode,'Uji zona waktu','2026-11-11T14:01:00+07');
    INSERT INTO erp.fg_stock_movements(id,lot_id,source_type,source_id,movement_type,product_id,location_id,quality_grade,qty_signed,physical_at)
    VALUES(pg_temp.id('movement'),pg_temp.id('lot'),'REWORK_ORDER',pg_temp.id('rw'),'REWORK_IN',
           pg_temp.id('sku-source'),pg_temp.id('warehouse'),'GRADE_A',2,'2026-11-12T10:45:09.127+07');
    INSERT INTO erp.hpp_versions(id,cost_state) VALUES(pg_temp.id('hpp'),'ESTIMATED');
    INSERT INTO pg_temp.native_quote_fixture VALUES(pg_temp.id('lot'),pg_temp.id('hpp'),pg_temp.id('sku-source'),
                                                   pg_temp.id('warehouse'),pg_temp.id('po'),2,17.5,p_pending,p_unknown_cost);
    INSERT INTO erp.be_execution_context_v1(backend_pid,transaction_id,request_id)
    VALUES(pg_backend_pid(),txid_current(),pg_temp.id('parent-request'));
END $$;
