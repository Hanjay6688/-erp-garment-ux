// @vitest-environment node
import { createHash } from 'node:crypto'
import { expect, test } from 'vitest'
import { openRuntime, jsonArg } from './f04/runtime.mjs'
import { DEFECTS } from './f04/netting-fixture.mjs'
import { ACTOR, ACCESS, QUERY, STAGED_DEFECTS, DEFAULT_BOUNDS, installStagedControls, stagedInput } from './f04/staged-analysis-fixture.mjs'
import { installStagedApiControls, callAs, refuseAs } from './f04/staged-api-fixture.mjs'
const SMALL={...DEFAULT_BOUNDS,targets_per_chunk:7,pairs_per_chunk:45,allocation_targets_per_step:4}
const uuid=(n:number)=>`03000000-0000-4000-8000-${n.toString(16).padStart(12,'0')}`
const sha=(t:string)=>createHash('sha256').update(t).digest('hex')
type Row=Record<string,any>

test('P19 product pages: every item and hash reassembles to the single analysis and Original at many byte cuts',async()=>{
 const db=await openRuntime({commandTimeoutMs:600000})
 try{
  await installStagedControls(db,{bounds:SMALL})
  // TEST ONLY: choose three byte budgets from the largest target fragment.
  // Pages still use the real byte-adaptive cut, never a fixed target count.
  await db.execute(`create function public.sp_case(c jsonb,req uuid,per integer)returns jsonb language plpgsql as $$
   declare job uuid;s jsonb;rid uuid;v jsonb;single jsonb;n integer;bytes integer;b jsonb;
   begin
    job:=cp7_analysis_stage.create_job('${ACTOR}',req,'${JSON.stringify(QUERY)}','${JSON.stringify(ACCESS)}',c);
    loop
     if (select kind from cp7_analysis_stage.units where job_id=job and idx=(select units_done from cp7_analysis_stage.jobs where id=job))='ANA_META'then
      select greatest(coalesce(max(z.bytes),0),1) into bytes from(select sum(utf8_bytes+2)::integer bytes from cp7_analysis_stage.fragments where job_id=job group by ord)z;
      b:=cp7_analysis_stage.bounds()||jsonb_build_object('page_utf8_bytes',4096+bytes*per);
      execute format('create or replace function cp7_analysis_stage.bounds()returns jsonb language sql immutable as %L', 'select '||quote_literal(b::text)||'::jsonb');
     end if;
     s:=cp7_analysis_stage.step(job);exit when s->>'state'<>'RUNNING';
    end loop;
    select run_id into rid from cp7_analysis_stage.jobs where id=job;
    single:=public.st_single(c,'${JSON.stringify(QUERY)}',rid,'${JSON.stringify(ACCESS)}');
    v:=public.sv_verify(job,case when single->>'state'='DONE'then single->'body'end);
    return v||jsonb_build_object('failure',s->'failure','single',single->>'state');
   end $$;`)
  const cases:unknown[]=[]
  const shapes=[{targets:40,positions:16,roots:14,models:3,complete:true},{targets:30,positions:24,roots:9,models:2,complete:false},{targets:9,positions:3,roots:4,models:2,complete:true}]
  for(let seed=1;seed<=3;seed++)for(const defect of [...DEFECTS,...STAGED_DEFECTS])cases.push(stagedInput(4000+seed*100+cases.length,shapes[seed-1],defect))
  for(let seed=10;seed<22;seed++)cases.push(stagedInput(5000+seed,shapes[seed%3]))
  const stats=[]
  for(const per of [1,3,7]){
   let done=0,refused=0,edges=0,zero=0;const arrays=new Set<string>()
   for(let i=0;i<cases.length;i+=8){
    const rows=await db.query(`select public.sp_case(x.c,('${uuid(per*0x10000).slice(0,-12)}'||lpad(to_hex(${per*0x10000+i}+x.o::integer),12,'0'))::uuid,${per})r from jsonb_array_elements(${jsonArg(cases.slice(i,i+8))})with ordinality x(c,o)order by x.o`)
    for(const {r} of rows as Row[]){
     if(r.state!=='DONE'){expect([r.page_set,r.pages]).toEqual([false,0]);refused++;continue}
     expect(r.bad).toEqual([]);if(r.single==='DONE')expect([r.same,r.text_same,r.document_same,r.hash_same]).toEqual([true,true,true,true])
     done++;edges+=Math.max(0,r.pages-1);if(r.targets===0)zero++;Object.keys(r.paged).forEach(k=>arrays.add(k))
    }
   }
   expect(done).toBeGreaterThanOrEqual(75);expect(edges).toBeGreaterThan(100);expect(zero).toBeGreaterThan(0)
   for(const k of ['recommendations','actions','timeline','metrics','demand_models','material_needs','assumptions','generation_warnings'])expect(arrays.has(k),k).toBe(true)
   stats.push({per,done,refused,edges,zero,arrays:[...arrays]})
  }
  console.log(JSON.stringify({runtime:db.flavor,variants:stats}))
 }finally{await db.close()}
},1800000)

