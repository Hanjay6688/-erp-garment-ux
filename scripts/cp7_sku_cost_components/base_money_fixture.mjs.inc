 // Explicit MODELED historical postconditions per isolated case. These
 // describe the retained starting conversion, not a production backfill.
 // Mixed-PO fixtures establish provenance before enrolling non-PO roots.
 initializeBaseFixture=async label=>{
 const poRoot=(label.startsWith('Mixed PO and non-PO return components')||label.startsWith('Mixed PO economic roots'))?x.root30:
  label.startsWith('Mixed PO cost projection')?x.root10:null;
 for(const[root,product,qty,amount,hpp]of[
  [x.root10,x.source,2,20,x.hpp10],[x.root30,x.source,2,60,x.hpp30],
  [x.root50,x.target,1,50,x.hpp50]]){
  if(root===poRoot)continue;
  await insert('cp7_sku_conversion.base_money_events_v4',{id:id(++serial),kind:'ORIGIN',source_id:hpp,
   root_lot_id:root,product_id:product,units_delta:qty,amount_delta:amount,
   source_proof:{explicit_model_historical_origin:true},economic_date:'2026-01-01'});
 }
 for(const[root,amount]of[[x.root10,5],[x.root30,15]])for(const[product,sign]of[[x.source,-1],[x.target,1]]){
  if(root===poRoot)continue;
  await insert('cp7_sku_conversion.base_money_events_v4',{id:id(++serial),kind:'TRANSFER',source_id:x.group,
   root_lot_id:root,product_id:product,units_delta:sign*.5,amount_delta:sign*amount,
   source_proof:{explicit_model_historical_transfer:true},economic_date:'2026-01-01'});
 }
 };
 async function modelBaseSourcePostcondition(root,total){
  // Two retained source-guard controls intentionally bypass the Native
  // opening command. Supply its monetary postconditions explicitly, keeping
  // their old book discrepancy and original exact refusal unchanged.
  const rows=(await query('select *from cp7_sku_conversion.base_money_cells_v4($1)order by product_id',[root])).rows;
  const qty=rows.reduce((n,r)=>n+Number(r.units),0);let units=0,prior=0;
  for(const row of rows){
   units+=Number(row.units);const target=Math.round(total*100*units/qty),delta=target-prior-Math.round(Number(row.amount)*100);prior=target;
   if(delta)await insert('cp7_sku_conversion.base_money_events_v4',{id:id(++serial),kind:'SOURCE_PRICE',source_id:id(++serial),
    root_lot_id:root,product_id:row.product_id,units_delta:0,amount_delta:delta/100,
    source_proof:{explicit_model_source_postcondition:true},economic_date:'2026-01-03'});
  }
 }
