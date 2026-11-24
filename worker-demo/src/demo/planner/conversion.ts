import {productCatalog} from '../../productCatalog'
import {baseSaleStock,readInvoices} from '../saleBook'
import {nativePosition,positionDelta,skuByKey} from '../skuCatalog'
import {dayOk} from '../warehouseDay'
import {fgActivity,comparePhysical,type FgMovement} from '../fgTimeline'
import {type Article,type Session,type StockChange} from './model'

export function stockAt(a:Article,size:string,s:Session,location=nativePosition(a).location,grade=nativePosition(a).grade) {
  const home=nativePosition(a),p=productCatalog.find(p=>p.brand===a.brand&&p.code===a.sku)
  const opening=location===home.location&&grade===home.grade?(p?baseSaleStock(p,readInvoices())[p.sizes.indexOf(size)]:a.opening[size]):0
  return (opening??0)+positionDelta(s,a.key,size,location,grade)
}
export function sizeBalanceAt(current:number,index:number,activity:FgMovement[],day:string,physicalTime=''){
  const cut={day,physicalTime}
  return activity.reduce((balance,row)=>row.day&&comparePhysical(row,cut)>0?balance-row.delta[index]:balance,current)
}
export type MoveInput={source:string;target:string;values:Record<string,string>;sizeMap:Record<string,string>;location:string;grade:string;date:string;physicalTime?:string;reason:string;notes?:string}
export function moveSnapshot(s:Session,m:MoveInput) {
  const out:Record<string,number>={}
  for(const key of [m.source,m.target]){
    const a=skuByKey(key,s)
    for(const size of a?.sizes??[])out[key+'|'+size]=stockAt(a!,size,s,m.location,m.grade)
  }
  return out
}
export function convertStock(s:Session,m:MoveInput,id:string,expected?:Record<string,number>):Session {
  const a=skuByKey(m.source,s),b=skuByKey(m.target,s)
  if(!a||!b||a.key===b.key||s.skuUpdates?.[m.source]?.active===false||s.skuUpdates?.[m.target]?.active===false)throw Error('Pilih dua SKU aktif yang berbeda.')
  if(!id||!m.reason.trim()||!m.location||m.grade!=='Good'||!dayOk(m.date))throw Error('Isi tanggal fisik, lokasi, dan alasan transaksi.')
  const lines=Object.entries(m.values).filter(([,v])=>v.trim()).sort(([x],[y])=>x.localeCompare(y))
  const intent=JSON.stringify([a.key,b.key,m.location,m.grade,m.date,m.reason.trim(),m.notes?.trim()||null,lines.map(([size,q])=>[size,m.sizeMap[size]??'',q]),...(m.physicalTime?[m.physicalTime]:[])])
  const prior=s.stockEvents?.find(e=>e.id===id)
  if(prior){if(prior.intent!==intent)throw Error('Permintaan ini sudah dipakai dengan isi berbeda.');return s}
  const balances=moveSnapshot(s,m)
  if(expected&&Object.keys(balances).some(k=>expected[k]!==balances[k]))throw Error('Stok berubah. Buka kembali pratinjau.')
  const activity=fgActivity(a,s,m.location,m.grade)
  const changes:StockChange[]=[]
  for(const [size,raw] of lines){
    if(!a.sizes.includes(size)||!/^\d{1,9}$/.test(raw))throw Error('Isi jumlah pcs bulat sesuai ukuran master.')
    const qty=Number(raw)
    if(!qty)continue
    const current=balances[a.key+'|'+size]
    if(qty>Math.min(current,sizeBalanceAt(current,a.sizes.indexOf(size),activity,m.date,m.physicalTime)))throw Error('Jumlah melebihi stok asal ukuran '+size+'.')
    const targetSize=m.sizeMap[size]
    if(!b.sizes.includes(targetSize))throw Error('Pilih ukuran tujuan untuk ukuran asal '+size+'.')
    changes.push({key:a.key,size,delta:-qty,location:m.location,grade:m.grade})
    const row=changes.find(c=>c.key===b.key&&c.size===targetSize)
    if(row)row.delta+=qty
    else changes.push({key:b.key,size:targetSize,delta:qty,location:m.location,grade:m.grade})
  }
  if(m.physicalTime&&!/^([01]\d|2[0-3]):[0-5]\d$/.test(m.physicalTime))throw Error('Jam fisik tidak valid.')
  if(!changes.length)throw Error('Isi setidaknya satu ukuran yang berubah.')
  for(const c of changes)c.after=balances[c.key+'|'+c.size]+c.delta
  return {...s,stockEvents:[...(s.stockEvents??[]),{id,action:'convert',date:m.date,physicalTime:m.physicalTime||undefined,recordedAt:new Date().toISOString(),intent,reason:m.reason.trim(),notes:m.notes?.trim()||null,changes}]}
}
