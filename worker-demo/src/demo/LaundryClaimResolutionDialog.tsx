import NumberEntry from '../../../src/components/NumberEntry'
import { useState } from 'react'
import { ShieldCheck } from 'lucide-react'
import { laundryDigits, laundryOutstandingSizes, type LaundryClaim, type LaundryClaimResolution, type LaundryDelivery } from './laundryModel'
import { validClaimResolution } from './laundryCredits'
import { amountText } from './accessoryPricing'
import { ReasonDialog } from './planner/ReasonDialog'
import { lastWarehouseDay } from './warehouseDay'

export function LaundryClaimResolutionDialog({delivery,claim,used,onClose,onSave}:{
  delivery:LaundryDelivery;claim:LaundryClaim;used:number;onClose:()=>void;onSave:(resolution:LaundryClaimResolution)=>void
}) {
  const outside=laundryOutstandingSizes(delivery)
  const [kind,setKind]=useState<LaundryClaimResolution['kind']>(claim.cents>0?'CREDIT':'REPLACEMENT')
  const [sizes,setSizes]=useState(()=>{
    const canFill=outside.filter(value=>value>0).length===1||outside.reduce((sum,value)=>sum+value,0)===claim.qty
    return outside.map(qty=>canFill&&qty>0?String(Math.min(qty,claim.qty)):'')
  })
  const [day,setDay]=useState(lastWarehouseDay)
  const [reason,setReason]=useState('')
  const [error,setError]=useState('')
  const closedSizes=claim.type==='BS'?[]:sizes.map(value=>Number(value||0))
  const chosen=closedSizes.reduce((sum,qty)=>sum+qty,0)
  return <ReasonDialog title="Selesaikan klaim laundry" closeLabel="Kembali" className="demo-operation-dialog money-dialog" icon={<ShieldCheck/>} onClose={onClose}>
    <form className="demo-operation-form" onSubmit={event=>{
      event.preventDefault()
      const resolution={kind,day,reason:reason.trim(),sizes:closedSizes}
      if(kind==='REPLACEMENT'&&used>0||!validClaimResolution(delivery,claim,resolution)){setError('Periksa jumlah per ukuran, tanggal, dan bukti penyelesaian.');return}
      onSave(resolution)
    }}><p>{delivery.vendor} · {delivery.id} · <strong>{claim.qty} pcs</strong></p>
      <label>Penyelesaian<select value={kind} onChange={event=>{setKind(event.target.value as LaundryClaimResolution['kind']);setError('')}}>
        {claim.cents>0&&<option value="CREDIT">Kompensasi jadi kredit tagihan</option>}
        {claim.type!=='BS'&&!used&&<option value="REPLACEMENT">Barang pengganti sudah diterima</option>}
      </select></label>
      {claim.type!=='BS'&&<fieldset className="laundry-claim-sizes"><legend>Ukuran yang diselesaikan</legend>
        <div className="demo-operation-fields">{delivery.sizeLabels.map((size,index)=><label key={size}>Ukuran {size}
          <NumberEntry aria-label={'Jumlah selesai ukuran '+size} inputMode="numeric" placeholder="0" disabled={!outside[index]}
            value={sizes[index]} onValueChange={rawInput =>setSizes(current=>current.map((item,i)=>i===index?laundryDigits(rawInput,outside[i]):item))}/>
          <small>{outside[index]} pcs masih di luar</small></label>)}</div><strong>{chosen} dari {claim.qty} pcs</strong>
      </fieldset>}
      <div className="demo-operation-facts"><article><span>{kind==='CREDIT'?'Kredit siap dipakai':'Barang pengganti masuk antrean'}</span>
        <strong>{kind==='CREDIT'?amountText((claim.cents-used)/100):chosen+' pcs → QC'}</strong>
        <small>{claim.type==='BS'?'Jumlah fisik BS tetap di riwayat penerimaan.':kind==='CREDIT'?'Qty yang dipilih keluar dari Stuck.':'Catat saat barang pengganti yang sesuai benar-benar diterima.'}</small></article></div>
      <label>Tanggal penyelesaian<input required type="date" min={claim.approvedOn} max={lastWarehouseDay()} value={day} onChange={event=>setDay(event.target.value)}/></label>
      <label>Bukti penyelesaian<textarea required minLength={4} maxLength={500} value={reason} placeholder="Contoh: konfirmasi potongan dari vendor" onChange={event=>setReason(event.target.value)}/></label>
      {error&&<p role="alert">{error}</p>}
      <footer><button className="primary-btn" disabled={claim.type!=='BS'&&chosen!==claim.qty}>Simpan penyelesaian klaim</button></footer>
    </form>
  </ReasonDialog>
}
