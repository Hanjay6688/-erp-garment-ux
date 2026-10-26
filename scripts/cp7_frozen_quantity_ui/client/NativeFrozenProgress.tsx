import {useEffect,useState} from 'react'
import type {StagedJob} from '../../../src/nativeStagedJob'
import {stagedNumber} from '../../../src/nativeAnalysisPages'
import {formatCp6WibDateTime} from '../../../src/cp6BusinessTime'
import {frozenDuration,frozenProgressView,FROZEN_NO_PROGRESS_MS} from './nativeFrozenProgress'

type Props={job:StagedJob|null;busy:boolean;interrupted:boolean;blocked:boolean;financeSelected:boolean}
export default function NativeFrozenProgress({job,busy,interrupted,blocked,financeSelected}:Props){
 const[now,setNow]=useState(Date.now)
 useEffect(()=>{if(!busy||job?.state==='DONE'||job?.state==='FAILED')return;setNow(Date.now());const timer=setInterval(()=>setNow(Date.now()),1000);return()=>clearInterval(timer)},[busy,job?.requestId,job?.state])
 if(!job)return busy||interrupted||blocked?<section aria-label="Kemajuan analisis"><p role="status">{blocked?'Analisis tertahan: periksa sumber atau lingkup data.':interrupted?'Status pekerjaan belum dapat dipastikan. Buka perhitungan tersimpan.':'Menyiapkan data… jumlah pekerjaan belum diketahui.'}</p><p>Permintaan tersimpan tetap dipakai saat halaman dibuka kembali.</p></section>:null
 const view=frozenProgressView(job),running=job.state==='RUNNING'
 const old=running&&now-Date.parse(job.lastProgressAt)>=FROZEN_NO_PROGRESS_MS
 const title=job.state==='FAILED'?'Analisis produksi gagal':job.state==='DONE'?'Perhitungan produksi selesai':interrupted?'Pemantauan terhenti — status terakhir belum selesai':view.queued?'Menunggu langkah pertama':'Analisis produksi berjalan'
 return <section aria-label="Kemajuan analisis" data-analysis-state={job.state}>
  <p role="status"><strong>{title}</strong>{running?` · ${view.stage}`:''}</p>
  <p>{stagedNumber(job.unitsDone)} dari {stagedNumber(job.unitCount)} langkah produksi selesai.{!job.planFinal?' Jumlah akhir masih disusun.':''}</p>
  {view.percent!==null?<><progress aria-label="Langkah produksi selesai" value={job.unitsDone} max={job.unitCount}/><p>{view.percent}% langkah produksi. Persentase ini tidak mencakup keuangan/HPP.</p></>:null}
  {running&&job.targetsTotal!==null?<p>Pada tahap ini: {stagedNumber(job.targetsDoneInStage)} dari {stagedNumber(job.targetsTotal)} target selesai. Tahap lain masih dapat tersisa.</p>:null}
  <p>Data acuan: {formatCp6WibDateTime(job.reference.capturedAt)}. Kemajuan terakhir: {formatCp6WibDateTime(job.lastProgressAt)}.</p>
  {running?<p>Durasi sejak data diambil: {frozenDuration((now-Date.parse(job.reference.capturedAt))/1000)}.</p>:null}
  {old?<p>Belum ada kemajuan terbaru. Status server perlu diperiksa; ini belum berarti pekerjaan gagal.</p>:null}
  {job.unitAttempts>0?<p>Server mencoba kembali langkah yang sama: {stagedNumber(job.unitAttempts)} kali.</p>:null}
  {running?<p>{job.serverRunner?.active?'Server sedang menjalankan pekerjaan ini. Halaman boleh ditutup; buka kembali untuk melihat pekerjaan yang sama.':'Pekerja server belum terkonfirmasi aktif. Saat halaman ditutup, buka kembali perhitungan tersimpan untuk melanjutkan pekerjaan yang sama.'}</p>:null}
  {financeSelected?<p>Produksi dan keuangan memiliki progres terpisah. Status keuangan/HPP terbaru ada pada bagian laporan resmi; produksi selesai belum berarti analisis gabungan lengkap.</p>:<p>Perhitungan ini tidak menyertakan keuangan/HPP.</p>}
 </section>
}
