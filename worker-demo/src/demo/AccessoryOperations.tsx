import NumberEntry from '../../../src/components/NumberEntry'
import { useState } from 'react'
import { ArrowLeftRight, ClipboardCheck, PackageOpen, Plus, ScanLine, Search, Wrench, X } from 'lucide-react'
import { browseMatchPieces } from '../browseMatch'
import { accessoryStockAt, amountText, mainAccessories, serviceAccessories, useAccessoryBook, type AccessoryLocation } from './accessoryPricing'
import { closeCustody, inspectSalvage, openSalvage, postCustody, postService, receiveSalvage, reverseSalvageInspection, reverseService, salvageInspectionBlockers, salvageLinks, salvageProgress, serviceActions, serviceReversalBlockers, type SalvageDocument, type ServiceAction } from './accessoryOperations'
import { StockSourceReversal } from './StockSourceReversal'
import { ReasonDialog } from './planner/ReasonDialog'
import { changeSession, usePlannerSession } from './planner/session'
import { lastWarehouseDay } from './warehouseDay'
import './demoCorrection.css'

const newId=(prefix:string)=>prefix+'-'+crypto.randomUUID().slice(0,8).toUpperCase()
const digits=(value:string)=>value.replace(/\D/g,'').slice(0,9)
const qtyText=(n:number)=>n.toLocaleString('id-ID')+' pcs'

type ServiceDraft={id:string;action:ServiceAction;location:AccessoryLocation;day:string;reason:string;lines:{id:string;code:string;qty:string;job:string}[]}
type CustodyDraft={id:string;customer:string;item:string;qty:string;job:string;day:string}
const emptyLine=()=>({id:newId('ITEM'),code:'',qty:'',job:''})

