import PocketReceiptForm from './PocketReceiptForm'
import { Icon } from '../components/AppIcon'
import { cleanMoneyInput, formatMoneyInput } from '../moneyInput'
import { Field } from './controls'
import { formatQuantity, money, parseDecimal } from './format'
import { useState } from 'react'

type ReceiptMode = 'fabric' | 'accessory' | 'pocket'

type RollDraft = { id: number; yards: string }

export function ProcurementPage() {
  const [mode,setMode] = useState<ReceiptMode>(()=>new URLSearchParams(location.search).get('jenis')==='kantong'?'pocket':'fabric')
  const [fabricUom,setFabricUom] = useState<'yd'|'m'>('yd')
  const [rolls,setRolls] = useState<RollDraft[]>([{id:1,yards:'131,5'},{id:2,yards:'91'},{id:3,yards:'124'},{id:4,yards:''}])
  const [benchmarkPrice,setBenchmarkPrice] = useState('48500')
  const [accessoryQty,setAccessoryQty] = useState('1200')
  const [accessoryPrice,setAccessoryPrice] = useState('850')
  const [historyOpen,setHistoryOpen] = useState(false)
  const [rollDetailOpen,setRollDetailOpen] = useState(false)
  const fabricUnitName=fabricUom==='yd'?'yard':'meter'
  const fabricUnitLabel=fabricUom==='yd'?'Yard (yd)':'Meter (m)'
  const activeRolls=rolls.filter((roll)=>parseDecimal(roll.yards)>0)
  const totalYards=activeRolls.reduce((sum,roll)=>sum+parseDecimal(roll.yards),0)
  const benchmark=parseDecimal(benchmarkPrice)
  const accessoryTotal=parseDecimal(accessoryQty)*parseDecimal(accessoryPrice)
  const updateRoll=(id:number,value:string)=>setRolls((rows)=>rows.map((roll)=>roll.id===id?{...roll,yards:value}:roll))
  const addRoll=()=>setRolls((rows)=>[...rows,{id:Math.max(0,...rows.map((roll)=>roll.id))+1,yards:''}])
  const removeRoll=(id:number)=>setRolls((rows)=>rows.length>1?rows.filter((roll)=>roll.id!==id):rows)

  return <>
    {mode!=='pocket'&&<section className="hero-copy compact procurement-hero"><div className="eyebrow">GUDANG · PENERIMAAN BARANG</div><h1>Pembelian & penerimaan</h1><p>Catat surat jalan saat barang datang. Kain dan kain kantong masuk per roll. Aksesori masuk sesuai satuan pembelian.</p></section>}
    <div className={'procurement-mode-bar panel'+(mode==='pocket'?' pocket-receipt-modes':'')} role="tablist" aria-label="Jenis penerimaan">
      <div className="mode-tabs"><button role="tab" aria-selected={mode==='fabric'} className={mode==='fabric'?'active':''} onClick={()=>setMode('fabric')}><Icon name="ruler"/><span><strong>Kain</strong><small>Roll + {fabricUnitName}</small></span></button><button role="tab" aria-selected={mode==='accessory'} className={mode==='accessory'?'active':''} onClick={()=>setMode('accessory')}><Icon name="boxes"/><span><strong>Aksesori</strong><small>Qty langsung</small></span></button><button role="tab" aria-selected={mode==='pocket'} className={mode==='pocket'?'active':''} onClick={()=>setMode('pocket')}><Icon name="ruler"/><span><strong>Kain kantong</strong><small>Roll + panjang</small></span></button></div>
      {mode!=='pocket'&&<div className="receiving-rule"><Icon name="document"/><span><strong>Dasar penerimaan: surat jalan</strong><small>Kasbon boleh menyusul tanpa menahan stok masuk.</small></span></div>}
    </div>
    {mode==='pocket'?<PocketReceiptForm/>:<section className="procurement-layout">
      <div className="panel receipt-editor">
        <div className="proc-panel-head"><div><div className="eyebrow">PENERIMAAN BARU</div><h2>{mode==='fabric'?'Kain per gulung':'Aksesori per jumlah'}</h2></div><span className="draft-pill">Draft</span></div>
        <div className="receipt-meta-grid" key={mode}>
          <Field label="Pabrik / supplier"><input className="erp-input" defaultValue={mode==='fabric'?'Sinaran':'Mitra Aksesori'}/></Field>
          <Field label={mode==='fabric'?'Nama bahan':'Nama aksesori'}><input className="erp-input" defaultValue={mode==='fabric'?'1069 Ori':'Kancing Metal 17 mm'}/></Field>
          <Field label="Nomor surat jalan"><input className="erp-input" defaultValue={mode==='fabric'?'SJ-SNR-0827-19':'SJ-MA-0827-08'}/></Field>
          <Field label="Tanggal barang datang"><input className="erp-input" type="date" defaultValue="2026-08-27"/></Field>
        </div>
        {mode==='fabric'?<>
          <div className="fabric-uom-picker">
            <div><Icon name="ruler"/><span><strong>UOM PENERIMAAN & HARGA</strong><small>Pilih sesuai satuan surat jalan. Angka roll dan harga disimpan dalam satuan yang sama.</small></span></div>
            <div className="fabric-uom-options" role="radiogroup" aria-label="UOM kain">
              {([['yd','Yard','yd'],['m','Meter','m']] as const).map(([value,label,short])=><button type="button" role="radio" aria-checked={fabricUom===value} className={fabricUom===value?'active':''} key={value} onClick={()=>setFabricUom(value)}><span className="uom-radio">{fabricUom===value&&<i/>}</span><strong>{label}</strong><small>{short}</small></button>)}
            </div>
            <p><Icon name="audit"/> UOM menjadi snapshot penerimaan. Invoice final wajib mengikuti UOM receipt; layar ini tidak mengonversi Yard ↔ Meter diam-diam.</p>
          </div>
          <div className="roll-entry-head"><div><span>RINCIAN GULUNG</span><strong>Satu baris untuk satu roll</strong></div><button className="soft-btn add-roll" onClick={addRoll}><Icon name="plus"/> Tambah roll</button></div>
          <div className="roll-entry-list" data-keyboard-grid>{rolls.map((roll,index)=><div className="roll-entry-row" key={roll.id}><span className="roll-number">{String(index+1).padStart(2,'0')}</span><div><label htmlFor={`roll-${roll.id}`}>{fabricUnitLabel} pada gulung</label><div className="yard-input"><input id={`roll-${roll.id}`} data-grid-row={index} data-grid-col={0} inputMode="decimal" value={roll.yards} placeholder="0" onChange={(event)=>updateRoll(roll.id,event.target.value)}/><span>{fabricUom}</span></div></div><small>{parseDecimal(roll.yards)>0?`${formatQuantity(parseDecimal(roll.yards))} ${fabricUnitName} siap diterima`:'Belum diisi'}</small><button className="remove-roll" aria-label={`Hapus roll ${index+1}`} onClick={()=>removeRoll(roll.id)} disabled={rolls.length===1}><Icon name="trash"/></button></div>)}</div>
          <div className="benchmark-entry"><div><Icon name="cost"/><span><strong>Harga benchmark / {fabricUnitName}</strong><small>Dipakai sementara sampai kasbon aktual datang.</small></span></div><div className="money-input"><span>Rp</span><input inputMode="numeric" value={formatMoneyInput(benchmarkPrice)} onChange={(event)=>setBenchmarkPrice(cleanMoneyInput(event.target.value))}/></div></div>
          <div className="receipt-total-strip"><div><span>TOTAL GULUNG</span><strong>{activeRolls.length}</strong><small>roll terisi</small></div><div><span>TOTAL PANJANG</span><strong>{formatQuantity(totalYards)} {fabricUom}</strong><small>jumlah semua roll</small></div><div className="receipt-grand-total"><span>NILAI BENCHMARK</span><strong>{money(totalYards*benchmark)}</strong><small>{formatQuantity(totalYards)} {fabricUom} × {money(benchmark)}</small></div></div>
        </>:<>
          <div className="accessory-entry-grid"><Field label="Jumlah diterima"><div className="qty-unit-input"><input inputMode="numeric" value={accessoryQty} onChange={(event)=>setAccessoryQty(event.target.value)}/><span>pcs</span></div></Field><Field label="Harga benchmark / pcs"><div className="money-input"><span>Rp</span><input inputMode="numeric" value={formatMoneyInput(accessoryPrice)} onChange={(event)=>setAccessoryPrice(cleanMoneyInput(event.target.value))}/></div></Field></div>
          <div className="accessory-total-card"><div><Icon name="boxes"/><span><small>JUMLAH MASUK</small><strong>{formatQuantity(parseDecimal(accessoryQty),0)} pcs</strong></span></div><div><small>NILAI BENCHMARK</small><strong>{money(accessoryTotal)}</strong></div></div>
        </>}
        <div className="receipt-actions"><button className="soft-btn">Simpan draft</button><button className="primary-btn">Review penerimaan <Icon name="arrow"/></button></div>
      </div>
      <aside className="procurement-side">{mode==='fabric'?<>
        <div className="panel current-receipt-card">
          <div className="current-receipt-head"><div><span>HARGA AKTIF</span><h2>Sinaran · 1069 Ori</h2><small>SJ-SNR-0821-07 · masuk 21 Agu 2026</small></div><span className="actual-pill"><Icon name="check"/> Aktual</span></div>
          <div className="receipt-quantity-hero"><div><span>27 gulung</span><strong>3.029,5 yd</strong></div><Icon name="ruler"/></div>
          <div className="active-price"><span>Harga kasbon terbaru</span><strong>{money(49200)}<small>/ yard</small></strong><em>Nilai aktif {money(3029.5*49200)}</em></div>
          <button className="history-toggle" aria-expanded={historyOpen} onClick={()=>setHistoryOpen(!historyOpen)}><span><Icon name="history"/> Riwayat harga</span><span>{historyOpen?'Tutup':'Lihat'} <Icon name={historyOpen?'up':'down'}/></span></button>
          {historyOpen&&<div className="price-history"><div><span className="timeline-dot current"/><div><strong>Rp49.200 / yd</strong><small>Kasbon aktual · 26 Agu 2026</small></div><b>Aktif</b></div><div><span className="timeline-dot"/><div><strong>Rp48.500 / yd</strong><small>Benchmark saat barang datang · 21 Agu 2026</small></div><b>Awal</b></div><div className="price-delta"><span>Selisih nilai</span><strong>+{money(3029.5*(49200-48500))}</strong></div></div>}
          <button className="roll-preview-toggle" aria-expanded={rollDetailOpen} onClick={()=>setRollDetailOpen(!rollDetailOpen)}><span>Rincian 27 roll</span><Icon name={rollDetailOpen?'up':'down'}/></button>
          {rollDetailOpen&&<div className="roll-preview-grid">{[131.5,91,124,115.5,109,127.25].map((yard,index)=><span key={`${yard}-${index}`}><small>ROLL {String(index+1).padStart(2,'0')}</small><strong>{formatQuantity(yard,2)} yd</strong></span>)}<span className="more-rolls"><strong>+21</strong><small>roll lainnya</small></span></div>}
        </div>
        <div className="panel pending-cost-card"><div><span className="estimated-dot"/><div><strong>Malibu · Denim 14 oz</strong><small>18 gulung · 1.984 yd</small></div><span>Menunggu kasbon</span></div><div><small>Harga benchmark aktif sementara</small><strong>{money(47800)} / yd</strong><em>{money(1984*47800)}</em></div></div>
      </>:<>
        <div className="panel current-receipt-card accessory-current"><div className="current-receipt-head"><div><span>PENERIMAAN TERAKHIR</span><h2>Kancing Metal 17 mm</h2><small>Mitra Aksesori · SJ-MA-0827-08</small></div><span className="actual-pill"><Icon name="check"/> Diterima</span></div><div className="accessory-quantity-hero"><span>Jumlah masuk</span><strong>1.200 pcs</strong><small>Tidak perlu dibuat roll atau yard.</small></div><div className="active-price"><span>Harga aktif</span><strong>{money(850)}<small>/ pcs</small></strong><em>Total {money(1200*850)}</em></div></div>
        <div className="panel procurement-note"><Icon name="link"/><div><strong>Tetap satu alur gudang</strong><p>Kain dan aksesori masuk dari surat jalan yang sama, tetapi cara hitung fisiknya tetap sesuai bentuk barang.</p></div></div>
      </>}</aside>
    </section>}
  </>
}
