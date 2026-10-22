// @vitest-environment jsdom
import {beforeEach,expect,it}from 'vitest'
import {persistMaterialRequest,readMaterialRequests}from './materialReorderRequests'
beforeEach(()=>localStorage.clear())
it.each(['500.000000','500.123456'])('persists the exact first Native fabric request (revision zero, formula choice, read-only decimal reference %s)',reference=>{
 const r={id:'ff0456e9-afad-45df-9a50-f76352ce3a9d',label:'Kain SS2 CEE08341',payload:{material_id:'49db9d9e-67b4-44c6-8e8b-553f38557247',expected_revision:0,lead_days:'6',manual_point:null,reason:'OW14b reviewed formula',fabric_rule:'FORMULA' as const,expected_legacy_minimum_qty:reference}}
 persistMaterialRequest('disposable:Native-owner','FABRIC',r)
 expect(readMaterialRequests('disposable:Native-owner','FABRIC').pending).toEqual([r])
})
