import { useMemo, useState } from 'react'
import { ArrowLeft, ArrowRight, CheckCircle2, ClipboardCheck, Clock3, Filter, Info, Layers3, LockKeyhole, PackageCheck, Search, Shirt, UserRound, Waves } from 'lucide-react'
import './finalization-flow.css'
import { productCatalog } from './productCatalog'

type NumberTuple = [number, number, number]
type StringTuple = [string, string, string]

export type QcSeed = {
  parentId: string
  batchId: string
  brand: string
  model: string
  material: string
  mandor: string
  laundry: string
  sizes: StringTuple
  expected: NumberTuple
  returnedGoodBySize: NumberTuple
  returnedBsBySize: NumberTuple
  stuckBySize: NumberTuple
}

export type QcFinalResult = QcSeed & {
  postedGoodBySize: NumberTuple
  postedBsBySize: NumberTuple
  postedRewashBySize: NumberTuple
  qcGood: NumberTuple
  qcBs: NumberTuple
  rewash: NumberTuple
  remainingBySize: NumberTuple
  readyRemainingBySize: NumberTuple
  completionStatus: 'PARTIAL_SELECTION' | 'WAITING_LAUNDRY' | 'WAITING_REWORK' | 'COMPLETE'
  completionCount: number
  finalSku: string
  finalProductName: string
  finalColor: string
  finalRange: string
  destination: string
}

const keyOf = (seed:QcSeed) => `${seed.parentId}::${seed.batchId}`
const asNumberTuple = (values:number[]):NumberTuple => [values[0]??0,values[1]??0,values[2]??0]
const asStringTuple = (values:string[]):StringTuple => [values[0]??'',values[1]??'',values[2]??'']
const total = (values:NumberTuple) => values.reduce((sum,value)=>sum+value,0)
const cleanNumber = (raw:string,max:number) => {
  const digits=raw.replace(/\D/g,'').replace(/^0+(?=\d)/,'')
  return digits===''?'':String(Math.min(max,Number(digits)))
}

