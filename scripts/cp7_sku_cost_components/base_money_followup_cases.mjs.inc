 const baseCentFindings=[];
 for(const mode of['LATE_POSITIVE_SOLD_SOURCE','LATE_NEGATIVE_SOLD_CHILD','EARLY_POSITIVE_SOLD_CHILD','LATE_ZERO_SOLD_SOURCE','BASE_AND_COST_REPRICE_SOLD_SOURCE']){
  await control('CHAIN: BASE CENT: sale return credit '+mode,async()=>{
   const early=mode==='EARLY_POSITIVE_SOLD_CHILD',negative=mode==='LATE_NEGATIVE_SOLD_CHILD';
   const combined=mode==='BASE_AND_COST_REPRICE_SOLD_SOURCE',zero=mode==='LATE_ZERO_SOLD_SOURCE';
   const unit=zero?0:(negative?49.99:50.01),descendant=early||negative;
   if(combined)await costReconcile(2);
   if(early)await query("select erp.post_opening_hpp_correction($1,$2,'MODEL current base before transfer','2026-01-02')",[x.root50,unit]);
   const child=await nextConversion(x.converted);
   const product=descendant?child.product:x.target,lot=descendant?child.lot:x.root50;
   const originalSale=early?35.01:(combined?36:35);
   const expected=zero?10:(negative?34.99:(combined?37.02:35.01));
   await moneySell(product,lot);
   const frozenSale=await scalar('select to_jsonb(v)from cp7_sku_conversion.sale_allocation_values_v2 v where sale_stock_allocation_id=$1',[x.saleA]);
   assert.equal(Number(frozenSale.effective_value),originalSale);
   const frozenMoney=await scalar('select jsonb_agg(to_jsonb(e)order by e.id)from cp7_sku_conversion.base_money_events_v4 e');
   if(!early)await query("select erp.post_opening_hpp_correction($1,$2,'MODEL current base after sale','2026-01-05')",[x.root50,unit]);
   if(combined)await costReconcile(4.01);
   assert.deepEqual(await values(product),{hpp:expected,fg:0,cogs:expected,other:0});
   const before={hpp_total_cost:expected,fg_value:0,cogs_value:expected,other_out_value:0};
   const after={hpp_total_cost:expected,fg_value:expected,cogs_value:0,other_out_value:0};
   assert.deepEqual(await canonicalTarget(product,lot,false),before);
   assert.deepEqual(await canonicalTarget(product,lot,true),after);
   const definition=await scalar("select pg_get_functiondef('cp7_sku_conversion.base_current_unit_v4(uuid,uuid)'::regprocedure)");
   const token='return c.amount/c.units;';assert.equal(definition.split(token).length,2);
   const beforeCounter=await costSnapshot();await db.exec('savepoint independent_base_money');
   await db.exec(definition.replace(token,'return c.amount/c.units+1;'));
   assert.notDeepEqual(await values(product),{hpp:expected,fg:0,cogs:expected,other:0});
   assert.deepEqual(await canonicalTarget(product,lot,false),before);
   assert.deepEqual(await canonicalTarget(product,lot,true),after);
   await db.exec('rollback to savepoint independent_base_money');assert.deepEqual(await costSnapshot(),beforeCounter);
   assert.equal(await scalar("select pg_get_functiondef('cp7_sku_conversion.base_current_unit_v4(uuid,uuid)'::regprocedure)"),definition);
   const returned=id(99711),item=id(99712);
   await insert('erp.sales_returns',{id:returned,sale_id:x.sale,customer_id:id(900),status:'DRAFT',physical_at:'2026-01-06T00:00:00Z'});
   await insert('erp.sales_return_items',{id:item,return_id:returned,sale_stock_allocation_id:x.saleA,
    product_id:product,lot_id:lot,location_id:x.location,quality_grade:'GRADE_A',qty_pcs:1,refund_amount:185000});
   await query("update erp.fg_lots set cached_qty_pcs=0,produced_at='2026-01-01'where id=$1",[lot]);
   await query('select erp.post_sales_return($1)',[returned]);
   const frozenReturn=await scalar('select to_jsonb(v)from cp7_sku_conversion.sales_return_values_v2 v where sales_return_item_id=$1',[item]);
   assert.equal(Number(frozenReturn.effective_value),expected);
   assert.deepEqual(await values(product),{hpp:expected,fg:expected,cogs:0,other:0});
   assert.deepEqual(await scalar('select to_jsonb(v)from cp7_sku_conversion.sale_allocation_values_v2 v where sale_stock_allocation_id=$1',[x.saleA]),frozenSale);
   assert.deepEqual(await scalar('select jsonb_agg(to_jsonb(e)order by e.id)from cp7_sku_conversion.base_money_events_v4 e where id=any($1::uuid[])',[frozenMoney.map(e=>e.id)]),frozenMoney);
   for(const p of[x.source,x.target,child.product])await query('select erp.assert_non_po_product_hpp_target_book_v2620f($1)',[p]);
   baseCentFindings.push({mode,originalSale,currentReturn:expected,canonical_before:before,canonical_after:after,
    independent_raw_base_oracle_ignores_official_helper:true,old_sale_and_money_immutable:true,all_scope_books_exact:true,actual_ERP_cases:0});
  });
 }
 await control('CHAIN: BASE CENT: fresh origin and exact bounded price history',async()=>{
  assert.equal(Number(await scalar('select count(*)from cp7_sku_conversion.base_money_events_v4 where root_lot_id=$1',[x.root90])),0);
  await query('select cp7_sku_conversion.ensure_base_money_v4($1)',[x.root90]);
  const enrolled=await costSnapshot();await query('select cp7_sku_conversion.ensure_base_money_v4($1)',[x.root90]);
  assert.deepEqual(await costSnapshot(),enrolled);
  const prices=[30.01,29.99,30.03,0,30.01];
  const expected=[[60.02,70],[59.99,69.99],[60.05,70.01],[15,55],[60.02,70]];
  for(let i=0;i<prices.length;i++){
   await query("select erp.post_opening_hpp_correction($1,$2,'MODEL bounded base price history','2026-01-06')",[x.root30,prices[i]]);
   for(const[p,value]of[[x.source,expected[i][0]],[x.target,expected[i][1]]]){
    assert.deepEqual(await values(p),{hpp:value,fg:value,cogs:0,other:0});
    await query('select erp.assert_non_po_product_hpp_target_book_v2620f($1)',[p]);
   }
  }
  const proofs=(await query("select source_proof from cp7_sku_conversion.base_money_events_v4 where kind='SOURCE_PRICE'")).rows;
  const depth=v=>v&&typeof v==='object'?1+Math.max(0,...Object.values(v).map(depth)):0;
  assert(proofs.length>=8);assert(proofs.every(r=>depth(r.source_proof)<=3));
  baseCentFindings.push({mode:'FRESH_ORIGIN_AND_PRICE_HISTORY',prices,expected,origin_replay_unchanged:true,max_receipt_depth:Math.max(...proofs.map(r=>depth(r.source_proof))),actual_ERP_cases:0});
 });
 await control('CHAIN: BASE CENT: unchanged physical opening refusal and exact corruption refusal',async()=>{
  const unchanged=await costSnapshot();await db.exec('savepoint original_physical_opening_guard');
  await assert.rejects(()=>query("select erp.post_opening_hpp_correction($1,10.01,'MODEL must refuse physically used opening','2026-01-06')",[x.root10]),e=>e.message.includes('sudah pernah dipakai conversion/rebrand'));
  await db.exec('rollback to savepoint original_physical_opening_guard');assert.deepEqual(await costSnapshot(),unchanged);
  await db.exec('savepoint corruption_guard');
  await query('update erp.hpp_versions set total_cost=total_cost+.01 where lot_id=$1 and is_current',[x.root30]);
  await assert.rejects(()=>values(x.source),e=>e.message.includes('CP7_SKU_BASE_MONEY_SOURCE_NOT_EXACT'));
  await db.exec('rollback to savepoint corruption_guard');assert.deepEqual(await costSnapshot(),unchanged);
  baseCentFindings.push({mode:'PHYSICAL_OPENING_AND_RAW_PRICE_CORRUPTION_REFUSED',complete_rollback:true,actual_ERP_cases:0});
 });
 await control('CHAIN: BASE CENT: private original history cannot be rewritten or initialized from converted custody',async()=>{
  const before=await costSnapshot();
  for(const sql of['update cp7_sku_conversion.base_money_events_v4 set amount_delta=amount_delta+.01','delete from cp7_sku_conversion.base_money_events_v4']){
   await db.exec('savepoint immutable_base_money');
   await assert.rejects(()=>query(sql),e=>e.message.includes('immutable')||e.message.includes('IMMUTABLE'));
   await db.exec('rollback to savepoint immutable_base_money');assert.deepEqual(await costSnapshot(),before);
  }
  await db.exec('savepoint unadmitted_base_origin');
  await assert.rejects(()=>query('select cp7_sku_conversion.ensure_base_money_v4($1)',[x.converted]),e=>e.message.includes('CP7_SKU_BASE_MONEY_UNADMITTED_PRIOR_CUSTODY'));
  await db.exec('rollback to savepoint unadmitted_base_origin');assert.deepEqual(await costSnapshot(),before);
  const acl=(await query("select r.rolname,has_table_privilege(r.rolname,'cp7_sku_conversion.base_money_events_v4','SELECT,INSERT,UPDATE,DELETE') access from pg_roles r where r.rolname in('anon','authenticated','service_role')")).rows;
  assert.equal(acl.length,3);assert(acl.every(r=>r.access===false));
  baseCentFindings.push({mode:'IMMUTABLE_PRIVATE_BASE_MONEY_AND_CONVERTED_ORIGIN_REFUSAL',model_role_acl:acl,complete_rollback:true,actual_ERP_cases:0});
 });
 assert.equal(baseCentFindings.length,8);assert.deepEqual(await costSnapshot(),costBaseline);
