/** Actual pure SQL E planner/leaf-set logic; supplied vectors, no Native writer proof. */
import {readFile} from 'node:fs/promises'
import assert from 'node:assert/strict'
const {PGlite}=await import(process.env.CP7_PGLITE_MODULE||'@electric-sql/pglite')
const here=new URL('./',import.meta.url),db=new PGlite()
try{
 await db.exec("create schema cp7_credit_note_carry_de;create schema cp7_credit;create function cp7_credit.cent_text(numeric)returns text language sql immutable as $$select round($1,2)::text$$;")
 await db.exec(await readFile(new URL('../cp7_customer_credit/kernel/kernel.sql',here),'utf8'))
 await db.exec(await readFile(new URL('note_carry/02_plan.sql',here),'utf8'))
 const readers=await readFile(new URL('note_carry/03_readers.sql',here),'utf8'),start=readers.indexOf('create function cp7_credit_note_carry_de.active_sales_v1'),end=readers.indexOf('end $$;',start)
 await db.exec(readers.slice(start,end+7))
 const event=(id,amount,day)=>({id,kind:'FUNDING',amount,economic_date:day,transaction_date:day,source_sha256:'a'.repeat(64)})
 const basis=(amount,minimum,events)=>({basis_sha256:'b'.repeat(64),transfer_amount:amount,minimum_replacement_net:minimum,incoming_events:events,issues:[]})
 const plan=async(basis,net)=>(await db.query('select cp7_credit_note_carry_de.plan_v1($1::jsonb,$2)q',[basis,net])).rows[0].q
 const first=basis('80.00','80.00',[event('apply','80.00','2026-10-02')])
 assert.deepEqual((({transfer_amount,replacement_net,remaining_amount,state})=>({transfer_amount,replacement_net,remaining_amount,state}))(await plan(first,'550.00')),{transfer_amount:'80.00',replacement_net:'550.00',remaining_amount:'470.00',state:'READY'})
 assert.equal((await plan(first,'80.00')).remaining_amount,'0.00')
 const tooSmall=await plan(first,'79.99');assert.equal(tooSmall.state,'REFUSE');assert(tooSmall.issues.includes('BASE_OVERFLOW_NONZERO'))
 const exact=basis('9007199254740993.99','9007199254740993.99',[event('huge','9007199254740993.99','2026-10-02')]);assert.equal((await plan(exact,'9007199254740994.00')).remaining_amount,'0.01')
 const historical=basis('130.00','180.00',[event('applied','180.00','2026-10-02'),event('named-undo','-50.00','2026-10-03')]);assert.equal((await plan(historical,'150.00')).state,'REFUSE');assert.equal((await plan(historical,'180.00')).remaining_amount,'50.00')
 await assert.rejects(()=>plan({...historical,minimum_replacement_net:'130.00'},'150.00'),/CP7_CREDIT_NOTE_CARRY_EXACT_BASIS_REQUIRED/)
 await assert.rejects(()=>plan(first,'80.001'),/EXACT_CENTS_REQUIRED/)
 const old={sale_ids:['a','old'],source:{current_leaf_ids:['a','old']},target:{current_leaf_ids:['a','old']}}
 const fresh={sale_ids:['a','old','new'],source:{current_leaf_ids:['a','new']},target:{current_leaf_ids:['a','new']}}
 const leaves=async(graph)=>(await db.query('select cp7_credit_note_carry_de.active_sales_v1($1::jsonb)q',[graph])).rows[0].q
 assert.deepEqual(await leaves(old),['a','old']);assert.deepEqual(await leaves(fresh),['a','new']);assert.deepEqual(old.sale_ids,['a','old']);assert.deepEqual(fresh.sale_ids,['a','old','new'])
 await assert.rejects(()=>leaves({...fresh,sale_ids:['a','old']}),/CAPTURED_LEAF_SET_CHANGED/)
 console.log(JSON.stringify({status:'PASS',tests:9,actual_SQL_pure_plan_and_captured_leaf_set:true,Native_execution:false,financial_writer_tested:false,standins:'supplied exact-cent incoming vectors and historical graph snapshots'},null,2))
}catch(error){console.error(JSON.stringify({status:'FAIL',message:error.message,sqlstate:error.code,Native_execution:false},null,2));process.exitCode=1}finally{await db.close()}
