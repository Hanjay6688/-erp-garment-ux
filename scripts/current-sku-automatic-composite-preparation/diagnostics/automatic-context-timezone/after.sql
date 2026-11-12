DO $$
DECLARE m text; zone text; origin text; q jsonb;
BEGIN
    FOREACH m IN ARRAY ARRAY['REWORK_SKU','REDYE_SKU'] LOOP
        origin := CASE WHEN m='REDYE_SKU' THEN 'REDYE' ELSE 'REWORK' END;
        FOREACH zone IN ARRAY ARRAY['UTC','Asia/Jakarta','America/Los_Angeles'] LOOP
            PERFORM set_config('TimeZone',zone,true);
            PERFORM pg_temp.open_fixture(m,CASE WHEN m='REWORK_SKU' THEN 1 ELSE 0 END,m='REDYE_SKU');
            PERFORM cp7_sku_conversion.automatic_enter_v5(pg_temp.id('rw'),'POST',pg_temp.id('child'));
            PERFORM pg_temp.must((SELECT rework_proof->>'completed_at' LIKE '%+00:00' AND target_proof->>'created_at' LIKE '%+00:00'
                                  FROM cp7_sku_conversion.automatic_context_v5),m||' UTC proof');
            PERFORM pg_temp.must(cp7_sku_conversion.automatic_valid_v5(),m||' valid outside forced UTC quote');
            q:=cp7_sku_conversion.pool_quote_v2(pg_temp.id('sku-source'),pg_temp.id('warehouse'),'GRADE_A');
            PERFORM pg_temp.must(q->>'state'='PROVISIONAL' AND (q->>'qty')::numeric=2 AND (q->>'value')::numeric=35
               AND (q->>'average')::numeric=17.5 AND q->'reserved_included'='true' AND q->'final_cost_ready'='false',m||' full provisional value');
            PERFORM pg_temp.must(current_setting('TimeZone')=zone,m||' timezone unchanged at caller');
            PERFORM pg_temp.must(NOT cp7_sku_conversion.automatic_scope_v5(pg_temp.id('sku-source'),pg_temp.id('other warehouse'),'GRADE_A'),m||' wrong warehouse refused');
            PERFORM pg_temp.must(NOT cp7_sku_conversion.automatic_scope_v5(pg_temp.id('sku-source'),pg_temp.id('warehouse'),'GRADE_B'),m||' wrong grade refused');
            PERFORM pg_temp.expect_error($q$SELECT cp7_sku_conversion.automatic_assert_native_v5(pg_temp.id('wrong child'),NULL,NULL,NULL)$q$,'CP7_SKU_AUTOMATIC_NATIVE_CHILD_NOT_EXACT');
            UPDATE erp.rework_orders SET updated_at=updated_at+interval '1 microsecond';
            PERFORM pg_temp.must(NOT cp7_sku_conversion.automatic_valid_v5(),m||' true timestamp mutation refused');
            DELETE FROM cp7_sku_conversion.automatic_context_v5;
            PERFORM pg_temp.expect_error($q$SELECT cp7_sku_conversion.pool_quote_v2(pg_temp.id('sku-source'),pg_temp.id('warehouse'),'GRADE_A')$q$,'CP7_SKU_POOL_HPP_UNKNOWN');
            PERFORM cp7_sku_conversion.automatic_enter_v5(pg_temp.id('rw'),'POST',pg_temp.id('child'));
            UPDATE pg_temp.native_quote_fixture SET unit_value=NULL;
            PERFORM pg_temp.expect_error($q$SELECT cp7_sku_conversion.pool_quote_v2(pg_temp.id('sku-source'),pg_temp.id('warehouse'),'GRADE_A')$q$,'CP7_SKU_AUTOMATIC_PRESENT_NUMERIC_PO_COMPONENTS_REQUIRED');
            UPDATE pg_temp.native_quote_fixture SET unit_value=17.5;
            INSERT INTO erp.fg_lots(id,product_id,lot_origin,initial_qty_pcs) VALUES(pg_temp.id('nonpo'),pg_temp.id('sku-source'),'OPENING',1);
            INSERT INTO pg_temp.native_quote_fixture VALUES(pg_temp.id('nonpo'),pg_temp.id('hpp'),pg_temp.id('sku-source'),pg_temp.id('warehouse'),NULL,1,10,0,false);
            PERFORM pg_temp.expect_error($q$SELECT cp7_sku_conversion.pool_quote_v2(pg_temp.id('sku-source'),pg_temp.id('warehouse'),'GRADE_A')$q$,'CP7_SKU_AUTOMATIC_PRESENT_NUMERIC_PO_COMPONENTS_REQUIRED');
            DELETE FROM pg_temp.native_quote_fixture WHERE lot_id=pg_temp.id('nonpo');
            DELETE FROM cp7_sku_conversion.automatic_context_v5;
            INSERT INTO erp.product_conversions(id,status,from_product_id,to_product_id,location_id,qty_pcs,physical_at)
                VALUES(pg_temp.id('child'),'POSTED',pg_temp.id('sku-source'),pg_temp.id('sku-target'),pg_temp.id('warehouse'),2,'2026-11-12T10:45:09.127+07');
            INSERT INTO erp.be_conversion_sources_v1(conversion_id,source_lot_id,rework_id,origin_kind)
                VALUES(pg_temp.id('child'),pg_temp.id('lot'),pg_temp.id('rw'),origin);
            PERFORM cp7_sku_conversion.automatic_enter_v5(pg_temp.id('rw'),'REVERSE',pg_temp.id('child'));
            PERFORM cp7_sku_conversion.automatic_assert_native_v5(pg_temp.id('child'),NULL,NULL,NULL);
            UPDATE erp.product_conversions SET status='REVERSED';
            PERFORM pg_temp.must(cp7_sku_conversion.automatic_valid_v5(),m||' reversed child remains exact');
            UPDATE erp.be_rework_targets_v1 SET reason='changed target';
            PERFORM pg_temp.must(NOT cp7_sku_conversion.automatic_valid_v5(),m||' true target mutation refused');
            RAISE NOTICE 'CP7_TZ_REPLAY_FIXED:%:%',m,zone;
        END LOOP;
    END LOOP;
END $$;

DO $$
BEGIN
    PERFORM pg_temp.must(
        (SELECT count(*)=2 FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
         WHERE n.nspname='cp7_sku_conversion' AND p.proname IN ('automatic_enter_v5','automatic_valid_v5')
         AND 'TimeZone=UTC'=ANY(p.proconfig) AND p.prosecdef
         AND p.provolatile=CASE p.proname WHEN 'automatic_valid_v5' THEN 's'::"char" ELSE 'v'::"char" END),
        'only expected function-local timezone metadata');
END $$;
