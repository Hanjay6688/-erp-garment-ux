import {describe,expect,it} from 'vitest'
import {articles,rangeChange,stockAt} from '../worker-demo/src/demo/planner/inventory'
import {emptySession,plan,productFor,recipePattern} from '../worker-demo/src/demo/planner/model'
describe('master sizes, optional recipes and warehouse movement',()=>{
 const source=articles.find(a=>a.key==='Vivo 93001')!,target=articles.find(a=>a.key===source.pair)!,order=productFor('93001')!
 it('keeps opposite entries per exact size across two different commercial codes',()=>{
   const s=rangeChange(emptySession,'convert',source,{31:'1',32:'2',33:''},'Pindah merek','c1')
   expect(s.stockEvents?.[0].changes.map(c=>c.delta)).toEqual([-1,1,-2,2])
   expect(stockAt(source,'32',s)).toBe(10);expect(stockAt(target,'32',s)).toBe(5)
   expect(plan(order,s).short).toBe(20)
   expect(rangeChange(s,'convert',source,{31:'1',32:'2'},'Pindah merek','c1')).toBe(s)
   expect(()=>rangeChange(s,'convert',source,{31:'1',32:'16'},'Test','c2')).toThrow()
   expect(()=>rangeChange(s,'convert',source,{32:'1'},'Test','c3',{32:12})).toThrow()
 })
 it('distinguishes a counted zero, an uncounted slot, and a special master size',()=>{
   const single=articles.find(a=>a.sizes.length===1)!
   const s=rangeChange(emptySession,'adjust',single,{27:'0'},'Hitung fisik','adj')
   expect(stockAt(single,'27',s)).toBe(0)
   expect(()=>rangeChange(s,'adjust',single,{28:'1'},'Salah ukuran','err')).toThrow()
   expect(()=>rangeChange(emptySession,'adjust',source,{31:'',32:''},'Belum hitung','err')).toThrow()
 })
 it('keeps an absent planned pattern separate from observed cutting and firm laundry',()=>{
   const s={...emptySession,patternRefs:{'Vivo 93001':null}}
   expect(recipePattern(order,s)).toBeNull()
   expect(plan(order,s)).toMatchObject({reference:null,confirmed:18,potential:0})
   expect(plan(order,{...s,patternRefs:{'Vivo 93001':'KJ'}})).toMatchObject({reference:'KJ',confirmed:18,potential:24})
 })
})
it('refuses changed values on a retry without changing a stock receipt',()=>{
  const article=articles[0],s=rangeChange(emptySession,'adjust',article,{32:'1'},'Hitung','a1')
  expect(()=>rangeChange(s,'adjust',article,{32:'0'},'Hitung','a1')).toThrow('isi berbeda')
})
it('reverses every size once, preserves the posted receipt and prevents an unbalanced undo',async()=>{
  const {reverseRange}=await import('../worker-demo/src/demo/planner/inventory'),article=articles[0]
  const posted=rangeChange(emptySession,'convert',article,{31:'1',32:'2'},'Tukar merek','original')
  const later=rangeChange(posted,'adjust',article,{32:'0'},'Opname','later')
  expect(()=>reverseRange(later,'original','reverse','Koreksi')).toThrow('lanjutan')
  const undone=reverseRange(posted,'original','reverse','Koreksi')
  expect(reverseRange(undone,'original','reverse','Koreksi')).toBe(undone)
  expect(undone.stockEvents?.length).toBe(2);expect(stockAt(article,'31',undone)).toBe(stockAt(article,'31',emptySession));expect(stockAt(article,'32',undone)).toBe(stockAt(article,'32',emptySession))
})
