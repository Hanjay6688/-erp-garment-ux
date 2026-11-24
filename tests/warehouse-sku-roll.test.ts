// @vitest-environment jsdom
import {beforeEach,describe,expect,it} from 'vitest'
import {emptySession} from '../worker-demo/src/demo/planner/model'
import {convertStock,moveSnapshot,type MoveInput} from '../worker-demo/src/demo/planner/conversion'
import {reverseRange} from '../worker-demo/src/demo/planner/inventory'
import {pairOf,pairSku,mainFg} from '../worker-demo/src/demo/skuCatalog'
import {fgProducts,fgTotals} from '../worker-demo/src/demo/fgOverview'
import {historyRows} from '../worker-demo/src/demo/FgHistory'
import {pocketRolls,receivePocket,reverseReceipt,type ReceiptDraft} from '../worker-demo/src/demo/pocketReceipts'

const move:MoveInput={source:'Vivo 93001',target:'Widie 73005',values:{31:'2',32:'3'},sizeMap:{31:'33',32:'33'},location:mainFg,grade:'Good',date:'2026-11-24',reason:'Koreksi label'}
beforeEach(()=>sessionStorage.clear())
describe('Warehouse workflows',()=>{
  it('sets, replaces and clears one commercial pair in both directions without stock entries',()=>{
    const s=pairSku(emptySession,'Vivo 93001','Widie 66001')
    expect(pairOf(s,'Widie 66001')).toBe('Vivo 93001')
    expect(pairOf(s,'Vivo 66001')).toBe(null);expect(pairOf(s,'Widie 66002')).toBe(null)
    const cleared=pairSku(s,'Widie 66001',null)
    expect(pairOf(cleared,'Vivo 93001')).toBe(null);expect(cleared.stockEvents).toBeUndefined()
  })
  it('moves two source sizes into one arbitrary SKU size at the same location and reverses',()=>{
    const base=pairSku(emptySession,move.source,null),s=convertStock(base,move,'A')
    const target=fgProducts(s).find(p=>p.brand==='Widie'&&p.code==='73005'&&p.location===mainFg)!
    expect(target.stocks).toEqual([0,0,5]);expect(historyRows(target,s)[0].delta).toEqual([0,0,5])
    expect(fgTotals(fgProducts(s))).toEqual(fgTotals(fgProducts(base)))
    expect(convertStock(s,move,'A')).toBe(s)
    const back=reverseRange(s,'A','B','Pulihkan');expect(fgTotals(fgProducts(back))).toEqual(fgTotals(fgProducts(base)))
    expect(fgProducts(back).find(p=>p.brand==='Widie'&&p.code==='73005'&&p.location===mainFg)?.stocks).toEqual([0,0,0])
  })
  it('refuses silent size selection, identical products and stale destination balances',()=>{
    expect(()=>convertStock(emptySession,{...move,sizeMap:{}},'a')).toThrow('ukuran tujuan')
    expect(()=>convertStock(emptySession,{...move,target:move.source},'a')).toThrow('berbeda')
    const snap=moveSnapshot(emptySession,move)
    const s=convertStock(emptySession,{...move,source:'Vivo 73002'},'other')
    expect(()=>convertStock(s,move,'a',snap)).toThrow('Stok berubah')
  })
  it('does not move a newly received size before its physical date',()=>{
    const first=convertStock(emptySession,move,'F')
    expect(()=>convertStock(first,{...move,source:move.target,target:'Vivo 73003',values:{33:'1'},sizeMap:{33:'34'},date:'2026-11-23'},'B')).toThrow('stok asal')
  })
  const receipt:ReceiptDraft={request:'pr1',number:'SJ-UJI-01',supplier:'Sinaran',location:'Gudang Bahan',material:'Kain kantong hitam',day:'2026-11-24',unit:'m',rate:'9000',reason:'Surat jalan',notes:'',rolls:[{number:'U-01',qty:'19,5'},{number:'U-02',qty:'7'},{number:'',qty:''}]}
  it('posts one purchase with individual rolls, keeps their original unit and refuses duplicates',()=>{
    expect(receivePocket(receipt).notes).toBeNull();expect(receivePocket(receipt).rolls).toHaveLength(2)
    expect(pocketRolls().slice(-2).map(r=>[r.id,r.length,r.unit])).toEqual([['U-01',19.5,'m'],['U-02',7,'m']])
    expect(()=>receivePocket({...receipt,request:'new'})).toThrow('surat jalan')
    expect(()=>receivePocket({...receipt,number:'SJ-DUP',request:'new'})).toThrow('roll')
    sessionStorage.setItem('erp.demo.pocket.period.v1',JSON.stringify({issues:[{roll:'U-02'}],allocations:[]}))
    expect(()=>reverseReceipt(receipt.number,'Salah')).toThrow('sudah dipakai')
    sessionStorage.removeItem('erp.demo.pocket.period.v1');reverseReceipt(receipt.number,'Salah nomor')
    expect(pocketRolls().some(r=>r.id==='U-02')).toBe(false)
  })
})
