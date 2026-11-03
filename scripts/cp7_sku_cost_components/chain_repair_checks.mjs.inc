   const originalCostEvents=await scalar('select jsonb_agg(to_jsonb(e)order by e.id)from erp.be_conversion_cost_events_v1 e where document_id=$1',[costDocument]);
   // Equal-and-opposite book errors cannot be hidden by redistribution.
   const beforeDrift=await costSnapshot();await db.exec('savepoint cost_opposite_drift');
   await query('update public.model_book set fg=fg+.01 where product_id=$1',[x.target]);
   await query('update public.model_book set fg=fg-.01 where product_id=$1',[child.product]);
   await assert.rejects(()=>costReconcile(4),e=>e.message.includes('NON_PO_HPP_TARGET_BOOK_MISMATCH'));
   await db.exec('rollback to savepoint cost_opposite_drift');assert.deepEqual(await costSnapshot(),beforeDrift);
   await costReconcile(4);await costBook();await query('select erp.assert_non_po_product_hpp_target_book_v2620f($1)',[child.product]);
   assert.deepEqual(await values(x.target),{hpp:37,fg:37,cogs:0,other:0});
   assert.deepEqual(await values(child.product),{hpp:37,fg:37,cogs:0,other:0});
   const rebalanced=await scalar('select jsonb_agg(to_jsonb(r)order by r.id)from cp7_sku_conversion.cost_source_rebalances_v3 r');
   assert.equal(rebalanced.length,1);assert.equal(Number(rebalanced[0].source_delta),2);
   const reallocation=await scalar('select lines from public.model_journal where id=$1',[rebalanced[0].journal_id]);
   assert.equal(reallocation.length,2);assert(reallocation.every(l=>l.mapping_key==='FG_INVENTORY'));
   assert.equal(reallocation.reduce((sum,l)=>sum+Number(l.debit)-Number(l.credit),0),0);
   const expectedSign=physicalSource===x.root50?-1:1;
   assert.equal(Number(reallocation.find(l=>l.product_id===x.target).debit)-Number(reallocation.find(l=>l.product_id===x.target).credit),expectedSign);
   assert.deepEqual(await scalar('select jsonb_agg(to_jsonb(e)order by e.id)from erp.be_conversion_cost_events_v1 e where id=any($1::uuid[])',[originalCostEvents.map(e=>e.id)]),originalCostEvents);
   const replayBefore=await costSnapshot();await costReconcile(4);
   assert.deepEqual(await costSnapshot(),replayBefore,'Unchanged current cost must create no new modeled facts');
   await costReconcile(0);await costBook();await query('select erp.assert_non_po_product_hpp_target_book_v2620f($1)',[child.product]);
   assert.deepEqual(await values(x.target),{hpp:35,fg:35,cogs:0,other:0});
   assert.deepEqual(await values(child.product),{hpp:35,fg:35,cogs:0,other:0});
   costChainFindings.push({caseName,physicalSource,physicalValue:child.physicalValue,
    expectedBefore:{originalProduct:36,descendantProduct:36},expectedAfter:{originalProduct:37,descendantProduct:37},
    reversalToZero:{originalProduct:35,descendantProduct:35},rebalanced,reallocation,
    equal_opposite_drift_refused:true,unchanged_cost_replay_no_effect:true,original_source_history_immutable:true,
    product_fix_admitted:false,actual_ERP_cases:0});
