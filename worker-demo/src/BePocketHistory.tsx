import { useState } from 'react'
import type { PocketOpening, PocketOpeningUsage } from './pocketOpening'
import type { Json } from './types/database.preconnect'
export default function BePocketHistory({ data, locked, canCorrect, onCorrect }: { data: PocketOpening; locked: boolean; canCorrect: boolean; onCorrect: (p: Record<string, Json>) => void }) {
  const [selected, setSelected] = useState<PocketOpeningUsage | null>(null), [amount, setAmount] = useState(''), [date, setDate] = useState(''), [reason, setReason] = useState('')
  const latest = data.usage.find(x=>x.id===selected?.id), stale = !!selected && latest?.amount !== selected.amount
  const valid = selected && !stale && /^\d{1,15}([.,]\d{1,2})?$/.test(amount) && date && reason.trim()
  return <section className="panel initial-import-table"><h2>Kain kantong sebelum saldo awal</h2>
    <p>{data.usage.length} dari {data.usage_count} sumber biaya; {data.sewing.length} dari {data.sewing_count} rincian hasil jahit. Gunakan pencarian di atas untuk menemukan dokumen atau mandor. Data berasal dari menu Impor Saldo Awal.</p>
    <table><thead><tr><th>Dokumen / baris</th><th>Tanggal</th><th>Bahan</th><th>Jumlah</th><th>Nilai terkini</th><th>Pembagian</th><th>Tindakan</th></tr></thead><tbody>{data.usage.map(s=><tr key={s.id}>
      <td>{s.document_number} / {s.line_number}</td><td>{s.date}</td><td>{s.material_sku} · {s.material_name}</td><td>{s.qty.replace(/\.?0+$/,'')}</td><td>Rp {s.amount.replace('.',',')}</td>
      <td>{s.allocation_status==='ALLOCATED' ? `Sudah dibagi sebelum saldo awal: ${s.prior_allocation_reference}` : s.active_period ? 'Sudah dibagi lewat periode' : 'Belum dibagi ke HPP'}</td>
      <td>{s.receipt_backed ? 'Koreksi melalui nota supplier asal' : canCorrect && s.allocation_status==='UNALLOCATED' && <button type="button" disabled={locked} onClick={()=>{setSelected(s);setAmount(s.amount);setDate('');setReason('')}}>Koreksi {s.document_number} / {s.line_number}</button>}</td>
    </tr>)}</tbody></table>
    {selected && <div className="initial-import-toolbar"><p>Koreksi nilai sumber {selected.document_number}/{selected.line_number}. Pembagian aktif dan HPP turunannya dihitung ulang; jumlah stok tetap.</p>
      {stale && <p role="alert">Nilai sumber berubah. Pilih ulang dokumennya.</p>}
      <label>Nilai yang benar<input aria-label="Nilai sumber kain kantong" inputMode="decimal" disabled={locked} value={amount} onChange={e=>setAmount(e.target.value)}/></label>
      <label>Tanggal koreksi<input aria-label="Tanggal koreksi kain kantong" type="date" disabled={locked} value={date} onChange={e=>setDate(e.target.value)}/></label>
      <label>Alasan koreksi<input aria-label="Alasan koreksi kain kantong" maxLength={1000} disabled={locked} value={reason} onChange={e=>setReason(e.target.value)}/></label>
      <button type="button" disabled={locked || !valid} onClick={()=>{if(valid)onCorrect({usage_id:selected.id,expected_amount:selected.amount,amount:amount.replace(',','.'),economic_date:date,reason:reason.trim()})}}>Sahkan koreksi nilai</button>
      <button type="button" disabled={locked} onClick={()=>setSelected(null)}>Tutup koreksi</button>
    </div>}
    <details><summary>Hasil jahit historis yang menjadi pembagi</summary><table><thead><tr><th>Dokumen / baris</th><th>Mandor</th><th>PCS</th><th>Posisi awal</th><th>Rujukan</th><th>Biaya dibagikan</th></tr></thead><tbody>{data.sewing.map(s=><tr key={s.id}>
      <td>{s.document_number} / {s.line_number}</td><td>{s.contractor_name}</td><td>{s.qty}</td><td>{s.target_kind==='FINISHED_GOODS'?'Barang jadi':s.target_kind==='COGS'?'Sudah terjual':s.target_kind}</td><td>{s.target_reference}{s.sold_reference && ` · ${s.sold_reference}`}</td><td>Rp {s.allocated_amount.replace('.',',')}</td>
    </tr>)}</tbody></table></details>
  </section>
}
