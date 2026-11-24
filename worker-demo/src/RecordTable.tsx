import {Children,Fragment,cloneElement,isValidElement,useId,useState,type ReactElement,type ReactNode,type TableHTMLAttributes} from 'react'
import './form-clarity.css'

type Part=ReactElement<{children?:ReactNode;colSpan?:number;dateTime?:string;value?:string|number;title?:string;'aria-label'?:string}>
const children=(v:ReactNode):ReactNode[]=>Children.toArray(v).flatMap(c=>isValidElement(c)&&c.type===Fragment?children((c as Part).props.children):[c])
const element=(c:ReactNode,t:string):c is Part=>isValidElement(c)&&c.type===t
const collator=new Intl.Collator('id',{numeric:true,sensitivity:'base'})
function words(node:ReactNode):string {
  if(node==null||typeof node==='boolean')return ''
  if(typeof node==='number'||typeof node==='string')return String(node)
  if(Array.isArray(node))return node.map(words).filter(Boolean).join(' ')
  if(!isValidElement(node))return ''
  const p=(node as Part).props
  return p.dateTime||words(p.children)||String(p.value??p['aria-label']??p.title??'')
}
const months=['jan','feb','mar','apr','mei','jun','jul','agu','sep','okt','nov','des']
export function recordDate(value:string):string|null {
  const text=value.trim().toLowerCase(),iso=text.match(/\b(\d{4})-(\d{2})-(\d{2})\b/),local=text.match(/\b(\d{1,2})[ ./-]([a-z]+|\d{1,2})[ ./-](\d{4})\b/)
  if(!iso&&!local)return null
  const year=Number(iso?.[1]??local?.[3]),day=Number(iso?.[3]??local?.[1]);const m=local?.[2]??''
  const month=iso?Number(iso[2]):/^\d+$/.test(m)?Number(m):months.indexOf(m.slice(0,3))+1
  const date=new Date(Date.UTC(year,month-1,day));return date.getUTCFullYear()===year&&date.getUTCMonth()===month-1&&date.getUTCDate()===day?date.toISOString().slice(0,10):null
}
function numberValue(s:string){const v=s.trim().replace(/^Rp\.?\s*/i,'').replace(/\s+(?:pcs|yd|lusin|roll|kg)$/i,'');return /^-?\d{1,3}(?:\.\d{3})+(?:,\d+)?$|^-?\d+(?:,\d+)?$/.test(v)?Number(v.replace(/\./g,'').replace(',','.')):null}
export default function RecordTable({children:content,...props}:TableHTMLAttributes<HTMLTableElement>) {
  const [sort,setSort]=useState(''),[desc,setDesc]=useState(false),[dateKey,setDateKey]=useState(''),[from,setFrom]=useState(''),[until,setUntil]=useState(''),id=useId()
  const parts=children(content),head=parts.find(p=>element(p,'thead')) as Part|undefined,body=parts.find(p=>element(p,'tbody')) as Part|undefined
  const header=head&&children(head.props.children).find(p=>element(p,'tr')) as Part|undefined
  const labels=header?children(header.props.children).map(c=>words(c).trim()):[]
  const standard=<table {...props}>{content}</table>
  if(!body||!labels.length||parts.filter(p=>element(p,'tbody')).length!==1)return standard
  const all=children(body.props.children);if(!all.every(r=>element(r,'tr')))return standard
  const data=(all as Part[]).map(row=>({row,cells:children(row.props.children).map(c=>words(c).trim())}))
  // Preserve summaries, manually ordered movements and grouped rows in their native order.
  if(!data.length||data.some(r=>r.cells.length!==labels.length||children(r.row.props.children).some(c=>isValidElement(c)&&(c as Part).props.colSpan)))return standard
  const sortOptions=labels.map((label,i)=>({label,i})).filter(c=>c.label&&!/^(aksi|tindakan|pilih|buka|opsi|pengaturan|detail)$/i.test(c.label))
  if(!sortOptions.length)return standard
  const dates=sortOptions.filter(c=>/tanggal|waktu|tenggat|jatuh tempo|berlaku|dibuat|diperbarui|periode/i.test(c.label)&&data.some(r=>recordDate(r.cells[c.i])))
  const dateIndex=dates.find(c=>String(c.i)===dateKey)?.i??dates[0]?.i
  const invalid=!!(from&&until&&from>until),filtered=dateIndex!==undefined&&(from||until)?data.filter(r=>{const date=recordDate(r.cells[dateIndex]);return !!date&&!invalid&&(!from||date>=from)&&(!until||date<=until)}):[...data]
  const col=sortOptions.find(c=>String(c.i)===sort)?.i
  if(col!==undefined)filtered.sort((a,b)=>{const left=a.cells[col],right=b.cells[col],x=recordDate(left),y=recordDate(right),n=numberValue(left),m=numberValue(right);return(desc?-1:1)*(x&&y?x.localeCompare(y):n!==null&&m!==null?n-m:collator.compare(left,right))})
  if(data.length<2&&!dates.length)return standard
  return <><details className="erp-table-tools"><summary>Filter dan urutkan <small>· halaman ini</small></summary><div>
    {dates.length>0&&<>{dates.length>1&&<label>Kolom tanggal<select value={String(dateIndex)} onChange={e=>setDateKey(e.target.value)}>{dates.map(x=><option key={x.i} value={x.i}>{x.label}</option>)}</select></label>}
    <label>{labels[dateIndex!]} mulai<input type="date" value={from} max={until||undefined} onChange={e=>setFrom(e.target.value)}/></label><label>Sampai<input type="date" value={until} min={from||undefined} onChange={e=>setUntil(e.target.value)}/></label></>}
    <label>Urutkan kolom<select value={sort} onChange={e=>setSort(e.target.value)}><option value="">Urutan asli</option>{sortOptions.map(x=><option key={x.i} value={x.i}>{x.label}</option>)}</select></label>
    {sort&&<label>Arah urutan<select value={desc?'desc':'asc'} onChange={e=>setDesc(e.target.value==='desc')}><option value="asc">Menaik</option><option value="desc">Menurun</option></select></label>}
    <button type="button" disabled={!from&&!until&&!sort&&!dateKey} onClick={()=>{setFrom('');setUntil('');setSort('');setDateKey('');setDesc(false)}}>Reset</button></div></details>
    {(from||until||sort)&&<small className="erp-table-count" role="status" id={id}>{invalid?'Tanggal akhir harus sesudah atau sama dengan tanggal mulai.':`${filtered.length} dari ${data.length} baris halaman ini`}</small>}
    <table {...props}>{parts.map(p=>p===body?cloneElement(body,{},filtered.length?filtered.map(r=>r.row):<tr><td colSpan={labels.length}>Tidak ada baris dalam periode ini.</td></tr>):p)}</table></>
}
