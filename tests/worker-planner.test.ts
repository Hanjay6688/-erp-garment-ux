import { describe, expect, it } from 'vitest'
import { confirmDestination, emptySession, lotsIn, plan, plansIn, productFor, recordCut, recordPickup, waitingLots, yardsLeft } from '../worker-demo/src/demo/planner/model'

const cut = {requestId:'draft-1',sku:'93001',patternId:'contoh-kulot-jumbo',size:'32',roll:'ORI-021',qty:18,yards:27,date:'2026-11-24'}
const pickup = {id:'POT-017',mandor:'Mandor Epi',at:'2026-11-24T10:30',batches:[{qty:24,note:'Biru muda'}]}
describe('November garment orders',()=>{
  it('uses the dated SQL projections with unassigned, in-process and late supply separated',()=>{
    expect(plansIn(emptySession).map(r=>[r.product.sku,r.confirmed,r.potential,r.base,r.short,r.late])).toEqual([
      ['93001',18,24,42,18,0],['66001',0,24,24,0,0],['66002',60,0,0,0,0],['66003',6,12,12,0,12]])
    expect(waitingLots(emptySession).map(l=>l.id)).toEqual(['POT-017','POT-021'])
  })
  it('counts each new cut once, consumes its roll, and reduces only the order it fits',()=>{
    const first=recordCut(emptySession,{...cut,qty:6,yards:9})
    expect(recordCut(first,{...cut,qty:6,yards:9})).toBe(first)
    expect(yardsLeft('ORI-021',first)).toBe(51)
    expect(plan(productFor('93001')!,first).short).toBe(12)
    const full=recordCut(first,{...cut,requestId:'second',qty:12,yards:18})
    expect(plan(productFor('93001')!,full)).toMatchObject({short:0,base:42,potential:42})
    expect(()=>recordCut(full,{...cut,requestId:'extra'})).toThrow()
    expect(waitingLots(full)).toHaveLength(4)
    for(const change of [{roll:'KW-023'},{size:'31'},{qty:0},{qty:19},{yards:61},{date:'2026-11-23'}])expect(()=>recordCut(emptySession,{...cut,...change})).toThrow()
  })
  it('moves the same batch from cutting to sewing when picked up, including a newly cut batch',()=>{
    const picked=recordPickup(emptySession,pickup)
    expect(waitingLots(picked).map(l=>l.id)).toEqual(['POT-021'])
    expect(plan(productFor('66001')!,picked)).toMatchObject({confirmed:24,potential:0,base:0,short:0})
    expect(lotsIn(picked).filter(l=>l.id===pickup.id)).toHaveLength(1)
    expect(()=>recordPickup(picked,pickup)).toThrow()
    expect(()=>recordPickup(emptySession,{...pickup,batches:[{qty:23,note:''}]})).toThrow()
    const saved=recordCut(emptySession,cut)
    const finish=recordPickup(saved,{...pickup,id:'POT-D01',batches:[{qty:18,note:''}]})
    expect(plan(productFor('93001')!,finish)).toMatchObject({confirmed:36,potential:24,base:24,short:0})
  })
  it('confirms a sewing destination without creating stock or bringing late laundry forward',()=>{
    const change=confirmDestination(emptySession,'JHT-044')
    expect(plan(productFor('66003')!,change)).toMatchObject({confirmed:18,potential:0,base:0,short:0,late:12})
    expect(lotsIn(change)).toHaveLength(lotsIn(emptySession).length)
    expect(()=>confirmDestination(change,'JHT-044')).toThrow()
  })
})
