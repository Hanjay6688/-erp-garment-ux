// @vitest-environment jsdom
import {expect,it} from 'vitest'
import {fabricKey,operationalFabricRolls,pocketHistoryRolls,rollBalance,rollTotalsByUnit,stockLengths} from '../worker-demo/src/demo/materialRollHistory'
import {correctionRolls,emptySession,yardsLeft,type Session} from '../worker-demo/src/demo/planner/model'
import {archiveDocumentFor,archiveDocuments,archiveIdentity,archiveSource} from '../worker-demo/src/demo/fabricArchive'
import {correctFabricIdentity,correctFabricReceiptRoll} from '../worker-demo/src/demo/fabricReceipts'
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

it('groups the lengths in their posted unit, including switches, canceled receipts and zero balances',()=>{
  const a={id:'A',number:'SJ-A',material:'Katun',supplier:'Pabrik',day:'2026-11-22',unit:'m' as const,rate:400,rolls:[{id:'A-1',length:3.123456}]}
  const b={...a,id:'B',number:'SJ-B',unit:'yd' as const,rolls:[{id:'B-1',length:0.123456}],reversal:{reason:'Duplikat',at:'2026-11-23T03:00:00Z'}}
  const session={...emptySession,fabricReceipts:[a,b]}
  const totals=rollTotalsByUnit(operationalFabricRolls(session).filter(roll=>roll.material==='Katun'))
  expect(totals.get('m')).toEqual({received:3.123456,used:0,returned:0,balance:3.123456})
  expect(totals.get('yd')).toEqual({received:0,used:0,returned:0,balance:0})
})

it('opens the individual source for each type of incoming fabric even when no supplier receipt exists',()=>{
  const seeds=operationalFabricRolls(emptySession)
  for(const roll of seeds)expect(roll.events[0].source?.href).toContain('arsip='+roll.id)
  for(const doc of archiveDocuments)for(const line of doc.lines)expect(archiveDocumentFor(line.id)).toBe(doc)
  expect(archiveDocumentFor('LCY-031')?.lines.map(r=>r.id)).toEqual(['LCY-031','LCY-030'])
  expect(archiveSource('LCY-029').label).toBe('Buka retur masuk')
  expect(archiveSource('LCY-022').label).toBe('Buka saldo awal')
  expect(archiveDocumentFor('KW-023')?.key).not.toBe(archiveDocumentFor('LCY-022')?.key)
})

it('corrects only the source in scope, preserves quantities, checks physical codes and rejects stale edits',()=>{
  const source=archiveDocumentFor('LCY-031')!.key
  const edit={id:'1',source,before:'Lucy',after:'Lucy Twill',reason:'Cek label pabrik',at:'2026-11-25T08:00:00Z'}
  const changed=correctFabricIdentity(emptySession,edit)
  expect(correctFabricIdentity(changed,edit)).toBe(changed)
  expect(archiveIdentity(changed,'LCY-030').material).toBe('Lucy Twill')
  expect(archiveIdentity(changed,'LCY-028').material).toBe('Lucy')
  expect(()=>correctFabricIdentity(changed,{...edit,id:'2',after:'Lucy C'})).toThrow(/sudah berubah/)
  const rollEdit={...edit,id:'r',roll:'LCY-031',before:'LCY-031',after:'LCY-022'}
  expect(()=>correctFabricIdentity(changed,rollEdit)).toThrow(/roll lain/)
  expect(()=>correctFabricIdentity(changed,{...rollEdit,after:'LCY-028'})).toThrow(/roll lain/)
  const physical=correctFabricIdentity(changed,{...rollEdit,after:'SNR-Fisik-31'})
  expect(archiveIdentity(physical,'LCY-031').physicalCode).toBe('SNR-Fisik-31')
  expect(archiveIdentity(physical,'LCY-030').physicalCode).toBeUndefined()
  const doc={id:'new',number:'SJ-R',material:'Katun',supplier:'Sinaran',day:'2026-11-23',unit:'yd' as const,rate:200,rolls:[{id:'SJ-R-01',length:20}]}
  const saved=correctFabricIdentity({...physical,fabricReceipts:[doc]},{...edit,id:'s',source:'penerimaan:new',before:'Katun',after:'Twill'})
  const projected=operationalFabricRolls(saved).find(r=>r.id==='SJ-R-01')!
  expect([projected.material,rollBalance(projected),correctionRolls(saved).find(r=>r.id===projected.id)?.material]).toEqual(['Twill',20,'Twill'])
  expect(projected.events.map(e=>e.delta)).toEqual([20,0])
  expect(doc.material).toBe('Katun')
  expect(()=>correctFabricReceiptRoll(saved,'new','SJ-R-01',{id:'d',length:20,code:'SNR-Fisik-31',reason:'Cek label',at:edit.at})).toThrow(/roll lain/)
  expect(()=>correctFabricIdentity({...saved,fabricReceipts:[{...doc,reversal:{reason:'Batal',at:edit.at}}]},{
    ...edit,source:'penerimaan:new',id:'late',before:'Twill'})).toThrow(/aktif/)
})
