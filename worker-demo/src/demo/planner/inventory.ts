import {dayOk} from '../warehouseDay'
import { articles, type Article, type Session, type StockChange, type StockEvent } from './model'
export {articles,type Article} from './model'
import {stockAt,convertStock} from './conversion'
import {skuByKey,nativePosition,mainFg,pairOf} from '../skuCatalog'
export {stockAt} from './conversion'
export function rangeChange(session:Session,action:StockEvent['action'],article:Article,values:Record<string,string>,reason:string,id:string,expected?:Record<string,number>,notes?:string,date='2026-11-24',physicalTime=''):Session {
  if(!dayOk(date)||(physicalTime&&!/^([01]\d|2[0-3]):[0-5]\d$/.test(physicalTime)))throw Error('Periksa tanggal dan jam fisik.')
  if(action==='convert'){
    const partner=pairOf(session,article.key)
    if(!partner)throw Error('Pilih SKU tujuan.')
    return convertStock(session,{source:article.key,target:partner,values,sizeMap:Object.fromEntries(article.sizes.map(x=>[x,x])),...nativePosition(article),date,physicalTime,reason,notes},id,expected?Object.fromEntries([article,skuByKey(partner)!].flatMap(a=>a.sizes.map(size=>[a.key+'|'+size,a.key===article.key?expected[size]:stockAt(a,size,session)]))):undefined)
  }
  const intent=JSON.stringify([action,article.key,Object.entries(values).filter(([,v])=>v.trim()).sort(([a],[b])=>a.localeCompare(b)),reason.trim(),notes?.trim()||null,...(date!=='2026-11-24'||physicalTime?[date,physicalTime]:[])])
  const previous=session.stockEvents?.find(e=>e.id===id)
  if(previous){if(previous.intent&&previous.intent!==intent)throw Error('Permintaan ini sudah dipakai dengan isi berbeda.');return session}
  const known=articles.find(a=>a.key===article.key)
  if(!known||!reason.trim()||!id)throw Error('Pilih SKU dan isi alasan pencatatan.')
  const changes:StockChange[]=[]
  for(const [size,raw] of Object.entries(values)){
    if(!raw.trim())continue
    const qty=Number(raw)
    if(!known.sizes.includes(size)||!/^\d{1,9}$/.test(raw)||!Number.isSafeInteger(qty))throw Error('Isi jumlah pcs bulat sesuai ukuran master.')
    const before=stockAt(known,size,session)
    if(expected&&expected[size]!==before)throw Error('Stok berubah. Buka kembali pratinjau.')
    if(action==='adjust'&&qty>before)throw Error('Untuk kelebihan lot hasil produksi, periksa penerimaan barang jadi atau koreksi sumbernya.')
    const delta=qty-before
    if(!delta)continue
    changes.push({key:known.key,size,delta,after:before+delta})

  }
  if(!changes.length)throw Error('Isi setidaknya satu ukuran yang berubah.')
  return {...session,stockEvents:[...(session.stockEvents??[]),{id,action,intent,date,physicalTime:physicalTime||undefined,recordedAt:new Date().toISOString(),reason:reason.trim(),notes:notes?.trim()||null,changes}]}
}

export function reverseRange(session:Session,originalId:string,id:string,reason:string):Session {
  const events=session.stockEvents??[],before=events.findIndex(e=>e.id===originalId),original=events[before],note=reason.trim()
  if(!original||original.reverses||!id||!note)throw Error('Pilih transaksi asal dan isi alasan pembalikan.')
  const replay=events.find(e=>e.id===id)
  if(replay){if(replay.reverses!==originalId||replay.reason!==note)throw Error('Isi pembalikan berbeda.');return session}
  if(events.some(e=>e.reverses===originalId))throw Error('Transaksi sudah dibalik.')
  const samePosition=(a:StockChange,b:StockChange)=>a.key===b.key&&a.size===b.size&&(a.location??mainFg)===(b.location??mainFg)&&(a.grade??'Good')===(b.grade??'Good')
  if(events.slice(before+1).some(e=>!e.reverses&&!events.some(r=>r.reverses===e.id)&&e.changes.some(c=>original.changes.some(o=>samePosition(c,o)))))throw Error('Masih ada transaksi lanjutan untuk ukuran ini. Periksa transaksi terbaru.')
  const changes=original.changes.map(c=>({...c,delta:-c.delta}));for(const c of changes){const a=skuByKey(c.key);c.after=a?stockAt(a,c.size,session,c.location??mainFg,c.grade??'Good')+c.delta:-1;if(c.after<0)throw Error('Stok saat ini tidak cukup untuk pembalikan.')}
  return {...session,stockEvents:[...events,{id,action:original.action,date:original.date??'2026-11-24',recordedAt:new Date().toISOString(),reverses:original.id,reason:note,changes}]}
}
