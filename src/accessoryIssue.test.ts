import { describe, expect, it } from 'vitest'
import { accessoryUuid, displayMoney, micro, previewAccessoryLine, type AccessoryChoice } from './accessoryIssue'
const material: AccessoryChoice = { id:'11111111-1111-4111-8111-111111111111',sku:'BTN',name:'Kancing',unit:'PCS',category:'Kancing',stock:'300.000000',price_version_id:'22222222-2222-4222-8222-222222222222',master_price:'36.000000',price_unit:'LUSIN',factor:'12.000000' }
describe('exact accessory quantity and independent retail price',()=>{
  it('keeps seven pcs separate from dozen/gross master pricing',()=>{
    for(const factor of ['12.000000','144.000000']){
      const p=previewAccessoryLine({material_id:material.id,qty:'7',mode:'MANUAL',manual_price:'3,25'},{...material,factor})
      expect(p.amount).toBe(22750000n);expect(p.payload).toEqual({material_id:material.id,qty:'7',mode:'MANUAL',manual_price:'3.25'})
    }
  })
  it('refuses a rounded package fraction and keeps configured package prices for exact quantities',()=>{
    expect(previewAccessoryLine({material_id:material.id,qty:'7',mode:'MASTER',manual_price:''},material).payload).toBeNull()
    const p=previewAccessoryLine({material_id:material.id,qty:'12',mode:'MASTER',manual_price:''},material)
    expect(p.amount).toBe(36000000n);expect(p.payload?.qty).toBe('12');expect(p.payload?.price_version_id).toBe(material.price_version_id)
  })
  it.each(['7.1','7,1','-7','0','7e0','seven',' 7','7000000000000'])('rejects physical quantity %s without rewriting it',qty=>{
    expect(previewAccessoryLine({material_id:material.id,qty,mode:'MANUAL',manual_price:'1'},material).payload).toBeNull()
  })
  it.each(['','-1','NaN','Infinity','3.251','1.000,00','Rp 2','1e3'])('rejects retail money %s without coercion',manual_price=>{
    expect(previewAccessoryLine({material_id:material.id,qty:'7',mode:'MANUAL',manual_price},material).payload).toBeNull()
  })
  it('distinguishes explicit zero from missing and keeps large money exact',()=>{
    expect(previewAccessoryLine({material_id:material.id,qty:'7',mode:'MANUAL',manual_price:'0'},material).amount).toBe(0n)
    const p=previewAccessoryLine({material_id:material.id,qty:'999999',mode:'MANUAL',manual_price:'999999999999.99'},material)
    expect(p.amount).toBe(999998999999990000010000n)
    expect(displayMoney(micro('9007199254740993.25'))).toBe('Rp 9.007.199.254.740.993,25')
  })
})
describe('D08: canonical UUID ids on the note page',()=>{
  it('accepts every canonical 8-4-4-4-12 id the uuid type produces, RFC or not, and refuses malformed ones',()=>{
    for(const id of ['a1000000-0000-0000-0000-000000000001','a2000000-0000-0000-0000-000000000001','11111111-1111-4111-8111-111111111111','00000000-0000-0000-0000-000000000000'])
      expect(accessoryUuid(id)).toBe(true)
    for(const id of ['','a1000000-0000-0000-0000-00000000001','a1000000-0000-0000-0000-0000000000011','g1000000-0000-0000-0000-000000000001',
      'a10000000000000000000000000000001','{a1000000-0000-0000-0000-000000000001}',' a1000000-0000-0000-0000-000000000001',
      'a1000000-0000-0000-0000-000000000001 ','a1000000_0000_0000_0000_000000000001',null,undefined,1])
      expect(accessoryUuid(id)).toBe(false)
  })
})
