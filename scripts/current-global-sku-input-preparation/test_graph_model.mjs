// New graph/capture behavior only. Real column types, modeled rows and providers.
// This does not run Native money, stock, HPP, Auth, RLS or concurrency scenarios.
import assert from 'node:assert/strict';
import { readFile, writeFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';

const { PGlite } = await import(process.env.CP7_PGLITE_MODULE);
const input = JSON.parse(await readFile(process.env.CP7_GRAPH_INPUT, 'utf8'));
assert.equal(input.classification, 'MODELED_GRAPH_AND_CAPTURE_ONLY_NOT_ERP_QUALIFICATION');
const db = new PGlite();
const results = [];
const id = n => '70000000-0000-4000-8000-' + String(n).padStart(12, '0');
const fixture = n => Object.fromEntries(['product','target','lot','rootLot','group','sale','allocation',
  'return','returnItem','valueEvent','oldValueEvent','componentEvent','oldComponentEvent','journal','po','saleItem']
  .map((key, offset) => [key, id(n + offset + 1)]));
const relevant = fixture(0), outside = fixture(100), unrelated = fixture(200);
const commonLocation = id(999);
const scalar = async (sql, params = []) => Object.values((await db.query(sql, params)).rows[0])[0];
const q = s => '"' + s.replaceAll('"','""') + '"';
const scope = () => scalar('select cp7_global_nonpo_native_graph.scope_v1($1::uuid[])', [[relevant.sale]]);
const capture = (s, o = true) => scalar('select cp7_global_nonpo_native_graph.capture_v1($1::jsonb,$2)', [JSON.stringify(s),o]);
const check = (label, fn) => { fn(); results.push({ label, result: 'PASS' }); };
async function insert(table, row) {
  const cols = Object.keys(row);
  await db.query('insert into '+table+'('+cols.map(q).join(',')+')values('+cols.map((_,i)=>'$'+(i+1)).join(',')+')', Object.values(row));
}
function skuRow(table, x) {
  const cols = input.columns['cp7_sku_conversion.'+table];
  const row = Object.fromEntries(cols.map(([name,,type])=>[name,
    type==='uuid'?null:type==='date'?'2018-01-02':type==='timestamp with time zone'?'2018-01-02T03:04:05Z':
    /^(numeric|integer|smallint|bigint)/.test(type)?1:type==='boolean'?false:type==='jsonb'?{}:'MODEL_HISTORY']));
  const values = {group_id:x.group,source_product_id:x.product,target_product_id:x.target,
    product_id:x.product,lot_id:x.lot,root_lot_id:x.rootLot,po_id:null,hpp_version_id:id(900),
    correction_journal_id:x.journal,sale_stock_allocation_id:x.allocation,sale_id:x.sale,
    return_id:x.return,sales_return_item_id:x.returnItem,location_id:commonLocation,
    quality_grade:'GRADE_A',phase:'REVERSE',side:'POOL',line_no:1,supersedes_phase:'POST'};
  for (const [key,value] of Object.entries(values)) if (key in row) row[key]=value;
  if (table==='valuation_events_v2' || table==='component_events_v2') {
    row.id=table==='valuation_events_v2'?x.valueEvent:x.componentEvent;
    row.group_id=null;row.source_type='SALE';row.source_id=x.sale;
    row.supersedes_event_id=table==='valuation_events_v2'?x.oldValueEvent:x.oldComponentEvent;
    if ('qty_delta' in row) row.qty_delta=-1;
    if ('units_delta' in row) row.units_delta=-1;
  }
  return row;
}
let engine;
try {
  engine=await scalar('select version()');assert.match(engine,/^PostgreSQL 17\./);
  await db.exec('create role anon;create role authenticated;create role service_role;create schema erp;create schema cp7_sku_conversion;create schema cp7_credit;create schema cp7_global_nonpo_native_graph;');
  for (const [table, columns] of Object.entries(input.columns)) {
    await db.exec('create table '+table+'('+columns.map(([name,,type])=>q(name)+' '+type).join(',')+')');
    const actual=await scalar('select jsonb_object_agg(attname,format_type(atttypid,atttypmod))from pg_attribute where attrelid=$1::regclass and attnum>0 and not attisdropped',[table]);
    assert.deepEqual(actual,Object.fromEntries(columns.map(([name,,type])=>[name,type])));
  }
  await db.exec(`create function cp7_credit.consumer_dependency_graph_v1(uuid)returns jsonb language sql stable as $$select jsonb_build_object('sale_ids',jsonb_build_array($1))$$;
    create function cp7_credit.source_hpp_lot_ids_v1(uuid)returns uuid[]language sql stable as $$select array_agg(a.lot_id order by a.lot_id)from erp.sale_stock_allocations a join erp.sales_items i on i.id=a.sale_item_id where i.sale_id=$1$$;
    create function cp7_credit.initial_hpp_account_facts_v1()returns jsonb language sql stable as $$select '{"model_provider":true}'::jsonb$$;
    create function cp7_credit.pg_jsonb_sha256(jsonb)returns text language sql immutable as $$select encode(sha256(convert_to($1::text,'UTF8')),'hex')$$;`);
  await db.exec(input.helpers.scope);await db.exec(input.helpers.capture);
  // PL/pgSQL syntax is compiled, but Native-dependent authority/inspect are not
  // executed. The exact SQL bodies were separately parsed in preflight.
  await db.exec(input.helpers.authority);await db.exec(input.helpers.inspect);
  check('Four exact derived helpers compile against 44 model relations with all 463 declared column types',()=>assert.equal(Object.keys(input.columns).length,44));
  for (const x of [relevant,outside,unrelated]) {
    await insert('erp.fg_lots',{id:x.lot,product_id:x.product,po_id:x===unrelated?x.po:null,lot_origin:'OPENING'});
    await insert('erp.fg_lots',{id:x.rootLot,product_id:x.target,po_id:x===unrelated?x.po:null,lot_origin:'OPENING'});
    await insert('erp.sales_items',{id:x.saleItem,sale_id:x.sale,product_id:x.product});
    await insert('erp.sale_stock_allocations',{id:x.allocation,sale_item_id:x.saleItem,lot_id:x.lot});
    for (const table of Object.keys(input.sku_tables)) await insert('cp7_sku_conversion.'+table,skuRow(table,x));
  }
  const selected=await scope(),full=await capture(selected,false),base=await capture(selected);
  const keys=d=>new Set(d.identity_keys.map(x=>x.kind+':'+x.id));
  const r=keys(selected.relevant),o=keys(selected.outside),s=keys(selected.support);
  check('Complete relevant and outside closures are disjoint and cover support',()=>{
    assert([...r].every(k=>!o.has(k)));assert.deepEqual(new Set([...r,...o]),s);
    assert(r.has('SALE:'+relevant.sale));assert(o.has('SALE:'+outside.sale));
    assert(!s.has('SALE:'+unrelated.sale));
  });
  check('Sharing a location creates no identity hub between disconnected pools',()=>{
    assert(o.has('PRODUCT:'+outside.product));assert(!r.has('PRODUCT:'+outside.product));
    assert(!s.has('PRODUCT:'+unrelated.product));
  });
  check('Historical reversal and superseded economic identities remain visible',()=>{
    for(const[kind,key]of[['SKU_GROUP','group'],['SKU_SALE_ALLOCATION','allocation'],['SKU_RETURN_ITEM','returnItem'],
      ['SKU_VALUE_EVENT','valueEvent'],['SKU_VALUE_EVENT','oldValueEvent'],['SKU_COMPONENT_EVENT','componentEvent'],['SKU_COMPONENT_EVENT','oldComponentEvent']])
      assert(o.has(kind+':'+outside[key]),kind);
    assert.equal(base.facts.SKU_valuation_events_v2[0].phase,'REVERSE');
    assert.equal(base.facts.SKU_component_events_v2[0].economic_date,'2018-01-02');
  });
  for(const[table,[,key]]of Object.entries(input.sku_tables)) {
    const values={group_id:outside.group,sale_stock_allocation_id:outside.allocation,sales_return_item_id:outside.returnItem,
      id:table==='valuation_events_v2'?outside.valueEvent:outside.componentEvent};
    const expected=await scalar('select jsonb_agg(to_jsonb(t)order by to_jsonb(t)::text collate "C")from cp7_sku_conversion.'+table+' t where '+q(key)+'=$1',[values[key]]);
    assert.deepEqual(base.facts['SKU_'+table],expected,table+': complete outside rows');
    assert.equal(full.facts['SKU_'+table].length,2,table+': support excludes unrelated PO component');
  }
  results.push({label:'All twelve new observations preserve every declared column and exact relevant/outside membership',result:'PASS'});
  const mutations={valuation_quotes_v2:'transfer_value',valuation_contributors_v2:'transfer_units',valuation_postings_v2:'correction_value',
    valuation_attributions_v2:'adjustment_delta',sale_allocation_values_v2:'effective_value',sale_allocation_attributions_v2:'adjustment_delta',
    sale_allocation_components_v2:'booked_value',sales_return_values_v2:'effective_value',sales_return_attributions_v2:'adjustment_delta',
    sales_return_components_v2:'booked_value',valuation_events_v2:'adjustment_delta',component_events_v2:'units_delta'};
  let oldCapture=input.helpers.capture;
  for(const route of [...input.proof.exact_routes].reverse())if(route.helper==='capture')oldCapture=oldCapture.replace(route.after,route.before);
  oldCapture=oldCapture.replaceAll('cp7_global_nonpo_native_graph.capture_v1','cp7_global_nonpo_native_graph.old_capture_model');
  await db.exec(oldCapture);
  const oldBase=await scalar('select cp7_global_nonpo_native_graph.old_capture_model($1::jsonb,true)',[JSON.stringify(selected)]);
  for(const[table,column]of Object.entries(mutations)) {
    await db.exec('begin');
    try {
      // Model-only mutation: actual immutable business tables forbid this DML.
      await db.exec('update cp7_sku_conversion.'+table+' set '+q(column)+'='+q(column)+'+0.25');
      const changed=await capture(selected);
      assert.notEqual(changed.sha256,base.sha256,table+': new observation must detect economic change');
      assert.deepEqual(await scalar('select cp7_global_nonpo_native_graph.old_capture_model($1::jsonb,true)',[JSON.stringify(selected)]),oldBase,
        table+': reproduces the former missing observation');
      results.push({label:'Economic change detected in '+table+' that original capture omitted',result:'PASS'});
    } finally {await db.exec('rollback');}
  }
  await db.exec('begin');
  try {
    await db.query('update cp7_sku_conversion.valuation_events_v2 set supersedes_event_id=$1 where id=$2',[unrelated.valueEvent,outside.valueEvent]);
    const expanded=await scope();
    check('A historical economic predecessor expands the finite support closure',()=>{
      assert(keys(expanded.outside).has('SKU_VALUE_EVENT:'+unrelated.valueEvent));
      assert(keys(expanded.outside).has('PRODUCT:'+unrelated.product));
    });
  } finally {await db.exec('rollback');}
  await db.exec('begin');
  try {
    await db.exec('insert into cp7_sku_conversion.valuation_contributors_v2 select *from cp7_sku_conversion.valuation_contributors_v2');
    const duplicated=await capture(selected);
    check('Full rowset observation preserves multiplicity instead of silently deduplicating',()=>{
      assert.equal(duplicated.facts.SKU_valuation_contributors_v2.length,2);assert.notEqual(duplicated.sha256,base.sha256);
    });
  } finally {await db.exec('rollback');}
  for(const role of ['anon','authenticated','service_role']) {
    const allowed=await scalar("select bool_or(has_function_privilege($1,p.oid,'EXECUTE'))from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='cp7_global_nonpo_native_graph'",[role]);
    check(role+' has no execution capability on any prepared graph helper',()=>assert.equal(allowed,false));
  }
  const report={status:'MODELED_POSTGRES17_GLOBAL_SKU_GRAPH_CAPTURE_PASS_NOT_NATIVE',engine,
    results,source_helpers:input.proof.derived_helpers,modeled_callbacks:input.modeled_callbacks,
    row_constraints_owners_RLS_Native_callbacks_and_business_transactions_are_not_tested:true,
    new_SKU_rowset_observations:12,economic_mutation_regressions:12,
    actual_Native_cases:0,actual_Auth_HTTP_cases:0,actual_browser_cases:0,production_go:false,independent_acceptance:false};
  await writeFile(process.env.CP7_GRAPH_REPORT,JSON.stringify(report,null,2)+'\n');
  console.log(JSON.stringify({status:report.status,checks:results.length,actual_Native_cases:0}));
} catch(error) {
  await writeFile(process.env.CP7_GRAPH_REPORT,JSON.stringify({status:'MODEL_FAILED',engine,results,
    error:{message:error.message,SQLSTATE:error.code??null,stack:error.stack},actual_Native_cases:0},null,2)+'\n');
  throw error;
} finally {await db.close();}
