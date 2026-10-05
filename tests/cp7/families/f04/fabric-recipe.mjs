import assert from 'node:assert/strict'
import {readFileSync,writeFileSync,mkdirSync} from 'node:fs'
import {dirname} from 'node:path'
import {openRuntime,digest,jsonArg} from './runtime.mjs'

// Controlled SQL/metadata kernels only. Masters, authority and Original serve
// are explicit stand-ins; no Native ERP/Auth/HTTP/race/browser credit is given.
const paths=['scripts/cp7-src/planning/fabric-requirements.sql','scripts/cp7-src/planning/fabric-commands.sql']
const sources=paths.map(p=>readFileSync(p,'utf8')),analysis=readFileSync('scripts/cp7-src/planning/analysis.sql','utf8')
const fact=analysis.slice(analysis.indexOf('create function cp7_analysis_native.fact('),analysis.indexOf('create function cp7_analysis_native.build('))
const normalization=readFileSync('scripts/cp7-src/wip/normalize.sql','utf8'),ref=normalization.slice(normalization.indexOf('create function cp7_wip.ref('),normalization.indexOf('create function ',normalization.indexOf('create function cp7_wip.ref(')+1))
const actor='aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',root='11111111-1111-4111-8111-111111111111',size='22222222-2222-4222-8222-222222222222'
const material='33333333-3333-4333-8333-333333333333',pattern='44444444-4444-4444-8444-444444444444',run='55555555-5555-4555-8555-555555555555',target=`${root}:${size}`
const products=[{root_id:root,size_id:size}],refs=[{kind:'SYNTHETIC_SQL_CONTROL',id:root,revision:'1'}],cases=[]
const db=await openRuntime()
try{
 await db.execute(`set TimeZone='UTC';create schema erp;create schema extensions;create schema cp7_private;create schema cp7_schedule_native;create schema cp7_analysis_native;
 alter role cp7_capture bypassrls;
 create function extensions.digest(bytea,text)returns bytea language sql immutable as $$select case when $2='sha256' then pg_catalog.sha256($1)else null end$$;
 create function cp7_private.immutable_run()returns trigger language plpgsql as $$begin raise exception 'CP7_IMMUTABLE_RUN';end$$;
 create table erp.materials(id uuid primary key,material_sku text,material_name text,unit_code text,material_type text,is_active boolean,row_version bigint,created_at timestamptz default clock_timestamp());
 create table erp.production_patterns(id uuid primary key,pattern_code text,pattern_name text,revision text,is_active boolean,row_version bigint,created_at timestamptz default clock_timestamp());
 insert into erp.materials(id,material_sku,material_name,unit_code,material_type,is_active,row_version)values('${material}','TEST-FABRIC','Explicit fixture fabric','M','FABRIC',true,1);
 insert into erp.production_patterns(id,pattern_code,pattern_name,revision,is_active,row_version)values('${pattern}','TEST-PATTERN','Explicit fixture pattern','R1',true,1);
 create table public.fabric_fixture(envelope jsonb,access jsonb,writing boolean);
 insert into public.fabric_fixture values(${jsonArg({run_id:run,source_state:'UNCHANGED',analysis:{snapshot:{capture_complete:true,source_hash:'a'.repeat(64)},recommendations:[{target:{key:target,kind:'PRODUCT'}}]}})},${jsonArg({actor,profile:{id:'explicit-fixture'},permissions:['fixture-only']})},true);
 update public.fabric_fixture set envelope=jsonb_set(envelope,'{analysis,versions}',jsonb_build_object('access_epoch',encode(extensions.digest(convert_to(access::text,'UTF8'),'sha256'),'hex')));
 grant select on public.fabric_fixture to cp7_capture;
 create function cp7_schedule_native.access_now(writing boolean)returns jsonb language plpgsql stable as $$declare a jsonb;can_write boolean;begin select f.access,f.writing into a,can_write from public.fabric_fixture f;if writing and not can_write then raise exception using errcode='42501',message='CP7_FIXTURE_ACCESS_DENIED';end if;return a;end$$;
 create function cp7_analysis_native.serve(p_run uuid)returns jsonb language plpgsql volatile as $$declare e jsonb;begin select f.envelope into e from public.fabric_fixture f;if e->>'run_id'<>p_run::text then raise exception using errcode='42501',message='CP7_FIXTURE_ORIGINAL_UNAVAILABLE';end if;return e;end$$;
 ${ref}
 ${fact}
 ${sources.join('\n')}`)
 const call=async(name,args)=>(await db.query(`select cp7_fabric_native.${name}(${args.join(',')})as result`))[0].result
 const catalog=(await db.query("select jsonb_build_object('materials',(select jsonb_agg(to_jsonb(m))from erp.materials m),'patterns',(select jsonb_agg(to_jsonb(p))from erp.production_patterns p))as result"))[0].result
 const nativeHash=async(table,id)=>(await db.query(`select encode(extensions.digest(convert_to(to_jsonb(x)::text,'UTF8'),'sha256'),'hex')hash from erp.${table} x where id='${id}'`))[0].hash
 const config={basis:'SELECTED_ASSUMPTIONS',effective_from:'2026-01-01T00:00:00Z',effective_to:null,material_id:material,material_hash:await nativeHash('materials',material),unit:'M',qty_per_good_pcs:'2',pattern_id:pattern,pattern_hash:await nativeHash('production_patterns',pattern)}
 const payload={run_id:run,target_key:target,source_hash:'a'.repeat(64),expected_revision:'0',config,reason:'Explicit synthetic fixture input, not factory rate'}
 const save=(p,key)=>call('save',[jsonArg(p),`'${key}'::uuid`])
 const source=at=>call('source',[jsonArg(products),`'${at}'::timestamptz`])
 const needs=(s,gap='100',key=target)=>call('needs',[jsonArg({fabric_source:s}),jsonArg({target_key:key,conditional_gap_pcs:gap,refs}),jsonArg([])])
 const check=(id,receipt)=>cases.push({id,status:'PASS',complete_receipt:receipt})
 const refusal=async(id,operation,error)=>{await assert.rejects(operation,new RegExp(error));check(id,{required_error:error,refused:true})}
 assert.deepEqual(await call('validate',[jsonArg(config),jsonArg(catalog)]),config);check('explicit_rate_and_full_Native_identity',{config})
 assert.deepEqual(await call('validate',[jsonArg({...config,pattern_id:null,pattern_hash:null,qty_per_good_pcs:'0.000001'}),jsonArg(catalog)]),{...config,pattern_id:null,pattern_hash:null,qty_per_good_pcs:'0.000001'});check('optional_pattern_and_decimal_micro_rate',{no_forced_pattern_or_rate:true})
 for(const [id,change,error]of[['zero_rate',{qty_per_good_pcs:'0'},'CP7_FABRIC_RATE'],['negative_rate',{qty_per_good_pcs:'-1'},'CP7_FABRIC_RATE'],['mixed_unit',{unit:'KG'},'CP7_FABRIC_NATIVE_MATERIAL_CHANGED'],['changed_material_hash',{material_hash:'0'.repeat(64)},'CP7_FABRIC_NATIVE_MATERIAL_CHANGED'],['unlinked_pattern',{pattern_id:null},'CP7_FABRIC_PATTERN'],['reversed_effective_window',{effective_to:'2025-01-01T00:00:00Z'},'CP7_FABRIC_EFFECTIVE_WINDOW']])await refusal(id,()=>call('validate',[jsonArg({...config,...change}),jsonArg(catalog)]),error)
 const workspaceQuery={run_id:run,target_key:target,material_query:'TEST-FABRIC',material_offset:'0',pattern_offset:'0',limit:'50'}
 const w=await call('workspace',[jsonArg(workspaceQuery)]);assert.equal(w.materials.length,1);assert.equal(w.patterns[0].revision,'R1');assert.equal(w.analysis.run_id,run);assert.equal(w.revision,'0');check('honest_catalog_page_and_Original',{workspace:w})
 const before=(await db.query('select to_jsonb(m)material,to_jsonb(p)pattern from erp.materials m cross join erp.production_patterns p'))
 const request='66666666-6666-4666-8666-666666666666',outcome=await save(payload,request)
 assert.equal(outcome.revision,'1');assert.deepEqual(await save(payload,request),outcome)
 assert.equal((await db.query('select count(*)::text n from cp7_fabric_native.recipes'))[0].n,'1');assert.deepEqual(await db.query('select to_jsonb(m)material,to_jsonb(p)pattern from erp.materials m cross join erp.production_patterns p'),before)
 check('same_UUID_one_recipe_no_Native_business_write',{outcome,masters_unchanged:true})
 await refusal('changed_UUID_payload',()=>save({...payload,reason:'different'},request),'CP7_FABRIC_REQUEST_CHANGED')
 await refusal('revision_CAS',()=>save(payload,'77777777-7777-4777-8777-777777777777'),'CP7_FABRIC_REVISION_CHANGED')
 await db.execute("update public.fabric_fixture set envelope=jsonb_set(envelope,'{source_state}','\"ARCHIVED_STALE\"');")
 await refusal('stale_Original',()=>save({...payload,expected_revision:'1'},'88888888-8888-4888-8888-888888888888'),'CP7_FABRIC_ANALYSIS_CHANGED')
 await db.execute("update public.fabric_fixture set envelope=jsonb_set(envelope,'{source_state}','\"UNCHANGED\"'),writing=false;")
 await refusal('current_metadata_write_permission',()=>save({...payload,expected_revision:'1'},'99999999-9999-4999-8999-999999999999'),'CP7_FIXTURE_ACCESS_DENIED')
 await db.execute('update public.fabric_fixture set writing=true;')
 await db.execute("update public.fabric_fixture set access=jsonb_set(access,'{profile,id}','\"changed-fixture\"');")
 await refusal('Original_authority_epoch',()=>save({...payload,expected_revision:'1'},'cccccccc-cccc-4ccc-8ccc-cccccccccccc'),'CP7_FABRIC_ORIGINAL_ACCESS_CHANGED')
 await db.execute("update public.fabric_fixture set access=jsonb_set(access,'{profile,id}','\"explicit-fixture\"');")
 await refusal('one_year_backdate_limit',()=>save({...payload,expected_revision:'1',config:{...config,effective_from:'2024-01-01T00:00:00Z'}},'dddddddd-dddd-4ddd-8ddd-dddddddddddd'),'CP7_FABRIC_BACKDATE_LIMIT')
 const at=(await db.query('select clock_timestamp()::text at'))[0].at,first=await source(at),firstNeeds=await needs(first)
 assert.equal(firstNeeds[0].gross.state,'ASSUMED');assert.equal(firstNeeds[0].gross.value,'200');assert.ok(firstNeeds[0].gross.assumption_ids.includes(outcome.recipe_id));assert.ok(firstNeeds[0].gross.refs.some(r=>r.kind==='erp.materials'))
 for(const key of['installed_proven','unused_allocated_proven','additional_external'])assert.equal(firstNeeds[0][key].state,'UNKNOWN')
 check('conditional_need100_rate2_gross200_not_installed_or_feasible',{result:firstNeeds})
 assert.equal((await needs(first,null))[0].gross.state,'UNKNOWN');assert.equal((await needs(first,'100',`${root}:ffffffff-ffff-4fff-8fff-ffffffffffff`))[0].gross.state,'UNKNOWN');check('unknown_need_and_exact_other_size_not_zero',{no_inherited_recipe:true})
 const future=new Date(Date.now()+86_400_000).toISOString(),expiry=new Date(Date.now()+172_800_000).toISOString()
 const successor=await save({...payload,expected_revision:'1',config:{...config,qty_per_good_pcs:'3',effective_from:future,effective_to:expiry}},'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb')
 const known=(await db.query('select clock_timestamp()::text at'))[0].at,early=await source(known),later=await source(future),expired=await source(expiry)
 assert.equal((await needs(early))[0].gross.value,'200');assert.equal((await needs(later))[0].gross.value,'300');assert.equal((await needs(expired))[0].gross.state,'UNKNOWN');assert.equal(expired.selected.length,0);assert.equal(later.selected[0].id,successor.recipe_id);assert.equal(firstNeeds[0].gross.value,'200')
 check('future_successor_half_open_expiry_no_old_rate_resurrection',{early,later,expired,old_receipt:firstNeeds})
 const unknownPast=await source('2025-01-01T00:00:00Z');assert.equal(unknownPast.versions.length,0);check('recording_clock_no_future_knowledge',{result:unknownPast})
 await db.execute('update erp.materials set row_version=2;');const changed=await source(future);assert.equal((await needs(changed))[0].gross.state,'UNKNOWN');check('full_master_revision_invalidates_review',{result:await needs(changed)})
 await db.execute('update erp.materials set row_version=1;update erp.production_patterns set revision=\'R2\';');assert.equal((await needs(await source(future)))[0].gross.state,'UNKNOWN');check('Native_pattern_revision_invalidates_review',{result:await needs(await source(future))})
 await refusal('immutable_recipe',()=>db.execute("update cp7_fabric_native.recipes set reason='rewrite';"),'CP7_IMMUTABLE_RUN')
 const boundary=(await db.query("select count(*)::text n from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='cp7_fabric_native'and(has_function_privilege('anon',p.oid,'EXECUTE')or has_function_privilege('authenticated',p.oid,'EXECUTE')or has_function_privilege('service_role',p.oid,'EXECUTE'))"))[0].n
 assert.equal(boundary,'0');assert.equal((await db.query("select count(*)::text n from pg_class where relnamespace='cp7_fabric_native'::regnamespace and relkind='r'and relrowsecurity"))[0].n,'2')
 check('private_function_ACLs_and_RLS',{private_functions_exposed:boundary,private_tables_RLS:2})
 const receipt={contract:'cp7.fabric-recipe-private-controls.v1',status:'PASS',runtime:db.flavor,version:db.version,source_sha256:Object.fromEntries(paths.map((p,i)=>[p,digest(sources[i])])),cases,passed:cases.length,standins:['Native master tables','Original serve','authorization','digest adapter pg_catalog.sha256'],Native_business_case_credit:0,Auth_HTTP_credit:0,race_credit:0,browser_credit:0,full_P08_acceptance:false,production_go:false,cleanup:'CLOSED_DISPOSABLE_RUNTIME'}
 if(process.env.F04_FABRIC_RECEIPT_PATH){mkdirSync(dirname(process.env.F04_FABRIC_RECEIPT_PATH),{recursive:true});writeFileSync(process.env.F04_FABRIC_RECEIPT_PATH,JSON.stringify(receipt,null,2)+'\n')}
 console.log(JSON.stringify(receipt))
}finally{await db.close()}
