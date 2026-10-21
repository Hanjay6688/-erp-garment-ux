import { PGlite } from '/workspace/scratch/9442228ed2dc/sql-dev/node_modules/@electric-sql/pglite/dist/index.js';
import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
const dir='/workspace/scratch/9442228ed2dc/ow04-next-scope-proposal/integration/sql_compile_review';
const input=JSON.parse(await fs.readFile(dir+'/compile_input.json','utf8'));
const db=new PGlite();
const errors=[]; const attempts=[]; const done=[];
function err(e){return {message:e.message,code:e.code,position:e.position,internalPosition:e.internalPosition,internalQuery:e.internalQuery,where:e.where,detail:e.detail,hint:e.hint};}
async function attempt(p,stage,pass){try{await db.exec(p.sql);done.push({id:p.id,kind:p.kind,stage,pass});return true;}catch(e){const rec={id:p.id,kind:p.kind,stage,pass,...err(e)};attempts.push(rec);if(!errors.some(x=>x.id===p.id))errors.push({...rec,sql:p.sql});return false;}}
async function fixed(parts,stage,max=8){let pending=parts;for(let pass=1;pass<=max&&pending.length;pass++){let next=[];let successes=0;for(const p of pending){if(await attempt(p,stage,pass))successes++;else next.push(p);}console.log(JSON.stringify({stage,pass,successes,pending:next.length}));if(!successes){pending=next;break;}pending=next;}return pending;}
try{
 await db.exec(`create role anon;create role authenticated;create role service_role;create role cp7_capture;create role cp7_sales_read;create role cp7_sales_write;create role cp7_note_write;create role cp7_note_read;create role cp7_credit_write;create role cp7_credit_visible_read;
 create schema erp;create schema auth;create schema extensions;create schema cp7_sales;create schema cp7_note;create schema cp7_payment_correction;create schema cp7_sales_return_correction;
 create function auth.uid() returns uuid language plpgsql stable as $$begin raise exception 'COMPILE_ONLY_AUTH_STANDIN';end$$;
 create function auth.jwt() returns jsonb language plpgsql stable as $$begin raise exception 'COMPILE_ONLY_AUTH_STANDIN';end$$;
 set check_function_bodies=on;`);
 const settings=await db.query("select version(),current_setting('check_function_bodies')check_function_bodies");
 const nativePending=await fixed(input.native_parts,'native_type_scaffold');
 const protoPending=await fixed(input.native_prototypes,'native_raising_signature_standins');
 const priorPending=await fixed(input.prior,'prior_cp7_actual_types_raising_signatures');
 const schemaParts=input.parts.filter(x=>x.kind==='actual_product_type'||x.kind==='actual_product_alter_table');
 const funcs=input.parts.filter(x=>x.kind==='actual_product_function');
 const mainPending=await fixed([...schemaParts,...funcs],'actual_product_type_and_function_validator');
 const typesPending=mainPending.filter(p=>p.kind!=='actual_product_function');
 const funcsPending=mainPending.filter(p=>p.kind==='actual_product_function');
 const rest=input.parts.filter(x=>!['actual_product_type','actual_product_alter_table','actual_product_function'].includes(x.kind));
 const restPending=await fixed(rest,'actual_product_metadata');
 const pending=[...nativePending,...protoPending,...priorPending,...typesPending,...funcsPending,...restPending];

 // Execute only real pure product functions with supplied synthetic vectors.
 // These literal arithmetic checks are not Native/source/admission evidence.
 const event=(id,kind,amount,date)=>({id,kind,amount,economic_date:date,transaction_date:date,source_sha256:'a'.repeat(64)});
 const move=(id,amount,date)=>({id,amount,economic_date:date,transaction_date:date,source_sha256:'b'.repeat(64)});
 const input1={contract_version:'ow04.ordinal-input.v1',family_root_sale_id:'synthetic-sale',base_events:[event('sale','NET','1000.00','2026-10-17'),event('pay','FUNDING','1000.00','2026-10-18')],families:[{family_id:'F1',ordinal:'1',first_return_id:'R1',registration_sha256:'c'.repeat(64),events:[event('return','NET','-200.00','2026-10-19'),event('inverse','NET','200.00','2026-10-21')],retained_recognition:[move('I200','200.00','2026-10-19')],consumptions:[]}]};
 const pure=[];
 const reconcile=async(inp)=>(await db.query('select ow04_ordinal_wrapper.reconcile_v1($1::jsonb)result',[JSON.stringify(inp)])).rows[0].result;
 const adjusted=async(family)=>(await db.query('select cp7_credit.source_adjustment_kernel_v1($1::jsonb)result',[JSON.stringify(family)])).rows[0].result;
 const result1=await reconcile(input1);const k1=await adjusted(result1.families[0]);
 assert.equal(k1.net_current_k,'-200.00');assert.equal(k1.components.length,1);assert.equal(k1.components[0].amount,'-200.00');assert.equal(k1.components[0].economic_date,'2026-10-21');assert.equal(Object.keys(k1.components[0]).length,6);
 pure.push({id:'ACTUAL_PURE_RETURN_REVERSE_MINUS200',status:'PASS',kernel:k1});
 const input2=structuredClone(input1);input2.base_events.push(event('prior-paid-inverse','FUNDING','-50.00','2026-10-20'));input2.families[0].retained_recognition.push(move('priorADJminus50','-50.00','2026-10-20'));
 const result2=await reconcile(input2);const k2=await adjusted(result2.families[0]);assert.equal(k2.net_current_k,'-150.00');assert.equal(k2.components.length,1);assert.equal(k2.components[0].amount,'-150.00');
 pure.push({id:'ACTUAL_PURE_RETAINED_INITIAL200_AND_ADJ_MINUS50',status:'PASS',kernel:k2});
 const zero=structuredClone(input1);zero.families.unshift({family_id:'F0',ordinal:'1',first_return_id:'R0',registration_sha256:'d'.repeat(64),events:[event('zeroReturn','NET','0.00','2026-10-18'),event('zeroInverse','NET','0.00','2026-10-21')],retained_recognition:[],consumptions:[]});zero.families[1].ordinal='2';zero.families[1].events=zero.families[1].events.filter(e=>e.id!=='inverse');
 const rz=await reconcile(zero);assert(rz.families.every(f=>f.has_reconciliation_effect===false&&f.reconciliation_components.length===0));pure.push({id:'ACTUAL_PURE_ZERO_DIFF_EARLY_ZERO_RETURN',status:'PASS',family_count:rz.families.length});
 await fs.writeFile(dir+'/PURE_FUNCTION_EXECUTION.json',JSON.stringify({classification:'ACTUAL_PURE_SQL_FUNCTION_EXECUTION_SYNTHETIC_INPUT_NOT_NATIVE_BUSINESS_PROOF',tests:pure},null,2)+'\n');
 // Reflect actual declared composite row fields against real scaffold tables.
 const missingFields=[];let checkedFields=0;
 for(const p of funcs){const de=p.sql.match(/\bdeclare([\s\S]*?)\bbegin/i);if(!de)continue;const vars=[...de[1].matchAll(/(?:^|;|\n)\s*(\w+)\s+((?:erp|cp7_credit|cp7_sales)\.\w+)(?:%rowtype)?/gi)];for(const m of vars){const variable=m[1],table=m[2];const fields=[...new Set([...p.sql.matchAll(new RegExp('\\b'+variable+'\\.(\\w+)','g'))].map(x=>x[1]))];for(const field of fields){const r=await db.query('select exists(select 1 from pg_attribute where attrelid=to_regclass($1)and attname=$2 and attnum>0 and not attisdropped)present',[table,field]);checkedFields++;if(!r.rows[0].present)missingFields.push({statement:p.id,variable,table,field});}}}
 await fs.writeFile(dir+'/COMPOSITE_ROW_FIELD_CHECKS.json',JSON.stringify({classification:'ACTUAL_CATALOG_ROW_FIELD_REFLECTION_NOT_FULL_PLPGSQL_RUNTIME',checkedFields,missingFields},null,2)+'\n');
 const report={classification:'LOCAL_PGLITE_COMPILE_ONLY_NOT_NATIVE_BUSINESS_PROOF',settings:settings.rows,actual_source_files:input.files,done_count:done.length,pending:pending.map(p=>({id:p.id,kind:p.kind,last_error:attempts.filter(x=>x.id===p.id).at(-1)})),standins:input.native_prototypes.length+input.prior.filter(x=>x.kind==='RAISING_COMPILE_ONLY_STANDIN').length+2,unresolved_actual_function_count:funcsPending.length,no_real_database_or_network:true,product_edits:0,assembler_order_proven:false,plpgsql_sql_expressions_prepared_only_at_runtime:true};
 await fs.writeFile(dir+'/COMPILE_RESULT.json',JSON.stringify(report,null,2)+'\n');
 await fs.writeFile(dir+'/FIRST_ERRORS.json',JSON.stringify(errors,null,2)+'\n');
 await fs.writeFile(dir+'/ALL_ATTEMPTS.json',JSON.stringify(attempts,null,2)+'\n');
 await fs.writeFile(dir+'/DONE.json',JSON.stringify(done,null,2)+'\n');
 console.log(JSON.stringify({classification:report.classification,actual_functions:funcs.length,compiled_actual_functions:funcs.length-funcsPending.length,unresolved_actual_function_count:funcsPending.length,pending_total:pending.length,first_errors:errors.length,settings:settings.rows}));
} finally {await db.close();}
