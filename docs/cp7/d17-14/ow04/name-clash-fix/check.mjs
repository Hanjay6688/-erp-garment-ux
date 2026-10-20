// Isolated execution of exact SELECT/PERFORM fragments, never Native authority.
import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
const {PGlite}=await import(process.env.PGLITE_MODULE||'@electric-sql/pglite');
const root=process.env.ERP_REPO||process.cwd();
const here=path.dirname(fileURLToPath(import.meta.url));
const dir=root+'/scripts/cp7_customer_credit/coordinator/';
const cases=[],db=new PGlite();
const one='00000000-0000-0000-0000-000000000001',two='00000000-0000-0000-0000-000000000002';
function cut(s,start,end){const a=s.indexOf(start);assert(a>=0,start);const b=s.indexOf(end,a);assert(b>a,end);return s.slice(a,b+end.length);}
async function run(name,q,red=false){try{await db.exec('begin');await db.exec(q);await db.exec('rollback');assert(!red,'old fragment unexpectedly succeeded');cases.push({name,status:'PASS'});}catch(e){await db.exec('rollback');if(!red)throw e;assert(['42702','55000'].includes(e.code),JSON.stringify({name,message:e.message,code:e.code}));cases.push({name,status:'PASS',first_failure:{message:e.message,sqlstate:e.code}});}}
try{
await db.exec(`create schema erp;create schema cp7_credit;
create table erp.sales_payments(sale_id uuid,status text,amount numeric);
insert into erp.sales_payments values('${one}','POSTED',900),('${one}','REVERSED',888),('${two}','POSTED',1000);
create table erp.fg_inventory_balances(product_id uuid,location_id uuid,quality_grade text);
create table erp.sale_stock_allocations(id uuid,sale_item_id uuid);
create table erp.sales_items(id uuid,product_id uuid);
insert into erp.fg_inventory_balances values('${one}','${two}','GRADE_A');
insert into erp.sale_stock_allocations values('${one}','${two}');insert into erp.sales_items values('${two}','${one}');
create table cp7_credit.financial_materialization_objects(object_kind text,object_id uuid);
insert into cp7_credit.financial_materialization_objects values('FAMILY','${one}');
create table cp7_credit.consumption_events(id uuid,cohort_id uuid,amount numeric,economic_date date,transaction_date date,source_sha256 text);
insert into cp7_credit.consumption_events values('${one}','${one}',200,'2026-10-18','2026-10-20','exact-source');
create function cp7_credit.cent_text(numeric)returns text language sql immutable as 'select to_char($1,''FM999999990.00'')';
create table cp7_credit.financial_materializations(id uuid);insert into cp7_credit.financial_materializations values('${one}');
create table cp7_credit.recognition_components(id uuid,plan_id uuid);insert into cp7_credit.recognition_components values('${one}','${two}');`);
for(const old of [true,false]){
 const tag=old?'FIRST_RED':'QUALIFIED';
 const get=async n=>old?execFileSync('git',['show','de3d5c6d23e788481f4d30957cf46615add5f3d6:scripts/cp7_customer_credit/coordinator/'+n],{cwd:root,encoding:'utf8'}):fs.readFile(dir+n,'utf8');
 const projection=await get('02_initial_projection.sql');
 const payment=projection.match(/select coalesce\(sum\((?:pay\.)?amount\),0\)into paid from erp\.sales_payments[^;]+;/)[0];
 await run(tag+'_PAYMENT_SUM',`do $$declare amount numeric;paid numeric;h record;begin select '${one}'::uuid id into h;${payment}if paid<>900 then raise exception 'wrong selected payment sum';end if;end $$;`,old);
 const hpp=cut(projection,'create function cp7_credit.initial_hpp_projection_v1(','end $$;');
 const group=old?'value':'group_amount';
 const loop=hpp.match(/for x in select value from jsonb_array_elements\(p_legacy->'items'\)loop/)[0];
 await run(tag+'_JSON_VALUE_COLUMN',`do $$declare x jsonb;${group} numeric;p_legacy jsonb:='{"items":[{"qty_pcs":"2"}]}';n int:=0;begin ${loop} n:=n+(x->>'qty_pcs')::int;end loop;if n<>2 then raise exception 'wrong JSON value';end if;end $$;`,old);
 const lock=cut(hpp,'perform 1 from erp.fg_inventory_balances ','for update;');
 await run(tag+'_HPP_BALANCE_LOCK',`do $$declare x jsonb;b record;p_legacy jsonb:='{"items":[{"allocation_id":"${one}","location_id":"${two}","quality_grade":"GRADE_A"}]}';begin ${lock}end $$;`,old);
 const allMaterial=await get('04_register_and_materialize.sql');
 const material=cut(allMaterial,'create function cp7_credit.materialize_initial_objects_v1(','end $$;');
 const selectNew=cut(material,'select coalesce(jsonb_agg('+(old?'x order by x':'obj order by obj'),"'object_kind'"+'and o.object_id=');
 // The terminator above sits before the final UUID expression; use the exact
 // next semicolon to retain the whole original SQL statement.
 const pos=material.indexOf(selectNew);const statement=material.slice(pos,material.indexOf(';',pos)+1);
 await run(tag+'_MATERIALIZED_OBJECT_FILTER',`do $$declare x jsonb;objects jsonb:='[{"object_kind":"FAMILY","object_id":"${one}"},{"object_kind":"MEMBER","object_id":"${two}"}]';new_objects jsonb;begin ${statement}if jsonb_array_length(new_objects)<>1 or new_objects->0->>'object_kind'<>'MEMBER'then raise exception 'wrong object filter';end if;end $$;`,old);
 const allProfile=await get('05_factual_profile.sql');
 const profile=cut(allProfile,'create function cp7_credit.assert_current_source_plan_profile(','end $$;');
 const start=profile.indexOf("select coalesce(jsonb_agg(jsonb_build_object('id',"+(old?'ce.id':'consumer.id')+'::text');
 assert(start>=0);const consumer=profile.slice(start,profile.indexOf(';',start)+1);
 await run(tag+'_CONSUMER_ROWS',`do $$declare ce cp7_credit.consumption_events;ch record;c_events jsonb;begin select '${one}'::uuid id into ch;${consumer}if jsonb_array_length(c_events)<>1 or c_events->0->>'amount'<>'200.00'then raise exception 'wrong consumer';end if;end $$;`,old);
 const provenance=cut(allProfile,'create function cp7_credit.assert_financial_materialization_provenance(','end $$;');
 const selected=provenance.match(/select (?:fm\.\*)?\*?into strict f from cp7_credit\.financial_materializations[^;]+;/)[0];
 await run(tag+'_PROVENANCE_MARKER',`do $$declare ${old?'id':'marker_id'} uuid:='${one}';f cp7_credit.financial_materializations;begin ${selected}if f.id<>'${one}'::uuid then raise exception 'wrong marker';end if;end $$;`,old);
 const closure=await get('06_finish_and_closed_routes.sql');
 const part=closure.match(/select plan_id into plan from cp7_credit\.recognition_components where id=\(row->>'component_id'\)::uuid;/)[0];
 await run(tag+'_DEFERRED_CLOSURE_LOOKUP',`do $$declare ${old?'id':'operation'} uuid;plan uuid;row jsonb:='{"component_id":"${one}"}';begin ${part}if plan<>'${two}'::uuid then raise exception 'wrong closure parent';end if;end $$;`,old);
}
const result={classification:'ACTUAL_SQL_FRAGMENT_NAME_RESOLUTION_NOT_ERP_NATIVE',status:'PASS',count:cases.length,cases,full_erp_native:false};
await fs.writeFile(here+'/RESULT.json',JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify({status:'PASS',count:cases.length}));
}catch(e){await fs.writeFile(here+'/FIRST_FAILURE.json',JSON.stringify({error:e.message,code:e.code,cases},null,2)+'\n');console.error(e);process.exitCode=1;}finally{await db.close();}
