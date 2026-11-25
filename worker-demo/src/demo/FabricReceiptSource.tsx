import {useState} from 'react'
import {ArrowLeft, ArrowRight, CalendarDays, ClipboardList, Factory, FileText, History, Layers3, Pencil, Plus, Ruler, Search} from 'lucide-react'
import {archiveDocuments, archiveIdentity, archiveSource, fabricIdentity, receiptMaterial, type FabricArchiveDocument} from './fabricArchive'
import {correctFabricIdentity, correctFabricReceiptRoll, fabricReceiptBlockers, fabricRollUses, reverseWarehouseReceipt} from './fabricReceipts'
import {browseMatch} from '../browseMatch'
import {materialHistoryPath, rollLength} from './materialRollHistory'
import {money} from './format'
import {cutDocumentPath, receiptDocumentPath, receiptRolls, type ReceiptRoll} from './receiptRollCorrection'
import {ReceiptRollEditor} from './ReceiptRollEditor'
import {StockSourceReversal} from './StockSourceReversal'
import {ReasonDialog} from './planner/ReasonDialog'
import {changeSession} from './planner/session'
import {yardsLeft, type FabricReceipt, type Session} from './planner/model'

const receiptPath='/gudang/pembelian-penerimaan/?jenis=kain'
const dateFormat=new Intl.DateTimeFormat('id-ID',{day:'numeric',month:'short',year:'numeric',timeZone:'Asia/Jakarta'})
const showDate=(day:string)=>dateFormat.format(new Date(day))

export function FabricReceiptRegister({session}:{session:Session}) {
  const [query,setQuery]=useState('')
  const [limit,setLimit]=useState(4)
  const documents=[
    ...(session.fabricReceipts??[]).map(doc=>({
      material:receiptMaterial(session,doc),supplier:doc.supplier,day:doc.day,ref:doc.number,unit:doc.unit,rolls:receiptRolls(doc),
      state:doc.reversal?'Dibalik':'Diterima',href:receiptDocumentPath(doc.number),
    })),
    ...archiveDocuments.filter(doc=>doc.kind==='surat').map(doc=>({
      material:fabricIdentity(session,doc.key,doc.material),supplier:doc.supplier,day:doc.day,ref:doc.reference,unit:'yd' as const,
      rolls:doc.lines.map(row=>({...row,physicalCode:archiveIdentity(session,row.id).physicalCode})),state:'Arsip',href:archiveSource(doc.lines[0].id).href,
    })),
  ].sort((a,b)=>b.day.localeCompare(a.day))
  const found=documents.filter(doc=>browseMatch(query,doc.ref,doc.material,doc.supplier,doc.day,doc.rolls.length,
    rollLength(doc.rolls.reduce((n,r)=>n+r.length,0),doc.unit),...doc.rolls.flatMap(r=>[r.id,r.physicalCode])))
  return <section className="panel receiving-register" id="riwayat-surat-jalan" aria-label="Penerimaan kain tersimpan">
    <header className="receiving-band"><i><ClipboardList/></i><h2>Riwayat penerimaan kain</h2></header>
    <label className="receiving-search"><Search size={16}/><input type="search" aria-label="Cari surat jalan kain" placeholder="Cari surat jalan, bahan, atau roll" value={query} onChange={e=>{setQuery(e.target.value);setLimit(4)}}/></label>
    <ul>{found.slice(0,limit).map(doc=><li key={doc.href}><a href={doc.href}>
      <span><strong>{doc.rolls.length} roll · {rollLength(doc.rolls.reduce((n,r)=>n+r.length,0),doc.unit)}</strong>
        <b>{doc.material} · {doc.supplier}</b><small>{doc.ref} · {showDate(doc.day)} · {doc.state}</small></span><ArrowRight size={17}/></a></li>)}</ul>
    {!found.length&&<p>Tidak ada surat jalan yang cocok.</p>}
    {found.length>limit&&<button type="button" className="soft-btn" onClick={()=>setLimit(limit+8)}>Lihat {Math.min(8,found.length-limit)} penerimaan lagi</button>}
  </section>
}

