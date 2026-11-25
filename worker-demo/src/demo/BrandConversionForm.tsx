import {useState} from 'react'
import {ArrowRight,ArrowLeftRight,BookOpen,Package,Search} from 'lucide-react'
import {fgQuantity} from '../fgQuantity'
import {lastWarehouseDay} from './warehouseDay'
import {amountText,fixtureDate} from './accessoryPricing'
import {rangeLabel,type Session,type ConversionKit} from './planner/model'
import {changeSession,usePlannerSession} from './planner/session'
import {ReasonDialog} from './planner/ReasonDialog'
import {convertStock,moveSnapshot,stockAt,type MoveInput} from './planner/conversion'
import {skuCatalog,allSkus,skuByKey,nativePosition,pairOf,pairSku} from './skuCatalog'
import {ConversionAccessoryFields,ConversionAccessoryHistory} from './ConversionAccessories'
import {emptyAccessories,kitCost} from './conversionAccessories'
import './warehouseForms.css'

const masterPath='/master/produk-sku/'
const draftKey='erp.owner.range-draft.convert'
const matchingSizes=(a:string,b:string)=>Object.fromEntries((skuByKey(a)?.sizes??[]).map(x=>[x,skuByKey(b)?.sizes.includes(x)?x:'']))
function initial(s:Session,source=allSkus(s,true)[0]?.key??skuCatalog[0].key):MoveInput{
  const target=pairOf(s,source)??''
  return {source,target,sizeMap:matchingSizes(source,target),location:nativePosition(skuByKey(source)!).location,grade:'Good',date:fixtureDate,values:{},reason:'',notes:''}
}
export function SkuPairField({sku}:{sku:string}){
  const s=usePlannerSession(),a=skuByKey(sku,s),current=pairOf(s,sku)??''
  const [value,setValue]=useState<string|null>(null),[msg,setMsg]=useState('')
  if(!a)return null
  const selected=value??current,other=pairOf(s,selected)
  return <section className="wh-pair sku-pair-panel" id="padanan" aria-label="Padanan SKU">
    <header><i><ArrowLeftRight size={19} aria-hidden="true"/></i><div><h3>Padanan beda merek</h3><p>Padanan tersimpan dipakai sebagai saran di Ganti Merek.</p></div></header>
    <label>Padanan di merek lain<select aria-label="SKU padanan beda merek" value={selected} onChange={e=>{setValue(e.target.value);setMsg('')}}>
      <option value="">Tanpa padanan</option>{allSkus(s,true).filter(b=>b.brand!==a.brand).map(b=><option key={b.key} value={b.key}>{b.key} · {b.model} · {rangeLabel(b.sizes)}</option>)}
    </select></label>
    <div className="wh-pair-foot"><span>{current ? `Tersimpan ${a.key} ↔ ${current}` : 'Belum ada padanan'}
      {selected!==current && other && other!==sku && <small>Akan menggantikan padanan {other}.</small>}</span>
      <button type="button" className="soft-btn" disabled={selected===current} onClick={()=>{try{changeSession(v=>pairSku(v,sku,selected||null));setValue(null);setMsg(selected?'Padanan dua arah tersimpan.':'Padanan dua arah dikosongkan.')}catch(e){setMsg((e as Error).message)}}}>Simpan padanan</button>
    </div>{msg&&<p role="status">{msg}</p>}
  </section>
}
export default function BrandConversionForm(){
  const s=usePlannerSession()
  const [m,setM]=useState(()=>initial(s)),[msg,setMsg]=useState(''),[discard,setDiscard]=useState(false),[hasDraft,setDraft]=useState(()=>!!sessionStorage.getItem(draftKey))
  const [preview,setPreview]=useState<{id:string;balances:Record<string,number>;changes:NonNullable<Session['stockEvents']>[number]['changes'];kit?:ConversionKit}|null>(null)
  const a=skuByKey(m.source)!,b=skuByKey(m.target),pair=pairOf(s,m.source)
  function edit(v:Partial<MoveInput>){setM({...m,...v});setPreview(null);setMsg('')}
  function target(v:string){edit({target:v,sizeMap:matchingSizes(m.source,v)})}
  const positions=[...new Set(skuCatalog.map(a=>{const p=nativePosition(a);return p.location+'|Good'}))]
  const total=(key:string)=>skuByKey(key)!.sizes.reduce((n,x)=>n+stockAt(skuByKey(key)!,x,s,m.location,m.grade),0)
  function review(){try{
    const id=crypto.randomUUID(),balances=moveSnapshot(s,m)
    const {changes,kit}=convertStock(s,m,id,balances).stockEvents!.at(-1)!
    setPreview({id,balances,changes,kit});setMsg('')
  }catch(e){setPreview(null);setMsg((e as Error).message)}}
  function submit(){if(!preview)return;try{
    changeSession(v=>{
      const next=convertStock(v,m,preview.id,preview.balances)
      const kit=next.stockEvents?.find(row=>row.id===preview.id)?.kit
      if(JSON.stringify(kit)!==JSON.stringify(preview.kit))throw Error('Stok atau harga aksesori berubah. Periksa kembali.')
      return next
    })
    sessionStorage.removeItem(draftKey);setDraft(false);setPreview(null);setM({...m,values:{},accessories:undefined});setMsg('Tersimpan. Saldo kedua SKU dan riwayat stok sudah diperbarui.')
  }catch(e){setPreview(null);setMsg((e as Error).message)}}
  function loadDraft(){try{
    const d=JSON.parse(sessionStorage.getItem(draftKey)??'null'),source=d?.source??d?.key
    if(!skuByKey(source)||!d.values)throw Error('Draft tidak tersedia.')
    const data={...initial(s,source),...d,source,notes:d.notes??d.note??''}
    if(data.target&&!skuByKey(data.target))data.target=''
    setM(data);setPreview(null);setMsg('Draft dibuka untuk diedit.')
  }catch(e){setMsg((e as Error).message)}}
  return <><section className="panel wh-conversion sku-range" aria-label="Ganti Merek">
    <header className="wh-section-head"><div><span>BARANG JADI</span><h2>Pindah stok antar-SKU</h2></div><ArrowLeftRight/></header>
    <div className="wh-columns">{(['source','target'] as const).map(side=>{
      const src=side==='source',item=src?a:b
      return <div className="wh-side" key={side}><header>{src?<Package size={18}/>:<ArrowRight size={18}/>}<h3>{src?'Keluar dari':'Masuk ke'}</h3></header>
        <label>{src?'SKU asal':'SKU tujuan'}<select aria-label={src?'Pilih SKU':'SKU tujuan'} value={m[side]} onChange={e=>src?edit(initial(s,e.target.value)):target(e.target.value)}>
          {!src&&<option value="">Pilih SKU tujuan</option>}{allSkus(s,true).filter(c=>src||c.key!==m.source).map(c=><option value={c.key} key={c.key}>{c.key} · {c.model}</option>)}</select></label>
        {item&&<div className="wh-stock"><div><small>{item.colour} · Ukuran {rangeLabel(item.sizes)}</small><span>Stok tersedia</span></div><strong>{fgQuantity(total(item.key))}</strong></div>}
      </div>})}</div>
    <div className="wh-recommend"><BookOpen size={17}/><span>{pair?'Saran master · '+pair:'Belum ada padanan di master'}</span>{pair&&m.target!==pair&&<button type="button" className="soft-btn" onClick={()=>target(pair)}>Pakai padanan</button>}<a href={masterPath+'?sku='+encodeURIComponent(m.source)+'#padanan'}>Atur padanan</a></div>
    <div className="wh-fields"><label>Lokasi dan kondisi<select aria-label="Lokasi dan kondisi" value={m.location+'|'+m.grade} onChange={e=>{const [location,grade]=e.target.value.split('|');edit({location,grade})}}>{positions.map(p=><option key={p} value={p}>{p.split('|').join(' · ')}</option>)}</select></label><label>Tanggal fisik<input type="date" max={lastWarehouseDay()} required value={m.date} onChange={e=>edit({date:e.target.value})}/></label><label>Jam fisik (WIB, opsional)<input type="time" value={m.physicalTime??''} onChange={e=>edit({physicalTime:e.target.value})}/></label></div>
    <details className="wh-size-entry" key={m.source}><summary>Detail ukuran · {rangeLabel(a.sizes)}</summary><div className="wh-size-map">{a.sizes.map(x=><div key={x}><div><strong>Ukuran {x}</strong><small>Tersedia {fgQuantity(stockAt(a,x,s,m.location,m.grade))}</small></div><label>Keluar (pcs)<input aria-label={'Jumlah ukuran '+x} inputMode="numeric" placeholder="0" value={m.values[x]??''} onChange={e=>edit({values:{...m.values,[x]:e.target.value}})}/></label><label>Ukuran tujuan<select aria-label={'Ukuran tujuan untuk '+x} value={m.sizeMap[x]??''} onChange={e=>edit({sizeMap:{...m.sizeMap,[x]:e.target.value}})}><option value="">Pilih ukuran</option>{b?.sizes.map(y=><option key={y}>{y}</option>)}</select></label></div>)}</div></details>
    <ConversionAccessoryFields value={m.accessories??emptyAccessories} session={s} onChange={accessories=>edit({accessories})}/>
    <div className="wh-fields"><label>Alasan · wajib<input aria-label="Alasan transaksi" value={m.reason} required onChange={e=>edit({reason:e.target.value})}/></label><label>Catatan · opsional<input aria-label="Catatan transaksi" value={m.notes??''} onChange={e=>edit({notes:e.target.value})}/></label></div>
    <footer className="wh-actions"><button className="primary-btn" onClick={review}><Search size={15}/>Periksa jumlah</button><button className="soft-btn" onClick={()=>{sessionStorage.setItem(draftKey,JSON.stringify(m));setDraft(true);setMsg('Draft form tersimpan di tab ini.')}}>Simpan draft form</button>{hasDraft&&<><button className="soft-btn" onClick={loadDraft}>Edit draft tersimpan</button><button className="soft-btn" onClick={()=>setDiscard(true)}>Hapus draft</button></>}</footer>
    {preview&&<div className="wh-preview"><h3>Perubahan stok latihan</h3><div className="wh-preview-rows">{preview.changes.map(c=><div key={c.key+c.size}><span>{c.key} · ukuran {c.size}</span><strong>{c.delta>0?'+':''}{fgQuantity(c.delta)}</strong><small>{fgQuantity(preview.balances[c.key+'|'+c.size])} → {fgQuantity(c.after!)}</small></div>)}</div>
      {preview.kit&&<div className="demo-operation-facts" aria-label="Dampak aksesori">
        {preview.kit.used.map(line=><article key={line.code}><small>{line.name}</small><strong>−{line.qty} pcs</strong><span>Dipakai · {amountText(line.qty*line.rate)}</span></article>)}
        {preview.kit.expected.map(line=><article key={line.code}><small>{line.name}</small><strong>{line.qty} pcs ditunggu</strong><span>Di {line.holder}</span></article>)}
      </div>}{preview.kit&&preview.kit.used.length>0&&<p>Biaya tambahan konversi <strong>{amountText(kitCost(preview.kit))}</strong></p>}
      <button className="primary-btn" onClick={submit}>Simpan transaksi latihan</button></div>}
    {discard&&<ReasonDialog title="Hapus draft form?" closeLabel="Kembali" onClose={()=>setDiscard(false)}><p>Draft ini belum mengubah saldo stok.</p><button className="soft-btn" onClick={()=>{sessionStorage.removeItem(draftKey);setDraft(false);setDiscard(false);setM(initial(s,m.source));setPreview(null);setMsg('Draft dihapus.')}}>Ya, hapus draft ini</button></ReasonDialog>}
    {msg&&<p className="wh-feedback" role="status">{msg}</p>}
  </section><ConversionAccessoryHistory session={s}/></>
}
