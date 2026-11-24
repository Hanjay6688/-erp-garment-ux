import { describe, expect, it } from 'vitest'
import { accessorySeeds, accessoryRateSeeds, issueQuote, saveRateVersion, saveSpecial } from '../worker-demo/src/demo/accessoryPricing'
import type {AccessoryBook} from '../worker-demo/src/demo/accessoryPricing'
import { sizeRangeLabel } from '../worker-demo/src/sizeRangeLabel'

const item=accessorySeeds.find(i=>i.name.endsWith('Metal'))!
const fixture=():AccessoryBook=>({items:accessorySeeds,rates:accessoryRateSeeds,special:[],free:[]})
const special=(book:AccessoryBook,amount:number|null,start:string)=>saveSpecial(book,{id:start,amount,mandor:'Afui',category:'Kancing',start,unit:'pcs'})

describe('accessory category and contractor',()=>{
 it('keeps regular, reimbursement and weighted cost independent',()=>{
  const book=fixture()
  expect(issueQuote(book,item,'Afui','2026-11-20')).toMatchObject({per:495,reimbursement:500,hpp:690,hasSpecial:false})
  expect(issueQuote(book,accessorySeeds[3],'Afui','2026-11-20')).toMatchObject({per:null,source:'Harga master belum diatur'})
 })
 it('prices the actual note date and returns to the prevailing normal on clearing',()=>{
  let book=special(fixture(),450,'2026-11-22')
  book=special(book,null,'2026-11-24')
  const changes=book.rates.map(r=>r.category!=='Kancing'?r:{...r,sellingPrices:saveRateVersion(r.sellingPrices,{id:'updated',amount:520,uom:'pcs',effectiveFrom:'2026-11-23',note:'',status:'CURRENT'})})
  book={...book,rates:changes}
  expect(['2026-11-20','2026-11-22','2026-11-23','2026-11-24'].map(d=>issueQuote(book,item,'Afui',d).per)).toEqual([495,450,450,520])
  expect(issueQuote(book,item,'Selo','2026-11-23').per).toBe(520)
  expect(book.special[0].amount).toBeNull()
 })
 it('requires an explicit policy for this mandor and category on the note date',()=>{
  const book={...fixture(),free:[{mandor:'Afui',categories:['Kancing'],start:'2026-11-24',end:'2026-11-25',version:'2'}]}
  expect(issueQuote(book,item,'Mandor Afui','2026-11-24','FREE')).toMatchObject({per:0,version:'2',reimbursement:500,hpp:690})
  for(const d of ['2026-11-23','2026-11-25'])expect(issueQuote(book,item,'Afui',d,'FREE').per).toBeNull()
  expect(issueQuote(book,item,'Epi','2026-11-24','FREE').per).toBeNull()
  expect(issueQuote(book,accessorySeeds[3],'Afui','2026-11-24','FREE').per).toBeNull()
  expect(issueQuote(book,item,'Afui','2026-11-24','MANUAL',0).per).toBeNull()
 })
})
it('shows only real contiguous SKU members, including a single size',()=>{
 expect(sizeRangeLabel(['33','29','28','30','32','29'])).toBe('28–30, 32–33')
 expect(sizeRangeLabel(['27'])).toBe('27')
 expect(sizeRangeLabel(['M','S','L'])).toBe('S–L')
 expect(sizeRangeLabel(['ONE SIZE'])).toBe('ONE SIZE')
})

it('uses the native PCS and decimal price rules for packages and free billing',async()=>{
 const {validAccessoryRetail,exactAccessoryQuantity,micro,previewAccessoryLine}=await import('../worker-demo/src/accessoryIssue')
 expect(exactAccessoryQuantity(7n,micro('12'))).toBe(false)
 expect(exactAccessoryQuantity(3n,micro('12'))).toBe(true)
 expect(validAccessoryRetail('0')).toBe(false)
 expect(validAccessoryRetail('3,25')).toBe(true)
 expect(validAccessoryRetail('3,251')).toBe(false)
 const item={id:'button',sku:'B',name:'Kancing',unit:'PCS',category:'Kancing',stock:'12',price_version_id:'v1',master_price:'0.000000',price_unit:'PCS',factor:'1.000000'}
 expect(previewAccessoryLine({material_id:item.id,qty:'7',mode:'MASTER',manual_price:''},item).payload).toBeNull()
})
