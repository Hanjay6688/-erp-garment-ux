 const baseCentFindings=[];
 for(const mode of['ROOT_PRICE_UP_TWO_SKUS','ROOT_PRICE_DOWN_TWO_SKUS','ROOT_PRICE_UP_AFTER_DESCENDANT']){
  await control('CHAIN: BASE CENT: repaired '+mode,async()=>{
   const descendant=mode==='ROOT_PRICE_UP_AFTER_DESCENDANT';
   const child=descendant?await nextConversion(x.converted):null;
   const root=descendant?x.root50:x.root30,unit=descendant?50.01:(mode==='ROOT_PRICE_UP_TWO_SKUS'?30.01:29.99);
   const products=[x.source,x.target,...(child?[child.product]:[])];
   const expected=descendant?[60,35.01,35]:(unit>30?[60.02,70]:[59.99,69.99]);
   const beforeMoney=await scalar('select jsonb_agg(to_jsonb(e)order by e.id)from cp7_sku_conversion.base_money_events_v4 e');
   const beforeTargets=await Promise.all(products.map(values));
   await query("select erp.post_opening_hpp_correction($1,$2,'MODEL exact base source cents','2026-01-06')",[root,unit]);
   const afterTargets=await Promise.all(products.map(values));
   for(let i=0;i<products.length;i++){
    assert.deepEqual(afterTargets[i],{hpp:expected[i],fg:expected[i],cogs:0,other:0});
    await query('select erp.assert_non_po_product_hpp_target_book_v2620f($1)',[products[i]]);
   }
   assert.deepEqual(await scalar('select jsonb_agg(to_jsonb(e)order by e.id)from cp7_sku_conversion.base_money_events_v4 e where id=any($1::uuid[])',[beforeMoney.map(e=>e.id)]),beforeMoney);
   const beforeRepeat=await costSnapshot();await db.exec('savepoint repeated_base_price');
   await assert.rejects(()=>query("select erp.post_opening_hpp_correction($1,$2,'MODEL unchanged base price','2026-01-06')",[root,unit]),e=>e.message.includes('HPP baru sama'));
   await db.exec('rollback to savepoint repeated_base_price');assert.deepEqual(await costSnapshot(),beforeRepeat);
   if(child){
    await query('select cp7_sku_conversion.assert_group_inverse_capacity_v3($1)',[child.group]);
    await modelNativeInverse(child,x.converted);await query('select cp7_sku_conversion.reverse_valuation_v2($1)',[child.group]);
    assert.deepEqual(await values(x.target),{hpp:70.01,fg:70.01,cogs:0,other:0});
    assert.deepEqual(await values(child.product),{hpp:0,fg:0,cogs:0,other:0});
   }
   baseCentFindings.push({mode,root,unit,beforeTargets,afterTargets,expected,exact_prepared_source_command:true,
    immutable_original_base_money:true,same_price_refusal_unchanged:true,descendant_current_inverse:!!child,actual_ERP_cases:0});
  });
 }
 for(const physicalSource of[x.root50,x.converted]){
  await control('CHAIN: BASE CENT: base price before transfer then current inverse physical '+physicalSource,async()=>{
   await query("select erp.post_opening_hpp_correction($1,50.01,'MODEL price before next conversion','2026-01-02')",[x.root50]);
   const child=await nextConversion(physicalSource);
   assert.deepEqual(await values(x.target),{hpp:35,fg:35,cogs:0,other:0});
   assert.deepEqual(await values(child.product),{hpp:35.01,fg:35.01,cogs:0,other:0});
   const original=await scalar('select jsonb_agg(to_jsonb(e)order by e.id)from cp7_sku_conversion.base_money_events_v4 e');
   await query('select cp7_sku_conversion.assert_group_inverse_capacity_v3($1)',[child.group]);
   await modelNativeInverse(child,physicalSource);await query('select cp7_sku_conversion.reverse_valuation_v2($1)',[child.group]);
   assert.deepEqual(await values(x.target),{hpp:70.01,fg:70.01,cogs:0,other:0});
   assert.deepEqual(await values(child.product),{hpp:0,fg:0,cogs:0,other:0});
   assert.deepEqual(await scalar('select jsonb_agg(to_jsonb(e)order by e.id)from cp7_sku_conversion.base_money_events_v4 e where id=any($1::uuid[])',[original.map(e=>e.id)]),original);
   baseCentFindings.push({mode:'SOURCE_PRICE_BEFORE_TRANSFER_AND_CURRENT_INVERSE',physicalSource,original_target_values:[35,35.01],inverse_values:[70.01,0],old_history_immutable:true,actual_ERP_cases:0});
  });
 }
 assert.equal(baseCentFindings.length,5);assert.deepEqual(await costSnapshot(),costBaseline);
