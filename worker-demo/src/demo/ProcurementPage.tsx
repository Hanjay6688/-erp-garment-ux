import {Boxes, ClipboardList, Coins, FileText, History, Ruler} from 'lucide-react'
import {archiveDocumentFor, archiveSource, fabricIdentity} from './fabricArchive'
import {FabricReceiptRegister, FabricReceiptSource} from './FabricReceiptSource'
import './receiving.css'
import PocketReceiptForm from './PocketReceiptForm'
import { Icon } from '../components/AppIcon'
import { cleanMoneyInput, formatMoneyInput } from '../moneyInput'
import { Field } from './controls'
import { formatQuantity, money, parseDecimal } from './format'
import { ReceiptRollRows } from './ReceiptRollRows'
import { useState } from 'react'
import { changeSession, usePlannerSession } from './planner/session'
import { type AccessoryReceipt, type FabricReceipt } from './planner/model'
import { accessoryReceiptBlockers, prepareFabricReceipt, postFabricReceipt, reverseWarehouseReceipt, type FabricReceiptDraft } from './fabricReceipts'
import {receiptDocumentPath} from './receiptRollCorrection'
import { StockSourceReversal } from './StockSourceReversal'
import { ReasonDialog } from './planner/ReasonDialog'
import { dayOk, lastWarehouseDay } from './warehouseDay'
import { useAccessoryBook } from './accessoryPricing'
import './demoCorrection.css'

type ReceiptMode = 'fabric' | 'accessory' | 'pocket'

type RollDraft = { id: number; yards: string }
const fabricDraftKey='erp.demo.fabric.receipt-draft.v1'
const standardReceipt=():FabricReceiptDraft=>({id:crypto.randomUUID(),number:'SJ-SNR-0827-19',material:'1069 Ori',supplier:'Sinaran',day:'2026-08-27',unit:'yd',price:'48500',lengths:['131,5','91','124','']})
const accessoryDraftKey='erp.demo.accessory.receipt-draft.v1'
const standardAccessory=()=>({id:crypto.randomUUID(),number:'SJ-MA-0827-08',code:'ACC-BTN-017-MTL',supplier:'Mitra Aksesori',day:'2026-08-27',qty:'1200',rate:'850'})

