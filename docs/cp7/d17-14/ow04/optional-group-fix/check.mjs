// Exact optional-account helper and SQL fragments; not Native posting proof.
import fs from'node:fs/promises';import{execFileSync}from'node:child_process';import path from'node:path';import assert from'node:assert/strict';
import{fileURLToPath}from'node:url';const{PGlite}=await import(process.env.PGLITE_MODULE||'@electric-sql/pglite');
const repo=process.env.ERP_REPO||process.cwd(),root=repo+'/scripts/cp7_customer_credit',here=path.dirname(fileURLToPath(import.meta.url));
const read=n=>fs.readFile(root+'/coordinator/'+n,'utf8'),before=async n=>execFileSync('git',['show','6d350f79dacd41cecb0c0e80d2c62ffb8b723dd8:scripts/cp7_customer_credit/coordinator/'+n],{cwd:repo,encoding:'utf8'});
const cut=(s,a,b)=>{const i=s.indexOf(a);assert(i>=0,a);const j=s.indexOf(b,i);assert(j>=i,b);return s.slice(i,j+b.length)};
const db=new PGlite(),cases=[],u='00000000-0000-0000-0000-000000000001';
async function check(name,sql,expectedError){await db.exec('begin');let error;try{await db.exec(sql)}catch(e){error=e}await db.exec('rollback');
if(expectedError){assert(error,name);assert(error.message.includes(expectedError)||error.code===expectedError,JSON.stringify({name,error:error.message,code:error.code}));}else if(error)throw error;
cases.push({name,status:'PASS',expected_refusal:expectedError||null,observed_error:error?.message||null});}
try{
await db.exec(`create schema cp7_credit;create schema erp;
create table erp.cash_accounts(id uuid,coa_account_id uuid,is_active boolean,cash_account_code text,cash_account_name text);
create table erp.chart_accounts(id uuid,is_active boolean,is_postable boolean,account_type text);
create table erp.accounting_account_mappings(account_id uuid,mapping_key text);
insert into erp.chart_accounts values('${u}',true,true,'ASSET');insert into erp.cash_accounts values('${u}','${u}',true,'CASH','Cash');
create table erp.sales_returns(id uuid,status text);create table erp.sales_return_items(return_id uuid,sale_stock_allocation_id uuid,qty_pcs int);
create table erp.sale_stock_allocations(id uuid,lot_id uuid);
insert into erp.sales_returns values('${u}','POSTED');insert into erp.sales_return_items values('${u}','${u}',2);
insert into erp.sale_stock_allocations values('${u}','${u}');`);
const projection=await read('02_initial_projection.sql'),cash=cut(projection,'create function cp7_credit.cash_account_facts_v1(','end $$;');await db.exec(cash);
const callback=await read('03_native_initial_callbacks.sql'),cashGuard=cut(callback,'if w.cash_account_snapshot is not null','end if;');
const shape=cut(await read('01_coordinator_facts.sql'),'credit_account_snapshot jsonb',"cash_account_snapshot jsonb check(cash_account_snapshot is null or jsonb_typeof(cash_account_snapshot)='object'),").replace(/,$/,'');
await db.exec('create table cp7_credit.optional_shape('+shape+')');
for(const old of[true,false]){
 const tag=old?'FIRST_RED':'FIXED',c=old?await before('03_native_initial_callbacks.sql'):callback;
 const expr=c.match(/cash_account_snapshot=([^\n]+)\n  where backend_pid=s\.backend_pid/)[1];
 await check(tag+'_ABSENT_CASH',`do $$declare b jsonb:='{"cash_account_snapshot":null}';w record;begin select ${expr}cash_account_snapshot,'{"cash_account_id":null}'::jsonb settlement into w;${cashGuard}end $$;`,old?'P0002':null);
 await check(tag+'_SELECTED_CASH_PRESERVED',`do $$declare b jsonb;w record;begin b:=jsonb_build_object('cash_account_snapshot',cp7_credit.cash_account_facts_v1('${u}'));select ${expr}cash_account_snapshot,'{"cash_account_id":"${u}"}'::jsonb settlement into w;${cashGuard}if w.cash_account_snapshot is null then raise exception 'selected account lost';end if;end $$;`);
 const store=old?await before('04_register_and_materialize.sql'):await read('04_register_and_materialize.sql');
 const s=store.indexOf("for x in select jsonb_build_object('component',z->'component'");assert(s>=0);const q=store.slice(s,store.indexOf(' loop',s)+5);
 await check(tag+'_GROUPED_NUMERIC_COMPONENTS',`do $$declare x jsonb;seen int[]:='{}';parts jsonb:='[{"component":{},"component_id":"a","component_ordinal":1},{"component":{},"component_id":"a","component_ordinal":1},{"component":{},"component_id":"b","component_ordinal":2},{"component":{},"component_id":"c","component_ordinal":10}]';begin ${q} seen:=seen||(x->>'ord')::int;end loop;if seen<>array[1,2,10]then raise exception 'wrong component order or duplicate';end if;end $$;`,old?'42803':null);
 const hpp=old?await before('02_initial_projection.sql'):projection;
 let start=hpp.indexOf(old?'if owned<0':'if (x->>\'qty_pcs\')::numeric>a.qty_pcs');assert(start>=0);
 const end=hpp.indexOf("group_amount:=(x->>'qty_pcs')",start);assert(end>start);const guards=hpp.slice(start,end);
 const setup=`declare a record;x jsonb:='{"qty_pcs":"1"}';p_legacy jsonb:='{"items":[{"allocation_id":"${u}","qty_pcs":"1"}]}';owned numeric:=6;sold numeric:=4;returned numeric:=2;begin select '${u}'::uuid id,'${u}'::uuid lot_id,2 qty_pcs into a;`;
 await check(tag+'_OVER_ALLOCATED_REFUSAL',`do $$${setup}${guards}end $$;`,old?'CP7_CREDIT_RETURN_QTY_SOURCE_INVALID':'AH_RETURN_EXCEEDS_ORIGINAL_ALLOCATION');
 await check(tag+'_VALID_QTY_STILL_ALLOWED',`update erp.sales_return_items set qty_pcs=0;do $$${setup}${guards}end $$;`);
}
await check('SQL_NULL_OPTIONAL_SHAPE_ALLOWED','insert into cp7_credit.optional_shape values(null,null)');
await check('JSON_NULL_OPTIONAL_SHAPE_REFUSED',"insert into cp7_credit.optional_shape values(null,'null'::jsonb)",'23514');
await check('ARRAY_OPTIONAL_SHAPE_REFUSED',"insert into cp7_credit.optional_shape values(null,'[]'::jsonb)",'23514');
await check('OBJECT_OPTIONAL_SHAPE_ALLOWED',"insert into cp7_credit.optional_shape values('{}','{}')");
await check('SELECTED_CASH_DELETED_STILL_REFUSES',`delete from erp.cash_accounts;do $$declare b jsonb:='{}';w record;begin select '{}'::jsonb cash_account_snapshot,'{"cash_account_id":"${u}"}'::jsonb settlement into w;${cashGuard}end $$;`,'P0002');
await fs.writeFile(here+'/RESULT.json',JSON.stringify({classification:'ACTUAL_SQL_FRAGMENTS_NOT_ERP_NATIVE',status:'PASS',count:cases.length,cases},null,2)+'\n');console.log(JSON.stringify({status:'PASS',count:cases.length}));
}catch(e){await fs.writeFile(here+'/FIRST_FAILURE.json',JSON.stringify({error:e.message,code:e.code,cases},null,2)+'\n');console.error(e);process.exitCode=1}finally{await db.close()}