type IdentityEdit={roll?:string;before:string}
export function FabricReceiptSource({session,receipt,archive,focusRoll}:{session:Session;receipt?:FabricReceipt;archive?:FabricArchiveDocument;focusRoll?:string}) {
  const [edit,setEdit]=useState<IdentityEdit|null>(null)
  const [rollEditor,setRollEditor]=useState<ReceiptRoll|null>(null)
  const [notice,setNotice]=useState('')
  const [rollQuery,setRollQuery]=useState((receipt?.rolls.length??0)>20?focusRoll??'':'')
  const [rollLimit,setRollLimit]=useState(20)
  if(!receipt&&!archive)return <section className="panel receipt-source missing-source"><FileText/><h1>Dokumen penerimaan tidak ditemukan</h1><p>Periksa surat jalan di riwayat penerimaan sesi demo ini.</p><a className="soft-btn" href={receiptPath}>Buka riwayat penerimaan <ArrowRight size={16}/></a></section>
  const key=archive?.key??'penerimaan:'+receipt!.id
  const material=fabricIdentity(session,key,(archive??receipt!).material)
  const reference=archive?.reference??receipt!.number
  const day=(archive??receipt!).day
  const unit=receipt?.unit??'yd'
  const correctedLines:ReceiptRoll[]=receipt?receiptRolls(receipt):archive!.lines.map(row=>({...row,physicalCode:archiveIdentity(session,row.id).physicalCode}))
  const foundLines=correctedLines.filter(row=>browseMatch(rollQuery,row.id,row.physicalCode,rollLength(row.length,unit)))
  const title=archive?.kind==='saldo'?'Saldo awal roll':archive?.kind==='retur'?'Retur masuk dari mandor':'Penerimaan kain'
  const identities=(session.fabricIdentities??[]).filter(event=>event.source===key)
  return <section className="receipt-source" aria-label="Penerimaan kain tersimpan" id="dokumen-penerimaan">
    <nav className="receipt-source-nav"><a className="soft-btn" href={materialHistoryPath(material)}><ArrowLeft size={16}/> Riwayat roll · {material}</a>
      <a className="soft-btn" href={receiptPath}><Plus size={16}/> Penerimaan baru</a></nav>
    <div className="panel receipt-source-sheet">
      <header className="receipt-source-header"><i><FileText/></i><div><small>{title}</small><h1>{reference}</h1></div>
        <span className={'wh-status '+(receipt?.reversal?'warn':archive?'neutral':'good')}>{receipt?.reversal?'Dibalik':archive?'Arsip':'Diterima'}</span></header>
      <div className="receipt-source-facts">
        <div className="receipt-source-material"><Layers3/><span><small>Nama bahan</small><strong>{material}</strong></span>
          {!receipt?.reversal&&<button className="soft-btn" type="button" onClick={()=>setEdit({before:material})}><Pencil size={15}/> Koreksi nama bahan</button>}</div>
        <div><Factory/><span><small>Supplier / pabrik</small><strong>{(archive??receipt!).supplier}</strong></span></div>
        <div><CalendarDays/><span><small>Tanggal masuk</small><strong>{showDate(day)}</strong></span></div>
      </div>
      {notice&&<p role="status" className="wh-feedback">{notice}</p>}
      <section className="receipt-source-lines">
        <header className="receiving-band"><i><Ruler/></i><div><h2>{archive?'Roll yang tercatat di arsip':'Roll pada surat jalan'}</h2>
          <p>{correctedLines.length} roll · {rollLength(correctedLines.reduce((n,r)=>n+r.length,0),unit)}{receipt?' · '+money(receipt.rate)+' / '+unit+' acuan':''}</p></div></header>
        {correctedLines.length>20&&<label className="receiving-search"><Search size={16}/><input type="search" aria-label="Cari roll dalam penerimaan" value={rollQuery} placeholder="Cari nomor roll atau panjang" onChange={e=>{setRollQuery(e.target.value);setRollLimit(20)}}/></label>}
        <ul>{foundLines.slice(0,rollLimit).map(row=>{
          const label=row.physicalCode??row.id
          const uses=archive?fabricRollUses(session,row.id):[]
          return <li key={row.id} aria-current={focusRoll===row.id?true:undefined} className={focusRoll===row.id?'receipt-source-selected':''}>
            <div><strong>{rollLength(row.length,unit)} diterima</strong><span>{label}{focusRoll===row.id&&correctedLines.length>1&&<small className="receipt-chosen-roll">Roll terpilih</small>}</span>
              {row.physicalCode&&<small>Kode ERP {row.id}</small>}
              {receipt&&!receipt.reversal&&<small>{rollLength(unit==='yd'?yardsLeft(row.id,session):row.length,unit)} tersisa</small>}
              {!!uses.length&&uses.map(({lot})=><a key={lot.id} className="source-row-link" href={cutDocumentPath(lot.id)}>Potongan {lot.id}</a>)}</div>
            {!receipt?.reversal&&<button className="soft-btn" type="button" aria-label={receipt?'Koreksi roll '+label:'Koreksi nomor roll '+label}
              onClick={()=>receipt?setRollEditor(row):setEdit({roll:row.id,before:label})}><Pencil size={15}/>{receipt?'Koreksi nomor / panjang':'Koreksi nomor roll'}</button>}
          </li>
        })}</ul>
        {!foundLines.length&&<p>Tidak ada roll yang cocok.</p>}
        {foundLines.length>rollLimit&&<button type="button" className="soft-btn" onClick={()=>setRollLimit(rollLimit+20)}>Lihat {Math.min(20,foundLines.length-rollLimit)} roll lagi</button>}
      </section>
      {(identities.length>0||!!receipt?.corrections?.length)&&<section className="receipt-source-audit">
        <header className="receiving-band"><i><History/></i><h2>Riwayat koreksi</h2></header><ul>
        {[...identities.map(row=>({id:row.id,at:row.at,title:row.roll?'Nomor roll':'Nama bahan',change:row.before+' → '+row.after,reason:row.reason})),
          ...(receipt?.corrections??[]).map(row=>({id:row.id,at:row.at,title:'Roll penerimaan',change:[row.beforeCode!==row.physicalCode?(row.beforeCode??row.roll)+' → '+(row.physicalCode??row.roll):'',
            row.beforeLength!==row.length?rollLength(row.beforeLength,unit)+' → '+rollLength(row.length,unit):''].filter(Boolean).join(' · '),reason:row.reason}))]
          .sort((a,b)=>b.at.localeCompare(a.at)).map(row=><li key={row.id}><strong>{row.title} · {row.change}</strong><small>{showDate(row.at)} · {row.reason}</small></li>)}</ul>
      </section>}
      {receipt&&<footer><StockSourceReversal label="Balikkan penerimaan kain" document={reference} reversal={receipt.reversal} blockers={fabricReceiptBlockers(session,receipt)}
        onReverse={reason=>{changeSession(live=>reverseWarehouseReceipt(live,'fabric',receipt.id,reason));setNotice('Penerimaan '+reference+' dibalik.')}}/></footer>}
    </div>
    {edit&&<IdentityDialog edit={edit} reference={reference} count={correctedLines.length} onClose={()=>setEdit(null)} onSave={(after,reason)=>{
      const correction={...edit,id:crypto.randomUUID(),source:key,after,reason,at:new Date().toISOString()}
      changeSession(live=>correctFabricIdentity(live,correction))
      setNotice(edit.roll?'Nomor roll diperbarui.':'Nama bahan diperbarui untuk '+correctedLines.length+' roll di dokumen ini.')
    }}/>}
    {rollEditor&&receipt&&<ReceiptRollEditor roll={rollEditor} receipt={receipt.number} unit={receipt.unit} onClose={()=>setRollEditor(null)} onSave={input=>{
      changeSession(live=>correctFabricReceiptRoll(live,receipt.id,rollEditor.id,input))
      setNotice('Koreksi roll tercatat di '+reference+'.')
    }}/>}
  </section>
}