export function ProcurementPage() {
  const session=usePlannerSession()
  const accessoryItems=useAccessoryBook().items.filter(item=>item.active&&item.stockUom.toLowerCase()==='pcs')
  const [initial]=useState<FabricReceiptDraft>(()=>JSON.parse(sessionStorage.getItem(fabricDraftKey)??'null')??standardReceipt())
  const [fabric,setFabric]=useState(initial)
  const [rollCount,setRollCount]=useState<string|null>(null)
  const [receiptPreview,setReceiptPreview]=useState<FabricReceipt|null>(null)
  const [receiptNotice,setReceiptNotice]=useState('')
  const [postedNumber,setPostedNumber]=useState('')
  const [receiptError,setReceiptError]=useState('')
  const query=new URLSearchParams(location.search)
  const linkedReceipt=query.get('surat')
  const [mode,setMode] = useState<ReceiptMode>(()=>{
    const kind=query.get('jenis')
    return kind==='kantong'?'pocket':kind==='aksesori'?'accessory':'fabric'
  })
  const [fabricUom,setFabricUom] = useState<'yd'|'m'>(initial.unit)
  const [rolls,setRolls] = useState<RollDraft[]>(()=>initial.lengths.map((yards,index)=>({id:index+1,yards})))
  const [benchmarkPrice,setBenchmarkPrice] = useState(initial.price)
  const [accessory,setAccessory] = useState<ReturnType<typeof standardAccessory>>(()=>JSON.parse(sessionStorage.getItem(accessoryDraftKey)??'null')??standardAccessory())
  const [accessoryPreview,setAccessoryPreview]=useState<AccessoryReceipt|null>(null)
  const [historyOpen,setHistoryOpen] = useState(false)
  const [rollDetailOpen,setRollDetailOpen] = useState(false)
  const fabricUnitName=fabricUom==='yd'?'yard':'meter'
  const activeRolls=rolls.filter((roll)=>parseDecimal(roll.yards)>0)
  const totalYards=activeRolls.reduce((sum,roll)=>sum+parseDecimal(roll.yards),0)
  const benchmark=parseDecimal(benchmarkPrice)
  const accessoryTotal=parseDecimal(accessory.qty)*parseDecimal(accessory.rate)
  const updateRoll=(id:number,value:string)=>setRolls((rows)=>rows.map((roll)=>roll.id===id?{...roll,yards:value}:roll))
  const addRoll=()=>setRolls((rows)=>[...rows,{id:Math.max(0,...rows.map((roll)=>roll.id))+1,yards:''}])
  const removeRoll=(id:number)=>setRolls((rows)=>rows.length>1?rows.filter((roll)=>roll.id!==id):rows)
  function chooseMode(next:ReceiptMode) {
    if(mode===next)return
    const url=new URL(location.href)
    url.search=new URLSearchParams({jenis:next==='pocket'?'kantong':next==='accessory'?'aksesori':'kain'}).toString()
    url.hash=''
    window.history.replaceState(window.history.state,'',url)
    setMode(next); setPostedNumber(''); setReceiptNotice(''); setReceiptError('')
  }
  function liveDraft():FabricReceiptDraft {
    return {...fabric,unit:fabricUom,price:benchmarkPrice,lengths:rolls.map(row=>row.yards)}
  }
  function generateRows() {
    const requested=rollCount??String(rolls.length)
    const count=Number(requested)
    if(!/^\d{1,3}$/.test(requested)||count<1){setReceiptError('Isi jumlah roll antara 1 dan 999.');return}
    if(rolls.slice(count).some(row=>row.yards.trim())){setReceiptError('Kosongkan dulu panjang roll yang akan dihapus.');return}
    setRolls(Array.from({length:count},(_,index)=>({id:index+1,yards:rolls[index]?.yards??''})))
    setReceiptError('')
  }
  function reviewReceipt() {
    try{setReceiptPreview(prepareFabricReceipt(liveDraft()));setReceiptError('');setReceiptNotice('')}
    catch(failure){setReceiptError((failure as Error).message)}
  }
  function saveReceipt() {
    if(!receiptPreview)return
    try{
      changeSession(live=>postFabricReceipt(live,receiptPreview))
      sessionStorage.removeItem(fabricDraftKey)
      setFabric({...fabric,id:crypto.randomUUID(),number:''})
      setRolls([{id:1,yards:''}]);setRollCount(null);setReceiptPreview(null);setReceiptError('')
      setPostedNumber(receiptPreview.number)
      setReceiptNotice(receiptPreview.number+' tersimpan · '+receiptPreview.rolls.length+' roll masuk gudang.')
    }catch(failure){setReceiptError((failure as Error).message)}
  }
  function reviewAccessory() {
    const qty=/^[1-9]\d{0,8}$/.test(accessory.qty)?Number(accessory.qty):NaN
    const rate=accessory.rate.trim()?Number(accessory.rate):NaN
    const number=accessory.number.trim(),supplier=accessory.supplier.trim()
    if(!accessoryItems.some(item=>item.code===accessory.code)||!number||!supplier||!dayOk(accessory.day)||!Number.isSafeInteger(Math.round(qty*rate*100))){
      setReceiptError('Isi aksesori, jumlah pcs, harga, dan surat jalan yang sah.');return
    }
    setAccessoryPreview({...accessory,number,supplier,qty,rate});setReceiptError('');setReceiptNotice('')
  }
  function saveAccessory() {
    if(!accessoryPreview)return
    try {
      changeSession(live=>{
        const receipts=live.accessoryReceipts??[]
        if(receipts.some(row=>row.id===accessoryPreview.id))return live
        if(receipts.some(row=>row.number.toLowerCase()===accessoryPreview.number.toLowerCase()))throw Error('Surat jalan aksesori sudah tercatat.')
        return {...live,accessoryReceipts:[accessoryPreview,...receipts]}
      })
      sessionStorage.removeItem(accessoryDraftKey)
      setAccessory({...accessory,id:crypto.randomUUID(),number:'',qty:''})
      setAccessoryPreview(null);setReceiptError('');setReceiptNotice(formatQuantity(accessoryPreview.qty,0)+' pcs aksesori diterima.')
    }catch(failure){setReceiptError((failure as Error).message)}
  }

  const archivedRoll=query.get('arsip')??(location.hash==='#penerimaan-arsip-1069'?'ORI-018':null)
  if(mode==='fabric'&&(linkedReceipt||archivedRoll))return <FabricReceiptSource session={session}
    receipt={linkedReceipt?session.fabricReceipts?.find(row=>row.number===linkedReceipt):undefined}
    archive={archivedRoll?archiveDocumentFor(archivedRoll):undefined} focusRoll={archivedRoll??query.get('roll')??undefined}/>
  return <div className="receiving-page">
    {mode!=='pocket'&&<section className="hero-copy compact procurement-hero"><div className="eyebrow">GUDANG · PENERIMAAN BARANG</div><h1>Pembelian & penerimaan</h1><p>Catat surat jalan saat barang datang. Kain dan kain kantong masuk per roll. Aksesori masuk sesuai satuan pembelian.</p></section>}
    <div className={'procurement-mode-bar panel'+(mode==='pocket'?' pocket-receipt-modes':'')} role="tablist" aria-label="Jenis penerimaan">
      <div className="mode-tabs"><button role="tab" aria-selected={mode==='fabric'} className={mode==='fabric'?'active':''} onClick={()=>chooseMode('fabric')}><Icon name="ruler"/><span><strong>Kain</strong><small>Roll + {fabricUnitName}</small></span></button><button role="tab" aria-selected={mode==='accessory'} className={mode==='accessory'?'active':''} onClick={()=>chooseMode('accessory')}><Icon name="boxes"/><span><strong>Aksesori</strong><small>Qty langsung</small></span></button><button role="tab" aria-selected={mode==='pocket'} className={mode==='pocket'?'active':''} onClick={()=>chooseMode('pocket')}><Icon name="ruler"/><span><strong>Kain kantong</strong><small>Roll + panjang</small></span></button></div>
      {mode!=='pocket'&&<div className="receiving-rule">{mode==='fabric'
        ? <a className="soft-btn receiving-history-link" href="#riwayat-surat-jalan"><History size={16}/> Riwayat surat jalan</a>
        : <><Icon name="document"/><span><strong>Stok masuk dari surat jalan</strong><small>Kasbon bisa menyusul.</small></span></>}</div>}
    </div>
    {mode!=='pocket'&&<section aria-label="Ringkasan draf penerimaan" className="receiving-summary">
      <div><i><Boxes/></i><span>{mode==='fabric'?'Roll terisi':'Jumlah diterima'}</span><strong>{mode==='fabric'?activeRolls.length+' roll':formatQuantity(parseDecimal(accessory.qty),0)+' pcs'}</strong></div>
      {mode==='fabric'&&<div className="receiving-length"><i><Ruler/></i><span>Panjang masuk</span><strong>{formatQuantity(totalYards,6)} {fabricUom}</strong></div>}
      <div className="receiving-estimate"><i><Coins/></i><span>Nilai benchmark</span><strong>{money(mode==='fabric'?totalYards*benchmark:accessoryTotal)}</strong></div>
    </section>}
    {mode==='pocket'?<PocketReceiptForm/>:<section className="procurement-layout">
      <div className="panel receipt-editor">
        <div className="proc-panel-head"><i className="receiving-glyph"><ClipboardList aria-hidden="true"/></i><div><div className="eyebrow">PENERIMAAN BARU</div><h2>{mode==='fabric'?'Kain per gulung':'Aksesori per jumlah'}</h2></div><span className="draft-pill">Draft</span></div>
        <section className="receiving-identity"><header className="receiving-band"><i><FileText aria-hidden="true"/></i><h3>Surat jalan dan barang</h3></header>
        <div className="receipt-meta-grid" key={mode}>
          <Field label="Pabrik / supplier">{mode==='fabric'
            ? <input className="erp-input" value={fabric.supplier} onChange={e=>setFabric({...fabric,supplier:e.target.value})}/>
            : <input className="erp-input" value={accessory.supplier} onChange={e=>setAccessory({...accessory,supplier:e.target.value})}/>}</Field>
          <Field label={mode==='fabric'?'Nama bahan':'Nama aksesori'}>{mode==='fabric'
            ? <input className="erp-input" value={fabric.material} onChange={e=>setFabric({...fabric,material:e.target.value})}/>
            : <select aria-label="Nama aksesori" className="erp-input" value={accessory.code} onChange={e=>setAccessory({...accessory,code:e.target.value})}>
                {accessoryItems.map(item=><option key={item.code} value={item.code}>{item.name}</option>)}</select>}</Field>
          <Field label="Nomor surat jalan">{mode==='fabric'
            ? <input className="erp-input" value={fabric.number} onChange={e=>setFabric({...fabric,number:e.target.value})}/>
            : <input className="erp-input" value={accessory.number} onChange={e=>setAccessory({...accessory,number:e.target.value})}/>}</Field>
          <Field label="Tanggal barang datang">{mode==='fabric'
            ? <input className="erp-input" type="date" max={lastWarehouseDay()} value={fabric.day} onChange={e=>setFabric({...fabric,day:e.target.value})}/>
            : <input className="erp-input" type="date" max={lastWarehouseDay()} value={accessory.day} onChange={e=>setAccessory({...accessory,day:e.target.value})}/>}</Field>
        </div></section>
        {mode==='fabric'?<>
          <div className="fabric-uom-picker">
            <div><Icon name="ruler"/><span><strong>Satuan penerimaan</strong><small>Panjang dan harga mengikuti satuan pada surat jalan.</small></span></div>
            <div className="fabric-uom-options" role="radiogroup" aria-label="UOM kain">
              {([['yd','Yard','yd'],['m','Meter','m']] as const).map(([value,label,short])=><button type="button" role="radio" aria-checked={fabricUom===value} className={fabricUom===value?'active':''} key={value} onClick={()=>setFabricUom(value)}><span className="uom-radio">{fabricUom===value&&<i/>}</span><strong>{label}</strong><small>{short}</small></button>)}
            </div>
          </div>
          <div className="roll-entry-head"><div className="receiving-band"><i><Ruler aria-hidden="true"/></i><h3>Rincian gulung</h3></div><button className="soft-btn add-roll" onClick={addRoll}><Icon name="plus"/> Tambah roll</button></div>
          <div className="fabric-generate-rolls">
            <label>Jumlah roll<input className="erp-input" value={rollCount??String(rolls.length)} inputMode="numeric"
              onChange={e=>setRollCount(e.target.value.replace(/\D/g,'').slice(0,3))}
              onKeyDown={e=>{if(e.key==='Enter'){e.preventDefault();generateRows()}}}/></label>
            <button type="button" className="soft-btn" onClick={generateRows}>Buat baris roll</button>
          </div>
          <ReceiptRollRows rows={rolls.map(roll => ({ key: roll.id, length: roll.yards }))} unit={fabricUom} byNumber
            onChange={(index, value) => updateRoll(rolls[index].id, value)} onRemove={index => removeRoll(rolls[index].id)}/>
          <div className="benchmark-entry"><div><Icon name="cost"/><span><strong>Harga benchmark / {fabricUnitName}</strong><small>Dipakai sementara sampai kasbon aktual datang.</small></span></div><div className="money-input"><span>Rp</span><input inputMode="numeric" value={formatMoneyInput(benchmarkPrice)} onChange={(event)=>setBenchmarkPrice(cleanMoneyInput(event.target.value))}/></div></div>
        </>:<>
          <div className="accessory-entry-grid"><Field label="Jumlah diterima"><div className="qty-unit-input"><input aria-label="Jumlah diterima" inputMode="numeric" value={accessory.qty} onChange={event=>setAccessory({...accessory,qty:cleanMoneyInput(event.target.value)})}/><span>pcs</span></div></Field><Field label="Harga benchmark / pcs"><div className="money-input"><span>Rp</span><input inputMode="numeric" value={formatMoneyInput(accessory.rate)} onChange={event=>setAccessory({...accessory,rate:cleanMoneyInput(event.target.value)})}/></div></Field></div>
        </>}
        {receiptError&&!receiptPreview&&!accessoryPreview&&<p role="alert" className="wh-feedback">{receiptError}</p>}
        {receiptNotice&&<p role="status" className="wh-feedback">{receiptNotice}{mode==='fabric'&&postedNumber&&<a className="receipt-confirm-link" href={receiptDocumentPath(postedNumber)}>Buka penerimaan <Icon name="arrow"/></a>}</p>}
        <div className="receipt-actions"><button className="soft-btn" onClick={()=>{
          if(mode==='fabric')sessionStorage.setItem(fabricDraftKey,JSON.stringify(liveDraft()))
          else sessionStorage.setItem(accessoryDraftKey,JSON.stringify(accessory))
          setPostedNumber('');setReceiptNotice('Draft penerimaan tersimpan.');setReceiptError('')
        }}>Simpan draft</button><button className="primary-btn" onClick={mode==='fabric'?reviewReceipt:reviewAccessory}>Review penerimaan <Icon name="arrow"/></button></div>
      </div>
      <aside className="procurement-side">{mode==='fabric'?<>
        <FabricReceiptRegister session={session}/>
        <div id="penerimaan-arsip-1069" className="panel current-receipt-card">
          <div className="current-receipt-head"><div><span>HARGA AKTIF</span><h2>Sinaran · {fabricIdentity(session,archiveDocumentFor('ORI-018')!.key,'1069 Ori')}</h2><small>SJ-SNR-0821-07 · masuk 21 Agu 2026</small></div><span className="actual-pill"><Icon name="check"/> Aktual</span></div>
          <a className="current-receipt-source" href={archiveSource('ORI-018').href}>Buka surat jalan <Icon name="arrow"/></a>
          <div className="receipt-quantity-hero"><div><span>27 gulung</span><strong>3.029,5 yd</strong></div><Icon name="ruler"/></div>
          <div className="active-price"><span>Harga kasbon terbaru</span><strong>{money(49200)}<small>/ yard</small></strong><em>Nilai aktif {money(3029.5*49200)}</em></div>
          <button className="history-toggle" aria-expanded={historyOpen} onClick={()=>setHistoryOpen(!historyOpen)}><span><Icon name="history"/> Riwayat harga</span><span>{historyOpen?'Tutup':'Lihat'} <Icon name={historyOpen?'up':'down'}/></span></button>
          {historyOpen&&<div className="price-history"><div><span className="timeline-dot current"/><div><strong>Rp49.200 / yd</strong><small>Kasbon aktual · 26 Agu 2026</small></div><b>Aktif</b></div><div><span className="timeline-dot"/><div><strong>Rp48.500 / yd</strong><small>Benchmark saat barang datang · 21 Agu 2026</small></div><b>Awal</b></div><div className="price-delta"><span>Selisih nilai</span><strong>+{money(3029.5*(49200-48500))}</strong></div></div>}
          <button className="roll-preview-toggle" aria-expanded={rollDetailOpen} onClick={()=>setRollDetailOpen(!rollDetailOpen)}><span>Rincian 27 roll</span><Icon name={rollDetailOpen?'up':'down'}/></button>
          {rollDetailOpen&&<div className="roll-preview-grid">{[131.5,91,124,115.5,109,127.25].map((yard,index)=><span key={`${yard}-${index}`}><small>ROLL {String(index+1).padStart(2,'0')}</small><strong>{formatQuantity(yard,2)} yd</strong></span>)}<span className="more-rolls"><strong>+21</strong><small>roll lainnya</small></span></div>}
        </div>
        <div className="panel pending-cost-card"><div><span className="estimated-dot"/><div><strong>Malibu · Denim 14 oz</strong><small>18 gulung · 1.984 yd</small></div><span>Menunggu kasbon</span></div><div><small>Harga benchmark aktif sementara</small><strong>{money(47800)} / yd</strong><em>{money(1984*47800)}</em></div></div>
      </>:<>
        {!!session.accessoryReceipts?.length&&<section className="panel fabric-receipts" id="dokumen-penerimaan" aria-label="Penerimaan aksesori tersimpan">
          <h2>Riwayat penerimaan aksesori</h2>{session.accessoryReceipts.map(row=><details key={row.id} open={linkedReceipt===row.number||undefined}>
            <summary><strong>{formatQuantity(row.qty,0)} pcs · {accessoryItems.find(item=>item.code===row.code)?.name??row.code}</strong>
              <small>{row.number} · {row.supplier}{row.reversal?' · Dibalik':''}</small></summary>
            <StockSourceReversal label="Balikkan penerimaan aksesori" document={row.number} reversal={row.reversal} blockers={accessoryReceiptBlockers(session,row)}
              onReverse={reason=>{changeSession(current=>reverseWarehouseReceipt(current,'accessory',row.id,reason));setReceiptNotice(row.number+' dibalik.')}}/>
          </details>)}</section>}
        <div className="panel current-receipt-card accessory-current"><div className="current-receipt-head"><div><span>PENERIMAAN TERAKHIR</span><h2>Kancing Metal 17 mm</h2><small>Mitra Aksesori · SJ-MA-0827-08</small></div><span className="actual-pill"><Icon name="check"/> Diterima</span></div><div className="accessory-quantity-hero"><span>Jumlah masuk</span><strong>1.200 pcs</strong><small>Tidak perlu dibuat roll atau yard.</small></div><div className="active-price"><span>Harga aktif</span><strong>{money(850)}<small>/ pcs</small></strong><em>Total {money(1200*850)}</em></div></div>
        <div className="panel procurement-note"><Icon name="link"/><div><strong>Tetap satu alur gudang</strong><p>Kain dan aksesori masuk dari surat jalan yang sama, tetapi cara hitung fisiknya tetap sesuai bentuk barang.</p></div></div>
      </>}</aside>
    </section>}
    {accessoryPreview&&<ReasonDialog title={'Terima '+accessoryPreview.number} closeLabel="Kembali" onClose={()=>setAccessoryPreview(null)} className="demo-operation-dialog">
      <div className="demo-operation-form">
        <p>{accessoryItems.find(item=>item.code===accessoryPreview.code)?.name} · {accessoryPreview.supplier} · {accessoryPreview.day}</p>
        <div className="demo-operation-facts"><article><small>Jumlah masuk</small><strong>{formatQuantity(accessoryPreview.qty,0)} pcs</strong></article>
          <article><small>Nilai acuan</small><strong>{money(accessoryPreview.qty*accessoryPreview.rate)}</strong></article></div>
        {receiptError&&<p role="alert">{receiptError}</p>}
        <footer><button className="primary-btn" onClick={saveAccessory}>Sahkan penerimaan aksesori</button></footer>
      </div>
    </ReasonDialog>}
    {receiptPreview&&<ReasonDialog title={'Terima '+receiptPreview.number} closeLabel="Kembali" onClose={()=>setReceiptPreview(null)} className="demo-operation-dialog">
      <div className="demo-operation-form">
        <p>{receiptPreview.material} · {receiptPreview.supplier} · {receiptPreview.day}</p>
        <div className="demo-operation-facts"><article><small>Roll masuk</small><strong>{receiptPreview.rolls.length} roll</strong></article>
          <article><small>Harga sementara</small><strong>{money(receiptPreview.rate)} / {receiptPreview.unit}</strong></article></div>
        <div className="fabric-receipt-review">{receiptPreview.rolls.map(roll=><div className="fabric-receipt-roll" key={roll.id}>
          <span>{roll.id}</span><strong>{formatQuantity(roll.length)} {receiptPreview.unit}</strong>
        </div>)}</div>
        {receiptError&&<p role="alert">{receiptError}</p>}
        <footer><button className="primary-btn" onClick={saveReceipt}>Sahkan penerimaan kain</button></footer>
      </div>
    </ReasonDialog>}
  </div>
}
