import { describe, expect, it } from 'vitest'
import { confirmDestination, cutRolls, emptySession, eligiblePieces, modelSeries, patternFor, setDestination, lotsIn, plan, plansIn, productFor, recordCut, recordPickup, suggestedCut, waitingLots, yardsLeft } from '../worker-demo/src/demo/planner/model'

const cut = {requestId:'draft-1',sku:'93001',brand:'Vivo',model:'Kulot Jumbo',series:modelSeries['Kulot Jumbo'],pattern:patternFor('KJ'),location:'Gudang Kain',date:'2026-11-24',eta:'2026-11-27',slots:['31','32','33'],rolls:[{id:'ORI-021',yards:27,quantities:[0,18,0]}]}
const pieces=(n:number,yd:number)=>[{id:'ORI-021',yards:yd,quantities:[0,n,0]}]
const pickup = {id:'POT-017',mandor:'Mandor Epi',at:'2026-11-24T10:30',batches:[{qty:24,note:'Biru muda'}]}
describe('November garment orders',()=>{
  it('uses the dated SQL projections with unassigned, in-process and late supply separated',()=>{
    expect(plansIn(emptySession).map(r=>[r.product.sku,r.confirmed,r.potential,r.base,r.short,r.late])).toEqual([
      ['93001',18,24,42,18,0],['66001',0,24,24,0,0],['66002',60,0,0,0,0],['66003',6,12,12,0,12]])
    expect(waitingLots(emptySession).map(l=>l.id)).toEqual(['POT-017','POT-021'])
  })
  it('counts each new cut once, consumes its roll, and reduces only the order it fits',()=>{
    const first=recordCut(emptySession,{...cut,rolls:pieces(6,9)})
    expect(recordCut(first,{...cut,rolls:pieces(6,9)})).toBe(first)
    expect(yardsLeft('ORI-021',first)).toBe(51)
    expect(cutRolls(first.cuts[0])[0]).toMatchObject({sourceYards:60,usedYards:9,remainingYards:51})
    const lowFabric=recordCut(emptySession,{...cut,rolls:pieces(6,57)})
    expect(suggestedCut(plan(productFor('93001')!,lowFabric),lowFabric).qty).toBe(2)
    expect(plan(productFor('93001')!,first).short).toBe(12)
    const full=recordCut(first,{...cut,requestId:'second',rolls:pieces(12,18)})
    expect(plan(productFor('93001')!,full)).toMatchObject({short:0,base:42,potential:42})
    expect(plan(productFor('93001')!,recordCut(full,{...cut,requestId:'extra'})).short).toBe(0)
    expect(waitingLots(full)).toHaveLength(4)
    for(const change of [{rolls:[]},{slots:['27']},{rolls:pieces(0,12)},{rolls:pieces(2,61)},{date:'2026-02-30'}])expect(()=>recordCut(emptySession,{...cut,...change})).toThrow()
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
  it('opens only the new shortage when the sewing lot belongs to another order',()=>{
    const changed=confirmDestination(emptySession,'JHT-044','elsewhere')
    const row=plan(productFor('66003')!,changed)
    expect(row).toMatchObject({confirmed:6,potential:0,base:12,short:12,late:12})
    expect(suggestedCut(row,changed,'Black Virgo').roll.id).toBe('BVG-025')
    const made=recordCut(changed,{...cut,sku:'66003',brand:'Widie',model:'Cutbray Lucy',pattern:patternFor('CL'),series:modelSeries['Cutbray Lucy'],slots:['28','29','30'],rolls:[{id:'BVG-025',yards:15,quantities:[0,0,12]}]})
    expect(plan(row.product,made)).toMatchObject({base:12,short:0,potential:12})
    expect(waitingLots(made).find(l=>l.id==='POT-D01')).toMatchObject({size:'30',material:'Black Virgo'})
  })

  it('carries two rolls and repeated drawings through one neutral batch, and checks only matching pieces',()=>{
    const made=recordCut(emptySession,{...cut,sku:'',brand:'',eta:null,slots:['31','32','32','33'],rolls:[{id:'ORI-021',yards:8,quantities:[2,3,4,0]},{id:'KW-023',yards:5,quantities:[0,1,1,3]}]})
    const lot=made.cuts[0],p=productFor('93001')!
    expect(lot).toMatchObject({qty:14,sku:null,brand:null,eta:null})
    expect(cutRolls(lot)[0].slots.map(s=>s.size+s.image)).toEqual(['31','32A','32B','33'])
    expect(eligiblePieces(lot,p)).toBe(7)
    expect(plan(p,made)).toMatchObject({short:18,review:[{id:lot.id}]})
    expect(yardsLeft('ORI-021',made)).toBe(52)
    const assigned=setDestination(made,lot.id,p.sku,p.due)
    expect(plan(p,assigned)).toMatchObject({short:11,confirmed:25})
    const batch={qty:14,note:'',sizes:{'31':2,'32':9,'33':3},sources:[{rollId:'ORI-021',size:'31',qty:2},{rollId:'ORI-021',size:'32',qty:7},{rollId:'KW-023',size:'32',qty:2},{rollId:'KW-023',size:'33',qty:3}]}
    expect(()=>recordPickup(made,{...pickup,id:lot.id,batches:[{...batch,sizes:{'31':14}}]})).toThrow()
    const sewn=recordPickup(made,{...pickup,id:lot.id,batches:[batch]})
    expect(lotsIn(sewn).find(l=>l.id===lot.id)).toMatchObject({stage:'sewing',qty:14,sku:null,brand:null})
    expect(plan(p,sewn).review).toHaveLength(1)
    for (const [sku,brand] of [['','Vivo'],['93001',''],['','']]){
      expect(recordCut(emptySession,{...cut,sku,brand}).cuts[0]).toMatchObject({sku:sku||null,brand:brand||null})
    }
  })
})
