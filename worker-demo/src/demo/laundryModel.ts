import { dayOk } from './warehouseDay'
import type { QcSeed } from '../QcFinalPage'
import { alignSizeQuantities } from '../sizeQuantities'
import { simulationPatternSnapshots } from './productionModel'
import type { ProductionPatternSnapshot, QtyTuple, SizeTuple } from './productionModel'
import { sewingWipSeeds } from './sewingModel'
import type { SewingBatchSeed, SewingParentSeed } from './sewingModel'

export type LaundryView = 'send' | 'return'

export type LaundryPrefill = { batchId: string; vendor: string; view: LaundryView }

export const laborBomComponents = [
  {id:'jahit-utama',name:'Jahit utama',rate:8250,required:true,note:'Badan, sambungan utama, dan bentuk model'},
  {id:'finishing-detail',name:'Ceming / finishing detail',rate:2500,required:true,note:'Detail sambungan sesuai snapshot model'},
  {id:'pinggang',name:'Ban & pinggang',rate:2600,required:true,note:'Ban, stik pinggang, dan penguat'},
  {id:'saku',name:'Saku & ritsleting',rate:2300,required:true,note:'Komponen fungsi depan/belakang'},
  {id:'centang',name:'Centang / bartack',rate:800,required:false,note:'Penguat titik dan pemeriksaan detail'},
  {id:'kancing',name:'Kancing',rate:500,required:false,note:'Pasang kancing sesuai model'},
  {id:'plastik',name:'Plastik & packing',rate:500,required:false,note:'Plastik per barang jadi'},
  {id:'hangtag',name:'Hangtag / label',rate:600,required:false,note:'Label dan hangtag final'},
  {id:'lipat',name:'Lipat akhir',rate:400,required:false,note:'Lipat dan susun serah gudang'},
]

export type LaundryReadyBatch = {
  id:string; parentId:string; sequence:number; plannedBrand?:string; skuRef?:string; model:string; material:string; mandor:string;
  pattern:ProductionPatternSnapshot|null; pickupAt:string; sewingDoneAt:string; vendor:string; process:string; qty:number; sizes:QtyTuple; sizeLabels:SizeTuple; note:string
}

type LaundryReturn = { at: string; good: QtyTuple; bs: QtyTuple }
export type LaundryFinalBill = { number: string; day: string; process: string; rate: number; qty: number }
export type LaundryDelivery = {
  id:string; parentId:string; sequence:number; batchId:string; plannedBrand?:string; skuRef?:string; model:string; material:string; mandor:string;
  pattern:ProductionPatternSnapshot|null; vendor:string; process:string; targetColor?:string|null; colourProcess?:string|null; sendNote?:string|null; sentAt:string; qty:number; sizes:QtyTuple; sizeLabels:SizeTuple;
  good:number; bs:number; goodSizes:QtyTuple; bsSizes:QtyTuple; reversed:number; reversedSizes:QtyTuple; reverseNote?:string
  estimatedRate?: number | null; returns?: LaundryReturn[]; instructionSource?: string | null; finalBills?: LaundryFinalBill[]
}

export function laundryPhysicalTime(value:string){
  if (/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/.test(value)) return value
  const [day,time]=value.split(' · ')
  if (time && !/^(?:[01]\d|2[0-3]):[0-5]\d$/.test(time)) return ''
  if(/^\d{4}-\d{2}-\d{2}$/.test(day))return day+'T'+(time??'00:00')
  const [d,m,y]=day.split(' '),month=['Jan','Feb','Mar','Apr','Mei','Jun','Jul','Agu','Sep','Okt','Nov','Des'].indexOf(m)+1
  return month&&y?y+'-'+String(month).padStart(2,'0')+'-'+d.padStart(2,'0')+'T'+(time??'00:00'):''
}

export const laundryProcesses = ['Stone Wash','Bio Wash','Enzyme Wash']

// Rates in the training data. Connected screens use the dated vendor tariff catalogue.
const trainingRates = [
  { vendor: 'Laundry Berkah', process: 'Stone Wash', from: '2026-09-01', rate: 7000 },
  { vendor: 'Laundry Berkah', process: 'Stone Wash', from: '2026-08-01', rate: 6500 },
  { vendor: 'Laundry Intan', process: 'Stone Wash', from: '2026-08-01', rate: 7200 },
  { vendor: 'Laundry Intan', process: 'Bio Wash', from: '2026-08-01', rate: 5500 },
  { vendor: 'Cemerlang Wash', process: 'Enzyme Wash', from: '2026-08-01', rate: 6000 },
]

export function laundryRateAt(vendor: string, process: string, day: string) {
  return trainingRates.find(row => row.vendor === vendor && row.process === process && row.from <= day)?.rate ?? null
}

