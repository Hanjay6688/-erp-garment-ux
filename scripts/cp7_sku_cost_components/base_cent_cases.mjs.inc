 const baseCentFindings=[];
 for(const mode of['ROOT_PRICE_UP_TWO_SKUS','ROOT_PRICE_DOWN_TWO_SKUS','ROOT_PRICE_UP_AFTER_DESCENDANT']){
  await control('CHAIN: BASE CENT: '+mode,async()=>{
   const descendant=mode==='ROOT_PRICE_UP_AFTER_DESCENDANT';
   const child=descendant?await nextConversion(x.converted):null;
   const root=descendant?x.root50:x.root30,unit=descendant?50.01:(mode==='ROOT_PRICE_UP_TWO_SKUS'?30.01:29.99);
   const products=[x.source,x.target,...(child?[child.product]:[])];
   const before=await costSnapshot();const beforeTargets=await Promise.all(products.map(values));
   const old=await scalar('select to_jsonb(h)from erp.hpp_versions h where lot_id=$1 and is_current',[root]);
   const exactSourceChange=Math.round((unit*Number(old.qty_basis_pcs)-Number(old.total_cost))*100)/100;
   // Read the exact candidate target against one explicit HPP postcondition.
   // This isolated observation does not claim a successful Native correction.
   await db.exec('savepoint base_cent_target_observation');
   await query('update erp.hpp_versions set total_cost=$1::numeric*qty_basis_pcs where lot_id=$2 and is_current',[unit,root]);
   const afterTargets=await Promise.all(products.map(values));
   const targetChange=Math.round((afterTargets.reduce((n,v)=>n+v.hpp,0)-beforeTargets.reduce((n,v)=>n+v.hpp,0))*100)/100;
   await db.exec('rollback to savepoint base_cent_target_observation');
   assert.deepEqual(await costSnapshot(),before);
   assert.notEqual(targetChange,exactSourceChange,'This retained counterexample must expose a real source-cent discrepancy');
   await db.exec('savepoint base_cent_exact_command');let failure;
   try{await query("select erp.post_opening_hpp_correction($1,$2,'MODEL exact source-cent counterexample','2026-01-06')",[root,unit]);}
   catch(error){failure={message:error.message,code:error.code,where:error.where};}
   await db.exec('rollback to savepoint base_cent_exact_command');
   assert.deepEqual(await costSnapshot(),before,'Refused source correction must restore every modeled table');
   assert(failure?.message.includes('OPENING_SOURCE_CHANGE_NOT_EXACT'),JSON.stringify(failure));
   baseCentFindings.push({mode,root,unit,beforeTargets,afterTargets,exactSourceChange,targetChange,failure,
    exact_prepared_source_command_refused:true,complete_modeled_rows_restored:true,actual_ERP_cases:0});
  });
 }
 assert.equal(baseCentFindings.length,3);assert.deepEqual(await costSnapshot(),costBaseline);