export default function QcFinalPage({seeds,initialSeedId,finalizedResults,onBack,onFinish,onOpenNota}:{
  seeds:QcSeed[]
  initialSeedId:string
  finalizedResults:QcFinalResult[]
  onBack:()=>void
  onFinish:(result:QcFinalResult)=>void
  onOpenNota:(result:QcFinalResult)=>void
}) {
  const [selectedId,setSelectedId]=useState(initialSeedId)
  const [query,setQuery]=useState('')
  const [mandorFilter,setMandorFilter]=useState('Semua mandor')
  const [laundryFilter,setLaundryFilter]=useState('Semua laundry')
  const [brandFilter,setBrandFilter]=useState('Semua merek')
  const [continuingId,setContinuingId]=useState<string|null>(null)
  const mandors=Array.from(new Set(seeds.map((seed)=>seed.mandor)))
  const laundries=Array.from(new Set(seeds.map((seed)=>seed.laundry)))
  const brands=Array.from(new Set(seeds.map((seed)=>seed.brand)))
  const visible=useMemo(()=>seeds.filter((seed)=>{
    const haystack=`${seed.parentId} ${seed.batchId} ${seed.brand} ${seed.model} ${seed.material} ${seed.mandor} ${seed.laundry}`.toLowerCase()
    return haystack.includes(query.toLowerCase())&&(mandorFilter==='Semua mandor'||seed.mandor===mandorFilter)&&(laundryFilter==='Semua laundry'||seed.laundry===laundryFilter)&&(brandFilter==='Semua merek'||seed.brand===brandFilter)
  }),[seeds,query,mandorFilter,laundryFilter,brandFilter])
  const selected=visible.find((seed)=>keyOf(seed)===selectedId)??visible[0]??seeds[0]
  const finalizedById=useMemo(()=>{
    const latest=new Map<string,QcFinalResult>()
    finalizedResults.forEach((result)=>{
      const key=keyOf(result)
      const current=latest.get(key)
      if(!current||result.completionCount>current.completionCount)latest.set(key,result)
    })
    return latest
  },[finalizedResults])
  const finalizedSelected=selected?finalizedById.get(keyOf(selected)):undefined
  const selectedKey=selected?keyOf(selected):null
  const nextPending=visible.find((seed)=>keyOf(seed)!==selectedKey&&finalizedById.get(keyOf(seed))?.completionStatus!=='COMPLETE')
  const continueSelected=Boolean(selectedKey&&continuingId===selectedKey)

  return <>
    <section className="hero-copy compact qc-flow-hero">
      <div><div className="eyebrow">PRODUKSI · SETELAH LAUNDRY</div><h1>QC & Final SKU</h1><p>Browse berdasarkan merek, Mandor, atau Laundry. Pilih Batch Distribusi yang fisiknya sudah kembali, lalu review per size.</p></div>
      <button type="button" className="soft-btn" onClick={onBack}><ArrowLeft/> Kembali ke WIP</button>
    </section>
    <div className="final-flow-strip"><span className="done"><b>1</b>Laundry kembali</span><i/><span className="active"><b>2</b>QC & Final SKU</span><i/><span><b>3</b>Serah FG</span><i/><span><b>4</b>Nota FG</span></div>
    <section className="qc-browser-shell">
      <aside className="panel qc-browser">
        <header><div><span>BROWSE ANTREAN QC</span><strong>{visible.length} Batch Distribusi</strong></div><Filter/></header>
        <label className="qc-browser-search"><Search/><input value={query} onChange={(event)=>setQuery(event.target.value)} placeholder="Cari PO, merek, Mandor, bahan..."/></label>
        <div className="qc-browser-filters">
          <label><span>MANDOR</span><select value={mandorFilter} onChange={(event)=>setMandorFilter(event.target.value)}><option>Semua mandor</option>{mandors.map((mandor)=><option key={mandor}>{mandor}</option>)}</select></label>
          <label><span>LAUNDRY</span><select value={laundryFilter} onChange={(event)=>setLaundryFilter(event.target.value)}><option>Semua laundry</option>{laundries.map((laundry)=><option key={laundry}>{laundry}</option>)}</select></label>
          <label><span>MEREK</span><select value={brandFilter} onChange={(event)=>setBrandFilter(event.target.value)}><option>Semua merek</option>{brands.map((brand)=><option key={brand}>{brand}</option>)}</select></label>
        </div>
        <div className="qc-browser-list">{visible.map((seed,index)=>{
          const returned=total(seed.returnedGoodBySize)+total(seed.returnedBsBySize)
          const stuck=total(seed.stuckBySize)
          const finalized=finalizedById.has(keyOf(seed))
          const result=finalizedById.get(keyOf(seed))
          const partial=result?.completionStatus==='PARTIAL_SELECTION'
          const waitingLaundry=result?.completionStatus==='WAITING_LAUNDRY'
          const waitingRework=result?.completionStatus==='WAITING_REWORK'
          const completedQty=result?total(result.qcGood)+total(result.qcBs):0
          const readyRemaining=result?total(result.readyRemainingBySize):0
          const expectedQty=total(seed.expected)
          const progressLabel=partial
            ? `SELESAI SEBAGIAN · ${completedQty} posted · ${readyRemaining} siap tersisa`
            : waitingLaundry
              ? `FG SIAP SUDAH POSTED · ${stuck} stuck Laundry`
              : waitingRework
                ? `MENUNGGU CUCI ULANG · ${expectedQty-completedQty} pcs`
                : finalized?'QC LENGKAP · card siap disusun':`${seed.laundry} · ${returned} kembali · ${stuck} stuck`
          return <button type="button" className={`${selected&&keyOf(seed)===keyOf(selected)?'active ':''}${finalized?'finalized ':''}${partial?'partial':''}`} onClick={()=>{setSelectedId(keyOf(seed));setContinuingId(null)}} key={keyOf(seed)}><span className="qc-browser-index">{finalized?<CheckCircle2/>:String(index+1).padStart(2,'0')}</span><span className="qc-browser-copy"><small>{seed.brand} · {seed.parentId}</small><strong>Batch {seed.batchId} · {seed.model}</strong><span className="qc-browser-mandor"><UserRound/><b>{seed.mandor}</b></span><em>{progressLabel}</em></span><ArrowRight/></button>
        })}{visible.length===0&&<div className="qc-browser-empty"><Search/><strong>Antrean tidak ketemu</strong><small>Ubah Mandor, Laundry, merek, atau pencarian.</small></div>}</div>
      </aside>
      <div className="qc-browser-detail">{selected?(finalizedSelected&&!continueSelected?<QcFinalizedView result={finalizedSelected} hasNext={Boolean(nextPending)} onNext={()=>{if(nextPending){setSelectedId(keyOf(nextPending));setContinuingId(null)}}} onContinue={()=>setContinuingId(keyOf(selected))} onOpenNota={()=>onOpenNota(finalizedSelected)}/>:<QcEditor key={`${keyOf(selected)}::${finalizedSelected?.completionCount??0}`} seed={selected} previous={continueSelected?finalizedSelected:undefined} onFinish={(result)=>{setContinuingId(null);onFinish(result)}}/>):<div className="panel qc-no-source"><ClipboardCheck/><strong>Belum ada barang kembali untuk QC</strong><small>Catat penerimaan di Laundry lebih dulu.</small></div>}</div>
    </section>
  </>
}

