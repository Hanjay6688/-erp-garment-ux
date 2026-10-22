// Actual four product bodies and kernels, controlled ERP/history/identity.
// This proves adapter arithmetic and closed writes, not Native/Auth/restore.
import {readFile,writeFile,mkdir,access} from 'node:fs/promises'
import {createHash,randomUUID} from 'node:crypto'
import {execFileSync} from 'node:child_process'
import assert from 'node:assert/strict'
const {PGlite}=await import(process.env.CP7_PGLITE_MODULE??'@electric-sql/pglite')
const db=new PGlite(),dir='scripts/cp7_target_policy_stage/sql/'
const read=path=>readFile(path,'utf8'),block=(s,name)=>{const start=s.search(new RegExp('create(?: or replace)? function '+name.replaceAll('.','\\.')+'\\('));assert.ok(start>=0,name);return s.slice(start,s.indexOf('$$;',s.indexOf('as $$',start))+3)}
await db.exec(`create role cp7_capture;create role cp7_policy;create role anon;create role authenticated;create role service_role;
create schema erp;create schema auth;create schema cp7_identity;create schema cp7_planning;create schema extensions;create schema cp7_analysis_stage;create schema cp7_baseline_native;
create function extensions.digest(bytea,text)returns bytea language sql immutable as $$select sha256($1)$$;
create function auth.uid()returns uuid language sql stable as $$select 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa'::uuid$$;
create function cp7_identity.access_now(boolean)returns jsonb language sql stable as $$select '{"actor":"aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"}'::jsonb$$;
create function cp7_identity.immutable_row()returns trigger language plpgsql as $$begin raise exception 'LOCAL_APPEND_ONLY';end$$;
create function cp7_planning.history_build(jsonb,jsonb)returns jsonb language sql immutable as $$select $1->'history_adapter'$$;
create table erp.products(id uuid,identity_root_id uuid,size_id uuid,model_id uuid,sku text,product_name text,is_active boolean,effective_from timestamptz,effective_to timestamptz);
create table erp.sizes(id uuid,size_code text);
create table erp.fg_stock_movements(id uuid,product_id uuid,qty_signed numeric,physical_at timestamptz,system_created_at timestamptz,quality_grade text,movement_type text,reversal_of_id uuid);
create table erp.production_orders(id uuid,model_id uuid,status text);
create table erp.cutting_groups(id uuid,po_id uuid,cut_at timestamptz,material_issue_posted boolean);
create table erp.fg_lots(id uuid,cutting_group_id uuid,qc_item_id uuid,produced_at timestamptz,lot_origin text);
create table erp.qc_inspection_items(id uuid,inspection_id uuid);
create table erp.qc_inspections(id uuid,status text);`)
for(const file of['wip/bootstrap.sql','demand/bootstrap.sql','demand/estimate.sql'])await db.exec(await read('scripts/cp7-src/'+file))
await db.exec(await read('scripts/cp7_production_stage/sql/cp7_baseline__target.sql'))
await db.exec(await read('scripts/cp7-src/planning/profile.sql'))
const stock=await read('scripts/cp7-src/stock-formula/formula.sql')
await db.exec(stock.slice(stock.indexOf('create schema cp7_stock_formula'),stock.indexOf('create function cp7_stock_formula.z(')))
for(const fn of['cp7_stock_formula.z','cp7_stock_formula.current_settings','cp7_stock_formula.open_groups'])await db.exec(block(stock,fn))
await db.exec(`create function cp7_stock_formula.model_wip(uuid,timestamptz)returns jsonb language sql as $$select '{"status":"COMPLETE","reason":null,"groups":0,"sizes":{}}'::jsonb$$;
create function cp7_stock_formula.compute_materials(timestamptz)returns jsonb language sql as $$select '{"materials":0,"materials_at_or_below":0}'::jsonb$$;`)
const files=['cp7_profile__apply.sql','cp7_baseline_native__build.sql','cp7_analysis_stage__baseline_rows.sql','cp7_stock_formula__compute.sql']
for(const file of files)await db.exec(await read(dir+file))
// Same actual functions under old names for complete legacy-result equality.
for(const [file,fn]of[['cp7_baseline_native__build.before.sql','cp7_baseline_native.build'],['cp7_analysis_stage__baseline_rows.before.sql','cp7_analysis_stage.baseline_rows']]){
 const sql=(await read(dir+file)).replace('function '+fn+'(','function '+fn+'_before(');await db.exec(sql)
}
const root='11111111-1111-4111-8111-111111111111',size='22222222-2222-4222-8222-222222222222',model='55555555-5555-4555-8555-555555555555',key=root+':'+size
const {at,today,from_date,through_date}= (await db.query(`select to_char(clock_timestamp()+interval'1 hour','YYYY-MM-DD"T"HH24:MI:SS.US"Z"')at,
 ((clock_timestamp()+interval'1 hour')at time zone'Asia/Jakarta')::date::text today,
 (((clock_timestamp()+interval'1 hour')at time zone'Asia/Jakarta')::date-14)::text from_date,
 (((clock_timestamp()+interval'1 hour')at time zone'Asia/Jakarta')::date-1)::text through_date`)).rows[0]