export function AccessoryService() {
  const session=usePlannerSession()
  const items=useAccessoryBook().items.filter(item=>item.active&&item.stockUom==='pcs')
  const [draft,setDraft]=useState<ServiceDraft|null>(null)
  const [custody,setCustody]=useState<CustodyDraft|null>(null)
  const [release,setRelease]=useState<{id:string;day:string}|null>(null)
  const [error,setError]=useState('')
  const [query,setQuery]=useState(()=>new URLSearchParams(location.search).get('dokumen')??'')
  const [feedback,setFeedback]=useState('')
  const atService=items.map(item=>({item,qty:accessoryStockAt(item,serviceAccessories,session)})).filter(row=>row.qty>0)
  const docs=(session.serviceDocuments??[]).filter(doc=>browseMatchPieces(query,doc.lines.map(row=>row.qty),doc.id,doc.day,doc.reason,
    ...doc.lines.flatMap(row=>[row.name,row.job,row.code]))).slice().reverse()
  const notes=(session.accessoryCustody??[]).slice().reverse()
  const source=draft?.action==='TO_SERVICE'?mainAccessories:draft?.action==='FROM_SERVICE'?serviceAccessories:draft?.location??mainAccessories
  const revise=(values:Partial<ServiceDraft>)=>setDraft(current=>current?{...current,...values}:null)
  const save=(action:()=>void,message:string)=>{
    try{action();setDraft(null);setCustody(null);setRelease(null);setFeedback(message);setError('')}
    catch(err){setError((err as Error).message)}
  }
  return <section className="panel demo-ops-panel" aria-label="Pemakaian dan Pos Servis">
    <header className="demo-ops-header"><div className="demo-operation-heading"><i><Wrench/></i><div><h2>Pemakaian &amp; Pos Servis</h2><p>Catat aksesori yang dipakai per pekerjaan atau pindahkan persediaan kerja antarlokasi.</p></div></div>
      <div className="demo-operation-actions"><button type="button" className="soft-btn" onClick={()=>{setError('');setCustody({id:newId('TTP'),customer:'',item:'',qty:'',job:'',day:lastWarehouseDay()})}}><PackageOpen size={16}/> Catat titipan</button>
        <button type="button" className="primary-btn" onClick={()=>{setError('');setDraft({id:newId('SRV'),action:'USE',location:mainAccessories,day:lastWarehouseDay(),reason:'',lines:[emptyLine()]})}}><Plus size={17}/> Catat pemakaian atau transfer</button></div>
    </header>
    {feedback&&<p role="status" className="biz-inline-notice">{feedback}</p>}
    <div className="demo-ops-columns">
      <section className="demo-ops-card"><div className="demo-operation-heading"><i><ArrowLeftRight/></i><div><h3>Saldo Pos Servis</h3><p>Stok kerja yang tersedia sekarang.</p></div></div>
        {atService.length?<ul>{atService.map(({item,qty})=><li key={item.code}><span>{item.name}</span><strong>{qtyText(qty)}</strong></li>)}</ul>:<p>Belum ada stok di Pos Servis.</p>}</section>
      <section className="demo-ops-card demo-operation-history"><div className="demo-operation-heading"><i><PackageOpen/></i><div><h3>Titipan pelanggan</h3><p>Barang milik pelanggan yang sedang ditangani.</p></div></div>
        {!notes.length&&<p>Belum ada titipan.</p>}
        {notes.map(row=><article key={row.id}><strong>{qtyText(row.qty)} · {row.item}</strong><small>{row.customer} · {row.job} · {row.day}</small>
          {row.returnedOn?<small>Dikembalikan {row.returnedOn}</small>:<div><button className="soft-btn" onClick={()=>{setError('');setRelease({id:row.id,day:lastWarehouseDay()})}}>Kembalikan ke pelanggan</button></div>}</article>)}</section>
    </div>
    <section className="demo-operation-history demo-ops-card" id="riwayat-servis"><div className="demo-operation-heading"><i><ClipboardCheck/></i><div><h3>Riwayat pemakaian dan transfer</h3></div></div>
      <label className="biz-search"><Search/><input aria-label="Cari mutasi servis" placeholder="Cari barang, pekerjaan, atau jumlah pcs…" value={query} onChange={event=>setQuery(event.target.value)}/></label>
      {!docs.length&&<p>Belum ada mutasi yang cocok.</p>}
      {docs.map(doc=><article key={doc.id}><strong>{qtyText(doc.lines.reduce((sum,row)=>sum+row.qty,0))} · {serviceActions[doc.action]}</strong>
        <small>{doc.day} · {doc.location} · {doc.id}</small>
        {doc.lines.map((line,index)=><span key={index}>{qtyText(line.qty)} · {line.name}{line.job?' · '+line.job:''}</span>)}
        <small>{doc.reason}{doc.action==='USE'?' · Biaya servis '+amountText(doc.lines.reduce((sum,line)=>sum+line.rate*line.qty,0)):''}</small>
        <StockSourceReversal label="Balikkan mutasi servis" document={doc.id} reversal={doc.reversal} blockers={serviceReversalBlockers(session,doc)}
          onReverse={reason=>{changeSession(current=>reverseService(current,doc.id,reason));setFeedback('Dokumen '+doc.id+' dibalik.')}}/>
      </article>)}
    </section>
    {draft&&<ReasonDialog title="Catat mutasi servis" closeLabel="Kembali" className="demo-operation-dialog" onClose={()=>setDraft(null)}>
      <form className="demo-operation-form" onSubmit={event=>{event.preventDefault();save(()=>changeSession(live=>postService(live,{...draft,lines:draft.lines.map(row=>({code:row.code,qty:Number(row.qty),job:row.job}))})), 'Mutasi servis tersimpan. Saldo lokasi diperbarui.')}}>
        <div className="demo-operation-fields"><label>Jenis mutasi<select value={draft.action} onChange={event=>revise({action:event.target.value as ServiceAction})}>{Object.entries(serviceActions).map(([value,label])=><option key={value} value={value}>{label}</option>)}</select></label>
          <label>Tanggal fisik<input type="date" required max={lastWarehouseDay()} value={draft.day} onChange={event=>revise({day:event.target.value})}/></label></div>
        {draft.action==='USE'?<label>Lokasi asal<select value={source} onChange={event=>revise({location:event.target.value as AccessoryLocation})}>{[mainAccessories,serviceAccessories].map(location=><option key={location}>{location}</option>)}</select></label>
          :<p><strong>{source}</strong> → {draft.action==='TO_SERVICE'?serviceAccessories:mainAccessories}</p>}
        {draft.lines.map((row,index)=>{
          const fields=(values:Partial<typeof row>)=>revise({lines:draft.lines.map(line=>line.id===row.id?{...line,...values}:line)})
          return <section className="demo-ops-card" key={row.id}><div className="demo-operation-fields">
            <label>Aksesori {index+1}<select aria-label={'Aksesori '+(index+1)} required value={row.code} onChange={event=>fields({code:event.target.value})}><option value="">Pilih aksesori</option>{items.map(item=><option key={item.code} value={item.code}>{item.name} · {qtyText(accessoryStockAt(item,source,session))}</option>)}</select></label>
            <label>Jumlah {index+1} (pcs)<NumberEntry className="demo-qty" required inputMode="numeric" value={row.qty} onValueChange={rawInput =>fields({qty:digits(rawInput)})}/></label>
          </div>{draft.action==='USE'&&<label>Pekerjaan atau tujuan {index+1}<input required maxLength={130} value={row.job} placeholder="Contoh RET-0045 · pasang kancing" onChange={event=>fields({job:event.target.value})}/></label>}
          {draft.lines.length>1&&<div><button type="button" className="soft-btn" onClick={()=>revise({lines:draft.lines.filter(item=>item.id!==row.id)})}><X size={15}/> Lepas baris</button></div>}</section>
        })}
        <div><button type="button" className="soft-btn" onClick={()=>revise({lines:[...draft.lines,emptyLine()]})}><Plus size={16}/> Tambah barang</button></div>
        <label>Catatan mutasi<textarea required minLength={4} maxLength={450} value={draft.reason} onChange={event=>revise({reason:event.target.value})}/></label>
        {error&&<p role="alert">{error}</p>}<footer><button className="primary-btn">Simpan mutasi</button></footer>
      </form>
    </ReasonDialog>}
    {custody&&<ReasonDialog title="Terima titipan pelanggan" closeLabel="Kembali" className="demo-operation-dialog" onClose={()=>setCustody(null)}>
      <form className="demo-operation-form" onSubmit={event=>{event.preventDefault();save(()=>changeSession(live=>postCustody(live,{...custody,qty:Number(custody.qty)})),'Titipan pelanggan tersimpan.')}}>
        <div className="demo-operation-fields"><label>Pemilik<input required maxLength={130} value={custody.customer} onChange={event=>setCustody({...custody,customer:event.target.value})}/></label>
          <label>Barang<input required maxLength={150} value={custody.item} onChange={event=>setCustody({...custody,item:event.target.value})}/></label>
          <label>Jumlah titipan (pcs)<NumberEntry required inputMode="numeric" value={custody.qty} onValueChange={rawInput =>setCustody({...custody,qty:digits(rawInput)})}/></label>
          <label>Tanggal terima<input type="date" required max={lastWarehouseDay()} value={custody.day} onChange={event=>setCustody({...custody,day:event.target.value})}/></label></div>
        <label>Referensi pekerjaan<input required maxLength={130} value={custody.job} onChange={event=>setCustody({...custody,job:event.target.value})}/></label>
        {error&&<p role="alert">{error}</p>}<footer><button className="primary-btn">Simpan titipan</button></footer>
      </form></ReasonDialog>}
    {release&&<ReasonDialog title="Kembalikan titipan pelanggan" closeLabel="Kembali" className="demo-operation-dialog" onClose={()=>setRelease(null)}>
      <form className="demo-operation-form" onSubmit={event=>{event.preventDefault();save(()=>changeSession(live=>closeCustody(live,release.id,release.day)), 'Titipan sudah dikembalikan.')}}>
        <label>Tanggal kembali<input type="date" required max={lastWarehouseDay()} value={release.day} onChange={event=>setRelease({...release,day:event.target.value})}/></label>
        {error&&<p role="alert">{error}</p>}<footer><button className="primary-btn">Simpan pengembalian</button></footer>
      </form></ReasonDialog>}
  </section>
}

