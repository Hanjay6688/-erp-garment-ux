import { useState } from 'react'
import { ChartNoAxesColumn, ClipboardList, ReceiptText, Search } from 'lucide-react'
import { browseMatchPieces } from '../browseMatch'
import { normalizeMandor } from './accessoryPricing'
import { mandorNames, readNotes } from './issueDocuments'
import { allPayrollSources } from './payrollSources'
import { trainingBom } from './trainingBom'
import { lastWarehouseDay } from './warehouseDay'
import './demoCorrection.css'

type CompareRow={category:string;unit:string;actual:number;standard:number;hasStandard:boolean;notes:Set<string>;fg:Set<string>}

export function AccessoryStandards() {
  const [mandor,setMandor]=useState('Mandor Afui')
  const [from,setFrom]=useState('2026-08-01')
  const [to,setTo]=useState(lastWarehouseDay)
  const [query,setQuery]=useState('')
  const results=new Map<string,CompareRow>()
  const same=(name:string)=>normalizeMandor(name)===normalizeMandor(mandor)
  const inRange=(day:string)=>day>=from&&day<=to
  const get=(raw:string,unit:string)=>{
    const category=raw==='Resleting'?'Sleting':raw
    const key=category+'|'+unit
    const result=results.get(key)??{category,unit,actual:0,standard:0,hasStandard:false,notes:new Set<string>(),fg:new Set<string>()}
    results.set(key,result)
    return result
  }
  for(const doc of readNotes().filter(row=>row.status==='POSTED'&&same(row.mandor)&&inRange(row.issuedOn))){
    for(const line of doc.lines){
      const row=get(line.category,line.unit)
      row.actual+=line.qty
      row.notes.add(doc.number)
    }
  }
  let missing=0
  let good=0
  for(const source of allPayrollSources()){
    if(source.kind!=='FG'||!same(source.mandor)||!inRange(source.day))continue
    const doc=source.doc
    const cards=doc.regularCards??[{sku:doc.sku,good:doc.good,standardBom:undefined}]
    for(const card of cards){
      good+=card.good
      if(!card.good)continue
      const bom=card.standardBom??(doc.number.startsWith('NFG-SIM-')?[]:trainingBom(card.sku,true))
      if(!bom.length)missing+=card.good
      for(const line of bom){
        const row=get(line.category,line.uom)
        row.standard+=card.good*line.quantity
        row.hasStandard=true
        row.fg.add(doc.number)
      }
    }
  }
  const visible=[...results.values()].filter(row=>browseMatchPieces(query,row.unit==='pcs'?[row.actual,...(row.hasStandard?[row.standard]:[])]:[],row.category,row.unit,...row.notes,...row.fg))
  const qty=(number:number,unit:string)=>number.toLocaleString('id-ID',{maximumFractionDigits:6})+' '+unit
  return <section className="panel demo-ops-panel" aria-label="Aktual dan standar aksesori">
    <header className="demo-ops-header"><div className="demo-operation-heading"><i><ChartNoAxesColumn/></i><div><h2>Aksesori aktual vs standar</h2><p>Bandingkan jumlah pada Nota Ambil dengan BOM per kategori dari hasil FG.</p></div></div>
      <a className="soft-btn" href="/keuangan/nota-ambil-mandor/"><ReceiptText size={17}/> Kembali ke Nota Ambil</a></header>
    <div className="demo-operation-form demo-operation-fields"><label>Mandor<select value={mandor} onChange={event=>setMandor(event.target.value)}>{mandorNames.map(name=><option key={name}>{name}</option>)}</select></label>
      <label>Dari tanggal<input type="date" value={from} onChange={event=>setFrom(event.target.value)}/></label>
      <label>Sampai tanggal<input type="date" value={to} onChange={event=>setTo(event.target.value)}/></label></div>
    <div className="demo-operation-facts"><article><span>Hasil FG Good</span><strong>{qty(good,'pcs')}</strong></article>
      <article><span>FG dengan standar tersimpan</span><strong>{qty(good-missing,'pcs')}</strong></article></div>
    {missing>0&&<p className="demo-subtle">{qty(missing,'pcs')} belum punya snapshot BOM. Selisih periode tampil setelah seluruh sumber tersedia.</p>}
    <label className="biz-search"><Search/><input aria-label="Cari kategori aksesori" placeholder="Cari kategori, nota, atau jumlah pcs…" value={query} onChange={event=>setQuery(event.target.value)}/></label>
    <div className="demo-operation-history">{visible.map(row=><article key={row.category+'|'+row.unit}>
      <div className="demo-ops-header"><strong>{row.category}</strong><span>{row.hasStandard&&missing===0?'Selisih '+qty(row.actual-row.standard,row.unit):'Selisih belum tersedia'}</span></div>
      <div className="demo-operation-facts"><article><span>Diambil</span><strong>{qty(row.actual,row.unit)}</strong></article>
        <article><span>Standar dari BOM</span><strong>{row.hasStandard?qty(row.standard,row.unit):'Belum tercatat'}</strong></article></div>
      <div className="demo-operation-actions">{[...row.notes].map(note=><a key={note} className="soft-btn" href={'/keuangan/nota-ambil-mandor/?nota='+encodeURIComponent(note)}>{note}</a>)}
        {[...row.fg].map(note=><a key={note} className="soft-btn" href={'/produksi/susun-nota-fg/?nota='+encodeURIComponent(note)}>{note}</a>)}</div>
    </article>)}</div>
    {visible.length===0&&<div className="biz-empty"><ClipboardList/><strong>Belum ada data untuk filter ini</strong></div>}
  </section>
}
