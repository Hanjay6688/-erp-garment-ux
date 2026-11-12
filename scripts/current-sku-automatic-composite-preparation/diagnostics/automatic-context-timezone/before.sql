DO $$
DECLARE m text;
BEGIN
    FOREACH m IN ARRAY ARRAY['REWORK_SKU','REDYE_SKU'] LOOP
        PERFORM set_config('TimeZone','Asia/Jakarta',true);
        PERFORM pg_temp.open_fixture(m,CASE WHEN m='REWORK_SKU' THEN 1 ELSE 0 END,m='REDYE_SKU');
        PERFORM cp7_sku_conversion.automatic_enter_v5(pg_temp.id('rw'),'POST',pg_temp.id('child'));
        PERFORM pg_temp.must(cp7_sku_conversion.automatic_valid_v5(),m||' valid in captured WIB');
        PERFORM pg_temp.must((SELECT rework_proof->>'completed_at' LIKE '%+07:00' FROM cp7_sku_conversion.automatic_context_v5),m||' proof stored with session offset');
        PERFORM pg_temp.expect_error($q$SELECT cp7_sku_conversion.pool_quote_v2(pg_temp.id('sku-source'),pg_temp.id('warehouse'),'GRADE_A')$q$,'CP7_SKU_POOL_HPP_UNKNOWN');
        PERFORM set_config('TimeZone','UTC',true);
        PERFORM pg_temp.must(NOT cp7_sku_conversion.automatic_valid_v5(),m||' old UTC validity false');
        PERFORM pg_temp.must((SELECT (f.rework_proof->>'completed_at')::timestamptz=r.completed_at
          FROM cp7_sku_conversion.automatic_context_v5 f JOIN erp.rework_orders r ON r.id=f.rework_id),m||' same typed instant');
        RAISE NOTICE 'CP7_TZ_REPLAY_OLD_REFUSAL:%',m;
    END LOOP;
END $$;
