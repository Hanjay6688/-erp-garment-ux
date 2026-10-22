// Actual OW14b SQL on a controlled ERP/identity adapter, not Native qualification.
import {readFile,writeFile,mkdir} from 'node:fs/promises'
import {createHash} from 'node:crypto'
import assert from 'node:assert/strict'
const {PGlite}=await import(process.env.CP7_PGLITE_MODULE??'@electric-sql/pglite')
const db=new PGlite(),frozen=await readFile('scripts/cp7-src/stock-formula/materials.sql','utf8'),alerts=await readFile('scripts/cp7-src/alerts/alerts.sql','utf8')
const stageNames=['cp7_stock_formula.compute_materials','cp7_stock_formula.material_source','cp7_stock_formula.material_workspace','cp7_stock_formula.save_material','cp7_alert_native.fabric_kind_source','cp7_alert_native.item_line']
const staged=Object.fromEntries(await Promise.all(stageNames.map(async name=>[name,(await readFile('scripts/cp7_production_stage/sql/'+name.replace('.','__')+'.sql','utf8')).replace('create or replace function','create function')])))
const source=frozen+'\n'+Object.values(staged).join('\n')
const block=(sql,name)=>{const start=sql.lastIndexOf('create function '+name+'(');assert.ok(start>=0,name);const end=sql.indexOf('$$;',sql.indexOf('as $$',start)+5);assert.ok(end>start,name);return sql.slice(start,end+3)}
await db.exec([
 "create role cp7_capture nologin;create role anon nologin;create role authenticated nologin;create role service_role nologin;",
 "create schema erp;create schema auth;create schema cp7_stock_formula authorization cp7_capture;create schema cp7_alert_native authorization cp7_capture;",
 "create table erp.materials(id uuid primary key,material_type text,material_sku text,material_name text,unit_code text,is_active boolean);",
 "create table erp.locations(id uuid primary key,location_type text,is_active boolean);create table erp.bc_accessory_zones_v1(location_id uuid);",
 "create table erp.fabric_master_profiles(material_id uuid primary key,minimum_stock_qty numeric);",
 "create table erp.material_stock_movements(id uuid,material_id uuid,roll_id uuid,location_id uuid,qty_signed numeric,physical_at timestamptz,system_created_at timestamptz,movement_type text,reversal_of_id uuid,source_type text);",
 "create table erp.bb_purchase_commitment_lines_v1(id uuid,material_id uuid);",
 "create function erp.bb_commitment_line_remaining_v1(uuid,uuid)returns numeric language sql as $$select 0::numeric$$;",
 "create function auth.uid()returns uuid language sql as $$select '11111111-1111-4111-8111-111111111111'::uuid$$;",
 "create function auth.jwt()returns jsonb language sql as $$select jsonb_build_object('role','authenticated')$$;",
 "create function erp.get_my_access_v1()returns jsonb language sql as $$select jsonb_build_object('allowed',coalesce(current_setting('ow14.allow',true),'yes')<>'no','profile',jsonb_build_object('role_code','OWNER'))$$;",
 "create function erp.has_permission(text)returns boolean language sql as $$select coalesce(current_setting('ow14.allow',true),'yes')<>'no'$$;",
 "create function cp7_stock_formula.current_settings()returns jsonb language sql as $$select jsonb_build_object('service_level','0.95','window_days',30,'revision',0)$$;",
 "create function cp7_stock_formula.z(numeric)returns numeric language sql as $$select 1.6449::numeric$$;",
 "create function cp7_stock_formula.append_only()returns trigger language plpgsql as $$begin raise exception 'CP7_FORMULA_APPEND_ONLY';end$$;",
].join('\n'))
await db.exec(frozen.slice(frozen.indexOf('create table cp7_stock_formula.material_settings('),frozen.indexOf('-- Every active fabric')))
await db.exec(await readFile('scripts/cp7_production_stage/sql/upgrade.sql','utf8'))
await db.exec(block(source,'cp7_stock_formula.compute_materials'))
// Only this boundary is an adapter: the local fixture contains no FG module.
await db.exec("create function cp7_stock_formula.compute(timestamptz,interval)returns jsonb language sql as $$select cp7_stock_formula.compute_materials($1)$$;")
for(const name of['ensure_computed','material_access_now','save_material','material_alert_row','material_source'])await db.exec(block(source,'cp7_stock_formula.'+name))
for(const name of['num','rp','tgl','item_line','fabric_source','fabric_kind_source'])await db.exec(block(alerts+'\n'+Object.values(staged).join('\n'),'cp7_alert_native.'+name))
await db.exec([
 "insert into erp.locations values('22222222-2222-4222-8222-222222222222','RAW_MATERIAL_WAREHOUSE',true);",
 "insert into erp.materials values('33333333-3333-4333-8333-333333333333','FABRIC','LOCAL-RULE','Controlled fabric','YD',true);",
 "insert into erp.fabric_master_profiles values('33333333-3333-4333-8333-333333333333',800);",
 "insert into erp.material_stock_movements values(gen_random_uuid(),'33333333-3333-4333-8333-333333333333',null,'22222222-2222-4222-8222-222222222222',1000,now()-interval'40 days',now()-interval'40 days','OPENING',null,'LOCAL_ADAPTER');",
 "insert into erp.material_stock_movements select gen_random_uuid(),'33333333-3333-4333-8333-333333333333',null,'22222222-2222-4222-8222-222222222222',-10,((now()at time zone'Asia/Jakarta')::date-g+time'10:00')at time zone'Asia/Jakarta',now()-interval'1 hour','INTERNAL_USE',null,'LOCAL_ADAPTER'from generate_series(1,30)g;",
].join('\n'))
const value=async(sql,args=[])=>(await db.query(sql,args)).rows[0].v
const evaluation=()=>value('select to_jsonb(e)v from cp7_stock_formula.material_evaluations e')
const save=(revision,choice,expected='800',id=crypto.randomUUID(),lead='6')=>value('select cp7_stock_formula.save_material($1::jsonb,$2::uuid)v',[JSON.stringify({material_id:'33333333-3333-4333-8333-333333333333',expected_revision:revision,lead_days:lead,manual_point:null,reason:'Explicit controlled-adapter choice',...(choice?{fabric_rule:choice,expected_legacy_minimum_qty:expected}:{})}),id])
const combined=()=>value('select cp7_alert_native.fabric_kind_source()v')
const results=[];async function test(id,fn){try{results.push({id,status:'PASS',observed:await fn()})}catch(e){results.push({id,status:'FAIL',error:String(e.stack).slice(0,1800)})}}
await test('OW14B_PREVIOUS_RULE_RETAINED_UNTIL_EXPLICIT_CHOICE',async()=>{
 await save(0);const e=await evaluation();assert.equal(e.fabric_rule,null);assert.equal(Number(e.point),800);assert.equal(Number(e.formula_point),60);assert.equal(Number(e.legacy_minimum_qty),800)
 const r=await combined();assert.equal(r.rows.length,1);assert.equal(r.rows[0].detail.minimum_qty,'800');return{free:'700',legacy_active:'800',inactive_formula:'60',one_reminder:true}
})
await test('OW14B_FORMULA_CHOICE_DOES_NOT_RESURRECT_LEGACY_ALERT',async()=>{
 await save(1,'FORMULA');const e=await evaluation();assert.equal(e.fabric_rule,'FORMULA');assert.equal(Number(e.point),60);assert.equal(e.manual_point,null);assert.equal(Number(e.legacy_minimum_qty),800)
 const r=await combined();assert.equal(r.rows.length,0);assert.equal(r.states['33333333-3333-4333-8333-333333333333'],'ABOVE_REORDER_POINT');return{one_active_formula:'60',legacy_reference:'800',old_rule_not_active:true}
})
await test('OW14B_REFERENCE_CHANGE_REFUSES_ATOMICALLY',async()=>{
 await db.exec('update erp.fabric_master_profiles set minimum_stock_qty=900')
 await assert.rejects(()=>save(2,'LEGACY_MINIMUM'),/CP7_FORMULA_FABRIC_REFERENCE_CHANGED/)
 assert.equal(await value('select count(*)::integer v from cp7_stock_formula.material_settings'),2);return{no_revision_appended:true}
})
await test('OW14B_SELECTED_LEGACY_IS_PINNED_AND_REPLAY_IS_EXACT',async()=>{
 const id=crypto.randomUUID();const first=await save(2,'LEGACY_MINIMUM','900',id)
 assert.equal(first.revision,3);assert.equal(Number((await evaluation()).point),900)
 await db.exec('update erp.fabric_master_profiles set minimum_stock_qty=1000')
 const replay=await save(2,'LEGACY_MINIMUM','900',id);assert.equal(replay.replay,true);assert.equal(replay.revision,3)
 await assert.rejects(()=>save(2,'FORMULA','900',id),/CP7_FORMULA_REQUEST_REUSED/)
 await save(3,undefined);const e=await evaluation();assert.equal(e.fabric_rule,'LEGACY_MINIMUM');assert.equal(Number(e.point),900);assert.equal(Number(e.legacy_minimum_qty),1000)
 const r=await combined();assert.equal(r.rows.length,1);assert.equal(r.rows[0].detail.reorder_point_qty,'900.0000')
 const item={...r.rows[0],kind:'FABRIC_BELOW_MINIMUM'}
 const line=await value('select cp7_alert_native.item_line($1::jsonb,$2::text)v',[JSON.stringify(item),'AMOUNT'])
 assert.ok(line.includes('minimum lama yang dipilih 900'),line)
 assert.ok(!line.includes('minimum rumus')&&!line.includes('dipesan'),line)
 const long={...item,detail:{...item.detail,name:'SYNTHETIC_LABEL_ONLY '.repeat(40)}}
 const bounded=await value('select cp7_alert_native.item_line($1::jsonb,$2::text)v',[JSON.stringify(long),'AMOUNT'])
 assert.ok(bounded.length<=256&&bounded.endsWith('minimum lama yang dipilih 900 YD'),bounded)
 return{chosen_legacy:'900',current_reference:'1000',older_client_preserves_choice:true,exact_replay:true,one_reminder:true}
})
await test('OW14B_ZERO_REFERENCE_IS_EXPLICITLY_DISABLED_NOT_UNKNOWN',async()=>{
 await db.exec('update erp.fabric_master_profiles set minimum_stock_qty=0');await save(4,'LEGACY_MINIMUM','0')
 const e=await evaluation();assert.equal(e.fabric_rule,'LEGACY_MINIMUM');assert.equal(Number(e.point),0);assert.equal(e.state,'NO_POINT');assert.equal((await combined()).rows.length,0)
 await save(5,'FORMULA','0');assert.equal(Number((await evaluation()).point),60);return{explicit_zero_legacy:'NO_POINT',formula_reenabled_only_by_choice:true}
})
await test('OW14B_CURRENT_ACCESS_AND_APPEND_ONLY',async()=>{
 await db.exec("set ow14.allow='no'");await assert.rejects(()=>save(6,'LEGACY_MINIMUM','0'),/CP7_FORMULA_ACCESS_DENIED/);await db.exec("set ow14.allow='yes'")
 assert.equal(await value('select count(*)::integer v from cp7_stock_formula.material_settings'),6)
 await assert.rejects(()=>db.exec('delete from cp7_stock_formula.material_settings'),/CP7_FORMULA_APPEND_ONLY/)
 return{current_denial_refuses:true,old_settings_immutable:true,native_lock_wait_race_not_claimed:true}
})
const report={classification:'LOCAL_ACTUAL_SQL_WITH_CONTROLLED_ERP_AND_IDENTITY_ADAPTER_NOT_NATIVE',status:results.every(x=>x.status==='PASS')?'PASS':'FAIL',
 source_sha256:createHash('sha256').update(source).digest('hex'),alert_source_sha256:createHash('sha256').update(alerts).update(Object.values(staged).join('\n')).digest('hex'),source_layout:'FROZEN_PREDECESSOR_PLUS_COUNTED_PRODUCTION_STAGE',cases:results,OW14b_complete:false,production_go:false}
await mkdir('docs/cp7/d17-14/ow14b',{recursive:true});await writeFile('docs/cp7/d17-14/ow14b/local-rule.json',JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));await db.close();if(report.status!=='PASS')process.exitCode=1
