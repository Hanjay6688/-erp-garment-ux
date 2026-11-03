// New PO observer regressions only; no repeated SKU12 or financial Native suite.
import assert from 'node:assert/strict';
import {readFile,writeFile} from 'node:fs/promises';
const {PGlite}=await import(process.env.CP7_PGLITE_MODULE);
const input=JSON.parse(await readFile(process.env.CP7_GRAPH_INPUT,'utf8'));
assert.equal(input.classification,'MODELED_PO_INPUT_CAPTURE_ONLY_NOT_FINANCIAL_QUALIFICATION');
const db=new PGlite(),results=[];
const id=n=>'71000000-0000-4000-8000-'+String(n).padStart(12,'0');
const names=['sale','saleItem','relevantLot','relevantProduct','outsideLot','outsideProduct','poLot','poProduct','po',
 'group','batch','peerGroup','peerPo','roll','yield','correction','qc','terminal','terminalReverse','hppEvent',
 'hppJournal','inputJournal','reversalJournal','line','account','pool','oldPool','destination','poolSource','usageSource',
 'usage','usageEvent','poolEvent','adjustment','adjustmentItem','adjustmentFact','issue','issueItem','movement',
 'movementReverse','issueMovement','adjustmentMovement','revaluation','material','skuGroup','location',
 'unrelatedPo','unrelatedLot','unrelatedProduct','unrelatedIssue','unrelatedItem','lotlessPo'];