function IdentityDialog({edit,reference,count,onSave,onClose}:{edit:IdentityEdit;reference:string;count:number;onSave:(value:string,reason:string)=>void;onClose:()=>void}) {
  const [value,setValue]=useState(edit.before)
  const [reason,setReason]=useState('')
  const [error,setError]=useState('')
  return <ReasonDialog title={edit.roll?'Koreksi nomor roll':'Koreksi nama bahan'} icon={<Pencil/>} closeLabel="Kembali" onClose={onClose} className="demo-operation-dialog money-dialog">
    <form className="demo-operation-form" onSubmit={e=>{e.preventDefault();try{onSave(value,reason);onClose()}catch(failure){setError((failure as Error).message)}}}>
      <p><strong>{reference}</strong> · {edit.roll?'Roll '+edit.before:count+' roll pada dokumen ini'}</p>
      <label>{edit.roll?'Nomor fisik yang benar':'Nama bahan yang benar'}<input required maxLength={90} value={value} onChange={e=>setValue(e.target.value)}/></label>
      <label>Alasan koreksi<textarea required minLength={4} maxLength={500} value={reason} onChange={e=>setReason(e.target.value)}/></label>
      {error&&<p role="alert">{error}</p>}
      <footer><button className="primary-btn" disabled={!value.trim()||value.trim()===edit.before||reason.trim().length<4}>Simpan koreksi</button></footer>
    </form>
  </ReasonDialog>
}
