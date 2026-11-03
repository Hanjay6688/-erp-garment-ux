 const currentInverseFindings=[];
 async function modelNativeInverse(child,physicalSource){
  // Retained Native inverse postconditions only; not an authority, dependency,
  // race or real Native command acceptance case.
  await movement(physicalSource,x.target,1,'MODEL_REBRAND_OUT_REVERSE',child.physicalValue);
  await movement(child.lot,child.product,-1,'MODEL_REBRAND_IN_REVERSE',child.physicalValue);
  for(const{journal_id}of(await query("select e.journal_id from erp.be_nonpo_transfer_events_v1 e join erp.journal_entries j on j.id=e.journal_id where e.conversion_id=$1 and j.status='POSTED'order by e.id",[child.conversion])).rows)
   await query("select erp.reverse_journal($1,'modeled physical inverse')",[journal_id]);
  const originalJournal=await scalar("select id from erp.journal_entries where source_type='PRODUCT_CONVERSION'and source_id=$1 and status='POSTED'",[child.conversion]);
  await query("select erp.reverse_journal($1,'modeled original conversion inverse')",[originalJournal]);
  await query("update erp.product_conversions set status='REVERSED'where id=$1",[child.conversion]);
  await query("select erp.be_nonpo_sync_all_v1('2026-01-04','PRODUCT_CONVERSION_REVERSE',$1,'modeled physical inverse')",[child.conversion]);
 }
 for(const physicalSource of[x.root50,x.converted])for(const currentCost of[0,2,4,-2,-4,4.02]){
  await control('CHAIN: current inverse at cost '+currentCost+' physical '+physicalSource,async()=>{
   if(currentCost<0)await query("update erp.be_conversion_cost_sources_v1 set kind='RECOVERY'where document_id=$1",[costDocument]);
   await costReconcile(currentCost<0?-2:2);const child=await nextConversion(physicalSource);
   await costReconcile(currentCost);
   await query('select cp7_sku_conversion.assert_group_inverse_capacity_v3($1)',[child.group]);
   const sourceFacts=await scalar('select cp7_sku_conversion.inverse_source_facts_v3($1)',[[x.root10,x.root30,x.root50,x.converted,child.lot]]);
   const frozenContributors=await scalar('select jsonb_agg(to_jsonb(c)order by c.group_id,c.line_no)from cp7_sku_conversion.cost_contributors_v3 c');
   const beforeMissingNative=await costSnapshot();await db.exec('savepoint required_native_inverse');
   await assert.rejects(()=>query('select cp7_sku_conversion.reverse_valuation_v2($1)',[child.group]),
    e=>e.message.includes('CP7_SKU_NATIVE_INVERSE_REQUIRED'));
   await db.exec('rollback to savepoint required_native_inverse');assert.deepEqual(await costSnapshot(),beforeMissingNative);
   await modelNativeInverse(child,physicalSource);
   const beforeDrift=await costSnapshot();await db.exec('savepoint inverse_opposite_drift');
   await query('update public.model_book set fg=fg+.01 where product_id=$1',[x.target]);
   await query('update public.model_book set fg=fg-.01 where product_id=$1',[child.product]);
   await assert.rejects(()=>query('select cp7_sku_conversion.reverse_valuation_v2($1)',[child.group]),
    e=>e.message.includes('NON_PO_HPP_TARGET_BOOK_MISMATCH'));
   await db.exec('rollback to savepoint inverse_opposite_drift');assert.deepEqual(await costSnapshot(),beforeDrift);
   await query('select cp7_sku_conversion.reverse_valuation_v2($1)',[child.group]);
   assert.deepEqual(await values(x.target),{hpp:70+currentCost,fg:70+currentCost,cogs:0,other:0});
   assert.deepEqual(await values(child.product),{hpp:0,fg:0,cogs:0,other:0});
   await costBook();await query('select erp.assert_non_po_product_hpp_target_book_v2620f($1)',[child.product]);
   const book=(await query('select product_id,fg,cogs,other_value from public.model_book where product_id=any($1::uuid[])order by product_id',[[x.target,child.product]])).rows;
   assert.equal(Number(book.find(b=>b.product_id===x.target).fg),70+currentCost);
   assert.equal(Number(book.find(b=>b.product_id===child.product).fg),0);
   assert.deepEqual(await scalar('select jsonb_agg(to_jsonb(c)order by c.group_id,c.line_no)from cp7_sku_conversion.cost_contributors_v3 c'),frozenContributors);
   assert.deepEqual(await scalar('select cp7_sku_conversion.inverse_source_facts_v3($1)',[[x.root10,x.root30,x.root50,x.converted,child.lot]]),sourceFacts);
   const proof=await scalar('select to_jsonb(r)from cp7_sku_conversion.group_inverse_rebalances_v3 r where group_id=$1',[child.group]);
   assert.equal(Number(proof.after_proof.target_change),0);assert.equal(Number(proof.after_proof.book_change),0);
   if(proof.journal_id){
    const lines=await scalar('select lines from public.model_journal where id=$1',[proof.journal_id]);
    assert.equal(lines.length,2);assert(lines.every(l=>l.mapping_key==='FG_INVENTORY'));
    assert.equal(lines.reduce((sum,l)=>sum+Math.round(Number(l.debit)*100)-Math.round(Number(l.credit)*100),0),0);
   }
   const after=await costSnapshot();await db.exec('savepoint private_inverse_repeat');
   await assert.rejects(()=>query('select cp7_sku_conversion.reverse_valuation_v2($1)',[child.group]),
    e=>e.message.includes('CP7_SKU_MOVAVG_ALREADY_REVERSED'));
   await db.exec('rollback to savepoint private_inverse_repeat');assert.deepEqual(await costSnapshot(),after);
   currentInverseFindings.push({physicalSource,currentCost,expected:[70+currentCost,0],book,proof,
    missing_native_inverse_refused:true,opposite_preexisting_drift_refused:true,old_source_and_contributors_immutable:true,
    actual_ERP_cases:0,execution:'MODELED_NATIVE_POSTCONDITIONS_AND_EXACT_PREPARED_CURRENT_VALUE_INVERSE'});
  });
 }
 assert.equal(currentInverseFindings.length,12);assert.deepEqual(await costSnapshot(),costBaseline);
 await control('CHAIN: unused physical child cannot hide consumed economic components',async()=>{
  await costReconcile(2);const child=await nextConversion(x.root50);
  const unrelated=id(99601),hpp=id(99602);
  await insert('erp.fg_lots',{id:unrelated,product_id:child.product,initial_qty_pcs:1,lot_origin:'OPENING',lot_number:'MODEL-UNRELATED'});
  await insert('erp.hpp_versions',{id:hpp,lot_id:unrelated,version_no:1,cost_state:'ADJUSTED',qty_basis_pcs:1,total_cost:50,is_current:true});
  await movement(unrelated,child.product,1,'OPENING',50);
  await query("select erp.post_journal('MODEL_OPENING',$1,'2026-01-03','explicit second physical lot',$2)",[unrelated,[
   {mapping_key:'FG_INVENTORY',product_id:child.product,debit:50,credit:0},
   {mapping_key:'OPENING_EQUITY',debit:0,credit:50}]]);
  await query('select cp7_sku_conversion.assert_group_inverse_capacity_v3($1)',[child.group]);
  await saleSetup(child.product,[unrelated],[1]);
  await query("update erp.sales_headers set sale_date='2026-01-03T00:00:00Z',source_location_id=$1,customer_id=$2 where id=$3",[x.location,id(900),x.sale]);
  await query('update erp.sales_items set qty_pcs=1,unit_price_snapshot=185000,discount_amount=0 where id=$1',[x.saleItem]);
  await insert('erp.fg_stock_movements',{id:id(++serial),lot_id:unrelated,product_id:child.product,location_id:x.location,
   quality_grade:'GRADE_A',qty_signed:-1,movement_type:'SALE_RESERVE',customer_id:id(900),source_type:'SALE_ITEM',source_id:x.saleItem,
   physical_at:'2026-01-03T00:00:00Z',system_created_at:'2026-01-03T00:00:00Z'});
  await query('select erp.post_sale($1)',[x.sale]);
  assert.deepEqual(await values(child.product),{hpp:86,fg:43,cogs:43,other:0});
  assert.equal(Number(await scalar("select count(*)from erp.fg_stock_movements where lot_id=$1 and movement_type in('SALE_RESERVE','SALE_OUT')",[child.lot])),0);
  const before=await costSnapshot();await db.exec('savepoint economic_capacity_inverse');
  await assert.rejects(()=>query('select cp7_sku_conversion.assert_group_inverse_capacity_v3($1)',[child.group]),
   e=>e.message.includes('CP7_SKU_INVERSE_ECONOMIC_COMPONENT_USED'));
  await db.exec('rollback to savepoint economic_capacity_inverse');assert.deepEqual(await costSnapshot(),before);
  currentInverseFindings.push({case:'unused physical child with consumed economic root',physical_child_unused:true,
   exact_sale_executed:true,economic_capacity_refused_before_native_inverse:true,complete_modeled_rollback:true,actual_ERP_cases:0});
 });
 assert.equal(currentInverseFindings.length,13);assert.deepEqual(await costSnapshot(),costBaseline);
