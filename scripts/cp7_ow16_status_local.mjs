// Actual OW16 SQL and roles on a minimal controlled ERP fixture. This is a
// relational/privilege test, not a claim of Native manufacturing or HTTP proof.
import {readFile,writeFile,mkdir} from 'node:fs/promises'
import {createHash} from 'node:crypto'
import assert from 'node:assert/strict'
const {PGlite}=await import(process.env.CP7_PGLITE_MODULE??'@electric-sql/pglite')
const db=new PGlite(),source=await readFile('scripts/cp7-src/cutting-yield/automatic-status.sql','utf8')
const id=n=>`${n.toString(16).padStart(8,'0')}-0000-4000-8000-000000000000`
const owner=id(1),admin=id(2),staff=id(3),material=id(4),otherMaterial=id(5),pattern=id(6),po=id(7),s=id(8),m=id(9),jumbo=id(10),target=id(11)
await db.exec(`
 create role cp7_capture nologin;create role cp7_policy nologin;
 create role anon nologin;create role authenticated nologin;create role service_role nologin;
 create schema erp;create schema auth;create schema cp7_planning;create schema cp7_wip;create schema cp7_cutting_yield;
 grant usage on schema erp,auth,cp7_planning,cp7_wip,cp7_cutting_yield to cp7_capture;
 grant usage on schema auth to cp7_policy;
 create table public.fixture_access(id uuid primary key,role_code text,can_manage boolean,active boolean);
 insert into public.fixture_access values('${owner}','OWNER',true,true),('${admin}','ADMIN',true,true),('${staff}','STAFF',true,true);
 create function auth.uid()returns uuid language sql as $$select nullif(current_setting('request.jwt.claim.sub',true),'')::uuid$$;
 create function erp.has_permission(k text)returns boolean language sql security definer set search_path=''as $$
  select coalesce((select active and(case when k='master.product.manage'then can_manage else true end)from public.fixture_access where id=auth.uid()),false)$$;
 create function cp7_cutting_yield.access_now()returns jsonb language plpgsql security definer set search_path=''as $$
 declare r public.fixture_access%rowtype;begin select *into r from public.fixture_access where id=auth.uid();
  if r.id is null or not r.active or r.role_code not in('OWNER','ADMIN')then raise exception using errcode='42501',message='fixture access denied';end if;
  return jsonb_build_object('actor',r.id,'profile',jsonb_build_object('role_code',r.role_code));end$$;
 create function cp7_wip.fields(p jsonb,keys text[])returns void language plpgsql as $$
 begin if jsonb_typeof(p)is distinct from'object'or exists(select 1 from jsonb_object_keys(p)k where not k=any(keys))then raise exception 'unexpected payload';end if;end$$;
 create function cp7_planning.utc(at timestamptz)returns text language sql immutable as $$select to_char(at at time zone 'UTC','YYYY-MM-DD"T"HH24:MI:SS.US"Z"')$$;
 create table erp.production_orders(id uuid primary key,status text,current_stage text);
 create table erp.cutting_groups(id uuid primary key,po_id uuid,row_version bigint,cut_at timestamptz,material_issue_posted boolean,
  pattern_id uuid,pattern_revision_snapshot text,pattern_code_snapshot text,pattern_name_snapshot text,created_by uuid,created_at timestamptz default clock_timestamp());
 create table erp.materials(id uuid primary key,material_sku text,material_name text,unit_code text);
 create table erp.material_rolls(id uuid primary key,material_id uuid);
 create table erp.sizes(id uuid primary key,size_code text,sort_order int);
 create table erp.cutting_group_size_slots(id uuid primary key,cutting_group_id uuid,size_id uuid);
 create table erp.cutting_group_rolls(id uuid primary key,cutting_group_id uuid,roll_id uuid,qty_consumed numeric);
 create table erp.cutting_roll_yields(id uuid primary key,cutting_group_roll_id uuid,size_slot_id uuid,qty_pcs bigint);
 grant select on all tables in schema erp to cp7_capture;
 insert into erp.production_orders values('${po}','SEWING','SEWING');
 insert into erp.materials values('${material}','FAB-A','Bahan A','M'),('${otherMaterial}','FAB-B','Bahan B','M');
 insert into erp.sizes values('${s}','S',1),('${m}','M',2),('${jumbo}','JUMBO',3);
`)
const results=[]
async function test(name,fn){try{results.push({id:name,status:'PASS',observed:await fn()})}catch(e){results.push({id:name,status:'FAIL',error:String(e.message).slice(0,2000)})}}
async function run(sql,args=[],actor=owner,role='authenticated'){
  await db.query("select set_config('request.jwt.claim.sub',$1,false)",[actor])
  await db.exec('set role '+role)
  try{return await db.query(sql,args)}finally{await db.exec('reset role')}
}
const workspace=async()=> (await run('select public.erp_cp7_get_cutting_status_v1($1::uuid) value',[target])).rows[0].value
const payload=(revision='0',state='ACTIVE')=>({expected_revision:revision,state,coverage:'0.8',min_groups:'3',reason:'Explicit fixture-owner policy, not a production default',explicit_review:true})
const save=async(p,key,actor=owner,lookup=false)=>(await run(`select public.${lookup?'erp_cp7_get_cutting_status_policy_request_v1':'erp_cp7_save_cutting_status_policy_v1'}($1::jsonb,$2::uuid) value`,[JSON.stringify(p),key],actor)).rows[0].value
async function refused(fn,code){let caught;try{await fn()}catch(e){caught=e}assert(caught,'expected refusal');if(code)assert.equal(caught.code,code);return caught.message}
let n=100
const cutTime=new Date(Date.now()-86400000).toISOString()
async function group({group=id(n++),pcs=100,consumed='10',kind=material,sizes=[s,m],pat=pattern,revision='R1',posted=true,offset=-3600000,creator=admin}={}){
  const roll=id(n++),slice=id(n++),slot=id(n++),at=new Date(Date.parse(cutTime)+offset).toISOString()
  await db.query('insert into erp.cutting_groups(id,po_id,row_version,cut_at,material_issue_posted,pattern_id,pattern_revision_snapshot,pattern_code_snapshot,pattern_name_snapshot,created_by) values($1,$2,1,$3,$4,$5,$6,$7,$8,$9)',[group,po,at,posted,pat,revision,'PAT-A','Pola A',creator])
  for(const size of sizes)await db.query('insert into erp.cutting_group_size_slots values($1,$2,$3)',[size===sizes[0]?slot:id(n++),group,size])
  await db.query('insert into erp.material_rolls values($1,$2)',[roll,kind])
  await db.query('insert into erp.cutting_group_rolls values($1,$2,$3,$4)',[slice,group,roll,consumed])
  await db.query('insert into erp.cutting_roll_yields values($1,$2,$3,$4)',[id(n++),slice,slot,pcs])
  return group
}
try{
 await db.exec(source)
 const earliest=await group({pcs:80});await group({pcs:100});await group({pcs:120})
 await group({pcs:10000,kind:otherMaterial});await group({pcs:10000,sizes:[jumbo]});await group({pcs:10000,pat:id(12)})
 await group({pcs:10000,revision:'R2'});await group({pcs:10000,posted:false});await group({pcs:10000,offset:3600000})
 await group({group:target,pcs:100,offset:0,creator:owner})
 // Equal entered physical times retain the genuinely earlier known group;
 // a later-created group at that same physical time is not prior evidence.
 await db.query('update erp.cutting_groups set cut_at=$1 where id=$2',[cutTime,earliest])
 await group({pcs:10000,offset:0})
 await test('NO_INVENTED_FACTORY_POLICY',async()=>{
  const value=await workspace();assert.equal(value.scope,'FACTORY');assert.equal(value.policy,null)
  assert.equal(value.materials[0].status,'POLICY_REQUIRED');assert.equal(value.materials[0].history_groups,'3')
  return {policy:null,status:value.materials[0].status}
 })
 const p=payload(),request=id(20)
 await test('OWNER_POLICY_EXACT_REPLAY_AND_CHANGED_REQUEST_REFUSAL',async()=>{
  const first=await save(p,request),again=await save(p,request)
  assert.deepEqual(first,again);assert.equal(first.policy.actor,owner);assert.equal(first.policy.revision,'1')
  await refused(()=>save({...p,min_groups:'4'},request))
  await refused(()=>save(p,id(21)),'40001')
  return {revision:first.policy.revision,same_request_same_result:true,changed_request_refused:true,stale_revision_refused:true}
 })
 await test('FACTORY_CONTEXT_EXCLUDES_OTHER_MATERIAL_PATTERN_SIZE_REVISION_FUTURE_AND_UNPOSTED',async()=>{
  const row=(await workspace()).materials[0]
  assert.equal(row.status,'WITHIN');assert.equal(row.history_groups,'3');assert.equal(row.lower_pcs,'80');assert.equal(row.upper_pcs,'120')
  assert.equal(row.total_pcs,'100');assert.deepEqual(row.size_ids,[s,m]);assert.equal(row.consumed,'10')
  return {history_groups:row.history_groups,lower_pcs:row.lower_pcs,upper_pcs:row.upper_pcs,other_actor_history_included:true}
 })
 await test('TOTAL_PCS_LOW_HIGH_AND_CONSUMPTION_NORMALIZATION',async()=>{
  const update=async(pcs,qty='10')=>{await db.query('update erp.cutting_roll_yields set qty_pcs=$1 where cutting_group_roll_id in(select id from erp.cutting_group_rolls where cutting_group_id=$2)',[pcs,target]);await db.query('update erp.cutting_group_rolls set qty_consumed=$1 where cutting_group_id=$2',[qty,target])}
  await update(79);assert.equal((await workspace()).materials[0].status,'LOW')
  await update(121);assert.equal((await workspace()).materials[0].status,'HIGH')
  await update(200,'20');const row=(await workspace()).materials[0]
  assert.equal(row.status,'WITHIN');assert.equal(row.lower_pcs,'160');assert.equal(row.upper_pcs,'240')
  await update(100)
  return {low79:true,high121:true,current_consumed20_range:['160','240']}
 })
 await test('READS_NEVER_CHANGE_NATIVE_FACTS',async()=>{
  const before=await db.query('select jsonb_agg(to_jsonb(g)order by id)as value from erp.cutting_groups g')
  for(let i=0;i<3;i++)await workspace()
  assert.deepEqual(await db.query('select jsonb_agg(to_jsonb(g)order by id)as value from erp.cutting_groups g'),before)
  const modes=(await db.query("select has_table_privilege('cp7_capture','erp.cutting_groups','INSERT,UPDATE,DELETE,TRUNCATE')as mutable")).rows[0]
  assert.equal(modes.mutable,false);return {read_only:true}
 })
 await test('ADMIN_CANNOT_SET_FACTORY_POLICY_AND_ANON_CANNOT_READ',async()=>{
  await refused(()=>save(payload('1'),id(22),admin),'42501')
  await refused(()=>run('select public.erp_cp7_get_cutting_status_v1($1::uuid)',[target],owner,'anon'),'42501')
  await refused(()=>run('select public.erp_cp7_get_cutting_status_v1($1::uuid)',[target],staff),'42501')
  await refused(()=>run("insert into cp7_cutting_status.policies values(null)",[]),'42501')
  return {owner_only_write:true,anonymous_closed:true,staff_closed:true,private_tables_closed:true}
 })
 await test('MISSING_HISTORY_PAUSED_POLICY_AND_NOT_FINISHED_STATES',async()=>{
  await save({...payload('1'),min_groups:'4'},id(23));assert.equal((await workspace()).materials[0].status,'INSUFFICIENT_HISTORY')
  await save(payload('2','PAUSED'),id(24));assert.equal((await workspace()).materials[0].status,'POLICY_PAUSED')
  await db.query('update erp.cutting_groups set material_issue_posted=false where id=$1',[target])
  assert.equal((await workspace()).materials[0].status,'NOT_FINISHED')
  await db.query('update erp.cutting_groups set material_issue_posted=true where id=$1',[target])
  await save(payload('3'),id(25));return {insufficient:true,paused:true,unposted:true}
 })
 await test('LOST_REPLY_LOOKUP_CLOSES_UNCOMMITTED_UUID',async()=>{
  const pending=payload('4'),key=id(26),lookup=await save(pending,key,owner,true)
  assert.equal(lookup.status,'NOT_COMMITTED');assert.equal(lookup.policy,null)
  assert.deepEqual(await save(pending,key),lookup)
  assert.equal((await workspace()).policy.revision,'4');return {no_late_commit_after_negative_lookup:true}
 })
 await test('LEGACY_MISSING_CONTEXT_IS_INCOMPLETE_NOT_ZERO_OR_NORMAL',async()=>{
  await db.query('update erp.cutting_groups set pattern_id=null where id=$1',[target])
  const value=await workspace();assert.equal(value.materials[0].status,'DATA_INCOMPLETE');assert.equal(value.materials[0].lower_pcs,null)
  await db.query('update erp.cutting_groups set pattern_id=$1 where id=$2',[pattern,target])
  return {missing_pattern_not_judged:true}
 })
 await test('POLICY_AND_RECEIPTS_IMMUTABLE',async()=>{
  for(const table of ['policies','requests']){
   await refused(()=>db.exec('delete from cp7_cutting_status.'+table))
   await refused(()=>db.exec('truncate cp7_cutting_status.'+table))
  }
  return {delete_refused:true,truncate_refused:true}
 })
 await test('MORE_THAN_500_FACTORY_GROUPS_NO_TRUNCATION',async()=>{
  for(let i=0;i<501;i++)await group({pcs:100})
  const row=(await workspace()).materials[0]
  assert.equal(row.history_groups,'504');assert.equal(row.status,'WITHIN');assert.equal(row.lower_pcs,'100');assert.equal(row.upper_pcs,'100')
  return {groups:row.history_groups,lower_pcs:row.lower_pcs,upper_pcs:row.upper_pcs}
 })
}catch(error){results.push({id:'SQL_INSTALL_OR_FIXTURE',status:'FAIL',error:String(error.stack).slice(0,3000)})}
const report={label:'OW16_STATUS_LOCAL',scope:'ACTUAL_SQL_ON_CONTROLLED_RELATIONAL_FIXTURE_WITH_STUBBED_IDENTITY_NOT_NATIVE_OR_HTTP',
 source_sha256:createHash('sha256').update(source).digest('hex'),status:results.length>0&&results.every(x=>x.status==='PASS')?'PASS':'FAIL',cases:results}
await mkdir('cp6-proof/ow16',{recursive:true});await writeFile('cp6-proof/ow16/LOCAL_STATUS.json',JSON.stringify(report,null,2)+'\n')
console.log(JSON.stringify(report,null,2));await db.close();if(report.status!=='PASS')process.exitCode=1