export function validLaundryTime(value: string) {
  return /^\d{4}-\d{2}-\d{2}T(?:[01]\d|2[0-3]):[0-5]\d$/.test(value) && dayOk(value.slice(0, 10))
}

export function returnLaundry(delivery: LaundryDelivery, at: string, good: QtyTuple, bs: QtyTuple): LaundryDelivery {
  if (!validLaundryTime(at) || at < laundryPhysicalTime(delivery.sentAt)) throw Error('Waktu kembali harus sama atau sesudah waktu kirim.')
  const remaining = laundryOutstandingSizes(delivery)
  if (good.length !== remaining.length || bs.length !== remaining.length || remaining.some((qty, i) =>
    !Number.isSafeInteger(good[i]) || !Number.isSafeInteger(bs[i]) || good[i] < 0 || bs[i] < 0 || good[i] + bs[i] > qty)) {
    throw Error('Jumlah kembali per ukuran melebihi sisa surat kirim.')
  }
  const totalGood = good.reduce((sum, qty) => sum + qty, 0)
  const totalBs = bs.reduce((sum, qty) => sum + qty, 0)
  if (!totalGood && !totalBs) throw Error('Isi jumlah Good atau BS yang kembali.')
  return {
    ...delivery, good: delivery.good + totalGood, bs: delivery.bs + totalBs,
    goodSizes: delivery.goodSizes.map((qty, i) => qty + good[i]), bsSizes: delivery.bsSizes.map((qty, i) => qty + bs[i]),
    returns: [...(delivery.returns ?? []), { at, good, bs }],
  }
}

export const laundryReadySeeds:LaundryReadyBatch[] = [
  {id:'042-02',skuRef:'Widie 66002',parentId:'POT-260827-042',sequence:42,plannedBrand:'Widie',pattern:simulationPatternSnapshots.lucyRegular,model:'Kulot Lucy',material:'Lucy',mandor:'Mandor Afat',pickupAt:'27 Agu 2026 · 10:30',sewingDoneAt:'27 Agu 2026 · 15:20',vendor:'Laundry Berkah',process:'Stone Wash',qty:225,sizes:[0,225,0],sizeLabels:['31','32','33'],note:'Maroon · obras rapat'},
  {id:'041-01',skuRef:'Widie 66001',parentId:'POT-260826-041',sequence:41,pattern:simulationPatternSnapshots.malibuRegular,model:'Malibu Regular',material:'Malibu',mandor:'Mandor Asep',pickupAt:'26 Agu 2026 · 14:15',sewingDoneAt:'26 Agu 2026 · 18:10',vendor:'Laundry Intan',process:'Bio Wash',qty:244,sizes:[82,81,81],sizeLabels:['28','29','30'],note:'Biru muda · benang senada · obras rapat'},
  {id:'039-01',parentId:'POT-260825-039',sequence:39,plannedBrand:'Vivo',pattern:simulationPatternSnapshots.zodiakJumbo,model:'Zodiak Jumbo',material:'Zodiak KW',mandor:'Mandor Dedi',pickupAt:'25 Agu 2026 · 09:40',sewingDoneAt:'25 Agu 2026 · 17:45',vendor:'Cemerlang Wash',process:'Enzyme Wash',qty:114,sizes:[38,38,38],sizeLabels:['34','35','36'],note:'Stone · stik bawah 2 jalur'},
]

export const laundryDeliverySeeds:LaundryDelivery[] = [
  {id:'LDR-260827-011',skuRef:'Widie 66001',targetColor:'Biru muda',colourProcess:'Celup',parentId:'POT-260826-041',sequence:41,batchId:'041-02',pattern:simulationPatternSnapshots.malibuRegular,model:'Malibu Regular',material:'Malibu',mandor:'Mandor Asep',vendor:'Laundry Intan',process:'Bio Wash',sentAt:'27 Agu 2026 · 08:30',qty:244,sizes:[81,81,82],sizeLabels:['28','29','30'],good:174,bs:6,goodSizes:[58,58,58],bsSizes:[2,2,2],reversed:0,reversedSizes:[0,0,0]},
  {id:'LDR-260826-010',parentId:'POT-260825-039',sequence:39,batchId:'039-02',plannedBrand:'Vivo',pattern:simulationPatternSnapshots.zodiakJumbo,model:'Zodiak Jumbo',material:'Zodiak KW',mandor:'Mandor Dedi',vendor:'Cemerlang Wash',process:'Enzyme Wash',sentAt:'26 Agu 2026 · 13:10',qty:114,sizes:[38,38,38],sizeLabels:['34','35','36'],good:112,bs:2,goodSizes:[37,37,38],bsSizes:[0,1,1],reversed:0,reversedSizes:[0,0,0]},
  {id:'LDR-260825-009',skuRef:'Vivo 93001',targetColor:'Biru tua',colourProcess:'Celup',parentId:'POT-260824-038',sequence:38,batchId:'038-01',plannedBrand:'Vivo',pattern:null,model:'Vivo Regular',material:'Denim 12 Oz',mandor:'Mandor Afat',vendor:'Laundry Berkah',process:'Stone Wash',sentAt:'25 Agu 2026 · 11:00',qty:180,sizes:[60,60,60],sizeLabels:['31','32','33'],good:176,bs:4,goodSizes:[59,59,58],bsSizes:[1,1,2],reversed:0,reversedSizes:[0,0,0]},
]