await db.query(`insert into erp.products values($1,$1,$2,$3,'LOCAL-STAT','Controlled statistical fixture',true,'2020-01-01',null)`,[root,size,model])
await db.query("insert into erp.sizes values($1,'M')",[size])
await db.query(`insert into cp7_stock_formula.settings(revision,service_level,window_days,reason,actor,request_id,request_hash)values(1,0.90,14,'LOCAL_SELECTED_SETTING_FIXTURE',$1,$2,$3)`,[root,randomUUID(),'a'.repeat(64)])
await db.query(`insert into erp.fg_stock_movements values(gen_random_uuid(),$1,1000,($2::date-1)::timestamp at time zone'Asia/Jakarta','2020-01-01','GRADE_A','OPENING',null)`,[root,from_date])
for(let i=0;i<14;i++)if(i%2===1)await db.query(`insert into erp.fg_stock_movements values(gen_random_uuid(),$1,-10,($2::date+$3::integer)::timestamp at time zone'Asia/Jakarta'+interval'12 hours','2020-01-01','GRADE_A','SALE',null)`,[root,from_date,i])
const legacy={mean_mode:'OWN_AVAILABLE_HISTORY',daily_pcs:null,minimum_available_days:'1',lead_days:'3',review_days:'7',buffer_days:'2'}
const statistical={...legacy,buffer_days:null,buffer_mode:'STATISTICAL',service_level:'0.95'}
const source=async config=>{
 const days=Array.from({length:14},(_,i)=>({date:new Date(Date.parse(from_date+'T00:00:00Z')+i*86400000).toISOString().slice(0,10),state:'AVAILABLE',gross_observed_pcs:i%2?'10':'0',returned_pcs:'0',training_pcs:i%2?'10':'0'}))
 const refs=[{kind:'CONTROLLED_SOURCE',id:root,revision:'1'}]
 return {captured_at:at,facts:{products:[]},profiles:[{root_id:root,size_id:size,product_version_id:root,sku:'LOCAL-STAT',product_name:'Controlled statistical fixture',profile_id:model,revision:'1',quality:'SELECTED_ASSUMPTION',config}],production_policies:{rows:[]},
  history_adapter:{history:{rows:[{target_key:key,size_id:size,available_days:14,days,refs}]},current_stock:[{target_key:key,native_available_pcs:'930',sku:'LOCAL-STAT',product_name:'Controlled statistical fixture'}]}}
}
const query={from_date,through_date,group_mode:'AS_SOLD'},hash='b'.repeat(64)
const direct=async(c,name='build')=>(await db.query('select cp7_baseline_native.'+name+'($1::jsonb,$2::jsonb)v',[JSON.stringify(c),JSON.stringify(query)])).rows[0].v
const staged=async(c,name='baseline_rows')=>(await db.query('select cp7_analysis_stage.'+name+'($1::jsonb,$2::jsonb,$3::jsonb,$4)v',[JSON.stringify(c),JSON.stringify(c.history_adapter.history.rows),JSON.stringify(c.history_adapter.current_stock),hash])).rows[0].v
let revision=0
const payload=config=>({root_id:root,product_version_id:root,expected_revision:String(revision),config,reason:'Controlled owner choice, not a production policy'})
const save=async(config,id=randomUUID(),p=payload(config))=>{const r=(await db.query('select cp7_profile.apply($1::jsonb,$2::uuid)v',[JSON.stringify(p),id])).rows[0].v;revision=Number(r.revision);return r}
const results=[];const test=async(id,fn)=>{try{results.push({id,status:'PASS',observed:await fn()})}catch(e){results.push({id,status:'FAIL',error:String(e.stack).slice(0,1700)})}}
await test('OW10_STAT_LEGACY_FULL_JSON_UNCHANGED',async()=>{
 const c=await source(legacy);assert.deepEqual(await direct(c),await direct(c,'build_before'));assert.deepEqual(await staged(c),await staged(c,'baseline_rows_before'))
 await save(legacy);return{direct_and_staged_legacy_full_JSON_equal:true,old_payload_saved_without_extra_keys:true}
})
await test('OW10_STAT_DIRECT_STAGED_AND_INDEPENDENT_ORACLE',async()=>{
 const c=await source(statistical),d=await direct(c),r=d.rows[0].target,s=(await staged(c))[0].target
 const strip=t=>{const x=structuredClone(t);delete x.inputs.snapshot_id;return x};assert.deepEqual(strip(r),strip(s))
 const oracle=JSON.parse(execFileSync('python',['-c',`from decimal import Decimal,localcontext,ROUND_CEILING
import json
with localcontext()as ctx:
 ctx.prec=80;y=[Decimal(i%2*10)for i in range(14)];m=sum(y)/len(y);sd=(sum((v-m)**2 for v in y)/13).sqrt();z=Decimal('1.6449')
 print(json.dumps({str(h):str((m*h+z*sd*Decimal(h).sqrt()).to_integral_value(rounding=ROUND_CEILING))for h in [3,10]}))`],{encoding:'utf8'}))
 assert.equal(r.reorder_point_pcs,oracle['3']);assert.equal(r.target_pcs,oracle['10']);assert.equal(r.inputs.buffer_days,null);assert.equal(r.inputs.counted_days,'14');assert.equal(r.inputs.daily_total_pcs,'70')
 assert.equal(d.contract_version,'cp7.native-baseline.v2');assert.equal(d.target_basis,'UNIFIED_TARGET_WITH_SELECTED_PROFILE_ASSUMPTIONS')
 await mkdir('tests/fixtures',{recursive:true});await writeFile('tests/fixtures/targetStatisticalAdapter.json',JSON.stringify({target:r,query,days:c.history_adapter.history.rows[0].days,oracle,classification:'ACTUAL_SQL_WITH_CONTROLLED_HISTORY_NOT_NATIVE'},null,2)+'\n')
 return{direct_staged_target_equal:true,independent_80_digit_decimal_oracle:oracle,one_variation_buffer:true}
})
await test('OW10_STAT_INCOMPLETE_HISTORY_NOT_ZERO',async()=>{
 const c=await source(statistical);c.history_adapter.history.rows[0].available_days=12
 for(const day of c.history_adapter.history.rows[0].days.slice(0,2)){day.state='UNKNOWN';day.training_pcs=null}
 const d=await direct(c),s=await staged(c);for(const r of[d.rows[0].target,s[0].target]){assert.equal(r.status,'UNKNOWN');assert.equal(r.target_pcs,null);assert.equal(r.reorder_point_pcs,null);assert.equal(r.inputs.counted_days,'12')}
 return{missing_available_days_refused_by_same_kernel:true,unknown_target_not_zero:true}
})
await test('OW10_STAT_PROFILE_CLOSED_MODES_REPLAY_AND_REFUSALS',async()=>{
 const id=randomUUID(),p=payload(statistical),saved=await save(statistical,id,p)
 assert.deepEqual(await save(statistical,id,p),saved)
 await assert.rejects(()=>save(legacy,id,{...p,config:legacy}),/CP7_PROFILE_REQUEST_CHANGED/)
 let rejected=0
 for(const config of[{...statistical,service_level:'0.97'},{...statistical,buffer_days:'2'},{...statistical,buffer_mode:'OTHER'},{...statistical,mean_mode:'SELECTED_MANUAL',daily_pcs:'5'},{...legacy,buffer_mode:'DAYS'},{...legacy,buffer_mode:'DAYS',service_level:'0.95'},{...legacy,buffer_mode:'DAYS',service_level:null,buffer_days:null}]){
  await assert.rejects(()=>save(config),/CP7_PROFILE_(STATISTICAL_BUFFER|BUFFER_MODE|DOUBLE_BUFFER|DAYS_BUFFER)/);rejected++
 }
 return{same_UUID_exact_replay:true,changed_body_refused:true,closed_and_double_buffer_refusals:rejected}
})
await test('OW10_STAT_ROP_EFFECTIVE_PROFILE_SAME_KERNEL',async()=>{
 await db.query('select cp7_stock_formula.compute($1::timestamptz,interval\'1 second\')',[at])
 const fg=(await db.query('select to_jsonb(e)v from cp7_stock_formula.evaluations e where root_id=$1',[root])).rows[0].v
 const d=await direct(await source(statistical));assert.equal(String(fg.formula_point),d.rows[0].target.reorder_point_pcs);assert.equal(fg.z,1.6449)
 assert.equal(fg.buffer_mode,'STATISTICAL');assert.equal(fg.buffer_days,null);assert.equal(fg.counted_days,14)
 await save({...statistical,minimum_available_days:'20'});await db.query('select cp7_stock_formula.compute($1::timestamptz,interval\'1 second\')',[at]);
 const limited=(await db.query('select to_jsonb(e)v from cp7_stock_formula.evaluations e where root_id=$1',[root])).rows[0].v;assert.equal(limited.point,null);assert.equal(limited.reason,'PROFILE_MINIMUM_NOT_MET');
 await writeFile('tests/fixtures/fgStatisticalMinimum.json',JSON.stringify({...limited,wip_read_at:null},null,2)+'\n');
 await save({...legacy,buffer_mode:'DAYS',service_level:null});await db.query('select cp7_stock_formula.compute($1::timestamptz,interval\'1 second\')',[at])
 const day=(await db.query('select to_jsonb(e)v from cp7_stock_formula.evaluations e where root_id=$1',[root])).rows[0].v
 assert.equal(day.formula_point,25);assert.equal(day.buffer_mode,'DAYS')
 return{profile95_over_general90:true,ROP_matches_same_kernel_L_horizon:true,DAYS_remains_one_buffer:true,allocated_WIP_not_proven:true}
})
const report={classification:'LOCAL_ACTUAL_FOUR_PRODUCT_BODIES_WITH_CONTROLLED_ERP_HISTORY_IDENTITY_NOT_NATIVE',status:results.every(r=>r.status==='PASS')?'PASS':'FAIL',
 sources:Object.fromEntries(await Promise.all(files.map(async file=>[file,createHash('sha256').update(await read(dir+file)).digest('hex')]))),cases:results,OW10_complete:false,full_A_chain_qualified:false,production_go:false}
await mkdir('docs/cp7/d17-14/ow10',{recursive:true});const out='docs/cp7/d17-14/ow10/statistical-local.json'
await writeFile(out,JSON.stringify(report,null,2)+'\n');if(report.status!=='PASS'){const first=out.replace('.json','-first-failure.json');try{await access(first)}catch{await writeFile(first,JSON.stringify(report,null,2)+'\n')}}
console.log(JSON.stringify(report,null,2));await db.close();if(report.status!=='PASS')process.exitCode=1
