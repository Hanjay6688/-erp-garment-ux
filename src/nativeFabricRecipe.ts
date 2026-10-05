import {parseNativeAnalysis,type NativeAnalysis,type AnalysisFinanceAccess} from './nativeAnalysis'
import type {NativeDemandQuery} from './nativeDemandHistory'

export type FabricConfig={basis:'SELECTED_ASSUMPTIONS';effective_from:string;effective_to:string|null;material_id:string;material_hash:string;unit:string;qty_per_good_pcs:string;pattern_id:string|null;pattern_hash:string|null}
export type FabricPayload={run_id:string;target_key:string;source_hash:string;expected_revision:string;config:FabricConfig;reason:string}
export type FabricRequest={id:string;payload:FabricPayload}
export type FabricMaterial={id:string;sku:string;name:string;unit:string;source_hash:string}
export type FabricPattern={id:string;code:string;name:string;revision:string;source_hash:string}
export type FabricWorkspace={analysis:NativeAnalysis;targetKey:string;revision:string;materials:FabricMaterial[];patterns:FabricPattern[];recipes:{id:string;revision:string;config:FabricConfig;reason:string;recorded_at:string}[];page:{limit:number;material_offset:number;material_total:string;pattern_offset:number;pattern_total:string;recipe_total:string;recipe_history_scope:'LATEST_50_REVISIONS'}}
const fail=():never=>{throw Error('Data review resep kain belum sesuai sumber ERP.')}
const obj=(v:unknown):Record<string,unknown>=>v!==null&&typeof v==='object'&&!Array.isArray(v)?v as Record<string,unknown>:fail()
function closed(v:unknown,keys:string[]){const x=obj(v);if(Object.keys(x).length!==keys.length||keys.some(k=>!Object.hasOwn(x,k)))fail();return x}
const id=(v:unknown):v is string=>typeof v==='string'&&/^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$/.test(v)
const hash=(v:unknown):v is string=>typeof v==='string'&&/^[a-f0-9]{64}$/.test(v)
const uint=(v:unknown):v is string=>typeof v==='string'&&/^(0|[1-9][0-9]{0,18})$/.test(v)&&BigInt(v)<=9223372036854775807n
const text=(v:unknown,max=200):v is string=>typeof v==='string'&&v.trim().length>0&&v.length<=max
function instant(v:unknown):v is string{return typeof v==='string'&&/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$/.test(v)&&Number.isFinite(Date.parse(v))&&new Date(v.slice(0,10)+'T00:00:00Z').toISOString().slice(0,10)===v.slice(0,10)}
export function parseFabricConfig(v:unknown):FabricConfig{
 const x=closed(v,['basis','effective_from','effective_to','material_id','material_hash','unit','qty_per_good_pcs','pattern_id','pattern_hash'])
 if(x.basis!=='SELECTED_ASSUMPTIONS'||!instant(x.effective_from)||x.effective_to!==null&&(!instant(x.effective_to)||Date.parse(x.effective_to)<=Date.parse(x.effective_from))||!id(x.material_id)||!hash(x.material_hash)||!text(x.unit,50)||typeof x.qty_per_good_pcs!=='string'||!/^(0|[1-9][0-9]{0,11})(\.[0-9]{1,6})?$/.test(x.qty_per_good_pcs)||!/[1-9]/.test(x.qty_per_good_pcs)||x.pattern_id===null&&x.pattern_hash!==null||x.pattern_id!==null&&(!id(x.pattern_id)||!hash(x.pattern_hash)))fail()
 return structuredClone(x)as FabricConfig
}
function payload(v:unknown):FabricPayload{
 const x=closed(v,['run_id','target_key','source_hash','expected_revision','config','reason'])
 if(!id(x.run_id)||typeof x.target_key!=='string'||x.target_key.split(':').length!==2||!x.target_key.split(':').every(id)||!hash(x.source_hash)||!uint(x.expected_revision)||BigInt(x.expected_revision)>=9223372036854775807n||!text(x.reason,1000))fail()
 parseFabricConfig(x.config);return structuredClone(x)as FabricPayload
}
export function parseFabricWorkspace(v:unknown,q:NativeDemandQuery,actor:string,target:string,access:AnalysisFinanceAccess):FabricWorkspace{
 const x=closed(v,['contract_version','actor_scope_id','run_id','target_key','source_hash','revision','analysis','materials','patterns','recipes','page','apply_enabled','production_go'])
 const analysis=parseNativeAnalysis(x.analysis,q,actor,access)
 if(x.contract_version!=='cp7.fabric-workspace.v1'||x.actor_scope_id!==actor||x.run_id!==analysis.runId||x.target_key!==target||!analysis.analysis.recommendations.some(r=>r.target.key===target&&r.target.kind==='PRODUCT')||analysis.state!=='UNCHANGED'||x.source_hash!==analysis.analysis.snapshot.source_hash||!uint(x.revision)||x.apply_enabled!==false||x.production_go!==false)fail()
 const page=closed(x.page,['limit','material_offset','material_total','pattern_offset','pattern_total','recipe_total','recipe_history_scope'])
 if(![page.limit,page.material_offset,page.pattern_offset].every(n=>Number.isSafeInteger(n))||(page.limit as number)<1||(page.limit as number)>50||(page.material_offset as number)<0||(page.pattern_offset as number)<0||Math.max(page.material_offset as number,page.pattern_offset as number)>1000000||![page.material_total,page.pattern_total,page.recipe_total].every(uint)||page.recipe_total!==x.revision||page.recipe_history_scope!=='LATEST_50_REVISIONS')fail()
 for(const domain of['materials','patterns','recipes']as const){
  const rawRows=x[domain];if(!Array.isArray(rawRows))fail();const rows=rawRows as unknown[]
  if(rows.length>(domain==='recipes'?50:page.limit as number)||new Set(rows.map(v=>obj(v).id)).size!==rows.length)fail()
  for(const raw of rows){const row=closed(raw,domain==='materials'?['id','sku','name','unit','source_hash']:domain==='patterns'?['id','code','name','revision','source_hash']:['id','revision','config','reason','recorded_at'])
   if(!id(row.id))fail()
   if(domain==='recipes'){if(!uint(row.revision)||row.revision==='0'||!text(row.reason,1000)||!instant(row.recorded_at))fail();parseFabricConfig(row.config)}
   else if(!hash(row.source_hash)||!text(row.name)||domain==='materials'&&(!text(row.sku)||!text(row.unit,50))||domain==='patterns'&&(!text(row.code)||!text(row.revision)))fail()
  }
 }
 const recipes=x.recipes as FabricWorkspace['recipes'];for(let i=0;i<recipes.length;i++)if(BigInt(recipes[i].revision)!==BigInt(x.revision as string)-BigInt(i))fail()
 if(recipes.length!==Number(BigInt(x.revision as string)>50n?50n:BigInt(x.revision as string)))fail()
 for(const [key,offset,total]of[['materials','material_offset','material_total'],['patterns','pattern_offset','pattern_total']]as const){const remaining=BigInt(page[total]as string)-BigInt(page[offset]as number),expected=remaining<0n?0n:remaining<BigInt(page.limit as number)?remaining:BigInt(page.limit as number);if(BigInt((x[key]as unknown[]).length)!==expected)fail()}
 return {analysis,targetKey:target,revision:x.revision as string,materials:structuredClone(x.materials)as FabricMaterial[],patterns:structuredClone(x.patterns)as FabricPattern[],recipes:structuredClone(recipes),page:structuredClone(page)as FabricWorkspace['page']}
}
export function checkFabricOutcome(v:unknown,r:FabricRequest,actor:string){const x=closed(v,['contract_version','actor_scope_id','request_id','recipe_id','target_key','revision','quality','apply_enabled','production_go']);if(x.contract_version!=='cp7.fabric-outcome.v1'||x.actor_scope_id!==actor||x.request_id!==r.id||!id(x.recipe_id)||x.target_key!==r.payload.target_key||!uint(x.revision)||BigInt(x.revision)!==BigInt(r.payload.expected_revision)+1n||x.quality!=='SELECTED_ASSUMPTIONS'||x.apply_enabled!==false||x.production_go!==false)fail()}
export const fabricRequestKey=(scope:string)=>'cp7.fabric-recipe.request.v1:'+scope
export function readFabricRequest(scope:string):{pending:FabricRequest|null;error:string|null}{try{const raw=localStorage.getItem(fabricRequestKey(scope));if(raw===null)return{pending:null,error:null};if(raw.length>15000)fail();const x=closed(JSON.parse(raw),['id','payload']);if(!id(x.id))fail();payload(x.payload);return{pending:structuredClone(x)as FabricRequest,error:null}}catch{return{pending:null,error:'Permintaan resep kain tersimpan belum dapat dibaca. Pastikan hasilnya sebelum membuat permintaan lain.'}}}
export function persistFabricRequest(scope:string,r:FabricRequest){if(!id(r.id))fail();payload(r.payload);const held=readFabricRequest(scope);if(held.error||held.pending)throw Error(held.error??'Pastikan permintaan resep kain yang sama dahulu.');localStorage.setItem(fabricRequestKey(scope),JSON.stringify(r));const stored=readFabricRequest(scope);if(stored.error||JSON.stringify(stored.pending)!==JSON.stringify(r))fail()}
export function clearFabricRequest(scope:string,id:string){const stored=readFabricRequest(scope);if(stored.error||stored.pending?.id!==id)fail();localStorage.removeItem(fabricRequestKey(scope))}
