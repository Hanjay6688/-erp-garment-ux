// @vitest-environment jsdom
import {beforeEach,expect,it}from 'vitest'
import {persistMaterialRequest,readMaterialRequests}from './materialReorderRequests'
import {parseMaterialSaveResult,parseMaterialWorkspace,type MaterialPayload}from './materialReorderContract'
import {materialWire,type MaterialWireRow}from '../tests/fixtures/materialReorder'
import native from '../tests/fixtures/materialNativePaddedSave.json'
beforeEach(()=>localStorage.clear())
it.each(['500.000000','500.123456'])('persists the exact first Native fabric request (revision zero, formula choice, read-only decimal reference %s)',reference=>{
 const r={id:'ff0456e9-afad-45df-9a50-f76352ce3a9d',label:'Kain SS2 CEE08341',payload:{material_id:'49db9d9e-67b4-44c6-8e8b-553f38557247',expected_revision:0,lead_days:'6',manual_point:null,reason:'OW14b reviewed formula',fabric_rule:'FORMULA' as const,expected_legacy_minimum_qty:reference}}
 persistMaterialRequest('disposable:Native-owner','FABRIC',r)
 expect(readMaterialRequests('disposable:Native-owner','FABRIC').pending).toEqual([r])
})
it('accepts the complete first PostgreSQL save reply and refreshed row without rounding its padded point',()=>{
 const args=native.args,payload=args.p_payload as MaterialPayload
 expect(native.response.evaluation.point).toBe('39.3200000000000000')
 expect(parseMaterialSaveResult(native.response,payload,'FABRIC').evaluation).toMatchObject({point:'39.32',fabricRule:'FORMULA',legacyMinimumQty:'500.000000'})
 const q={material_type:'FABRIC' as const,q:'',filter:'ALL' as const,offset:0,limit:25}
 const ws=materialWire([native.response.evaluation as MaterialWireRow],q,{contract_version:'cp7.material-reorder.v2'})
 expect(parseMaterialWorkspace(ws,q).page.rows[0].point).toBe('39.32')
 for(const point of ['39.3200000000000001','39.32e0','+39.32','39.32.'+'0'.repeat(12)]){
  expect(()=>parseMaterialSaveResult({...native.response,evaluation:{...native.response.evaluation,point}},payload,'FABRIC')).toThrow()
 }
})
