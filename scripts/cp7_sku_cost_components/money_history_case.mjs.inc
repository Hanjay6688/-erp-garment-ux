 await control('CHAIN: MONEY CREDIT: repeated price receipts keep bounded nesting and exact source cents',async()=>{
  await costReconcile(2);const child=await nextConversion(x.root50);
  const observations=[];
  function depth(value){return value&&typeof value==='object'?1+Math.max(0,...Object.values(value).map(depth)):0;}
  for(const price of[4.01,3.99,4.03,2.01,5.01,1.99,0]){
   const prior=await scalar('select coalesce(jsonb_agg(to_jsonb(e)order by e.id),\'[]\')from cp7_sku_conversion.cost_money_events_v3 e');
   await costReconcile(price);await costBook();await query('select erp.assert_non_po_product_hpp_target_book_v2620f($1)',[child.product]);
   const rows=(await query("select id,amount_delta::text,source_proof,octet_length(source_proof::text)bytes from cp7_sku_conversion.cost_money_events_v3 where kind='SOURCE_PRICE'and not(id=any($1::uuid[]))order by product_id",[prior.map(e=>e.id)])).rows;
   assert(rows.length>0);assert(rows.every(e=>!Object.hasOwn(e.source_proof,'old_root')));
   assert(rows.every(e=>depth(e.source_proof)<=3));
   assert(rows.every(e=>Number.isInteger(Number(e.source_proof.before_money_event_count))&&/^[a-f0-9]{32}$/.test(e.source_proof.before_money_revision)));
   assert.equal(Math.round(Number(await scalar('select coalesce(sum(amount_delta),0)from cp7_sku_conversion.cost_money_events_v3 where root_lot_id=$1',[x.converted]))*100),Math.round(price*100));
   assert.deepEqual(await scalar('select jsonb_agg(to_jsonb(e)order by e.id)from cp7_sku_conversion.cost_money_events_v3 e where id=any($1::uuid[])',[prior.map(e=>e.id)]),prior);
   observations.push({price,receipts:rows.map(e=>({bytes:e.bytes,depth:depth(e.source_proof)}))});
  }
  moneyCreditFindings.push({case:'bounded repeated price proof',observations,old_money_facts_immutable:true,exact_source_cents:true,actual_ERP_cases:0});
 });
 assert.equal(moneyCreditFindings.length,4);assert.deepEqual(await costSnapshot(),costBaseline);
