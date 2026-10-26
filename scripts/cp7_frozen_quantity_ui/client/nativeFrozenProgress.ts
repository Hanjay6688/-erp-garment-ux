import type {StagedJob} from '../../../src/nativeStagedJob'

// Existing Native units are bounded at 8s. A 30s HTTP wait leaves transport
// margin; it is NOT a deadline for the complete factory analysis. A two-minute
// unchanged unit plan is a client observation requiring status recovery, not
// a claim that the server transaction failed. Neither threshold changes SQL.
export const FROZEN_RPC_WAIT_MS=30_000
export const FROZEN_NO_PROGRESS_MS=120_000
export const FROZEN_WAIT_MESSAGE='Server belum memberi jawaban. Hasil permintaan belum diketahui. Buka perhitungan tersimpan untuk memeriksa pekerjaan yang sama; jangan membuat ulang.'
export const FROZEN_STALL_MESSAGE='Kemajuan belum berubah selama dua menit. Pemantauan dihentikan. Buka perhitungan tersimpan untuk memeriksa pekerjaan yang sama; proses server belum dinyatakan gagal.'

type Abortable<T>=PromiseLike<T>&{abortSignal?:(signal:AbortSignal)=>PromiseLike<T>}
export async function boundedFrozenReply<T>(start:()=>Abortable<T>,waitMs=FROZEN_RPC_WAIT_MS):Promise<T>{
 const controller=new AbortController()
 let timer:ReturnType<typeof setTimeout>|undefined
 try{
  const request=start(),reply=request.abortSignal?request.abortSignal(controller.signal):request
  const timeout=new Promise<never>((_,reject)=>{timer=setTimeout(()=>{reject(Error(FROZEN_WAIT_MESSAGE));controller.abort()},waitMs)})
  return await Promise.race([reply,timeout])
 }finally{if(timer!==undefined)clearTimeout(timer)}
}

export function frozenProgressGuard(now:()=>number=()=>performance.now()){
 let signature:string|null=null,advancedAt=now()
 return(job:StagedJob)=>{
  const next=JSON.stringify([job.state,job.stage,job.unitsDone,job.unitCount,job.planFinal,job.targetsDoneInStage,job.targetsTotal])
  if(next!==signature){signature=next;advancedAt=now()}
  else if(job.state==='RUNNING'&&now()-advancedAt>=FROZEN_NO_PROGRESS_MS)throw Error(FROZEN_STALL_MESSAGE)
 }
}

const names:Record<string,string>={HIST_PREP:'Menyiapkan data dan riwayat',HIST_EVENTS:'Membaca kejadian penjualan',HIST_VALIDATE:'Memeriksa riwayat',HIST_ROWS:'Menghitung riwayat per produk',HIST_STOCK:'Menghitung stok tersedia',BASE_ROWS:'Menghitung kebutuhan dasar',SUPPLY:'Memeriksa barang dalam proses',SCENARIO:'Memeriksa jadwal produksi',NET_PREP:'Menyiapkan pembagian persediaan',NET_TARGETS:'Memeriksa kebutuhan produk',NET_PAIRS:'Mencocokkan barang dalam proses',NET_PLAN:'Menyusun rencana persediaan',ALLOC_PREP:'Menyiapkan pembagian kapasitas',ALLOC_STEP:'Membagi kapasitas produksi',ALLOC_FINAL:'Memeriksa hasil pembagian',NET_ROWS:'Menghitung kekurangan akhir',FABRIC_PLAN:'Memeriksa kebutuhan bahan',ANA_TARGETS:'Menyusun hasil per produk',ANA_META:'Memeriksa kelengkapan hasil',PAGES:'Menyimpan halaman hasil',FINAL:'Menyelesaikan hasil'}
export const frozenStageName=(stage:string|null)=>stage?names[stage]??'Memproses tahap analisis':'Menyelesaikan hasil'
export const frozenDuration=(seconds:number)=>{const s=Math.max(0,Math.floor(seconds));return s<60?`${s} detik`:s<3600?`${Math.floor(s/60)} menit ${s%60} detik`:`${Math.floor(s/3600)} jam ${Math.floor(s%3600/60)} menit`}
export function frozenProgressView(job:StagedJob){
 const percent=job.planFinal?Math.floor(job.unitsDone/job.unitCount*100):null
 return{percent,stage:frozenStageName(job.stage),queued:job.state==='RUNNING'&&job.unitsDone===0&&!job.workerActive}
}
