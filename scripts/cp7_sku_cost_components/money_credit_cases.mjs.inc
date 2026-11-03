 const moneyCreditFindings=[];
 async function moneySell(product,lot){
  await saleSetup(product,[lot],[1]);
  await query("update erp.sales_headers set sale_date='2026-01-04T00:00:00Z',source_location_id=$1,customer_id=$2 where id=$3",[x.location,id(900),x.sale]);
  await query('update erp.sales_items set qty_pcs=1,unit_price_snapshot=185000,discount_amount=0 where id=$1',[x.saleItem]);
  await insert('erp.fg_stock_movements',{id:id(++serial),lot_id:lot,product_id:product,location_id:x.location,
   quality_grade:'GRADE_A',qty_signed:-1,movement_type:'SALE_RESERVE',customer_id:id(900),source_type:'SALE_ITEM',source_id:x.saleItem,
   physical_at:'2026-01-04T00:00:00Z',system_created_at:'2026-01-04T00:00:00Z'});
  await query('select erp.post_sale($1)',[x.sale]);
 }
 const canonicalTarget=async(product,lot,after)=>{
  const v=await scalar('select cp7_credit.initial_hpp_targets_v1($1,null,$2,$3)',[product,[{allocation_id:x.saleA,lot_id:lot,qty_pcs:1}],after]);
  return Object.fromEntries(['hpp_total_cost','fg_value','cogs_value','other_out_value'].map(k=>[k,Number(v.target[k])]));
 };
 for(const mode of['LATE_POSITIVE_TO_DESCENDANT','EARLY_POSITIVE_SOURCE_REMAINDER','LATE_NEGATIVE_SOURCE_REMAINDER']){
  await control('CHAIN: MONEY CREDIT: '+mode,async()=>{
   const early=mode==='EARLY_POSITIVE_SOURCE_REMAINDER',negative=mode==='LATE_NEGATIVE_SOURCE_REMAINDER';
   const price=negative?-4.01:4.01;
   if(negative)await query("update erp.be_conversion_cost_sources_v1 set kind='RECOVERY'where document_id=$1",[costDocument]);
   await costReconcile(early?price:(negative?-2:2));const child=await nextConversion(x.root50);
   const product=mode==='LATE_POSITIVE_TO_DESCENDANT'?child.product:x.target;
   const lot=product===child.product?child.lot:x.converted;
   const expected=negative?32.99:37,originalSale=early?37:(negative?34:36);
   await moneySell(product,lot);
   const frozenSale=await scalar('select to_jsonb(v)from cp7_sku_conversion.sale_allocation_values_v2 v where sale_stock_allocation_id=$1',[x.saleA]);
   assert.equal(Number(frozenSale.effective_value),originalSale);
   if(!early)await costReconcile(price);
   assert.deepEqual(await values(product),{hpp:expected,fg:0,cogs:expected,other:0});
   await query('select erp.assert_non_po_product_hpp_target_book_v2620f($1)',[product]);
   const expectedBefore={hpp_total_cost:expected,fg_value:0,cogs_value:expected,other_out_value:0};
   const expectedAfter={hpp_total_cost:expected,fg_value:expected,cogs_value:0,other_out_value:0};
   assert.deepEqual(await canonicalTarget(product,lot,false),expectedBefore);
   assert.deepEqual(await canonicalTarget(product,lot,true),expectedAfter);
   // Deliberately corrupt only the official current-price helper in this
   // isolated model. Independent credit arithmetic must keep its exact target.
   const definition=await scalar("select pg_get_functiondef('cp7_sku_conversion.cost_current_unit_v3(uuid,uuid)'::regprocedure)");
   const token='return owned.amount/owned.units;';assert.equal(definition.split(token).length,2);
   const beforeCounter=await costSnapshot();await db.exec('savepoint independent_money_reader');
   await db.exec(definition.replace(token,'return owned.amount/owned.units+1;'));
   assert.notEqual((await values(product)).hpp,expected);
   assert.deepEqual(await canonicalTarget(product,lot,false),expectedBefore);
   assert.deepEqual(await canonicalTarget(product,lot,true),expectedAfter);
   await db.exec('rollback to savepoint independent_money_reader');assert.deepEqual(await costSnapshot(),beforeCounter);
   assert.equal(await scalar("select pg_get_functiondef('cp7_sku_conversion.cost_current_unit_v3(uuid,uuid)'::regprocedure)"),definition);
   const returned=id(99701),item=id(99702);
   await insert('erp.sales_returns',{id:returned,sale_id:x.sale,customer_id:id(900),status:'DRAFT',physical_at:'2026-01-05T00:00:00Z'});
   await insert('erp.sales_return_items',{id:item,return_id:returned,sale_stock_allocation_id:x.saleA,
    product_id:product,lot_id:lot,location_id:x.location,quality_grade:'GRADE_A',qty_pcs:1,refund_amount:185000});
   await query("update erp.fg_lots set cached_qty_pcs=0,produced_at='2026-01-01'where id=$1",[lot]);
   await query('select erp.post_sales_return($1)',[returned]);
   const frozenReturn=await scalar('select to_jsonb(v)from cp7_sku_conversion.sales_return_values_v2 v where sales_return_item_id=$1',[item]);
   assert.equal(Number(frozenReturn.effective_value),expected);
   assert.deepEqual(await values(product),{hpp:expected,fg:expected,cogs:0,other:0});
   await query('select erp.assert_non_po_product_hpp_target_book_v2620f($1)',[product]);
   assert.deepEqual(await scalar('select to_jsonb(v)from cp7_sku_conversion.sale_allocation_values_v2 v where sale_stock_allocation_id=$1',[x.saleA]),frozenSale);
   await costReconcile(0);
   for(const product of[x.target,child.product]){
    assert.deepEqual(await values(product),{hpp:35,fg:35,cogs:0,other:0});
    await query('select erp.assert_non_po_product_hpp_target_book_v2620f($1)',[product]);
   }
   assert.deepEqual(await scalar('select to_jsonb(v)from cp7_sku_conversion.sales_return_values_v2 v where sales_return_item_id=$1',[item]),frozenReturn);
   moneyCreditFindings.push({mode,product,lot,price,originalSale,currentReturn:expected,
    exact_prepared_sale_and_return_SQL:true,canonical_before:expectedBefore,canonical_after:expectedAfter,
    official_price_helper_counter_did_not_change_independent_targets:true,
    every_model_table_and_helper_restored_after_counter:true,old_sale_and_return_history_immutable:true,actual_ERP_cases:0});
  });
 }
 assert.equal(moneyCreditFindings.length,3);assert.deepEqual(await costSnapshot(),costBaseline);
