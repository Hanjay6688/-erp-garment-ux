// @vitest-environment jsdom
import {beforeEach,expect,it} from 'vitest'
import {clearMaterialRequest,materialRequestDefinitelyRefused,materialRequestPrefix,persistMaterialRequest,readMaterialRequests,type MaterialRequest} from './materialReorderRequests'
import {materialId} from '../tests/fixtures/materialReorder'
const scope='disposable:owner-A'
const first=():MaterialRequest=>({id:'11111111-1111-4111-8111-111111111111',label:'Kain yang diperiksa',payload:{material_id:materialId(1),expected_revision:2,
 lead_days:'6.50',manual_point:null,reason:'Saya memilih aturan',fabric_rule:'LEGACY_MINIMUM',expected_legacy_minimum_qty:'1000.0000'}})
beforeEach(()=>localStorage.clear())
it('recovers the original complete payload and UUID after a fresh reader, with no decimal conversion',()=>{
 const r=first();persistMaterialRequest(scope,'FABRIC',r);expect(readMaterialRequests(scope,'FABRIC')).toEqual({pending:[r],error:''})
 expect(()=>persistMaterialRequest(scope,'FABRIC',{...r,payload:{...r.payload,fabric_rule:'FORMULA'}})).toThrow()
 expect(readMaterialRequests(scope,'FABRIC').pending).toEqual([r])
})
it('retains both simultaneous same-revision intents and completes only the acknowledged one',()=>{
 const a=first(),b={...first(),id:'22222222-2222-4222-8222-222222222222'}
 persistMaterialRequest(scope,'FABRIC',a);persistMaterialRequest(scope,'FABRIC',b)
 expect(readMaterialRequests(scope,'FABRIC').pending).toEqual([a,b]);clearMaterialRequest(scope,'FABRIC',a)
 expect(readMaterialRequests(scope,'FABRIC').pending).toEqual([b])
})
it('does not mix another actor, project or material kind into recovery',()=>{
 persistMaterialRequest(scope,'FABRIC',first())
 for(const key of['disposable:owner-B','another-project:owner-A'])expect(readMaterialRequests(key,'FABRIC').pending).toEqual([])
 expect(readMaterialRequests(scope,'ACCESSORY').pending).toEqual([])
})
it.each(['json','smuggled','pair','wrong-type'])('preserves a corrupt pending record without silently repairing it: %s',kind=>{
 const r=first(),raw={contract_version:'cp7.material-request.v1',material_type:'FABRIC',...r}
 if(kind==='smuggled')Object.assign(raw.payload,{extra:'untrusted'})
 if(kind==='pair')delete raw.payload.expected_legacy_minimum_qty
 if(kind==='wrong-type')raw.material_type='ACCESSORY'
 const original=kind==='json'?'broken':JSON.stringify(raw),key=materialRequestPrefix(scope,'FABRIC')+r.id
 localStorage.setItem(key,original);expect(readMaterialRequests(scope,'FABRIC').error).not.toBe('')
 expect(localStorage.getItem(key)).toBe(original)
})
it('refuses clearing a different payload and preserves the unanswered intent',()=>{
 const r=first();persistMaterialRequest(scope,'FABRIC',r)
 expect(()=>clearMaterialRequest(scope,'FABRIC',{...r,payload:{...r.payload,lead_days:'7'}})).toThrow()
 expect(readMaterialRequests(scope,'FABRIC').pending).toEqual([r])
})
it('only classifies post-replay/pre-insert refusals as definitely not appended',()=>{
 for(const message of['CP7_FORMULA_MATERIAL_STALE','CP7_FORMULA_FABRIC_REFERENCE_CHANGED','CP7_FORMULA_FABRIC_REFERENCE_NOT_SET'])expect(materialRequestDefinitelyRefused({message})).toBe(true)
 for(const message of['CP7_FORMULA_ACCESS_DENIED','CP7_FORMULA_MATERIAL_ACCESS_CHANGED','CP7_FORMULA_REQUEST_REUSED','fetch failed'])expect(materialRequestDefinitelyRefused({message})).toBe(false)
})