export const laundryDigits = (value:string,max:number) => {
  const digits=value.replace(/\D/g,'').replace(/^0+(?=\d)/,'')
  return digits===''?'':String(Math.min(max,Number(digits)))
}

export const laundryOutstanding = (delivery:LaundryDelivery) => Math.max(0,delivery.qty-delivery.good-delivery.bs-delivery.reversed)

export const laundryReturnedSizes = (delivery:LaundryDelivery):QtyTuple => delivery.goodSizes.map((qty,index)=>qty+delivery.bsSizes[index]) as QtyTuple

export const laundryOutstandingSizes = (delivery:LaundryDelivery):QtyTuple => delivery.sizes.map((qty,index)=>Math.max(0,qty-delivery.goodSizes[index]-delivery.bsSizes[index]-delivery.reversedSizes[index])) as QtyTuple

export const summarizeLaundryBatch = (deliveries:LaundryDelivery[],batchId:string) => {
  const rows=deliveries.filter((delivery)=>delivery.batchId===batchId)
  const good=rows.reduce((sum,delivery)=>sum+delivery.good,0)
  const bs=rows.reduce((sum,delivery)=>sum+delivery.bs,0)
  const returned=good+bs
  const outside=rows.reduce((sum,delivery)=>sum+laundryOutstanding(delivery),0)
  const reversed=rows.reduce((sum,delivery)=>sum+delivery.reversed,0)
  const sizeLabels=Array.from(new Set(rows.flatMap(row=>row.sizeLabels)))
  const goodSizes=(sizeLabels.map((size)=>rows.reduce((sum,delivery)=>sum+(delivery.goodSizes[delivery.sizeLabels.indexOf(size)] ?? 0),0)) as QtyTuple)
  const bsSizes=(sizeLabels.map((size)=>rows.reduce((sum,delivery)=>sum+(delivery.bsSizes[delivery.sizeLabels.indexOf(size)] ?? 0),0)) as QtyTuple)
  const outsideSizes=(sizeLabels.map((size)=>rows.reduce((sum,delivery)=>sum+(laundryOutstandingSizes(delivery)[delivery.sizeLabels.indexOf(size)] ?? 0),0)) as QtyTuple)
  const activeVendors=Array.from(new Set(rows.filter((delivery)=>laundryOutstanding(delivery)>0).map((delivery)=>delivery.vendor)))
  const returnedVendors=Array.from(new Set(rows.filter((delivery)=>delivery.good+delivery.bs>0).map((delivery)=>delivery.vendor)))
  return {good,bs,returned,outside,reversed,sizeLabels,goodSizes,bsSizes,outsideSizes,activeVendors,returnedVendors}
}

function makeQcSeed(parent:SewingParentSeed,batch:SewingBatchSeed,summary:ReturnType<typeof summarizeLaundryBatch>):QcSeed {
  const sizes=Array.from(new Set([...parent.sizes,...summary.sizeLabels]))
  const good=alignSizeQuantities(summary.sizeLabels,summary.goodSizes,sizes),bs=alignSizeQuantities(summary.sizeLabels,summary.bsSizes,sizes),outside=alignSizeQuantities(summary.sizeLabels,summary.outsideSizes,sizes)
  const qcSourceSizes=sizes.map((_,index)=>good[index]+bs[index]+outside[index])
  return {
    parentId:parent.id,batchId:batch.id,plannedBrand:parent.plannedBrand,pattern:parent.pattern,model:parent.model,material:parent.material,mandor:parent.mandor,
    laundry:[...new Set([...summary.activeVendors,...summary.returnedVendors])].join(' & '),
    sizes,expected:qcSourceSizes,returnedGoodBySize:good,returnedBsBySize:bs,stuckBySize:outside,
  }
}

