import {formatCp6WibDateTime} from './cp6BusinessTime'
import {targetDemandBasisLabel,analogUnavailableLabel,type TargetDemand} from './nativeTargetDemand'
import {modelTargetReasonLabel} from './nativeModelTarget'

export default function TargetDemandDetails({value}:{value:TargetDemand}){
 const a=value.analog,m=value.model
 return <section className="target-demand-details" aria-label="Dasar kebutuhan target">
  <h5>{m?.state==='MODEL_PROJECTED'?'Target memakai perkiraan model':targetDemandBasisLabel(value.basis)}</h5>
  <p>Periode {value.query.from_date} sampai {value.query.through_date}. Data per {formatCp6WibDateTime(value.capturedAt)}.</p>
  <p>Penjualan asli produk ini saat stok tersedia: {value.ownTotalPcs} PCS dari {value.ownAvailableDays} hari.</p>
  {m?.state==='MODEL_PROJECTED'?<>
   <p>Metode {m.model!.method}; perkiraan {m.forecasts!.length} hari mulai {m.forecastFrom}. Kebijakan versi {m.policy!.policy.revision}.</p>
   <p>Target tanpa model: {m.baselineTarget} PCS; titik pesan ulang tanpa model: {m.baselineReorderPoint} PCS.</p>
   <p>{m.mode==='DAYS'?'Kebutuhan dijumlahkan sesuai tanggal; cadangan hari dihitung satu kali.':'Cadangan tetap memakai variasi penjualan historis dan tingkat layanan yang dipilih. Ini belum bukti bahwa rentang perkiraan model sudah terkalibrasi.'}</p>
  </>:m?<p>{modelTargetReasonLabel(m.reason)}</p>:null}
  {a?.state==='READY'?<>
   <p>Pembanding: {a.sourceSku} · {a.sourceName}. Skala {a.scale}; pilihan revisi {a.revision}.</p>
   <p>Penjualan pembanding saat stok tersedia: {a.sourceTotalPcs} PCS dari {a.availableDays} hari. Kebutuhan target memakai {a.scaledTotalPcs} ÷ {a.availableDays} PCS/hari.</p>
   <p>Alasan pemeriksaan: {a.reviewReason}</p>
  </>:a?<p>{analogUnavailableLabel(a.reason)} Nilai belum diketahui tetap belum diketahui.</p>:value.basis==='SELECTED_MANUAL_ASSUMPTION'?<p>Kebutuhan manual: {value.dailyTotalPcs} PCS/hari.</p>:null}
  <p>Target rencana: {value.targetPcs===null?'belum diketahui':value.targetPcs+' PCS'}.</p>
 </section>
}