function QcEditor({seed,previous,onFinish}:{seed:QcSeed;previous?:QcFinalResult;onFinish:(result:QcFinalResult)=>void}) {
  const cumulativeReturnedBySize=asNumberTuple(seed.returnedGoodBySize.map((qty,index)=>qty+seed.returnedBsBySize[index]))
  const previousProcessedBySize=asNumberTuple(seed.sizes.map((_,index)=>(previous?.qcGood[index]??0)+(previous?.qcBs[index]??0)+(previous?.rewash[index]??0)))
  const returnedBySize=asNumberTuple(cumulativeReturnedBySize.map((qty,index)=>Math.max(0,qty-previousProcessedBySize[index])))
  const sizeRange=`${seed.sizes[0]}–${seed.sizes[seed.sizes.length-1]}`
  const [completionInputs,setCompletionInputs]=useState<StringTuple>(()=>asStringTuple(returnedBySize.map(String)))
  const [bsInputs,setBsInputs]=useState<StringTuple>(()=>asStringTuple(seed.returnedBsBySize.map((qty,index)=>String(Math.min(returnedBySize[index],Math.max(0,qty-(previous?.qcBs[index]??0)))))))
  const [rewashInputs,setRewashInputs]=useState<StringTuple>(['0','0','0'])
  const compatibleProducts=useMemo(()=>productCatalog.filter((product)=>product.sizes.every((size,index)=>size===seed.sizes[index])),[seed.sizes])
  const brandOptions=Array.from(new Set(compatibleProducts.map((product)=>product.brand)))
  const requestedBrand=previous?.brand??seed.brand
  const initialBrand=brandOptions.includes(requestedBrand)?requestedBrand:(brandOptions[0]??seed.brand)
  const [selectedBrand,setSelectedBrand]=useState(initialBrand)
  const productsForBrand=compatibleProducts.filter((product)=>product.brand===selectedBrand)
  const [finalSku,setFinalSku]=useState(productsForBrand.some((product)=>product.code===previous?.finalSku)?previous?.finalSku??'':productsForBrand[0]?.code??'')
  const [destination,setDestination]=useState(previous?.destination??'Gudang FG Utama')
  const [reviewing,setReviewing]=useState(false)
  const [submitted,setSubmitted]=useState(false)
  const selectedProduct=productsForBrand.find((product)=>product.code===finalSku)??productsForBrand[0]
  const selectedNow=asNumberTuple(completionInputs.map((value)=>Number(value)||0))
  const qcBs=asNumberTuple(bsInputs.map((value)=>Number(value)||0))
  const rewash=asNumberTuple(rewashInputs.map((value)=>Number(value)||0))
  const qcGood=asNumberTuple(selectedNow.map((qty,index)=>Math.max(0,qty-qcBs[index]-rewash[index])))
  const readyRemainingBySize=asNumberTuple(returnedBySize.map((qty,index)=>Math.max(0,qty-selectedNow[index])))
  const cumulativeGood=asNumberTuple(qcGood.map((qty,index)=>qty+(previous?.qcGood[index]??0)))
  const cumulativeBs=asNumberTuple(qcBs.map((qty,index)=>qty+(previous?.qcBs[index]??0)))
  const cumulativeRewash=asNumberTuple(rewash.map((qty,index)=>qty+(previous?.rewash[index]??0)))
  const remainingBySize=asNumberTuple(seed.expected.map((qty,index)=>Math.max(0,qty-cumulativeGood[index]-cumulativeBs[index])))
  const totalGood=total(qcGood),totalBs=total(qcBs),totalRewash=total(rewash),totalStuck=total(seed.stuckBySize),expectedTotal=total(seed.expected)
  const availableTotal=total(returnedBySize),selectedTotal=total(selectedNow),readyRemainingTotal=total(readyRemainingBySize),remainingTotal=total(remainingBySize),cumulativeRewashTotal=total(cumulativeRewash),priorCompleted=previous?total(previous.qcGood)+total(previous.qcBs):0,cumulativeCompleted=total(cumulativeGood)+total(cumulativeBs)
  const completionStatus:QcFinalResult['completionStatus']=readyRemainingTotal>0?'PARTIAL_SELECTION':totalStuck>0?'WAITING_LAUNDRY':remainingTotal>0&&cumulativeRewashTotal>0?'WAITING_REWORK':'COMPLETE'
  const statusLabel=completionStatus==='PARTIAL_SELECTION'?'SELESAI SEBAGIAN':completionStatus==='WAITING_LAUNDRY'?'MENUNGGU LAUNDRY':completionStatus==='WAITING_REWORK'?'MENUNGGU CUCI ULANG':'QC LENGKAP'
  const updateCompletion=(index:number,raw:string)=>{
    const next=cleanNumber(raw,returnedBySize[index])
    const nextQty=Number(next)||0
    const nextBs=Math.min(qcBs[index],nextQty)
    const nextRewash=Math.min(rewash[index],Math.max(0,nextQty-nextBs))
    setCompletionInputs((current)=>asStringTuple(current.map((value,row)=>row===index?next:value)))
    setBsInputs((current)=>asStringTuple(current.map((value,row)=>row===index?String(nextBs):value)))
    setRewashInputs((current)=>asStringTuple(current.map((value,row)=>row===index?String(nextRewash):value)))
    setReviewing(false)
  }
  const updateException=(kind:'bs'|'rewash',index:number,raw:string)=>{
    const other=kind==='bs'?rewash[index]:qcBs[index]
    const next=cleanNumber(raw,Math.max(0,selectedNow[index]-other))
    if(kind==='bs')setBsInputs((current)=>asStringTuple(current.map((value,row)=>row===index?next:value)))
    else setRewashInputs((current)=>asStringTuple(current.map((value,row)=>row===index?next:value)))
    setReviewing(false)
  }
  const chooseBrand=(brand:string)=>{
    const firstProduct=compatibleProducts.find((product)=>product.brand===brand)
    setSelectedBrand(brand)
    setFinalSku(firstProduct?.code??'')
    setReviewing(false)
  }
  const finish=()=>{
    if(submitted)return
    setSubmitted(true)
    onFinish({...seed,brand:selectedBrand,postedGoodBySize:qcGood,postedBsBySize:qcBs,postedRewashBySize:rewash,qcGood:cumulativeGood,qcBs:cumulativeBs,rewash:cumulativeRewash,remainingBySize,readyRemainingBySize,completionStatus,completionCount:(previous?.completionCount??0)+1,finalSku,finalProductName:selectedProduct?.name??seed.model,finalColor:selectedProduct?.color??'',finalRange:selectedProduct?.range??sizeRange,destination})
  }

  return <>
    <section className="panel qc-source-card"><span className="qc-source-order"><Shirt/></span><div><small>{seed.brand} · BATCH PRODUKSI · BATCH DISTRIBUSI</small><h2>{seed.parentId} · Batch {seed.batchId}</h2><p>{seed.model} · {seed.material}</p></div><div className="qc-mandor-hero"><UserRound/><span><small>MANDOR PENANGGUNG JAWAB</small><strong>{seed.mandor}</strong></span></div><div><small>LAUNDRY</small><strong>{seed.laundry||'Belum tercatat'}</strong></div></section>
    <section className="qc-flow-layout">
      <div className="panel qc-size-workbench">
        <header><div><span>01 · HASIL FISIK PER SIZE</span><h2>Good dihitung otomatis</h2><p>Qty kembali dan Stuck berasal dari penerimaan Laundry per size—bukan dibagi rata atau ditebak.</p></div><ClipboardCheck/></header>
        {previous&&<div className="qc-continuation-banner"><Layers3/><span><strong>Lanjut penyelesaian #{previous.completionCount+1}</strong><small>{priorCompleted} dari {expectedTotal} pcs sudah terkunci pada {previous.completionCount} posting sebelumnya. Form hanya menampilkan fisik tambahan yang belum pernah diposting.</small></span><em>{remainingTotal} pcs open</em></div>}
        {previous&&availableTotal===0&&<div className="qc-no-new-return"><Clock3/><span><strong>Belum ada fisik tambahan untuk diposting.</strong><small>Catat penerimaan Laundry berikutnya dulu. Lot FG dan card sebelumnya tetap aman.</small></span></div>}
        <div className="qc-good-formula"><span><small>SELESAIKAN SEKARANG</small><strong>{selectedTotal} pcs</strong></span><b>−</b><span className="input"><small>BS</small><strong>{totalBs} pcs</strong></span><b>−</b><span className="input"><small>CUCI ULANG</small><strong>{totalRewash} pcs</strong></span><b>=</b><span className="result"><small>GOOD OTOMATIS</small><strong>{totalGood} pcs</strong></span></div>
        <div className="qc-size-head"><span>Size</span><span>{previous?'Sisa target':'Potongan'}</span><span>Siap QC</span><span>Selesaikan sekarang</span><span>BS · input</span><span>Cuci ulang · input</span><span>Stuck Laundry</span><span className="result">Good otomatis</span></div>
        <div className="qc-size-rows" data-keyboard-grid>{seed.sizes.map((size,index)=><div className="qc-size-row" key={size}><strong data-label="SIZE">{size}</strong><span data-label={previous?'SISA TARGET':'POTONGAN'}>{previous?.remainingBySize[index]??seed.expected[index]}</span><span data-label="SIAP QC">{returnedBySize[index]}</span><label data-label="SELESAIKAN SEKARANG"><input data-grid-row={index} data-grid-col={0} inputMode="numeric" value={completionInputs[index]} onFocus={(event)=>event.currentTarget.select()} onChange={(event)=>updateCompletion(index,event.target.value)}/></label><label data-label="BS · INPUT"><input data-grid-row={index} data-grid-col={1} inputMode="numeric" value={bsInputs[index]} onFocus={(event)=>event.currentTarget.select()} onChange={(event)=>updateException('bs',index,event.target.value)}/></label><label data-label="CUCI ULANG · INPUT"><input data-grid-row={index} data-grid-col={2} inputMode="numeric" value={rewashInputs[index]} onFocus={(event)=>event.currentTarget.select()} onChange={(event)=>updateException('rewash',index,event.target.value)}/></label><span data-label="STUCK" className={seed.stuckBySize[index]>0?'stuck':''}>{seed.stuckBySize[index]}</span><strong data-label="GOOD · OTOMATIS" className="good"><small>OTOMATIS</small>{qcGood[index]}</strong></div>)}</div>
        <div className="keyboard-grid-hint"><kbd>Enter</kbd> turun · <kbd>Shift + Enter</kbd> naik · <kbd>↑ ↓ ← →</kbd> pindah sel</div>
        <div className="qc-equation"><span><small>FISIK SIAP QC</small><strong>{availableTotal}</strong></span><b>=</b><span><small>DISELESAIKAN SEKARANG</small><strong>{selectedTotal}</strong></span><b>+</b><span><small>SIAP TERSISA</small><strong>{readyRemainingTotal}</strong></span><b>·</b><span className="stuck"><small>STUCK LAUNDRY TERPISAH</small><strong>{totalStuck}</strong></span></div>
        {totalStuck>0&&<div className="qc-auto-stuck"><Waves/><div><strong>{totalStuck} pcs masih di {seed.laundry}</strong><span>{seed.sizes.map((size,index)=>`Size ${size}: ${seed.stuckBySize[index]}`).join(' · ')}. Belum boleh berubah menjadi BS sebelum fisiknya kembali.</span></div></div>}
        <section className="qc-final-product"><header><span>02 · IDENTITAS BARANG JADI</span><strong>Pilih merek, lalu SKU</strong><small>SKU yang tampil sudah dibatasi ke range Size {sizeRange} supaya posting FG tidak salah produk.</small></header><div className="qc-final-fields" data-keyboard-scope>
          <label><span>1 · MEREK</span><select value={selectedBrand} onChange={(event)=>chooseBrand(event.target.value)}>{brandOptions.map((brand)=><option key={brand}>{brand}</option>)}</select></label>
          <label><span>2 · SKU</span><select value={finalSku} onChange={(event)=>{setFinalSku(event.target.value);setReviewing(false)}}>{productsForBrand.map((product)=><option value={product.code} key={product.code}>{product.code}</option>)}</select></label>
          <article className="qc-product-preview"><Shirt/><span><small>3 · BARANG TERPILIH</small><strong>{selectedProduct?.name??'Produk belum tersedia'} · {selectedProduct?.color??'—'}</strong><em>{selectedBrand} · Range {selectedProduct?.range??sizeRange} · {seed.material}</em></span></article>
          <label><span>4 · TUJUAN FG</span><select value={destination} onChange={(event)=>{setDestination(event.target.value);setReviewing(false)}}><option>Gudang FG Utama</option><option>Gudang FG Cadangan</option></select></label>
        </div></section>
      </div>
      <aside className="panel qc-review-ticket"><div className="qc-review-title"><span>REVIEW FINISHING · {selectedBrand}</span><h2>{selectedBrand} · SKU {finalSku||'—'}</h2><p>{selectedProduct?.name??seed.model} · {selectedProduct?.color??seed.material} · Size {sizeRange}</p><div className="qc-ticket-mandor"><UserRound/><span><small>MANDOR</small><strong>{seed.mandor}</strong></span></div></div><div className="qc-partial-progress"><span><small>PROGRESS KUMULATIF SESUDAH POST</small><strong>{cumulativeCompleted}/{expectedTotal} pcs</strong></span><em>{statusLabel}</em><i><b style={{width:`${expectedTotal>0?Math.min(100,cumulativeCompleted/expectedTotal*100):0}%`}}/></i><small>{completionStatus==='PARTIAL_SELECTION'?`${readyRemainingTotal} pcs sudah kembali dan sengaja belum dipilih; bisa dipost pada completion berikutnya.`:completionStatus==='WAITING_LAUNDRY'?`${totalStuck} pcs masih tercatat di Laundry, bukan Selesai Sebagian.`:completionStatus==='WAITING_REWORK'?`${totalRewash} pcs menunggu cuci ulang.`:'Seluruh Potongan sudah terjelaskan sebagai Good atau BS.'}</small></div><div className="qc-review-totals"><p><span>Lolos QC / serah FG sekarang</span><strong>{totalGood} pcs</strong></p><p><span>BS posting sekarang</span><strong>{totalBs} pcs</strong></p><p><span>Siap QC belum dipilih</span><strong>{readyRemainingTotal} pcs</strong></p><p className="stuck"><span>Stuck Laundry</span><strong>{totalStuck} pcs</strong></p></div><div className="qc-review-rule"><Info/><span><strong>Setiap posting menjadi fakta terpisah.</strong><small>Good membuat lot FG baru. Barang siap yang tidak dipilih tetap eligible; Stuck tetap milik Laundry sampai ada penyelesaian fisik.</small></span></div>{!reviewing?<button className="primary-btn qc-review-button" disabled={!selectedProduct||selectedTotal<=0} onClick={()=>setReviewing(true)}>Review {completionStatus==='PARTIAL_SELECTION'?'selesai sebagian':'penyelesaian'} <ArrowRight/></button>:<div className="qc-final-confirm"><PackageCheck/><div><strong>{completionStatus==='PARTIAL_SELECTION'?'Posting sebagian siap dikunci':'Qty terpilih siap dikunci'}</strong><span>Posting ini {totalGood+totalBs} pcs · kumulatif {cumulativeCompleted}/{expectedTotal} pcs.</span></div><button className="primary-btn" disabled={submitted||totalGood+totalBs<=0||!selectedProduct} onClick={finish}>{submitted?'Posting sedang dikunci':completionStatus==='PARTIAL_SELECTION'?'Post FG sebagian & buat card':'Post FG terpilih & buat card'} <ArrowRight/></button></div>}<small className="qc-prototype-note">Writer backend memakai UUID idempotency + row_version. Klik ulang tidak membuat lot, stok, atau card kedua.</small></aside>
    </section>
  </>
}

function QcFinalizedView({result,hasNext,onNext,onContinue,onOpenNota}:{result:QcFinalResult;hasNext:boolean;onNext:()=>void;onContinue:()=>void;onOpenNota:()=>void}) {
  const good=total(result.postedGoodBySize)
  const bs=total(result.postedBsBySize)
  const rewash=total(result.postedRewashBySize)
  const stuck=total(result.stuckBySize)
  const readyRemaining=total(result.readyRemainingBySize)
  const remaining=total(result.remainingBySize)
  const returned=good+bs+rewash
  const cumulativeCompleted=total(result.qcGood)+total(result.qcBs)
  const expected=total(result.expected)
  const partial=result.completionStatus==='PARTIAL_SELECTION'
  const waitingLaundry=result.completionStatus==='WAITING_LAUNDRY'
  const waitingRework=result.completionStatus==='WAITING_REWORK'
  const statusLabel=partial?'SELESAI SEBAGIAN':waitingLaundry?'MENUNGGU LAUNDRY':waitingRework?'MENUNGGU CUCI ULANG':'LENGKAP'
  const bannerTitle=partial
    ? `${good+bs} pcs pada completion ini sudah posted; ${readyRemaining} pcs siap QC tetap eligible.`
    : waitingLaundry
      ? `${good+bs} pcs siap sudah posted; ${stuck} pcs tetap outstanding di Laundry.`
      : waitingRework
        ? `${good+bs} pcs sudah posted; ${rewash} pcs menunggu hasil cuci ulang.`
        : 'Seluruh hasil QC sudah terkunci dan card finishing tersimpan.'
  const bannerNote=partial
    ? `Kumulatif ${cumulativeCompleted}/${expected} pcs. Ini Selesai Sebagian karena operator sengaja tidak memilih seluruh fisik yang sudah siap.`
    : waitingLaundry
      ? 'Stuck bukan Selesai Sebagian dan tidak ikut FG. Catat susulan lewat Barang BS & Rework agar outstanding Laundry otomatis turun.'
      : waitingRework
        ? 'Cuci ulang tetap open dan akan menjadi sumber completion berikutnya setelah kembali.'
        : 'Kembali dari Nota FG atau menutup halaman tidak membatalkan QC.'
  return <section className={`panel qc-finalized-view ${partial?'partial':''}`}>
    <header><span><LockKeyhole/></span><div><small>{result.completionStatus==='COMPLETE'?'QC FINAL · READ ONLY':'POSTING FG · READ ONLY'}</small><h2>{result.parentId} · Batch {result.batchId}</h2><p>{result.brand} · SKU {result.finalSku} · {result.finalProductName}</p></div><em><CheckCircle2/> {statusLabel}</em></header>
    <div className="qc-finalized-banner"><CheckCircle2/><span><strong>{bannerTitle}</strong><small>{bannerNote}</small></span></div>
    <div className="qc-finalized-card"><div><span>CARD FINISHING · COMPLETION {String(result.completionCount).padStart(2,'0')}</span><strong>FIN-{result.batchId}-{String(result.completionCount).padStart(2,'0')}</strong><small>Belum masuk Nota FG · siap digabung dengan card {result.mandor} lainnya</small></div><Layers3/></div>
    <div className="qc-finalized-facts"><article><small>DIPROSES SEKARANG</small><strong>{returned} pcs</strong><span>Hasil completion yang baru dipost</span></article><article className="good"><small>GOOD → FG</small><strong>{good} pcs</strong><span>Masuk stok barang jadi</span></article><article className="bs"><small>SIAP QC TERSISA</small><strong>{readyRemaining} pcs</strong><span>Sudah kembali, belum dipilih</span></article><article className="stuck"><small>STUCK LAUNDRY</small><strong>{stuck} pcs</strong><span>Belum ikut FG atau completion</span></article></div>
    <div className="qc-finalized-actions"><span><LockKeyhole/><small>Posting #{result.completionCount} immutable. Koreksi memakai reversal; penyelesaian sisa membuat posting baru.</small></span>{result.completionStatus!=='COMPLETE'&&<button type="button" className="soft-btn" onClick={onContinue}>{partial?`Lanjutkan ${readyRemaining} pcs siap`:waitingLaundry?'Cek fisik susulan':`Lanjutkan ${remaining} pcs`}</button>}<button type="button" className="soft-btn" disabled={!hasNext} onClick={onNext}>{hasNext?'QC antrean berikutnya':'Tidak ada antrean lain'}</button><button type="button" className="primary-btn" onClick={onOpenNota}>Buka card ke Nota FG <ArrowRight/></button></div>
  </section>
}
