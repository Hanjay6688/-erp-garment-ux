 for(const lot of[x.root50,x.converted])for(const early of[2,2.01,-2.01]){
  await control('CHAIN: BASE CENT: LEGACY COST BEFORE exact Native selected lot '+lot+' cost '+early,async()=>{
   await legacyTargetSetup();
   if(early<0)await query("update erp.be_conversion_cost_sources_v1 set kind='RECOVERY'where document_id=$1",[costDocument]);
   await costReconcile(early);
   const expectedForward=early===2?[36,36]:early===2.01?[36,36.01]:[33.99,34];
   const later=early<0?-3.01:3.01;
   const expectedLater=early<0?[33.49,33.5]:[36.51,36.5];
   // Independent integer-cent oracle, fixed before the Native command.
   assert(x.target<legacyTarget);
   const payload=await legacyPayload(lot);
   const preview=await scalar('select erp.be_conversion_preview_v1($1)',[payload]);
   assert.equal(Number(preview.cost.source_value),expectedForward[1]);
   const result=await legacyAction('POST',payload,legacyRequest);
   assert.equal(Number(result.cost.source_value),expectedForward[1]);
   await legacyBooks(...expectedForward);await legacyContextsClear();
   const original=await scalar('select jsonb_build_object(\'conversion\',(select to_jsonb(c)from erp.product_conversions c where id=$1),\'allocation\',(select jsonb_agg(to_jsonb(a)order by id)from erp.product_conversion_allocations a where conversion_id=$1))',[legacyRequest]);
   await costReconcile(later);await legacyBooks(...expectedLater);
   assert.deepEqual(await scalar('select jsonb_build_object(\'conversion\',(select to_jsonb(c)from erp.product_conversions c where id=$1),\'allocation\',(select jsonb_agg(to_jsonb(a)order by id)from erp.product_conversion_allocations a where conversion_id=$1))',[legacyRequest]),original);
   await legacyAction('REVERSE',{conversion_id:legacyRequest,reason:'Current inverse after early and late costs'},id(97704));
   await legacyBooks(early<0?66.99:73.01,0);await legacyContextsClear();
   await costReconcile(0);await legacyBooks(70,0);
   baseCentFindings.push({physicalSource:lot,earlyCost:early,expectedForward,laterCost:later,expectedLater,
    currentInverse:early<0?66.99:73.01,zeroCostAfterInverse:70,postedFactsUnchanged:true,actual_ERP_cases:0});
  });
 }
 await control('CHAIN: BASE CENT: LEGACY COST BEFORE exact two-child SKU action',async()=>{
  await legacyTargetSetup();await costReconcile(2);
  let payload={source_product_id:x.target,target_product_id:legacyTarget,location_id:x.location,
   qty_pcs:2,physical_at:'2026-01-03T00:00:00Z',reason:'Existing cost before two exact Native children'};
  const preview=await scalar('select cp7_sku_conversion.preview_v1($1)',[payload]);
  assert.equal(preview.allocations.length,2);assert.equal(Number(preview.cost.source_value),72);
  payload={...payload,expected_version:preview.source_revision};
  const made=await legacyAction('POST',payload,legacyRequest);assert.equal(made.conversion_ids.length,2);
  await legacyBooks(0,72);await costReconcile(3.01);await legacyBooks(0,73.01);
  await legacyAction('REVERSE',{conversion_id:legacyRequest,reason:'Current two-child inverse after early cost'},id(97704));
  await legacyBooks(73.01,0);await legacyContextsClear();
  assert.equal(Number(await scalar('select count(*)from cp7_sku_conversion.legacy_groups_v4')),0);
  baseCentFindings.push({twoExactNativeChildren:true,earlyCost:2,laterCost:3.01,currentInverse:73.01,actual_ERP_cases:0});
 });
 assert.equal(baseCentFindings.length,7);assert.deepEqual(await costSnapshot(),costBaseline);
