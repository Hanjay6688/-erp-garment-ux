import NumberEntry from '../../src/components/NumberEntry'
import { sizeRangeLabel } from './sizeRangeLabel'
import {useEffect,useRef,useState} from 'react'
import {parseFgWorkspace,type FgRow} from './fgContract'
import {parseSkuMaster,type SkuGroup} from './skuMaster'
import {getUatSupabaseClient} from './lib/supabase'
type Client=ReturnType<typeof getUatSupabaseClient>
export type CountedLot={row:FgRow;qty:string}
export default function FgRangeEntry({client,finance,disabled,add}:{client:Client;finance:boolean;disabled:boolean;add:(items:CountedLot[])=>void}) {
 const [query,setQuery]=useState(''),[groups,setGroups]=useState<SkuGroup[]>([]),[page,setPage]=useState(1),[pages,setPages]=useState(1)
 const [group,setGroup]=useState<SkuGroup|null>(null),[stock,setStock]=useState<FgRow[]>([]),[scope,setScope]=useState('')
 const [amounts,setAmounts]=useState<Record<string,string>>({}),[lots,setLots]=useState<Record<string,string>>({})
 const [message,setMessage]=useState(''),[busy,setBusy]=useState(false)
 const seq=useRef(0)
 useEffect(()=>()=>{++seq.current},[])
 async function search(q:string,p:number) {
   const token=++seq.current;setBusy(true);setGroups([]);setGroup(null);setStock([]);setMessage('')
   try{
     const r=await client.rpc('erp_get_sku_workspace_v1',{p_filters:{query:q.trim(),page:p}})
     if(r.error)throw Error('Master SKU belum bisa dibaca.')
     const w=parseSkuMaster(r.data)
     if(w.page!==p)throw Error('Halaman master SKU berbeda. Cari kembali.')
     if(token===seq.current){setGroups(w.groups);setPage(w.page);setPages(Math.max(1,Math.ceil(w.groups_total/w.page_size)))}
   }catch(e){if(token===seq.current)setMessage((e as Error).message)}finally{if(token===seq.current)setBusy(false)}
 }
 async function choose(g:SkuGroup|undefined) {
   const token=++seq.current
   setGroup(g??null);setStock([]);setScope('');setAmounts({});setLots({});setMessage('');setBusy(Boolean(g))
   if(!g)return
   try {
     const rows:FgRow[]=[]
     let offset:number|null=0
     while(offset!==null) {
       const cursor:number=offset
       const r=await client.rpc('erp_cp7_get_fg_v1',{p_query:{purpose:'SUMMARY',q:g.sku,show_zero:true,offset:cursor,limit:25}})
       if(token!==seq.current)return
       if(r.error)throw Error('Stok per lot belum bisa dibaca.')
       const w=parseFgWorkspace(r.data,finance,'SUMMARY')
       if(w.page.offset!==cursor||(w.page.next_offset!==null&&w.page.next_offset<=cursor))throw Error('Halaman stok berubah. Cari SKU kembali.')
       rows.push(...w.page.rows.filter(row=>row.brand_name===g.brand_name&&row.commercial_sku===g.sku&&g.members.some(m=>m.size===row.size_code)))
       offset=w.page.next_offset
     }
     const available=rows.filter(r=>r.quality==='KNOWN'&&r.lot_id)
     setStock(available)
     const choices=[...new Set(available.map(r=>r.location_id+'|'+r.quality_grade))]
     if(choices.length===1)setScope(choices[0])
   }catch(e){if(seq.current===token)setMessage((e as Error).message)}finally{if(seq.current===token)setBusy(false)}
 }
 const choices=[...new Map(stock.map(r=>[r.location_id+'|'+r.quality_grade,r])).entries()]
 const positions=(size:string)=>stock.filter(r=>r.size_code===size&&r.location_id+'|'+r.quality_grade===scope)
 const line=(size:string)=>{const choices=positions(size);return choices.length===1?choices[0]:choices.find(r=>r.lot_id===lots[size])}
 function apply() {
   try{
     const items:CountedLot[]=[]
     for(const m of group?.members??[]){
       const raw=amounts[m.id]?.trim()
       if(!raw)continue
       const row=line(m.size)
       if(!row||!/^\d{1,9}$/.test(raw))throw Error('Pilih lot dan isi hasil hitung bulat untuk ukuran '+m.size+'.')
       const delta=Number(raw)-Number(row.physical_qty)
       if(delta)items.push({row,qty:String(delta)})
     }
     if(!items.length)throw Error('Belum ada selisih untuk dicatat.')
     add(items);setAmounts({});setMessage('Selisih masuk ke draft per ukuran dan lot.')
   }catch(e){setMessage((e as Error).message)}
 }
 return <section className="panel"><h2>Hitung satu seri SKU</h2>
   <form onSubmit={e=>{e.preventDefault();void search(query,1)}}><label>Cari merek atau SKU<input value={query} onChange={e=>setQuery(e.target.value)}/></label><button disabled={disabled||busy}>Cari seri master</button></form>
   <label>SKU dan warna<select aria-label="Seri SKU penyesuaian" value={group?.id??''} onChange={e=>void choose(groups.find(g=>g.id===e.target.value))}><option value="">Pilih SKU</option>{groups.map(g=><option value={g.id} key={g.id}>{g.brand_name} {g.sku} · {g.color_name} · {sizeRangeLabel(g.members.map(m => m.size))}</option>)}</select></label>
   {pages>1&&<div><button disabled={busy||page<=1} onClick={()=>void search(query,page-1)}>Sebelumnya</button> {page}/{pages} <button disabled={busy||page>=pages} onClick={()=>void search(query,page+1)}>Berikutnya</button></div>}
   {group&&<><label>Gudang dan grade<select aria-label="Gudang dan grade seri" value={scope} onChange={e=>{setScope(e.target.value);setAmounts({});setLots({})}}><option value="">Pilih gudang dan grade</option>{choices.map(([key,r])=><option key={key} value={key}>{r.location_name} · {r.quality_grade}</option>)}</select></label><div className="cproc-grid">{group.members.map(m=><div key={m.id}><strong>Ukuran {m.size}</strong>{positions(m.size).length>1&&<label>Lot<select aria-label={'Lot ukuran '+m.size} value={lots[m.size]??''} onChange={e=>{setLots({...lots,[m.size]:e.target.value});setAmounts({...amounts,[m.id]:''})}}><option value="">Pilih lot yang dihitung</option>{positions(m.size).map(r=><option key={r.lot_id} value={r.lot_id!}>{r.lot_number}</option>)}</select></label>}
    <label>Fisik · {line(m.size)?.lot_number??'lot belum tersedia'}<NumberEntry aria-label={'Hitung fisik ukuran '+m.size} disabled={disabled||busy||!line(m.size)} inputMode="numeric" placeholder="Lewati" value={amounts[m.id]??''} onValueChange={rawInput =>setAmounts({...amounts,[m.id]:rawInput})}/></label></div>)}</div><button disabled={disabled||busy} onClick={apply}>Masukkan selisih ke draft</button></>}
   {busy&&<p role="status">Memuat master dan stok…</p>}{message&&<p role="status">{message}</p>}
 </section>
}
