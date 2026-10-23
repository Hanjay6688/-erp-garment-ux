import {expect,it} from 'vitest'
import {materialDraftOf,materialChanged,materialPayload,parseMaterialSaveResult,parseMaterialWorkspace} from './materialReorderContract'
import {materialRow,materialWire,type MaterialWireRow} from '../tests/fixtures/materialReorder'
const query={material_type:'FABRIC' as const,q:'',filter:'ALL' as const,offset:0,limit:25}
const wire=(r:MaterialWireRow)=>materialWire([r],query,{contract_version:'cp7.material-reorder.v2'})
const formula=()=>({...materialRow(1),legacy_minimum_qty:'500.0000',fabric_rule:'FORMULA',point:'63.34'})
const selected=()=>({...materialRow(1),legacy_minimum_qty:'1000.0000',fabric_rule:'LEGACY_MINIMUM',manual_point:'900.0000',manual_source:'FABRIC_MINIMUM',point:'900.0000',basis:'MANUAL',reason:null})
it('reads v1 archives and v2 with a separate read-only reference and one active formula',()=>{
 expect(parseMaterialWorkspace(materialWire([materialRow(1)],query),query).page.rows[0].legacyMinimumQty).toBeNull()
 expect(parseMaterialWorkspace(wire(formula()),query).page.rows[0]).toMatchObject({fabricRule:'FORMULA',legacyMinimumQty:'500.0000',manualPoint:null,basis:'FORMULA',point:'63.34'})
})
it('preserves a selected minimum even when the old reference later differs',()=>{
 expect(parseMaterialWorkspace(wire(selected()),query).page.rows[0]).toMatchObject({fabricRule:'LEGACY_MINIMUM',legacyMinimumQty:'1000.0000',manualPoint:'900',point:'900'})
})
it.each(['partial','missing-mode','double-active','manual-without-selection','wrong-previous-reference','accessory-injection','bad-version'])('refuses inconsistent rule state: %s',kind=>{
 const r:MaterialWireRow=formula(),v=wire(r)
 if(kind==='partial')delete r.legacy_minimum_qty
 if(kind==='missing-mode')delete r.fabric_rule
 if(kind==='double-active')Object.assign(r,{manual_point:500,manual_source:'FABRIC_MINIMUM',basis:'MANUAL',point:500})
 if(kind==='manual-without-selection')r.fabric_rule='LEGACY_MINIMUM'
 if(kind==='wrong-previous-reference')r.fabric_rule=null
 if(kind==='accessory-injection')r.material_type='ACCESSORY'
 if(kind==='bad-version')v.contract_version='cp7.material-reorder.v3'
 expect(()=>parseMaterialWorkspace(v,query)).toThrow()
})
it('sends a deliberate choice and exact observed reference, while an ordinary lead edit preserves the active rule',()=>{
 const r=parseMaterialWorkspace(wire(selected()),query).page.rows[0],d={...materialDraftOf(r),reason:'Pilihan yang saya periksa'}
 expect(materialChanged('FABRIC',r,d)).toBe(false)
 expect(materialPayload(r,'FABRIC',{...d,lead:'7'})).not.toHaveProperty('fabric_rule')
 const chosen={...d,fabricRule:'FORMULA' as const}
 expect(materialChanged('FABRIC',r,chosen)).toBe(true)
 expect(materialPayload(r,'FABRIC',chosen)).toMatchObject({fabric_rule:'FORMULA',expected_legacy_minimum_qty:'1000.0000',manual_point:null})
 expect(()=>materialPayload({...r,legacyMinimumQty:null},'FABRIC',{...d,fabricRule:'LEGACY_MINIMUM'})).toThrow()
})
it('binds a save outcome to the exact chosen rule and pinned quantity',()=>{
 const row=selected(),r=parseMaterialWorkspace(wire(row),query).page.rows[0]
 const payload=materialPayload(r,'FABRIC',{...materialDraftOf(r),fabricRule:'LEGACY_MINIMUM',reason:'Saya periksa minimum lama'})
 const out={replay:false,material_id:r.materialId,revision:r.settingRevision!+1,evaluation:{...row,setting_revision:r.settingRevision!+1,manual_point:'1000.0000',point:'1000.0000'}}
 expect(parseMaterialSaveResult(out,payload,'FABRIC').evaluation?.point).toBe('1000')
 expect(()=>parseMaterialSaveResult({...out,evaluation:{...out.evaluation,manual_point:'900.0000',point:'900.0000'}},payload,'FABRIC')).toThrow()
})
