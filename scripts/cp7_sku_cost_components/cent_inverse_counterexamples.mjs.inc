 const remainingCostGaps=[];
 for(const[caseName,physicalSource,inverseBook]of[
  ['Physical unrelated cost root',x.root50,71],['Physical sourced cost root',x.converted,69]]){
  await control('CHAIN: retained cent and current inverse counterexamples '+caseName,async()=>{
   await costReconcile(2);const child=await nextConversion(physicalSource);
   const before=await costSnapshot();let centFailure;
   await db.exec('savepoint cost_fractional_source');
   try{await costReconcile(4.01);}catch(error){centFailure={message:error.message,code:error.code,where:error.where};}
   await db.exec('rollback to savepoint cost_fractional_source');assert.deepEqual(await costSnapshot(),before);
   assert(centFailure?.message.includes('CP7_SKU_COST_SOURCE_TOTAL_NOT_EXACT'),JSON.stringify(centFailure));
   assert(centFailure.message.includes('source 2.01, target change 2.02, book change 2.01'),centFailure.message);
   await costReconcile(0);await costBook();
   // Explicit retained Native inverse postconditions, not a Native command:
   // physical movements, posted physical recost journals, original conversion
   // journal and status reverse before the prepared group value hook.
   await movement(physicalSource,x.target,1,'MODEL_REBRAND_OUT_REVERSE',child.physicalValue);
   await movement(child.lot,child.product,-1,'MODEL_REBRAND_IN_REVERSE',child.physicalValue);
   for(const{journal_id}of(await query("select e.journal_id from erp.be_nonpo_transfer_events_v1 e join erp.journal_entries j on j.id=e.journal_id where e.conversion_id=$1 and j.status='POSTED'order by e.id",[child.conversion])).rows)
    await query("select erp.reverse_journal($1,'modeled physical inverse')",[journal_id]);
   const originalJournal=await scalar("select id from erp.journal_entries where source_type='PRODUCT_CONVERSION'and source_id=$1 and status='POSTED'",[child.conversion]);
   await query("select erp.reverse_journal($1,'modeled original conversion inverse')",[originalJournal]);
   await query("update erp.product_conversions set status='REVERSED'where id=$1",[child.conversion]);
   await query("select erp.be_nonpo_sync_all_v1('2026-01-04','PRODUCT_CONVERSION_REVERSE',$1,'modeled physical inverse')",[child.conversion]);
   await query('select cp7_sku_conversion.reverse_valuation_v2($1)',[child.group]);
   const target=await values(x.target),descendant=await values(child.product);
   const book=(await query('select product_id,fg,cogs,other_value from public.model_book where product_id=any($1::uuid[])order by product_id',[[x.target,child.product]])).rows;
   assert.deepEqual(target,{hpp:70,fg:70,cogs:0,other:0});assert.deepEqual(descendant,{hpp:0,fg:0,cogs:0,other:0});
   assert.equal(Number(book.find(b=>b.product_id===x.target).fg),inverseBook);
   assert.equal(Number(book.find(b=>b.product_id===child.product).fg),70-inverseBook);
   remainingCostGaps.push({caseName,centFailure,inverseExpected:{source:70,descendant:0},inverseObserved:book,
    inverse_execution:'MODELED_NATIVE_POSTCONDITIONS_PLUS_EXACT_PREPARED_VALUE_INVERSE_NOT_ACTUAL_NATIVE_COMMAND',
    fractional_failure_rolled_back_every_table:true,actual_ERP_cases:0,product_fix_admitted:false});
  });
 }
 assert.equal(remainingCostGaps.length,2);assert.deepEqual(await costSnapshot(),costBaseline);