type SalvageDraft={id:string;code:string;holder:string;reference:string;conversion:string;day:string;qty:string;expected:string}
type Inspection={doc:SalvageDocument;id:string;day:string;mode:'check'|'receive';qty:string;good:string;damaged:string;note:string}

export function AccessorySalvage() {
  const session=usePlannerSession()
  const master=useAccessoryBook().items.filter(item=>item.active&&item.stockUom==='pcs')
  const [intake,setIntake]=useState<SalvageDraft|null>(null)
  const [action,setAction]=useState<Inspection|null>(null)
  const linkedDoc=new URLSearchParams(location.search).get('dokumen')
  const [query,setQuery]=useState(linkedDoc??'')
  const [notice,setNotice]=useState('')
  const [error,setError]=useState('')
  const links=intake?salvageLinks(session,intake.code):[]
  const docs=(session.accessorySalvage??[]).map(doc=>({doc,...salvageProgress(doc)})).slice().reverse()
  const visible=docs.filter(({doc,received,good,damaged,pending,held})=>browseMatchPieces(query,[received,good,damaged,pending,held],doc.id,doc.holder,doc.name,doc.reference))
  function save(operation:()=>void,message:string) {
    try{operation();setNotice(message);setIntake(null);setAction(null);setError('')}
    catch(err){setError((err as Error).message)}
  }
  const start=(doc:SalvageDocument,mode:Inspection['mode'])=>{setError('');setAction({doc,id:newId('CEK'),day:lastWarehouseDay(),mode,qty:'',good:'',damaged:'',note:''})}
  return <section className="panel demo-ops-panel" aria-label="Penerimaan bongkaran">
    <header className="demo-ops-header"><div className="demo-operation-heading"><i><PackageOpen/></i><div><h2>Bongkaran aksesori</h2>
      <p>Terima kapan barangnya tiba. Hasil inspeksi menentukan jumlah yang masuk stok.</p></div></div>
      <button className="primary-btn" onClick={()=>{setError('');setIntake({id:newId('BKR'),code:'',holder:'',reference:'',conversion:'',day:lastWarehouseDay(),qty:'',expected:''})}}><Plus size={17}/> Terima bongkaran</button></header>
    <div className="demo-operation-facts"><article><span>Menunggu pemeriksaan</span><strong>{qtyText(docs.reduce((sum,row)=>sum+row.pending,0))}</strong></article>
      <article><span>Layak masuk stok</span><strong>{qtyText(docs.reduce((sum,row)=>sum+row.good,0))}</strong></article>
      <article><span>Rusak</span><strong>{qtyText(docs.reduce((sum,row)=>sum+row.damaged,0))}</strong></article>
      <article><span>Masih di pemegang</span><strong>{qtyText(docs.reduce((sum,row)=>sum+row.held,0))}</strong></article></div>
    <label className="biz-search"><Search/><input aria-label="Cari bongkaran" placeholder="Cari barang, pemegang, atau jumlah pcs…" value={query} onChange={event=>setQuery(event.target.value)}/></label>
    {notice&&<p role="status" className="biz-inline-notice">{notice}</p>}
    {!visible.length&&<div className="biz-empty"><ScanLine/><strong>Belum ada penerimaan yang cocok</strong></div>}
    <div className="demo-operation-history" id="riwayat-bongkaran">
      {visible.map(({doc,received,good,damaged,pending,held})=><article key={doc.id}>
        <div className="demo-ops-header"><div><strong>{qtyText(received)} · {doc.name}</strong><small>{doc.id} · {doc.day} · Dari {doc.holder}</small></div>
          <b className="biz-pill">{pending?'Menunggu Pemeriksaan':held?'Kembali sebagian':'Pemeriksaan selesai'}</b></div>
        <small>{qtyText(good)} layak · {qtyText(damaged)} rusak · {qtyText(pending)} menunggu · {qtyText(held)} ditahan</small>
        {(doc.conversion||doc.reference)&&<small>Sumber {doc.reference||'Ganti Merek '+doc.conversion?.slice(0,8)}</small>}
        <details open={linkedDoc===doc.id||undefined}><summary>Jejak penerimaan dan pemeriksaan</summary>{doc.receipts.map(row=><p key={row.id}>{row.day} · {qtyText(row.qty)} diterima</p>)}
          {doc.inspections.map(row=><div key={row.id}><p>{row.day} · {qtyText(row.good)} layak · {qtyText(row.damaged)} rusak · {row.note}</p>
            <StockSourceReversal label="Balikkan pemeriksaan" document={doc.id+' · '+row.id} reversal={row.reversal} blockers={salvageInspectionBlockers(session,doc,row)}
              onReverse={reason=>{changeSession(current=>reverseSalvageInspection(current,doc.id,row.id,reason));setNotice('Pemeriksaan '+row.id+' dibalik.')}}/>
          </div>)}</details>
        <div className="demo-operation-actions">{pending>0&&<button className="primary-btn" onClick={()=>start(doc,'check')}><ClipboardCheck size={16}/> Periksa barang</button>}
          {held>0&&<button className="soft-btn" onClick={()=>start(doc,'receive')}>Terima susulan</button>}</div>
      </article>)}
    </div>
    {intake&&<ReasonDialog title="Terima bongkaran aksesori" closeLabel="Kembali" onClose={()=>setIntake(null)} className="demo-operation-dialog">
      <form className="demo-operation-form" onSubmit={event=>{event.preventDefault();save(()=>changeSession(live=>openSalvage(live,{
        ...intake,qty:Number(intake.qty),expected:Number(intake.expected||intake.qty),conversion:intake.conversion||undefined,reference:intake.reference.trim()||undefined,holder:intake.holder.trim(),
      })),'Penerimaan tersimpan di Menunggu Pemeriksaan.')}}>
        <label>Aksesori<select aria-label="Aksesori" required value={intake.code} onChange={event=>setIntake({...intake,code:event.target.value,conversion:'',expected:''})}>
          <option value="">Pilih aksesori</option>{master.map(item=><option key={item.code} value={item.code}>{item.name}</option>)}</select></label>
        {links.length>0&&<label>Tautkan ke Ganti Merek (opsional)<select value={intake.conversion} onChange={event=>{
          const link=links.find(row=>row.id===event.target.value)
          setIntake({...intake,conversion:link?.id??'',holder:link?.holder||intake.holder,expected:link?.left==null?'':String(link.left)})
        }}><option value="">Penerimaan mandiri</option>{links.map(link=><option key={link.id} value={link.id}>{link.label}{link.left===null?'':' · '+qtyText(link.left)} · {link.day}</option>)}</select></label>}
        <div className="demo-operation-fields"><label>Jumlah fisik diterima (pcs)<NumberEntry required inputMode="numeric" value={intake.qty} onValueChange={rawInput =>setIntake({...intake,qty:digits(rawInput)})}/></label>
          <label>Total diharapkan (opsional)<NumberEntry inputMode="numeric" placeholder="Sama dengan jumlah diterima" value={intake.expected} onValueChange={rawInput =>setIntake({...intake,expected:digits(rawInput)})}/></label></div>
        <div className="demo-operation-fields"><label>Diterima dari<input required maxLength={130} value={intake.holder} onChange={event=>setIntake({...intake,holder:event.target.value})}/></label>
          <label>Tanggal fisik<input required type="date" max={lastWarehouseDay()} value={intake.day} onChange={event=>setIntake({...intake,day:event.target.value})}/></label></div>
        <label>Referensi asal atau servis (opsional)<input maxLength={140} value={intake.reference} onChange={event=>setIntake({...intake,reference:event.target.value})}/></label>
        {error&&<p role="alert">{error}</p>}<footer><button className="primary-btn">Simpan penerimaan</button></footer>
      </form></ReasonDialog>}
    {action&&<ReasonDialog title={action.mode==='check'?'Periksa aksesori bongkaran':'Terima bongkaran susulan'} closeLabel="Kembali" onClose={()=>setAction(null)} className="demo-operation-dialog">
      <form className="demo-operation-form" onSubmit={event=>{
        event.preventDefault()
        const {id,day,qty,good,damaged,note}=action
        save(()=>changeSession(live=>action.mode==='check'?inspectSalvage(live,action.doc.id,{id,day,good:Number(good),damaged:Number(damaged),note:note.trim()}):receiveSalvage(live,action.doc.id,{id,day,qty:Number(qty)})),
          action.mode==='check'?'Pemeriksaan tersimpan. Jumlah layak masuk stok.':'Penerimaan susulan tersimpan.')
      }}><p>{action.doc.name} · {action.doc.id}</p>
        {action.mode==='check'?<><div className="demo-operation-fields"><label>Layak pakai (pcs)<NumberEntry inputMode="numeric" value={action.good} onValueChange={rawInput =>setAction({...action,good:digits(rawInput)})}/></label>
          <label>Rusak (pcs)<NumberEntry inputMode="numeric" value={action.damaged} onValueChange={rawInput =>setAction({...action,damaged:digits(rawInput)})}/></label></div>
          <label>Hasil pemeriksaan<textarea required minLength={4} maxLength={400} value={action.note} onChange={event=>setAction({...action,note:event.target.value})}/></label></>
          :<label>Jumlah fisik susulan (pcs)<NumberEntry required inputMode="numeric" value={action.qty} onValueChange={rawInput =>setAction({...action,qty:digits(rawInput)})}/></label>}
        <label>Tanggal fisik<input required type="date" min={action.doc.day} max={lastWarehouseDay()} value={action.day} onChange={event=>setAction({...action,day:event.target.value})}/></label>
        {error&&<p role="alert">{error}</p>}<footer><button className="primary-btn">{action.mode==='check'?'Simpan hasil pemeriksaan':'Simpan susulan'}</button></footer>
      </form></ReasonDialog>}
  </section>
}