export function buildQcSeeds(deliveries:LaundryDelivery[]):QcSeed[] {
  const batchIds=Array.from(new Set(deliveries.filter((delivery)=>delivery.good+delivery.bs>0).map((delivery)=>delivery.batchId)))
  return batchIds.map((batchId)=>{
    const rows=deliveries.filter((delivery)=>delivery.batchId===batchId)
    const first=rows[0]
    const parent=sewingWipSeeds.find((item)=>item.id===first.parentId)
    const batch=parent?.batches.find((item)=>item.id===batchId)
    if(parent&&batch)return makeQcSeed(parent,batch,summarizeLaundryBatch(deliveries,batchId))
    const summary=summarizeLaundryBatch(deliveries,batchId)
    const {sizeLabels,goodSizes,bsSizes,outsideSizes:stuckBySize}=summary
    const expected=sizeLabels.map((_,i)=>goodSizes[i]+bsSizes[i]+stuckBySize[i])
    return {parentId:first.parentId,batchId,plannedBrand:first.plannedBrand,pattern:first.pattern,model:first.model,material:first.material,mandor:first.mandor,laundry:Array.from(new Set(rows.map(row=>row.vendor))).join(' & '),sizes:sizeLabels,expected,returnedGoodBySize:goodSizes,returnedBsBySize:bsSizes,stuckBySize}
  }).sort((a,b)=>b.parentId.localeCompare(a.parentId))
}

export function laundryReadyFromRows(parent:SewingParentSeed&{skuRef?:string},batch:SewingBatchSeed&{line?:{mandor:string;at:string}},vendor:string):LaundryReadyBatch{
  return {id:batch.id,parentId:parent.id,sequence:parent.sequence,plannedBrand:parent.plannedBrand,skuRef:parent.skuRef,pattern:parent.pattern,model:parent.model,material:parent.material,
    mandor:batch.line?.mandor??parent.mandor,pickupAt:batch.line?.at??parent.pickupAt,sewingDoneAt:'Siap kirim',vendor,process:'',qty:batch.qty,sizes:batch.sizes,sizeLabels:parent.sizes,note:batch.note}
}
export function laundryReadyFromSewingBatch(batchId:string,vendor:string,snapshot?:{qty:number;sizes:QtyTuple}):LaundryReadyBatch|null {
  const parent=sewingWipSeeds.find((item)=>item.batches.some((batch)=>batch.id===batchId))
  const batch=parent?.batches.find((item)=>item.id===batchId)
  if(!parent||!batch)return null
  return {id:batch.id,parentId:parent.id,sequence:parent.sequence,plannedBrand:parent.plannedBrand,pattern:parent.pattern,model:parent.model,material:parent.material,mandor:parent.mandor,pickupAt:parent.pickupAt,sewingDoneAt:'27 Agu 2026 · siap kirim',vendor,process:'',qty:snapshot?.qty??batch.qty,sizes:snapshot?.sizes??batch.sizes,sizeLabels:parent.sizes,note:batch.note}
}

export const proportionalLaundrySizes = (sizes:QtyTuple,total:number,qty:number):QtyTuple => {
  const raw=sizes.map((size)=>total>0?(size/total)*qty:0)
  const values=raw.map(Math.floor)
  let remainder=qty-values.reduce((sum,value)=>sum+value,0)
  raw.map((value,index)=>({index,fraction:value-values[index]})).sort((a,b)=>b.fraction-a.fraction).forEach(({index})=>{if(remainder>0){values[index]+=1;remainder-=1}})
  return values as QtyTuple
}

export const laundryReadyFromDelivery = (delivery:LaundryDelivery,qty:number):LaundryReadyBatch => {
  const source=laundryReadyFromSewingBatch(delivery.batchId,'Belum dipilih')
  const outstandingSizes=laundryOutstandingSizes(delivery)
  return source?{...source,qty,sizes:outstandingSizes,vendor:'Belum dipilih',process:delivery.process}:{
    id:delivery.batchId,parentId:delivery.parentId,sequence:delivery.sequence,plannedBrand:delivery.plannedBrand,pattern:delivery.pattern,model:delivery.model,material:delivery.material,mandor:delivery.mandor,pickupAt:delivery.sentAt,sewingDoneAt:delivery.sentAt,vendor:'Belum dipilih',process:delivery.process,qty,sizes:outstandingSizes,sizeLabels:delivery.sizeLabels,note:'Dikembalikan dari laundry · pilih tujuan baru',
  }
}

export const laundryDeliveryStatus = (delivery:LaundryDelivery) => {
  const received=delivery.good+delivery.bs
  const outstanding=laundryOutstanding(delivery)
  if(delivery.reversed>0&&outstanding===0)return received>0?'Sisa kembali WIP':'Kembali ke WIP'
  return received===0?'Di laundry':outstanding>0?'Kembali sebagian':'Selesai'
}
