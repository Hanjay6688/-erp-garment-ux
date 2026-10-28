import type {ProgressTelemetry} from '../cp7_current_analysis_progress/telemetry'
import {formatCp6WibDateTime} from './vendor/src/cp6BusinessTime'
import {stagedNumber} from './vendor/src/nativeAnalysisPages'
import {frozenDuration,FROZEN_NO_PROGRESS_MS} from './vendor/scripts/cp7_frozen_quantity_ui/client/nativeFrozenProgress'

export default function CombinedProgress({value}:{value:ProgressTelemetry}){
 const progress=value.progress,finance=value.finance
 return <section aria-label="Kemajuan analisis gabungan" data-combined-state={progress.state}>
  <h3>Kemajuan produksi dan laporan resmi</h3>
  <p role="status">{progress.message}</p>
  {value.elapsedMs!==null?<p>{value.processingFinished?'Waktu pemrosesan':'Waktu berjalan yang tercatat'}: {frozenDuration(value.elapsedMs/1000)}.</p>:null}
  <p>Status server diperiksa {formatCp6WibDateTime(value.observedAt)}. Data operasional per {formatCp6WibDateTime(progress.capturedAt)}.</p>
  {([['Produksi',progress.operational],['Keuangan dan HPP',progress.finance]]as const).map(([name,phase])=><div key={name}>
   <h4>{name}</h4><p>{phase.label}.</p>
   {phase.done!==null?<p>{stagedNumber(phase.done)} langkah selesai{phase.total===null?'; jumlah akhir belum diketahui.':` dari ${stagedNumber(phase.total)}.`}</p>:null}
   {phase.percent!==null&&phase.total!==null&&phase.total>0?<><progress aria-label={`Kemajuan ${name.toLowerCase()}`} value={phase.done??0} max={phase.total}/><p>{phase.percent}% bagian {name.toLowerCase()}.</p></>:null}
  </div>)}
  {finance&&finance.activity!=='TERMINAL'?<div aria-label="Aktivitas keuangan terakhir">
   <p>Aktivitas keuangan terakhir tercatat {formatCp6WibDateTime(finance.lastActivityAt)}.</p>
   <p>{finance.activity==='WORKER_OBSERVED'?'Proses keuangan teramati aktif saat pemeriksaan ini.':'Tidak ada proses keuangan aktif yang teramati saat pemeriksaan ini.'}</p>
   {finance.idleMs>=FROZEN_NO_PROGRESS_MS?<p role="alert">Belum ada aktivitas keuangan baru yang tercatat selama {frozenDuration(finance.idleMs/1000)}. Periksa kemajuan pekerjaan yang sama atau buka kembali pekerjaan tersimpan. Pekerjaan belum dinyatakan gagal.</p>:null}
  </div>:null}
  <p>Kemajuan setiap bagian dihitung terpisah. Produksi selesai belum berarti laporan keuangan dan HPP siap.</p>
 </section>
}
