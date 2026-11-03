 // Explicit postconditions for the already constructed historical fixture.
 // Production initialization refuses any unadmitted prior conversion. These
 // exact origin/transfer facts supply no historical-backfill/ERP acceptance.
 for(const[root,product,qty,amount,hpp]of[
  [x.root10,x.source,2,20,x.hpp10],[x.root30,x.source,2,60,x.hpp30],
  [x.root50,x.target,1,50,x.hpp50]]){
  await insert('cp7_sku_conversion.base_money_events_v4',{id:id(++serial),kind:'ORIGIN',source_id:hpp,
   root_lot_id:root,product_id:product,units_delta:qty,amount_delta:amount,
   source_proof:{explicit_model_historical_origin:true},economic_date:'2026-01-01'});
 }
 for(const[root,amount]of[[x.root10,5],[x.root30,15]])for(const[product,sign]of[[x.source,-1],[x.target,1]]){
  await insert('cp7_sku_conversion.base_money_events_v4',{id:id(++serial),kind:'TRANSFER',source_id:x.group,
   root_lot_id:root,product_id:product,units_delta:sign*.5,amount_delta:sign*amount,
   source_proof:{explicit_model_historical_transfer:true},economic_date:'2026-01-01'});
 }
