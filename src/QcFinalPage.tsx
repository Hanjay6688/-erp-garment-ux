import { useMemo, useState } from 'react'
import { ArrowLeft, ArrowRight, ClipboardCheck, Filter, Info, PackageCheck, Search, Shirt, UserRound, Waves } from 'lucide-react'
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
  qcGood: NumberTuple
  qcBs: NumberTuple
  rewash: NumberTuple
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

export default function QcFinalPage({seeds,initialSeedId,onBack,onFinish}:{
  seeds:QcSeed[]
  initialSeedId:string
  onBack:()=>void
  onFinish:(result:QcFinalResult)=>void
}) {
  const [selectedId,setSelectedId]=useState(initialSeedId)
  const [query,setQuery]=useState('')
  const [mandorFilter,setMandorFilter]=useState('Semua mandor')
  const [laundryFilter,setLaundryFilter]=useState('Semua laundry')
  const [brandFilter,setBrandFilter]=useState('Semua merek')
  const mandors=Array.from(new Set(seeds.map((seed)=>seed.mandor)))
  const laundries=Array.from(new Set(seeds.map((seed)=>seed.laundry)))
  const brands=Array.from(new Set(seeds.map((seed)=>seed.brand)))
  const visible=useMemo(()=>seeds.filter((seed)=>{
    const haystack=`${seed.parentId} ${seed.batchId} ${seed.brand} ${seed.model} ${seed.material} ${seed.mandor} ${seed.laundry}`.toLowerCase()
    return haystack.includes(query.toLowerCase())&&(mandorFilter==='Semua mandor'||seed.mandor===mandorFilter)&&(laundryFilter==='Semua laundry'||seed.laundry===laundryFilter)&&(brandFilter==='Semua merek'||seed.brand===brandFilter)
  }),[seeds,query,mandorFilter,laundryFilter,brandFilter])
  const selected=visible.find((seed)=>keyOf(seed)===selectedId)??visible[0]??seeds[0]

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
          return <button type="button" className={selected&&keyOf(seed)===keyOf(selected)?'active':''} onClick={()=>setSelectedId(keyOf(seed))} key={keyOf(seed)}><span className="qc-browser-index">{String(index+1).padStart(2,'0')}</span><span className="qc-browser-copy"><small>{seed.brand} · {seed.parentId}</small><strong>Batch {seed.batchId} · {seed.model}</strong><span className="qc-browser-mandor"><UserRound/><b>{seed.mandor}</b></span><em>{seed.laundry} · {returned} kembali · {stuck} stuck</em></span><ArrowRight/></button>
        })}{visible.length===0&&<div className="qc-browser-empty"><Search/><strong>Antrean tidak ketemu</strong><small>Ubah Mandor, Laundry, merek, atau pencarian.</small></div>}</div>
      </aside>
      <div className="qc-browser-detail">{selected?<QcEditor key={keyOf(selected)} seed={selected} onFinish={onFinish}/>:<div className="panel qc-no-source"><ClipboardCheck/><strong>Belum ada barang kembali untuk QC</strong><small>Catat penerimaan di Laundry lebih dulu.</small></div>}</div>
    </section>
  </>
}

