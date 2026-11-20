import original from './nativeAnalysisStandin.json'
import type {FabricConfig,FabricRequest} from '../../src/nativeFabricRecipe'
import type {AnalysisResult} from '../../src/cp7/contract'

// Synthetic receiver/DOM input only; Native qualification uses its own masters.
export const fabricMaterialId='00000000-0000-4000-8000-00000000f001',fabricPatternId='00000000-0000-4000-8000-00000000f002',fabricRecipeId='00000000-0000-4000-8000-00000000f003'
export const fabricConfig:FabricConfig={basis:'SELECTED_ASSUMPTIONS',effective_from:'2026-09-28T00:00:00Z',effective_to:null,material_id:fabricMaterialId,material_hash:'c'.repeat(64),unit:'M',qty_per_good_pcs:'2',pattern_id:fabricPatternId,pattern_hash:'d'.repeat(64)}
export function fabricWorkspaceFixture(){return{contract_version:'cp7.fabric-workspace.v1',actor_scope_id:original.analysis.scope.actor_scope_id,run_id:original.run_id,target_key:original.analysis.recommendations[0].target.key,source_hash:original.analysis.snapshot.source_hash,revision:'0',analysis:structuredClone(original),materials:[{id:fabricMaterialId,sku:'KAIN-TEST',name:'Kain fixture',unit:'M',source_hash:fabricConfig.material_hash}],patterns:[{id:fabricPatternId,code:'POLA-TEST',name:'Pola fixture',revision:'R1',source_hash:fabricConfig.pattern_hash}],recipes:[],page:{limit:50,material_offset:0,material_total:'1',pattern_offset:0,pattern_total:'1',recipe_total:'0',recipe_history_scope:'LATEST_50_REVISIONS'},apply_enabled:false,production_go:false}}
export function fabricOutcomeFixture(request:FabricRequest){return{contract_version:'cp7.fabric-outcome.v1',actor_scope_id:original.analysis.scope.actor_scope_id,request_id:request.id,recipe_id:fabricRecipeId,target_key:request.payload.target_key,revision:(BigInt(request.payload.expected_revision)+1n).toString(),quality:'SELECTED_ASSUMPTIONS',apply_enabled:false,production_go:false}}
export function fabricAnalysisFixture(){const x={...structuredClone(original),analysis:structuredClone(original.analysis)as unknown as AnalysisResult},target=x.analysis.recommendations[0].target.key
 x.analysis.assumptions.push({id:fabricRecipeId,label:'Pemakaian kain yang dipilih; bukan konsumsi aktual',origin:'OWNER_INPUT',confirmed_for_operation:false})
 const refs=[{kind:'CP7_FABRIC_RECIPE',id:fabricRecipeId,revision:'1'},{kind:'erp.materials',id:fabricMaterialId,revision:fabricConfig.material_hash},{kind:'erp.production_patterns',id:fabricPatternId,revision:fabricConfig.pattern_hash!}],unknown={state:'UNKNOWN' as const,unit:'M',reason:'SOURCE_INPUT_NOT_PROVEN',refs}
 x.analysis.material_needs.push({target_key:target,material_key:'FABRIC_MATERIAL:'+fabricMaterialId,gross:{state:'ASSUMED',value:'186',unit:'M',refs,assumption_ids:[fabricRecipeId]},installed_proven:structuredClone(unknown),unused_allocated_proven:structuredClone(unknown),additional_external:structuredClone(unknown),reason:'Kain fixture: pemakaian per PCS yang dipilih; pemasangan dan alokasi belum terbukti.'})
 return x
}