test('P19 product pages: access epoch, actor binding, no partial/whole reads, immutable output, bounded multibyte pages',async()=>{
 const db=await openRuntime({commandTimeoutMs:600000})
 try{
  await installStagedControls(db,{bounds:{...SMALL,page_utf8_bytes:160000}});await installStagedApiControls(db)
  const c=stagedInput(7004,{targets:40,positions:16,roots:14,models:3,complete:true}) as Row
  for(const row of c.stub_scenario.supply_run_result.baseline_run_result.rows)row.refs.push({kind:'UTF8_TEST',id:'☃😀',revision:'1'})
  for(const p of c.facts.products){p.product_name='Kaos 😀 é ✓';p.sku='SKU-😀-'+p.id}
  await db.execute(`insert into public.stage_capture values(${jsonArg(c)});`)
  const req=uuid(0x801),other=uuid(0xb2)
  let s=await callAs(db,ACTOR,`public.erp_cp7_request_staged_analysis_v1(${jsonArg(QUERY)},'${req}')`)
  await refuseAs(db,ACTOR,`public.erp_cp7_read_staged_analysis_pages_v1('${(await db.query(`select run_id from cp7_analysis_stage.jobs where request_id='${req}'`))[0].run_id}')`,'CP7_ANALYSIS_RUN_UNAVAILABLE')
  for(let i=0;i<1000&&s.state==='RUNNING';i++)s=await callAs(db,ACTOR,`public.erp_cp7_step_staged_analysis_v1('${req}')`)
  expect(s.state).toBe('DONE')
  const run=s.run_id,m=await callAs(db,ACTOR,`public.erp_cp7_read_staged_analysis_pages_v1('${run}')`)
  expect(Object.keys(m).sort()).toEqual(['access_epoch','apply_enabled','contract_version','header','identity_hash','page_count','paged','pages','production_go','reference','request_id','run_id','targets_total','totals'])
  expect(m.reference).toEqual(s.reference);expect(m.targets_total).toBe(40);expect(m.page_count).toBeGreaterThan(1)
  expect(sha(m.header.body)).toBe(m.header.sha256);expect(sha(m.header.sha256+'\n'+m.pages.map((p:Row)=>p.sha256).join('\n'))).toBe(m.identity_hash)
  const h=JSON.parse(m.header.body);expect(h.financial_source).toBeNull();expect(h.analysis_header).not.toHaveProperty('semantic_hash')
  let hi=0,sawMultibyte=false
  for(const e of m.pages){
   const p=await callAs(db,ACTOR,`public.erp_cp7_read_staged_analysis_page_v1('${run}',${e.index},'${m.access_epoch}')`)
   expect(p).toMatchObject({identity_hash:m.identity_hash,header_sha256:m.header.sha256,target_lo:hi+1,target_hi:e.target_hi})
   expect(sha(p.body)).toBe(e.sha256);expect(Buffer.byteLength(p.body)).toBe(e.utf8_bytes);expect(e.utf8_bytes).toBeLessThanOrEqual(160000);hi=e.target_hi;sawMultibyte ||= p.body.includes('☃😀')
  }
  expect(hi).toBe(40);expect(sawMultibyte).toBe(true)
  await refuseAs(db,ACTOR,`public.erp_cp7_read_staged_analysis_page_v1('${run}',0,'${m.access_epoch}')`,'CP7_ANALYSIS_ACCESS_CHANGED',"set test.perm='changed';")
  await refuseAs(db,other,`public.erp_cp7_read_staged_analysis_pages_v1('${run}')`,'CP7_ANALYSIS_RUN_UNAVAILABLE')
  const [{epoch}]=await db.query(`select encode(sha256(convert_to(jsonb_build_object('actor','${other}','permissions','view')::text,'UTF8')),'hex') epoch`)
  await refuseAs(db,other,`public.erp_cp7_read_staged_analysis_page_v1('${run}',0,'${m.access_epoch}')`,'CP7_ANALYSIS_ACCESS_CHANGED')
  await refuseAs(db,other,`public.erp_cp7_read_staged_analysis_page_v1('${run}',0,'${epoch}')`,'CP7_ANALYSIS_RUN_UNAVAILABLE')
  await refuseAs(db,ACTOR,`public.erp_cp7_read_staged_analysis_page_v1('${run}',${m.page_count},'${m.access_epoch}')`,'CP7_ANALYSIS_PAGE_UNAVAILABLE')
  await refuseAs(db,'',`public.erp_cp7_read_staged_analysis_pages_v1('${run}')`,'CP7_ACCESS_DENIED')
  await refuseAs(db,ACTOR,`public.erp_cp7_read_analysis_manifest_v1('${run}')`,'CP7_ANALYSIS_RUN_UNAVAILABLE')
  await refuseAs(db,ACTOR,`public.erp_cp7_read_analysis_v1('${run}')`,'CP7_ANALYSIS_RUN_UNAVAILABLE')
  const before=await callAs(db,ACTOR,`public.erp_cp7_check_staged_analysis_source_v1('${run}')`);expect(before.source_state).toBe('UNCHANGED')
  await db.execute(`update public.stage_capture set c=c||'{"analysis_engine_signature":"changed"}'::jsonb;`)
  expect((await callAs(db,ACTOR,`public.erp_cp7_check_staged_analysis_source_v1('${run}')`)).source_state).toBe('ARCHIVED_STALE')
  expect((await callAs(db,ACTOR,`public.erp_cp7_read_staged_analysis_pages_v1('${run}')`)).identity_hash).toBe(m.identity_hash)
  for(const table of ['pages','page_sets','headers'])await expect(db.execute(`reset role;update cp7_analysis_stage.${table} set run_id=run_id`)).rejects.toThrow(/CP7_RUN_IMMUTABLE/)
 }finally{await db.close()}
},900000)


test('P19 product refuses a target above the page budget without exposing a header or page set',async()=>{
 const db=await openRuntime({commandTimeoutMs:600000})
 try{
  await installStagedControls(db,{bounds:{...SMALL,page_utf8_bytes:4097}})
  const c=stagedInput(7011,{targets:9,positions:3,roots:4,models:2,complete:true})
  const [{r}]=await db.query(`select public.st_case(${jsonArg(c)},'${uuid(0x900)}') r`)
  expect(r).toMatchObject({state:'FAILED',page_set:false,header:false,pages:0,failure:{code:'CP7_ANALYSIS_PAGE_BODY_LIMIT'}})
 }finally{await db.close()}
},900000)