const x=Object.fromEntries(names.map((n,i)=>[n,id(i+1)]));
const quote=s=>'"'+s.replaceAll('"','""')+'"';
const scalar=async(sql,params=[])=>Object.values((await db.query(sql,params)).rows[0])[0];
const scope=()=>scalar('select cp7_global_nonpo_native_graph.scope_v1($1::uuid[])',[[x.sale]]);
const capture=(s,o=true)=>scalar('select cp7_global_nonpo_native_graph.capture_v1($1::jsonb,$2)',[JSON.stringify(s),o]);
const oldCapture=s=>scalar('select cp7_global_nonpo_native_graph.prior_capture_model($1::jsonb,true)',[JSON.stringify(s)]);
const check=(label,fn)=>{fn();results.push({label,result:'PASS'});};
async function insert(table,values){
 const columns=input.columns[table];assert(columns,table);
 const row=Object.fromEntries(columns.map(([name,,type])=>[name,
  type==='uuid'||type.endsWith('[]')?null:type==='date'?'2018-01-02':type==='timestamp with time zone'?'2018-01-02T03:04:05Z':
  type==='timestamp without time zone'?'2018-01-02 03:04:05':type==='xid8'?'1':
  /^(numeric|integer|smallint|bigint)/.test(type)?1:type==='boolean'?false:type==='jsonb'?{}:'M']));
 for(const[k,v]of Object.entries(values)){assert(Object.hasOwn(row,k),table+'.'+k);row[k]=v;}
 for(const[name,,type]of columns){const limit=type.match(/^character(?: varying)?\((\d+)\)$/);
  if(limit&&row[name]!==null)assert([...String(row[name])].length<=Number(limit[1]),table+'.'+name+': fixture text bound');}
 await db.query('insert into '+table+'('+Object.keys(row).map(quote).join(',')+')values('+Object.keys(row).map((_,i)=>'$'+(i+1)).join(',')+')',Object.values(row));
}
let engine;
try{
 engine=await scalar('select version()');assert.match(engine,/^PostgreSQL 17\./);
 await db.exec('create role anon;create role authenticated;create role service_role;create schema erp;create schema cp7_sku_conversion;create schema cp7_credit;create schema cp7_global_nonpo_native_graph;');
 for(const[table,columns]of Object.entries(input.columns)){
  await db.exec('create table '+table+'('+columns.map(([n,,t])=>quote(n)+' '+t).join(',')+')');
  const actual=await scalar('select jsonb_object_agg(attname,format_type(atttypid,atttypmod))from pg_attribute where attrelid=$1::regclass and attnum>0 and not attisdropped',[table]);
  assert.deepEqual(actual,Object.fromEntries(columns.map(([n,,t])=>[n,t])));
 }
 await db.exec(`create function cp7_credit.consumer_dependency_graph_v1(uuid)returns jsonb language sql stable as $$select jsonb_build_object('sale_ids',jsonb_build_array($1))$$;
 create function cp7_credit.source_hpp_lot_ids_v1(uuid)returns uuid[]language sql stable as $$select array_agg(a.lot_id order by a.lot_id)from erp.sale_stock_allocations a join erp.sales_items i on i.id=a.sale_item_id where i.sale_id=$1$$;
 create function cp7_credit.initial_hpp_account_facts_v1()returns jsonb language sql stable as $$select '{"model_provider":true}'::jsonb$$;
 create function cp7_credit.pg_jsonb_sha256(jsonb)returns text language sql immutable as $$select encode(sha256(convert_to($1::text,'UTF8')),'hex')$$;`);
 await db.exec(input.helpers.scope);await db.exec(input.helpers.capture);
 await db.exec(input.prior_helpers.capture.replaceAll('cp7_global_nonpo_native_graph.capture_v1','cp7_global_nonpo_native_graph.prior_capture_model'));
 check('Exact new helper SQL compiles against all 71 real column maps; no modeled financial writer',()=>assert.equal(Object.keys(input.columns).length,71));
 for(const[lot,product,po,origin]of[[x.relevantLot,x.relevantProduct,null,'OPENING'],[x.outsideLot,x.outsideProduct,null,'OPENING'],[x.poLot,x.poProduct,x.po,'PRODUCTION'],[x.unrelatedLot,x.unrelatedProduct,x.unrelatedPo,'PRODUCTION']])
  await insert('erp.fg_lots',{id:lot,product_id:product,po_id:po,lot_origin:origin,cutting_group_id:po===x.po?x.group:null,qc_item_id:po===x.po?x.qc:null});
 await insert('erp.sales_items',{id:x.saleItem,sale_id:x.sale,product_id:x.relevantProduct});
 await insert('erp.sale_stock_allocations',{id:id(90),sale_item_id:x.saleItem,lot_id:x.relevantLot});
 for(const[lot,po]of[[x.outsideLot,null],[x.poLot,x.po]])await insert('cp7_sku_conversion.valuation_contributors_v2',{group_id:x.skuGroup,root_lot_id:lot,po_id:po});
 for(const po of[x.po,x.peerPo,x.unrelatedPo])await insert('erp.production_orders',{id:po,status:'CANCELLED',notes:'retained history'});
 for(const[group,po]of[[x.group,x.po],[x.peerGroup,x.peerPo]])await insert('erp.cutting_groups',{id:group,po_id:po,cutting_batch_id:x.batch,status:'CANCELLED'});
 await insert('erp.cutting_batches',{id:x.batch,po_id:x.po,status:'CANCELLED'});
 await insert('erp.cutting_group_rolls',{id:x.roll,cutting_group_id:x.peerGroup});
 await insert('erp.cutting_roll_yields',{id:x.yield,cutting_group_roll_id:x.roll});
 await insert('erp.cutting_qty_correction_lines',{id:x.correction,cutting_group_id:x.peerGroup});
 await insert('erp.qc_inspection_items',{id:x.qc,cutting_group_id:x.group});
 await insert('erp.sewing_terminal_events',{id:x.terminal,po_id:x.po,cutting_group_id:x.group,event_kind:'SELESAI_DIJAHIT'});
 await insert('erp.sewing_terminal_events',{id:x.terminalReverse,po_id:null,reversal_of_id:x.terminal,event_kind:'REVERSAL',qty_signed:-1});
 await insert('erp.po_hpp_gl_lot_state_v1',{lot_id:x.poLot,po_id:x.po,pocket_by_pool:{[x.oldPool]:7}});
 await insert('erp.po_hpp_gl_material_state_v1',{po_id:x.po,source_key:'M:'+x.movement});
 await insert('erp.po_hpp_gl_state',{po_id:x.po});
 await insert('erp.po_hpp_gl_events',{id:x.hppEvent,po_id:x.po,journal_entry_id:x.hppJournal});
 await insert('erp.pocket_period_destinations',{id:x.destination,po_id:x.po,pool_id:x.pool,event_id:x.terminal,cutting_group_id:x.group});
 for(const pool of[x.pool,x.oldPool])await insert('erp.pocket_periods',{id:pool});
 await insert('erp.pocket_period_events',{id:x.poolEvent,pool_id:x.pool,kind:'CANCEL',journal_entry_id:x.inputJournal});
 await insert('erp.pocket_period_sources',{id:x.poolSource,pool_id:x.pool,adjustment_id:x.adjustment});
 await insert('erp.pocket_period_sources',{id:x.usageSource,pool_id:x.pool,historical_usage_id:x.usage});
 await insert('erp.be_pocket_usage_v1',{id:x.usage,material_id:x.material,journal_id:x.inputJournal,allocation_status:'CANCELLED'});
 await insert('erp.be_pocket_source_events_v1',{id:x.usageEvent,usage_id:x.usage,journal_id:x.inputJournal});
 await insert('erp.material_adjustments',{id:x.adjustment,status:'REVERSED',location_id:x.location});
 await insert('erp.material_adjustment_items',{id:x.adjustmentItem,adjustment_id:x.adjustment,material_id:x.material});
 await insert('erp.bc_adjustment_purposes_v1',{adjustment_id:x.adjustment,account_id:x.account});
 await insert('erp.material_adjustment_revaluation_facts',{id:x.adjustmentFact,adjustment_id:x.adjustment,journal_entry_id:x.inputJournal});
 for(const[issue,item,po]of[[x.issue,x.issueItem,x.po],[x.unrelatedIssue,x.unrelatedItem,x.unrelatedPo]]){
  await insert('erp.contractor_material_issues',{id:issue,po_id:po,status:'REVERSED',location_id:x.location});
  await insert('erp.contractor_material_issue_items',{id:item,issue_id:issue,material_id:x.material});
 }
 for(const[mid,type,source,reverse]of[[x.movement,'CUTTING_GROUP',x.peerGroup,null],
  [x.movementReverse,'REVERSAL',null,x.movement],[x.issueMovement,'CONTRACTOR_MATERIAL_ISSUE_ITEM',x.issueItem,null],
  [x.adjustmentMovement,'MATERIAL_ADJUSTMENT_ITEM',x.adjustmentItem,null]])
  await insert('erp.material_stock_movements',{id:mid,source_type:type,source_id:source,reversal_of_id:reverse,material_id:x.material});
 await insert('erp.material_cost_revaluation_events',{id:x.revaluation,movement_id:x.movement,po_id:x.po,journal_entry_id:x.inputJournal});
 await insert('erp.materials',{id:x.material,material_type:'FABRIC'});
 for(const[journal,reverse]of[[x.hppJournal,null],[x.inputJournal,null],[x.reversalJournal,x.inputJournal]])
  await insert('erp.journal_entries',{id:journal,reversal_of_id:reverse,status:'REVERSED'});
 await insert('erp.journal_lines',{id:x.line,journal_entry_id:x.reversalJournal,account_id:x.account,po_id:null,product_id:null});
 await insert('erp.accounting_account_mappings',{mapping_key:'MATERIAL_INVENTORY',account_id:x.account});
 await insert('erp.chart_accounts',{id:x.account});
 await insert('erp.invoice_recost_execution_context',{transaction_id:1,invoice_date:'2018-01-02'});
 const selected=await scope(),baseline=await capture(selected),old=await oldCapture(selected);
 const identities=part=>new Set(selected[part].identity_keys.map(v=>v.kind+':'+v.id));
 check('SKU economic links reach the outside PO and its undimensioned event journal',()=>{
  const outside=identities('outside');assert(outside.has('PO:'+x.po));assert(outside.has('PO_HPP_EVENT:'+x.hppEvent));assert(outside.has('JOURNAL:'+x.hppJournal));
  assert(!identities('relevant').has('PO:'+x.po));assert(!identities('support').has('PO:'+x.unrelatedPo));assert(!identities('support').has('PO:'+x.peerPo));
 });
 check('Shared material and location do not connect unrelated POs; shared batch input is still observed',()=>{
  assert.deepEqual(baseline.facts.PO_contractor_issues.map(v=>v.id),[x.issue]);
  assert.deepEqual(new Set(baseline.facts.PO_cutting_groups.map(v=>v.id)),new Set([x.group,x.peerGroup]));
  assert.equal(baseline.facts.PO_materials.length,1);assert.equal(baseline.facts.PO_cutting_yields[0].id,x.yield);
 });
 check('Reversal history, cancelled sources and saved pocket pools without current destinations remain visible',()=>{
  assert.equal(baseline.facts.PO_sewing_events.length,2);assert.equal(baseline.facts.PO_material_movements.length,4);
  assert.equal(baseline.facts.PO_pocket_pools.length,2);assert.equal(baseline.facts.PO_pocket_events[0].kind,'CANCEL');
  assert.equal(baseline.facts.PO_input_journals.length,3);assert.equal(baseline.facts.PO_input_journal_lines[0].po_id,null);
 });
 check('All 31 new observations contain every physical column, with no money-only or timestamp projection',()=>{
  for(const[name,,table]of input.observations){const rows=baseline.facts['PO_'+name];assert(rows.length>0,name);
   assert.deepEqual(Object.keys(rows[0]).sort(),input.columns['erp.'+table].map(([n])=>n).sort(),name);}
 });
 const mutations={orders:'target_qty_pcs',cutting_groups:'notes',cutting_batches:'notes',cutting_rolls:'qty_consumed',cutting_yields:'qty_pcs',
  cutting_corrections:'qty_delta_pcs',qc_items:'qty_good_pcs',sewing_events:'qty_signed',lot_states:'hpp_per_pcs',material_states:'material_value',
  hpp_events:'fg_delta',pocket_destinations:'source_snapshot',pocket_pools:'denominator',pocket_events:'ledger_delta',pocket_sources:'original_amount',
  pocket_usages:'original_amount',pocket_usage_events:'new_amount',adjustments:'notes',adjustment_items:'qty_signed',adjustment_purposes:'purpose',
  adjustment_revaluations:'ledger_delta',contractor_issues:'notes',contractor_issue_items:'unit_cost_snapshot',material_movements:'unit_cost_snapshot',
  material_revaluations:'delta_amount',materials:'material_type',input_journals:'description',input_journal_lines:'debit',account_mappings:'notes',
  accounts:'account_name',invoice_context:'invoice_date'};
 for(const[name,,table]of input.observations){
  const column=mutations[name],type=input.columns['erp.'+table].find(([n])=>n===column)[2];
  const expression=/^(numeric|integer|smallint|bigint)/.test(type)?quote(column)+'+1':type==='jsonb'?"'{\"changed\":true}'::jsonb":type==='date'?quote(column)+"+1":"'CHANGED'";
  await db.exec('begin');try{
   // Synthetic model rows only. Actual immutable business rows are not edited.
   await db.exec('update erp.'+table+' set '+quote(column)+'='+expression);
   const changed=await capture(selected);assert.notEqual(changed.sha256,baseline.sha256,name);
   assert.notDeepEqual(changed.facts['PO_'+name],baseline.facts['PO_'+name],name);
   results.push({label:'Full PO basis detects changed '+name+'.'+column,result:'PASS'});
  }finally{await db.exec('rollback');}
 }
 for(const[table,column]of[['po_hpp_gl_lot_state_v1','updated_at'],['po_hpp_gl_material_state_v1','updated_at'],['po_hpp_gl_events','created_at']]){
  await db.exec('begin');try{
   await db.exec('update erp.'+table+' set '+column+'='+column+"+interval '1 second'");
   assert.notEqual((await capture(selected)).sha256,baseline.sha256,table);assert.deepEqual(await oldCapture(selected),old,table);
   results.push({label:'Timestamp-only change in '+table+' is detected; previous observer omitted it',result:'PASS'});
  }finally{await db.exec('rollback');}
 }
 await db.exec('begin');try{
  await insert('erp.po_hpp_gl_state',{po_id:x.lotlessPo});
  const direct=structuredClone(selected);direct.outside.po_ids.push(x.lotlessPo);
  assert.equal((await capture(direct)).facts.po_states.length,2);assert.equal((await oldCapture(direct)).facts.po_states.length,1);
  results.push({label:'Direct PO identity retains saved state even when no surviving lot selects it',result:'PASS'});
 }finally{await db.exec('rollback');}
 await db.exec('begin');try{
  await db.exec('insert into erp.po_hpp_gl_material_state_v1 select *from erp.po_hpp_gl_material_state_v1');
  const duplicate=await capture(selected);assert.equal(duplicate.facts.PO_material_states.length,2);assert.notEqual(duplicate.sha256,baseline.sha256);
  results.push({label:'PO full-row observation preserves duplicate multiplicity',result:'PASS'});
 }finally{await db.exec('rollback');}
 // Final source admission remains closed; these are read-only model helpers.
 const report={status:'MODELED_POSTGRES17_GLOBAL_SKU_PO_OBSERVATIONS_PASS_NOT_NATIVE',engine,results,
  source_helpers:input.proof.derived_helpers,modeled_callbacks:input.modeled_callbacks,
  column_tables:71,column_count:733,new_PO_rowset_observations:31,new_PO_identity_edges:3,
  row_constraints_owners_RLS_Native_callbacks_and_business_transactions_are_not_tested:true,
  actual_Native_cases:0,actual_Auth_HTTP_cases:0,actual_browser_cases:0,production_go:false,independent_acceptance:false};
 await writeFile(process.env.CP7_GRAPH_REPORT,JSON.stringify(report,null,2)+'\n');
 console.log(JSON.stringify({status:report.status,checks:results.length,actual_Native_cases:0}));
}catch(error){
 await writeFile(process.env.CP7_GRAPH_REPORT,JSON.stringify({status:'MODEL_FAILED',engine,results,error:{message:error.message,SQLSTATE:error.code??null,stack:error.stack},actual_Native_cases:0},null,2)+'\n');
 throw error;
}finally{await db.close();}
