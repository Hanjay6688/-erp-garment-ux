import{readFileSync}from'node:fs';import assert from'node:assert/strict';
const{PGlite}=await import(process.env.OW04_PGLITE_MODULE||'@electric-sql/pglite');
const ledger=readFileSync(new URL('../ledger/01_immutable_facts.proposal.sql',import.meta.url),'utf8');
const helper=readFileSync(new URL('04_credit_book_bound.sql',import.meta.url),'utf8');
assert.equal((helper.match(/do \$not_an_installer\$/g)||[]).length,1);
const input={
 kernel:readFileSync(new URL('../kernel/kernel.sql',import.meta.url),'utf8'),
 domain:'create domain cp7_credit.cent_amount'+ledger.split('create domain cp7_credit.cent_amount')[1].split('create function cp7_credit.native_journal_cent_max')[0],
 helper:helper.replace(/do \$not_an_installer\$begin[\s\S]*?end \$not_an_installer\$;/,'')
};
const db=new PGlite(),checks=[];const day=n=>'2026-10-'+String(n).padStart(2,'0');
const move=(id,amount,e,b)=>({id,amount,economic_date:day(e),transaction_date:day(b),source_sha256:'1'.repeat(64)});
async function plan(i,c,amount,e=19,lawful=19,floor=19,clock='2026-10-21T23:00:00+07:00'){
 return(await db.query('select cp7_credit.consumer_positive_credit_book_bound_v1($1::jsonb,$2::jsonb,$3::numeric,$4::timestamptz,$5::date,$6::date,$7::timestamptz)as result',[JSON.stringify(i),JSON.stringify(c),amount,day(e)+'T12:00:00+07:00',lawful===null?null:day(lawful),floor===null?null:day(floor),clock])).rows[0].result;
}
async function refuse(fn,pattern){try{await fn()}catch(e){assert.match(e.message,pattern);return}throw Error('Expected refusal '+pattern)}
try{
await db.exec('create role anon;create role authenticated;create role service_role;create role cp7_capture;create role cp7_sales_read;create role cp7_sales_write;create role cp7_credit_write;create schema cp7_credit;');
await db.exec(input.kernel);await db.exec(input.domain);await db.exec(input.helper);
let x=await plan([move('I200','200.00',19,19)],[],'80.00');assert.equal(x.minimum_source_book_date,day(19));assert.equal(x.source_authority_proven,false);assert.equal(x.complete_financial_operation_proven,false);checks.push('SIMPLE80_USES_EARLY_SOURCE_BOOK_BOUND_ONLY');
const split=[move('I100early','100.00',19,19),move('I100late','100.00',19,21)];
x=await plan(split,[],'80.00');assert.equal(x.minimum_source_book_date,day(19));checks.push('LATER_UNRELATED100_DOES_NOT_DELAY_EARLY80');
x=await plan(split,[move('C80','80.00',19,19)],'120.00');assert.equal(x.minimum_source_book_date,day(21));checks.push('REMAINING120_WAITS_FOR_ACTUAL_SOURCE_BOOK21');
x=await plan(split,[move('C80','80.00',19,19)],'20.00');assert.equal(x.minimum_source_book_date,day(19));checks.push('REMAINING_EARLY20_STAYS_BOOK19');
x=await plan([move('I200','200.00',19,19)],[],'80.00',19,21,19);assert.equal(x.minimum_source_book_date,day(21));checks.push('SUPPLIED_NATIVE_LAWFUL_FLOOR_PRESERVED');
x=await plan([move('I200','200.00',19,19)],[],'80.00',19,19,21);assert.equal(x.minimum_source_book_date,day(21));checks.push('SUPPLIED_SOURCE_FLOOR_PRESERVED');
const restored=[move('C80','80.00',19,19),move('UNDO80','-80.00',20,20)];
await refuse(()=>plan([move('I200','200.00',19,19)],restored,'200.00'),/INSUFFICIENT_DATED_SOURCE_CAPACITY/);checks.push('LATER_UNDO_CANNOT_FUND_EARLIER_ECONOMIC_USE');
x=await plan([move('I200','200.00',19,19)],restored,'200.00',20,20,20);assert.equal(x.minimum_source_book_date,day(20));checks.push('FULL_RESTORED200_AVAILABLE_AT_LAWFUL_LATER_PAIR');
await refuse(()=>plan([move('Ia','100.00',19,21),move('Ib','100.00',20,20)],[move('C','100.00',19,20)],'1.00',21,21,19),/EXISTING_JOINT_HISTORY_UNFUNDED/);checks.push('ECONOMIC_AND_BOOK_MARGINS_CANNOT_HIDE_NEGATIVE_JOINT_RECTANGLE');
await refuse(()=>plan([move('I','200.00',19,19),move('Iinverse','-200.00',20,20)],[move('C','200.00',19,19),move('Cundo','-200.00',21,21)],'1.00',21,21,19),/EXISTING_JOINT_HISTORY_UNFUNDED/);checks.push('CURRENT_NET_ZERO_C_DOES_NOT_ERASE_UNFUNDED_INTERMEDIATE_HISTORY');
await refuse(()=>plan([move('I','200.00',19,19)],[move('C','200.00',19,19)],'0.01'),/INSUFFICIENT_DATED_SOURCE_CAPACITY/);checks.push('ONE_CENT_AFTER_FULL_USE_REFUSED');
for(const amount of ['0','-1','0.001','NaN','Infinity'])await refuse(()=>plan([move('I','200.00',19,19)],[],amount),/EXACT_POSITIVE_CENTS_REQUIRED/);checks.push('ZERO_NEGATIVE_SUBCENT_AND_NONFINITE_AMOUNTS_REFUSED');
await refuse(()=>plan([move('I','200.00',19,19)],[],'1.00',19,19,null),/EXPLICIT_VALID_DATE_REQUIRED/);checks.push('MISSING_SOURCE_FLOOR_REFUSED');
await refuse(()=>plan([move('I','200.00',19,19)],[],'1.00',19,19,22),/SOURCE_BOOK_IN_FUTURE/);checks.push('FUTURE_BOOK_FLOOR_REFUSED');
await refuse(()=>plan([move('I','200.00',19,19)],[],'1.00',22,22,22),/EXPLICIT_VALID_DATE_REQUIRED/);checks.push('FUTURE_PHYSICAL_INPUT_REFUSED');
for(const role of ['anon','authenticated','service_role','cp7_capture','cp7_sales_read','cp7_sales_write','cp7_credit_write'])assert.equal((await db.query("select has_function_privilege($1,'cp7_credit.consumer_positive_credit_book_bound_v1(jsonb,jsonb,numeric,timestamptz,date,date,timestamptz)','EXECUTE')as allowed",[role])).rows[0].allowed,false);checks.push('ALL_OUTSIDER_AND_OUTER_ROLE_EXECUTE_DENIED');
const result={classification:'LOCAL_PGLITE_SUPPLIED_VECTOR_SOURCE_CAPACITY_BOUND_ONLY_NOT_NATIVE_OR_FULL_DATE_APPROVAL',status:'PASS',check_count:checks.length,checks,Native_cases_added:0,complete_financial_operation_proven:false,consumer_command_implemented:false,production_go:false};assert.equal(checks.length,16);console.log(JSON.stringify(result));
}catch(e){console.error(JSON.stringify({status:'FAIL_LOCAL_CONTROL',error:e.message,query:e.query?.slice(0,180)}));process.exitCode=1;}finally{await db.close()}
