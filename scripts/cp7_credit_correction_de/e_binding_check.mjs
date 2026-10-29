/** Actual E reader/price SQL on explicit structural/source doubles only.
 * No money writer, actual Native parent, authority or deferred-closure proof.
 */
import {readFile} from 'node:fs/promises'
import {execFileSync} from 'node:child_process'
import assert from 'node:assert/strict'
const {PGlite}=await import(process.env.CP7_PGLITE_MODULE||'@electric-sql/pglite')
const here=new URL('./',import.meta.url),db=new PGlite(),checks=[]
const uid=n=>`11111111-1111-4111-8111-${String(n).padStart(12,'0')}`
const [source,old,next,customer,op,actor,request,revision,event,cohort,journal,product,item]=Array.from({length:13},(_,i)=>uid(i+1))
const q=async(sql,args=[])=>(await db.query(sql,args)).rows[0]?.answer
async function run(name,fn){await fn();checks.push(name)}
try{
 await db.exec(execFileSync('python3',[new URL('e_compile_fixture.py',here).pathname,process.argv[2]],{encoding:'utf8',maxBuffer:15e6,env:{...process.env,PYTHONPATH:new URL('../',here).pathname}}))
 await db.exec(`create function cp7_credit.pg_jsonb_sha256(jsonb)returns text language sql immutable as $$select encode(sha256(convert_to($1::text,'UTF8')),'hex')$$;
 create table public.declared_journal_double(id uuid,payload jsonb);
 create or replace function cp7_credit.materialized_journal_payload(uuid)returns jsonb language sql stable as $$select payload from public.declared_journal_double where id=$1$$;
 create or replace function cp7_credit.current_leaf_assignment(uuid)returns table(root_sale_id uuid,current_leaf_id uuid,customer_id uuid,requested_status text)language sql stable as $$
 select coalesce(r.root_sale_id,h.id),coalesce(r.replacement_sale_id,h.id),h.customer_id,h.status from erp.sales_headers h left join cp7_note.revisions r on h.id in(r.root_sale_id,r.replacement_sale_id)where h.id=$1$$;`)
 for(const file of['../cp7_customer_credit/kernel/kernel.sql','note_carry/01_facts.sql','note_carry/02_plan.sql','note_carry/03_readers.sql'])await db.exec(await readFile(new URL(file,here),'utf8'))
 for(const [file,name]of[['04_basis.sql','public_basis_v1'],['04_basis.sql','assert_price_only_v1'],['07_profile_closure.sql','target_assignment_v1'],['06_owning.sql','guard_later_native_source_v1']]){
  const text=await readFile(new URL('note_carry/'+file,here),'utf8'),start=text.indexOf('create function cp7_credit_note_carry_de.'+name),end=text.indexOf('$$;',start)
  assert(start>=0&&end>start);await db.exec(text.slice(start,end+3))
 }
 await db.query(`insert into erp.sales_headers(id,customer_id,status,sale_number,row_version)values($1,$4,'POSTED','SOURCE',1),($2,$4,'REVERSED','TARGET',2),($3,$4,'POSTED','TARGET-R1',1)`,[source,old,next,customer])
 await db.query('insert into cp7_note.revisions(id,root_sale_id,previous_sale_id,replacement_sale_id,revision,actor,request_id)values($1,$2,$2,$3,1,$4,$5)',[revision,old,next,actor,request])
 const proof={operation_id:op,actor,request_id:request,source_sale_id:old,replacement_sale_id:next,revision_id:revision,phase:'MATERIALIZED'}
 await db.query(`insert into cp7_credit_note_carry_de.operations_v1(operation_id,actor,request_id,source_sale_id,replacement_sale_id,revision_id,payload,expected_version,proof,response)values($1,$2,$3,$4,$5,$6,'{}','1',$7,'{}')`,[op,actor,request,old,next,revision,proof])
 await db.query(`insert into cp7_credit.consumption_events(id,cohort_id,event_kind,amount,target_sale_id,journal_id,economic_date,transaction_date)values($1,$2,'APPLY',80,$3,$4,'2026-10-02','2026-10-02')`,[event,cohort,old,journal])
 const journalValue={declared_reader_double:true,lines:[{customer_id:customer,amount:'80.00'}]}
 await db.query('insert into public.declared_journal_double values($1,$2)',[journal,journalValue])
 const eventValue=await q('select to_jsonb(e)answer from cp7_credit.consumption_events e where id=$1',[event])
 await db.query(`insert into cp7_credit_note_carry_de.assignments_v1 select $1,e.id,'APPLY',e.target_sale_id,$2,$3,to_jsonb(e),cp7_credit.materialized_journal_payload(e.journal_id),cp7_credit.pg_jsonb_sha256(to_jsonb(e)),cp7_credit.pg_jsonb_sha256(cp7_credit.materialized_journal_payload(e.journal_id))from cp7_credit.consumption_events e where e.id=$4`,[op,old,next,event])
 const effective=id=>q('select cp7_credit_note_carry_de.effective_target_v1($1)answer',[id])
 await run('CURRENT_TARGET_FOLLOWS_REPLACEMENT_WITHOUT_MUTATING_ORIGINAL_MONEY',async()=>{assert.equal(await effective(event),next);assert.deepEqual(await q('select to_jsonb(e)answer from cp7_credit.consumption_events e where id=$1',[event]),eventValue);assert.deepEqual(await q('select cp7_credit.materialized_journal_payload($1)answer',[journal]),journalValue)})
 await run('SAME_LOGICAL_TARGET_REQUIRES_OWNED_CHAIN',async()=>{assert.equal(await q('select cp7_credit_note_carry_de.same_target_v1($1,$2)answer',[old,next]),true);assert.equal(await q('select cp7_credit_note_carry_de.same_target_v1($1,$2)answer',[source,next]),false)})
 await run('MISSING_ASSIGNMENT_REFUSES_AND_UNRELATED_FLAT_TARGET_REMAINS_VALID',async()=>{await db.query(`insert into cp7_credit.consumption_events(id,event_kind,target_sale_id)values($1,'APPLY',$2),($3,'APPLY',$4),($5,'REFUND',null)`,[uid(30),old,uid(31),source,uid(32)]);await assert.rejects(()=>effective(uid(30)),/EVENT_ASSIGNMENT_MISSING/);assert.equal(await effective(uid(31)),source);assert.equal(await effective(uid(32)),null)})
 await run('CHANGED_ORIGINAL_AMOUNT_OR_JOURNAL_REFUSES',async()=>{await db.query('update cp7_credit.consumption_events set amount=81 where id=$1',[event]);await assert.rejects(()=>effective(event),/EVENT_ASSIGNMENT_CHANGED/);await db.query('update cp7_credit.consumption_events set amount=80 where id=$1',[event]);await db.query(`update public.declared_journal_double set payload='{}'where id=$1`,[journal]);await assert.rejects(()=>effective(event),/EVENT_ASSIGNMENT_CHANGED/);await db.query('update public.declared_journal_double set payload=$2 where id=$1',[journal,journalValue])})
 await run('INACTIVE_REPLACEMENT_REFUSES',async()=>{await db.query(`update erp.sales_headers set status='REVERSED'where id=$1`,[next]);await assert.rejects(()=>effective(event),/NOTE_ASSIGNMENT_CHANGED/);await db.query(`update erp.sales_headers set status='POSTED'where id=$1`,[next])})
 const selection={target_root_sale_id:old,target_current_leaf_id:next,target_sale_id:next,restores_event_id:null}
 const assignment=s=>q('select cp7_credit_note_carry_de.target_assignment_v1($1::jsonb)answer',[s])
 await run('APPLY_AND_NAMED_UNDO_REVIEW_KEEP_EXACT_CURRENT_AND_HISTORICAL_IDENTITIES',async()=>{const a=await assignment(selection),u=await assignment({...selection,restores_event_id:event});assert.equal(a.current_sale_id,next);assert.equal(a.current_number,'TARGET-R1');assert.equal(a.historical_target_id,next);assert.equal(a.original_event_id,null);assert.equal(a.revision_id,revision);assert.equal(u.original_event_id,event);assert.equal(u.historical_target_id,old);assert.equal(u.current_sale_id,next)})
 await run('NEW_APPLICATION_AFTER_CORRECTION_REMAINS_ON_REPLACEMENT',async()=>{await db.query(`insert into cp7_credit.consumption_events(id,event_kind,target_sale_id)values($1,'APPLY',$2)`,[uid(33),next]);assert.equal(await effective(uid(33)),next);assert.equal((await assignment({...selection,restores_event_id:uid(33)})).historical_target_id,next)})
 await run('LATER_NATIVE_MUTATION_CANNOT_ESCAPE_VIA_NEW_LEAF_OR_OLD_ROOT',async()=>{for(const sale of[old,next])await assert.rejects(()=>q("select cp7_credit_note_carry_de.guard_later_native_source_v1('SALE_REVERSE',$1)answer",[sale]),/LATER_NATIVE_MUTATION_ADAPTER_REQUIRED/);await q("select cp7_credit_note_carry_de.guard_later_native_source_v1('SALE_REVERSE',$1)answer",[source]);await db.query('insert into erp.sales_payments(id,sale_id)values($1,$2)',[uid(35),next]);await assert.rejects(()=>q("select cp7_credit_note_carry_de.guard_later_native_source_v1('PAYMENT',$1)answer",[uid(35)]),/LATER_NATIVE_MUTATION_ADAPTER_REQUIRED/)})
 await db.query('insert into erp.sales_items(id,sale_id,product_id,qty_pcs,line_total)values($1,$2,$3,5,500)',[item,old,product])
 const payload={sale_id:old,item_lineage:[item],items:[{product_id:product,qty_pcs:'5',unit_price_snapshot:'110.00',discount_amount:'0.01'}]},price=p=>q('select cp7_credit_note_carry_de.assert_price_only_v1($1::jsonb)::text answer',[p])
 await run('EXACT_PRICE_CENTS_AND_IMMUTABLE_QUANTITY_LINEAGE',async()=>{assert.equal(await price(payload),'549.99');for(const p of[{...payload,items:[{...payload.items[0],qty_pcs:'4'}]},{...payload,items:[{...payload.items[0],product_id:uid(34)}]},{...payload,item_lineage:[null]},{...payload,items:[],item_lineage:[]}])await assert.rejects(()=>price(p),/PRICE_ONLY_REQUIRED/)})
 await run('PUBLIC_REVIEW_SERIALIZES_AMOUNT_AND_BIGINT_VERSION_AS_TEXT',async()=>{const r=await q('select cp7_credit_note_carry_de.public_basis_v1($1::jsonb)answer',[{sale_id:old,root_sale_id:old,row_version:'9007199254740993',incoming_facts:[{event:eventValue}],issues:[]}]);assert.equal(r.row_version,'9007199254740993');assert.equal(r.consumers[0].amount,'80.00')})
 console.log(JSON.stringify({status:'PASS',checks,Native_execution:false,financial_writer_tested:false,deferred_closure_proven:false,standins:'structural Native/private columns, synthetic leaf graph and declared journal reader; actual E reader/price/review SQL unchanged'},null,2))
}catch(error){console.error(JSON.stringify({status:'FAIL',message:error.message,where:error.where,sqlstate:error.code,checks,Native_execution:false},null,2));process.exitCode=1}finally{await db.close()}
