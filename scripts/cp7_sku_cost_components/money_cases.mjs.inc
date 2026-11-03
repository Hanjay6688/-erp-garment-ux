 const moneyFindings=[];
 for(const physicalSource of[x.root50,x.converted])for(const order of['SOURCE_BEFORE_TRANSFER','SOURCE_AFTER_TRANSFER','NEGATIVE_AFTER_TRANSFER']){
  await control('CHAIN: exact fractional source cents '+order+' physical '+physicalSource,async()=>{
   const negative=order==='NEGATIVE_AFTER_TRANSFER',before=order==='SOURCE_BEFORE_TRANSFER',price=negative?-4.01:4.01;
   if(negative)await query("update erp.be_conversion_cost_sources_v1 set kind='RECOVERY'where document_id=$1",[costDocument]);
   await costReconcile(before?price:(negative?-2:2));const child=await nextConversion(physicalSource);
   if(!before)await costReconcile(price);
   const expected=before?[37,37.01]:(negative?[32.99,33]:[37.01,37]);
   assert.deepEqual(await values(x.target),{hpp:expected[0],fg:expected[0],cogs:0,other:0});
   assert.deepEqual(await values(child.product),{hpp:expected[1],fg:expected[1],cogs:0,other:0});
   await costBook();await query('select erp.assert_non_po_product_hpp_target_book_v2620f($1)',[child.product]);
   const cells=(await query('select product_id,units::text,amount::text from cp7_sku_conversion.cost_money_cells_v3($1)order by product_id',[x.converted])).rows;
   assert.equal(cells.reduce((n,c)=>n+Math.round(Number(c.amount)*100),0),Math.round(price*100));
   const completeBeforeReplay=await costSnapshot();await costReconcile(price);assert.deepEqual(await costSnapshot(),completeBeforeReplay);
   const immutableMoney=await scalar('select jsonb_agg(to_jsonb(e)order by e.id)from cp7_sku_conversion.cost_money_events_v3 e');
   await costReconcile(0);await costBook();await query('select erp.assert_non_po_product_hpp_target_book_v2620f($1)',[child.product]);
   assert.deepEqual(await values(x.target),{hpp:35,fg:35,cogs:0,other:0});assert.deepEqual(await values(child.product),{hpp:35,fg:35,cogs:0,other:0});
   assert.equal(Number(await scalar('select count(*)from cp7_sku_conversion.cost_money_cells_v3($1)where amount<>0',[x.converted])),0);
   assert.deepEqual(await scalar('select jsonb_agg(to_jsonb(e)order by e.id)from cp7_sku_conversion.cost_money_events_v3 e where id=any($1::uuid[])',[immutableMoney.map(e=>e.id)]),immutableMoney);
   await query('select cp7_sku_conversion.assert_group_inverse_capacity_v3($1)',[child.group]);
   await modelNativeInverse(child,physicalSource);await query('select cp7_sku_conversion.reverse_valuation_v2($1)',[child.group]);
   assert.deepEqual(await values(x.target),{hpp:70,fg:70,cogs:0,other:0});assert.deepEqual(await values(child.product),{hpp:0,fg:0,cogs:0,other:0});
   await costBook();await query('select erp.assert_non_po_product_hpp_target_book_v2620f($1)',[child.product]);
   moneyFindings.push({physicalSource,order,sourcePrice:price,expected,actualCells:cells,unchanged_price_replay_no_effect:true,
    zero_source_clears_every_cell:true,old_money_history_immutable:true,current_inverse_after_zero_exact:true,actual_ERP_cases:0});
  });
 }
 assert.equal(moneyFindings.length,6);assert.deepEqual(await costSnapshot(),costBaseline);
