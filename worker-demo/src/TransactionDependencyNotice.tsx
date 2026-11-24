import {AlertTriangle,ArrowRight} from 'lucide-react'
import './record-tools.css'

export type TransactionDependencyStep={key:string;message:string;buttonLabel:string;onOpen?:()=>void;disabled:boolean}

export default function TransactionDependencyNotice({documentNumber,steps}:{documentNumber:string;steps:readonly TransactionDependencyStep[]}){
 if(!steps.length)return null
 return <section className="transaction-dependencies" role="status" aria-label={`Penghalang pembatalan ${documentNumber}`}>
  <h3><AlertTriangle aria-hidden="true"/> Bereskan transaksi berikut dahulu</h3>
  <p>Untuk menghapus / membatalkan {documentNumber}, periksa dan batalkan transaksi aktif yang terkait. Setelah itu muat ulang invoice dan periksa kembali. Edit isi nota tetap melalui Benerin nota.</p>
  <ol>{steps.map(step=><li key={step.key}><p>{step.message}</p>{step.onOpen?<button type="button" disabled={step.disabled} onClick={step.onOpen}>{step.buttonLabel}<ArrowRight aria-hidden="true"/></button>:<p>Minta pengguna dengan hak yang sesuai untuk membuka {step.buttonLabel.toLowerCase()}.</p>}</li>)}</ol>
  <small>Riwayat pembatalan tetap tersimpan. Sistem memeriksa kembali ketergantungan saat pembatalan dikirim.</small>
 </section>
}
