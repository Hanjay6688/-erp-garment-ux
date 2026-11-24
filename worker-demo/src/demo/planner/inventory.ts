import { modelSeries, patternFor, products, stockDelta, type Session, type StockChange, type StockEvent } from './model'
export type Article={key:string;sku:string;brand:string;colour:string;model:string;sizes:string[];opening:Record<string,number>;pair?:string}
export const articles:Article[]=products.map(p=>({
  key:p.brand+' '+p.sku,sku:p.sku,brand:p.brand,colour:p.colour,model:patternFor(p.routes[0].pattern).name,sizes:p.sizes,
  opening:Object.fromEntries(p.sizes.map(size=>[size,size===p.size?p.fg:6])),
  pair:p.sku==='93001'?'Widie 66002':p.sku==='66001'?'Vivo 66001':undefined,
}))
articles.push(
  {key:'Widie 66002',sku:'66002',brand:'Widie',colour:'Biru tua',model:'Kulot Jumbo',sizes:modelSeries['Kulot Jumbo'].sizes,opening:{31:2,32:3,33:4},pair:'Vivo 93001'},
  {key:'Vivo 66001',sku:'66001',brand:'Vivo',colour:'Biru muda',model:'Kulot Kecil',sizes:modelSeries['Kulot Kecil'].sizes,opening:{28:2,29:3,30:4},pair:'Widie 66001'},
  {key:'Vivo 93001-27',sku:'93001-27',brand:'Vivo',colour:'Biru tua',model:'Kulot Kecil',sizes:['27'],opening:{27:3}},
)
export const stockAt=(article:Article,size:string,session:Session)=>article.opening[size]+stockDelta(article.key,size,session)
export function rangeChange(session:Session,action:StockEvent['action'],article:Article,values:Record<string,string>,reason:string,id:string,expected?:Record<string,number>,notes?:string):Session {
  if(session.stockEvents?.some(e=>e.id===id))return session
  const known=articles.find(a=>a.key===article.key)
  if(!known||!reason.trim()||!id)throw Error('Pilih SKU dan isi alasan pencatatan.')
  const target=articles.find(a=>a.key===known.pair)
  if(action==='convert'&&(!target||target.pair!==known.key))throw Error('SKU padanan belum diatur di master.')
  const changes:StockChange[]=[]
  for(const [size,raw] of Object.entries(values)){
    if(!raw.trim())continue
    const qty=Number(raw)
    if(!known.sizes.includes(size)||!/^\d{1,9}$/.test(raw)||!Number.isSafeInteger(qty))throw Error('Isi jumlah pcs bulat sesuai ukuran master.')
    const before=stockAt(known,size,session)
    if(expected&&expected[size]!==before)throw Error('Stok berubah. Buka kembali pratinjau.')
    if(action==='adjust'&&qty>before)throw Error('Untuk kelebihan lot hasil produksi, periksa penerimaan barang jadi atau koreksi sumbernya.')
    if(action==='convert'&&qty>before)throw Error('Jumlah melebihi stok asal ukuran '+size+'.')
    const delta=action==='adjust'?qty-before:-qty
    if(!delta)continue
    changes.push({key:known.key,size,delta})
    if(action==='convert'&&target){
      if(!target.sizes.includes(size))throw Error('Ukuran '+size+' belum terdaftar pada SKU tujuan.')
      changes.push({key:target.key,size,delta:-delta})
    }
  }
  if(!changes.length)throw Error('Isi setidaknya satu ukuran yang berubah.')
  return {...session,stockEvents:[...(session.stockEvents??[]),{id,action,reason:reason.trim(),notes:notes?.trim()||null,changes}]}
}
