// @vitest-environment jsdom
import {expect,it} from 'vitest'
import {fabricKey,operationalFabricRolls,pocketHistoryRolls,rollBalance,stockLengths} from '../worker-demo/src/demo/materialRollHistory'
import {emptySession,yardsLeft,type Session} from '../worker-demo/src/demo/planner/model'
import type {PocketReceipt} from '../worker-demo/src/demo/pocketReceipts'

it('keeps both sides of a switched cut under their physical materials and preserves a later reversal',()=>{
  const session:Session={...emptySession,fabricReceipts:[
    {id:'a',number:'SJ-KW',material:'1069 KW',supplier:'Pabrik A',day:'2026-11-20',unit:'yd',rate:40000,rolls:[{id:'R-KW',length:40}],
      corrections:[{id:'c',roll:'R-KW',beforeLength:40,length:42,physicalCode:'FISIK-01',reason:'Ukur fisik',at:'2026-11-22T08:00:00Z'}]},
    {id:'b',number:'SJ-M',material:'1069 kw',supplier:'Pabrik B',day:'2026-11-20',unit:'m',rate:48000,rolls:[{id:'R-M',length:9.5}]},
  ],rollCorrections:[{id:'sw',cut:'POT-021',original:'ORI-018',from:'ORI-018',to:'R-KW',yards:36,reason:'Roll fisik benar',at:'2026-11-25T10:00:00Z',costDifference:null}]}
  const book=operationalFabricRolls(session)
  const replacement=book.find(r=>r.id==='R-KW')!
  expect(replacement.label).toBe('FISIK-01')
  expect(replacement.events.map(e=>e.delta)).toEqual([40,2,-36])
  expect(rollBalance(replacement)).toBe(yardsLeft('R-KW',session))
  expect(book.find(r=>r.id==='ORI-018')!.events.map(e=>e.delta)).toEqual([50,-36,36])
  expect(stockLengths(book.filter(r=>r.materialKey===fabricKey('1069 KW')))).toBe('76 yd · 9,5 m')
  const back=operationalFabricRolls({...session,cutReversals:{'POT-021':{reason:'Dibatalkan',at:'2026-11-25T11:00:00Z'}}})
  expect(rollBalance(back.find(r=>r.id==='R-KW')!)).toBe(42)
  expect(rollBalance(back.find(r=>r.id==='ORI-018')!)).toBe(50)
  expect(fabricKey('Denim 1069 Ori')).toBe(fabricKey('1069 Ori'))
})

it('retains an exhausted or reversed pocket roll by master identity, including undated legacy reversals',()=>{
  const document:PocketReceipt={request:'pr',number:'SJ-KT',supplier:'Pabrik',day:'2026-11-20',reason:'Terima',notes:null,
    rolls:[{id:'new',name:'Kain putih',materialId:'pabrik-a',length:12,rate:1000,unit:'m',date:'2026-11-20',location:'Gudang',receipt:'SJ-KT'}]}
  const issue={id:'P-01',roll:'new',date:'2026-11-21',qty:12000000,cents:1200000,reason:'Pakai'}
  const rows=pocketHistoryRolls([document],{issues:[issue],allocations:[]})
  const roll=rows.find(r=>r.materialKey==='pabrik-a')!
  expect(rollBalance(roll)).toBe(0)
  expect(roll.events.map(row=>row.delta)).toEqual([12,-12])
  const reversed=pocketHistoryRolls([{...document,reversal:{reason:'Salah',at:'2026-11-24T07:00:00Z'}}],
    {issues:[{...issue,reversal:'Dikembalikan'}],allocations:[]}).find(r=>r.id==='new')!
  expect(reversed.voided).toBe(true)
  expect(rollBalance(reversed)).toBe(0)
  expect(reversed.events.find(row=>row.title==='Pembalikan pemakaian')?.at).toBe('')
})