function QcEditor({seed,onFinish}:{seed:QcSeed;onFinish:(result:QcFinalResult)=>void}) {
  const returnedBySize=asNumberTuple(seed.returnedGoodBySize.map((qty,index)=>qty+seed.returnedBsBySize[index]))
  const sizeRange=`${seed.sizes[0]}–${seed.sizes[seed.sizes.length-1]}`
  const [bsInputs,setBsInputs]=useState<StringTuple>(()=>asStringTuple(seed.returnedBsBySize.map(String)))
  const [rewashInputs,setRewashInputs]=useState<StringTuple>(['0','0','0'])
  const compatibleProducts=useMemo(()=>productCatalog.filter((product)=>product.sizes.every((size,index)=>size===seed.sizes[index])),[seed.sizes])
  const brandOptions=Array.from(new Set(compatibleProducts.map((product)=>product.brand)))
  const initialBrand=brandOptions.includes(seed.brand)?seed.brand:(brandOptions[0]??seed.brand)
  const [selectedBrand,setSelectedBrand]=useState(initialBrand)
  const productsForBrand=compatibleProducts.filter((product)=>product.brand===selectedBrand)
  const [finalSku,setFinalSku]=useState(productsForBrand[0]?.code??'')
  const [destination,setDestination]=useState('Gudang FG Utama')
  const [reviewing,setReviewing]=useState(false)
  const selectedProduct=productsForBrand.find((product)=>product.code===finalSku)??productsForBrand[0]
  const qcBs=asNumberTuple(bsInputs.map((value)=>Number(value)||0))
  const rewash=asNumberTuple(rewashInputs.map((value)=>Number(value)||0))
  const qcGood=asNumberTuple(returnedBySize.map((qty,index)=>Math.max(0,qty-qcBs[index]-rewash[index])))
  const totalGood=total(qcGood),totalBs=total(qcBs),totalRewash=total(rewash),totalStuck=total(seed.stuckBySize),expectedTotal=total(seed.expected)
  const updateException=(kind:'bs'|'rewash',index:number,raw:string)=>{
    const other=kind==='bs'?rewash[index]:qcBs[index]
    const next=cleanNumber(raw,Math.max(0,returnedBySize[index]-other))
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
  const finish=()=>onFinish({...seed,brand:selectedBrand,qcGood,qcBs,rewash,finalSku,finalProductName:selectedProduct?.name??seed.model,finalColor:selectedProduct?.color??'',finalRange:selectedProduct?.range??sizeRange,destination})

  return <>
    <section className="panel qc-source-card"><span className="qc-source-order"><Shirt/></span><div><small>{seed.brand} · BATCH PRODUKSI · BATCH DISTRIBUSI</small><h2>{seed.parentId} · Batch {seed.batchId}</h2><p>{seed.model} · {seed.material}</p></div><div className="qc-mandor-hero"><UserRound/><span><small>MANDOR PENANGGUNG JAWAB</small><strong>{seed.mandor}</strong></span></div><div><small>LAUNDRY</small><strong>{seed.laundry||'Belum tercatat'}</strong></div></section>
    <section className="qc-flow-layout">
      <div className="panel qc-size-workbench">
        <header><div><span>01 · HASIL FISIK PER SIZE</span><h2>Good dihitung otomatis</h2><p>Qty kembali dan Stuck berasal dari penerimaan Laundry per size—bukan dibagi rata atau ditebak.</p></div><ClipboardCheck/></header>
        <div className="qc-good-formula"><span><small>QTY KEMBALI</small><strong>{total(returnedBySize)} pcs</strong></span><b>−</b><span className="input"><small>BS</small><strong>{totalBs} pcs</strong></span><b>−</b><span className="input"><small>CUCI ULANG</small><strong>{totalRewash} pcs</strong></span><b>=</b><span className="result"><small>GOOD OTOMATIS</small><strong>{totalGood} pcs</strong></span></div>
        <div className="qc-size-head"><span>Size</span><span>Potongan</span><span>Kembali</span><span>BS · input</span><span>Cuci ulang · input</span><span>Stuck Laundry</span><span className="result">Good otomatis</span></div>
        <div className="qc-size-rows" data-keyboard-grid>{seed.sizes.map((size,index)=><div className="qc-size-row" key={size}><strong data-label="SIZE">{size}</strong><span data-label="POTONGAN">{seed.expected[index]}</span><span data-label="KEMBALI">{returnedBySize[index]}</span><label data-label="BS · INPUT"><input data-grid-row={index} data-grid-col={0} inputMode="numeric" value={bsInputs[index]} onFocus={(event)=>event.currentTarget.select()} onChange={(event)=>updateException('bs',index,event.target.value)}/></label><label data-label="CUCI ULANG · INPUT"><input data-grid-row={index} data-grid-col={1} inputMode="numeric" value={rewashInputs[index]} onFocus={(event)=>event.currentTarget.select()} onChange={(event)=>updateException('rewash',index,event.target.value)}/></label><span data-label="STUCK" className={seed.stuckBySize[index]>0?'stuck':''}>{seed.stuckBySize[index]}</span><strong data-label="GOOD · OTOMATIS" className="good"><small>OTOMATIS</small>{qcGood[index]}</strong></div>)}</div>
        <div className="keyboard-grid-hint"><kbd>Enter</kbd> turun · <kbd>Shift + Enter</kbd> naik · <kbd>↑ ↓ ← →</kbd> pindah sel</div>
        <div className="qc-equation"><span><small>POTONGAN</small><strong>{expectedTotal}</strong></span><b>=</b><span><small>GOOD</small><strong>{totalGood}</strong></span><b>+</b><span><small>BS</small><strong>{totalBs}</strong></span><b>+</b><span><small>CUCI ULANG</small><strong>{totalRewash}</strong></span><b>+</b><span className="stuck"><small>STUCK</small><strong>{totalStuck}</strong></span></div>
        {totalStuck>0&&<div className="qc-auto-stuck"><Waves/><div><strong>{totalStuck} pcs masih di {seed.laundry}</strong><span>{seed.sizes.map((size,index)=>`Size ${size}: ${seed.stuckBySize[index]}`).join(' · ')}. Belum boleh berubah menjadi BS sebelum fisiknya kembali.</span></div></div>}
        <section className="qc-final-product"><header><span>02 · IDENTITAS BARANG JADI</span><strong>Pilih merek, lalu SKU</strong><small>SKU yang tampil sudah dibatasi ke range Size {sizeRange} supaya posting FG tidak salah produk.</small></header><div className="qc-final-fields" data-keyboard-scope>
          <label><span>1 · MEREK</span><select value={selectedBrand} onChange={(event)=>chooseBrand(event.target.value)}>{brandOptions.map((brand)=><option key={brand}>{brand}</option>)}</select></label>
          <label><span>2 · SKU</span><select value={finalSku} onChange={(event)=>{setFinalSku(event.target.value);setReviewing(false)}}>{productsForBrand.map((product)=><option value={product.code} key={product.code}>{product.code}</option>)}</select></label>
          <article className="qc-product-preview"><Shirt/><span><small>3 · BARANG TERPILIH</small><strong>{selectedProduct?.name??'Produk belum tersedia'} · {selectedProduct?.color??'—'}</strong><em>{selectedBrand} · Range {selectedProduct?.range??sizeRange} · {seed.material}</em></span></article>
          <label><span>4 · TUJUAN FG</span><select value={destination} onChange={(event)=>{setDestination(event.target.value);setReviewing(false)}}><option>Gudang FG Utama</option><option>Gudang FG Cadangan</option></select></label>
        </div></section>
      </div>
      <aside className="panel qc-review-ticket"><div className="qc-review-title"><span>REVIEW FINISHING · {selectedBrand}</span><h2>{selectedBrand} · SKU {finalSku||'—'}</h2><p>{selectedProduct?.name??seed.model} · {selectedProduct?.color??seed.material} · Size {sizeRange}</p><div className="qc-ticket-mandor"><UserRound/><span><small>MANDOR</small><strong>{seed.mandor}</strong></span></div></div><div className="qc-review-totals"><p><span>Lolos QC / serah FG</span><strong>{totalGood} pcs</strong></p><p><span>BS dari QC</span><strong>{totalBs} pcs</strong></p><p><span>Cuci ulang</span><strong>{totalRewash} pcs</strong></p><p className="stuck"><span>Masih di laundry</span><strong>{totalStuck} pcs</strong></p></div><div className="qc-review-rule"><Info/><span><strong>QC hanya mengesahkan hasil fisik.</strong><small>Good, BS, cuci ulang, dan Stuck diperiksa di sini. BOM dan komponen pembayaran tidak dipilih dari QC.</small></span></div>{!reviewing?<button className="primary-btn qc-review-button" disabled={!selectedProduct} onClick={()=>setReviewing(true)}>Review finishing <ArrowRight/></button>:<div className="qc-final-confirm"><PackageCheck/><div><strong>Komposisi sudah cocok</strong><span>{totalGood+totalBs+totalRewash+totalStuck}/{expectedTotal} pcs terjelaskan.</span></div><button className="primary-btn" disabled={totalGood<=0||!selectedProduct} onClick={finish}>Finalkan QC & lanjut ke Serah FG <ArrowRight/></button></div>}<small className="qc-prototype-note">Prototype frontend: posting backend belum aktif.</small></aside>
    </section>
  </>
}
