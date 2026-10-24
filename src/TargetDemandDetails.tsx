import {formatCp6WibDateTime} from './cp6BusinessTime'
import {targetDemandBasisLabel,analogUnavailableLabel,type TargetDemand} from './nativeTargetDemand'

export default function TargetDemandDetails({value}:{value:TargetDemand}){
 const a=value.analog
 return <section className="target-demand-details" aria-label="Dasar kebutuhan target">
  <h5>{targetDemandBasisLabel(value.basis)}</h5>
  <p>Periode {value.query.from_date} sampai {value.query.through_date}. Data per {formatCp6WibDateTime(value.capturedAt)}.</p>
  <p>Penjualan asli produk ini saat stok tersedia: {value.ownTotalPcs} PCS dari {value.ownAvailableDays} hari.</p>
  {a?.state==='READY'?<>
   <p>Pembanding: {a.sourceSku} · {a.sourceName}. Skala {a.scale}; pilihan revisi {a.revision}.</p>
   <p>Penjualan pembanding saat stok tersedia: {a.sourceTotalPcs} PCS dari {a.availableDays} hari. Kebutuhan target memakai {a.scaledTotalPcs} ÷ {a.availableDays} PCS/hari.</p>
   <p>Alasan pemeriksaan: {a.reviewReason}</p>
  </>:a?<p>{analogUnavailableLabel(a.reason)} Nilai belum diketahui tetap belum diketahui.</p>:value.basis==='SELECTED_MANUAL_ASSUMPTION'?<p>Kebutuhan manual: {value.dailyTotalPcs} PCS/hari.</p>:null}
  <p>Target rencana: {value.targetPcs===null?'belum diketahui':value.targetPcs+' PCS'}.</p>
 </section>
}
