import { useEffect, useMemo, useState } from 'react'
import {
  AlertTriangle, CheckCircle2, History, LoaderCircle, PackageCheck, RefreshCw,
  RotateCcw, Search, Send, ShieldCheck, Undo2, Waves,
} from 'lucide-react'
import { useAuth } from './auth/AuthProvider'
import { SENSITIVE_ACTION_PERMISSION, hasPermission } from './auth/accessCatalog'
import { Cp6ActionBlocked, Cp6PermissionNotice } from './Cp6PermissionNotice'
import { CP6_BUSINESS_TIME_LABEL, cp6WibPhysicalTimeToIso, formatCp6WibDateTime } from './cp6BusinessTime'
import {
  findLaundryRateAt, productEffectiveAt, totalReadyToSend, type LaundryQcWorkspace,
} from './laundryQcModel'
import { useLaundryQcWorkspace } from './useLaundryQcWorkspace'
import type { Json } from './types/database.preconnect'
import './connected-laundry-qc.css'

type RunAction = (
  action: 'POST_DELIVERY' | 'POST_RECEIPT' | 'POST_FAILED_WASH' | 'REVERSE_DELIVERY' | 'REVERSE_RECEIPT',
  payload: Json,
  expectedVersion: number | null,
  retireCommittedForm: () => void,
) => Promise<boolean>

const parseQuantity = (value: string) => {
  if (!value.trim()) return 0
  const parsed = Number(value)
  return /^\d+$/.test(value.trim()) && Number.isSafeInteger(parsed)
    ? parsed
    : null
}
const quantity = (value: string) => parseQuantity(value) ?? 0
const money = (value: number) => `Rp${Math.round(value).toLocaleString('id-ID')}`
const statusLabel: Record<string, string> = {
  DRAFT: 'Draft', SENT: 'Dikirim', PARTIAL_RETURN: 'Kembali sebagian',
  RECEIVED: 'Selesai diterima', POSTED: 'Tersimpan', REVERSED: 'Dibatalkan',
}
const status = (value: string) => statusLabel[value] ?? value.replaceAll('_', ' ')

function SendLaundryForm({ workspace, writerLocked, canCreate, canPost, onAction }: {
  workspace: LaundryQcWorkspace; writerLocked: boolean; canCreate: boolean; canPost: boolean; onAction: RunAction
}) {
  const [batchId, setBatchId] = useState('')
  const [vendorId, setVendorId] = useState('')
  const [processId, setProcessId] = useState('')
  const [targetColor, setTargetColor] = useState('')
  const [physicalAt, setPhysicalAt] = useState('')
  const [reason, setReason] = useState('')
  const [notes, setNotes] = useState('')
  const [confirmed, setConfirmed] = useState(false)
  const [quantities, setQuantities] = useState<Record<string, string>>({})
  useEffect(() => setConfirmed(false), [workspace])
  const actionAllowed = canCreate && canPost
  const actionLocked = writerLocked || !actionAllowed
  const batch = workspace.ready_batches.find((row) => row.distribution_batch_id === batchId) ?? null
  const physicalIso = cp6WibPhysicalTimeToIso(physicalAt)
  const rate = findLaundryRateAt(workspace, vendorId, processId, physicalIso ?? '')
  const selectedLines = batch?.sizes.map((row) => ({
    size_id: row.size_id,
    qty_sent_pcs: quantity(quantities[row.size_id] ?? '0'),
  })).filter((row) => row.qty_sent_pcs > 0) ?? []
  const total = selectedLines.reduce((sum, row) => sum + row.qty_sent_pcs, 0)
  const invalidQuantity = batch?.sizes.some((row) =>
    parseQuantity(quantities[row.size_id] ?? '0') === null) ?? false
  const over = batch?.sizes.some((row) =>
    quantity(quantities[row.size_id] ?? '0') > row.available_qty_pcs) ?? false
  const valid = Boolean(batch && workspace.readiness.laundry_writer_ready && actionAllowed
    && vendorId && processId && targetColor.trim() && physicalIso && rate
    && total > 0 && !invalidQuantity && !over && total <= batch.group_unsent_ready_qty_pcs
    && reason.trim().length >= 4 && confirmed)

  const fillReady = () => {
    if (!batch) return
    let remaining = batch.group_unsent_ready_qty_pcs
    const next: Record<string, string> = {}
    batch.sizes.forEach((row) => {
      const take = Math.min(row.available_qty_pcs, remaining)
      next[row.size_id] = String(take)
      remaining -= take
    })
    setQuantities(next)
    setConfirmed(false)
  }

  return <section className="clq-panel">
    <header><div><span>KIRIM FISIK · JAHIT → LAUNDRY</span><h2>Catat barang yang benar-benar keluar</h2><p>Jumlah dimulai dari nol. “Isi dari sisa siap” hanya membantu menyalin batas data server; operator tetap mencocokkan fisiknya.</p></div><Send/></header>
    <Cp6ActionBlocked allowed={actionAllowed} action="pengiriman Laundry" requirement="izin Buat dan Post Laundry"/>
    {!workspace.readiness.laundry_writer_ready ? <div className="clq-warning"><AlertTriangle/><span><strong>Master Laundry belum lengkap.</strong> Lengkapi vendor, proses, dan tarif yang berlaku. Sistem tidak memakai data contoh sebagai pengganti.</span></div> : null}
    <div className="clq-form-grid">
      <label className="wide"><span>BATCH DISTRIBUSI DARI DATA SERVER</span><select aria-label="BATCH DISTRIBUSI AUTHORITATIVE" value={batchId} disabled={actionLocked} onChange={(event) => {
        setBatchId(event.target.value); setQuantities({}); setConfirmed(false)
      }}><option value="">Pilih batch yang fisiknya dikirim…</option>{workspace.ready_batches.map((row) => <option key={row.distribution_batch_id} value={row.distribution_batch_id}>{row.po_number} · {row.group_number} · Batch {row.batch_no} · siap {row.group_unsent_ready_qty_pcs} pcs</option>)}</select></label>
      <label><span>VENDOR LAUNDRY</span><select value={vendorId} disabled={actionLocked} onChange={(event) => { setVendorId(event.target.value); setConfirmed(false) }}><option value="">Pilih vendor…</option>{workspace.lookups.vendors.map((row) => <option key={row.id} value={row.id}>{row.code} · {row.name}</option>)}</select></label>
      <label><span>PROSES CUCI YANG DIMINTA</span><select aria-label="PROSES CUCI TARGET" value={processId} disabled={actionLocked} onChange={(event) => { setProcessId(event.target.value); setConfirmed(false) }}><option value="">Pilih proses…</option>{workspace.lookups.wash_processes.map((row) => <option key={row.id} value={row.id}>{row.code} · {row.name}</option>)}</select></label>
      <label><span>WARNA YANG DIMINTA</span><input aria-label="WARNA TARGET" value={targetColor} disabled={actionLocked} onChange={(event) => { setTargetColor(event.target.value); setConfirmed(false) }} placeholder="Contoh: Navy"/></label>
      <label><span>WAKTU FISIK KELUAR · WIB</span><input aria-label="WAKTU FISIK KELUAR" type="datetime-local" value={physicalAt} disabled={actionLocked} onChange={(event) => { setPhysicalAt(event.target.value); setConfirmed(false) }}/><small>Wajib diisi operator · {CP6_BUSINESS_TIME_LABEL}</small></label>
      <label className="wide"><span>BUKTI / ALASAN SERAH TERIMA</span><input aria-label="ALASAN / BUKTI SERAH TERIMA" value={reason} disabled={actionLocked} onChange={(event) => { setReason(event.target.value); setConfirmed(false) }} placeholder="Contoh: surat jalan diterima dan jumlah dihitung bersama vendor"/></label>
      <label className="wide"><span>INSTRUKSI KHUSUS · OPSIONAL</span><textarea value={notes} disabled={actionLocked} onChange={(event) => setNotes(event.target.value)} placeholder="Catatan proses, warna, atau penanganan khusus"/></label>
    </div>
    {batch ? <div className="clq-line-editor"><header><div><strong>{batch.model_code} · {batch.group_number} · Batch {batch.batch_no}</strong><small>{batch.contractor_name} · Pola {batch.pattern_code ?? 'data lama tidak tercatat'}</small></div><button type="button" disabled={actionLocked} onClick={fillReady}>Isi dari sisa siap</button></header>{batch.sizes.map((row) => <label key={row.size_id}><span><b>Ukuran {row.size_code}</b><small>Dibagi {row.allocated_qty_pcs} · sudah dikirim {row.sent_qty_pcs} · bisa dikirim {row.available_qty_pcs}</small></span><input aria-label={`Qty kirim size ${row.size_code}`} inputMode="numeric" disabled={actionLocked} value={quantities[row.size_id] ?? '0'} onChange={(event) => {
      setQuantities((current) => ({ ...current, [row.size_id]: event.target.value })); setConfirmed(false)
    }}/></label>)}</div> : <div className="clq-empty"><Waves/><strong>Pilih batch yang akan dikirim</strong><small>Pilihan hanya berasal dari pembagian yang sudah tersimpan dan hasil jahit yang tersedia.</small></div>}
    <div className="clq-impact"><ShieldCheck/><span><strong>{total} pcs · tarif {rate ? money(rate.rate_per_pcs) : 'belum tersedia untuk waktu ini'}</strong><small>Perkiraan biaya {rate ? money(total * rate.rate_per_pcs) : 'belum dapat dihitung'}. Saat disimpan, server memperbarui WIP, biaya Laundry, HPP, jurnal, dan laporan sekaligus. Jika satu gagal, semuanya batal.</small></span></div>
    {batch && (invalidQuantity || over || total > batch.group_unsent_ready_qty_pcs) ? <div className="clq-warning"><AlertTriangle/><span>{invalidQuantity ? 'Qty harus bilangan bulat pcs. Input mentah tetap ditampilkan dan tidak diubah diam-diam.' : over ? 'Qty melebihi sisa data server pada salah satu batch/ukuran. Angka tidak diubah diam-diam; koreksi input fisiknya.' : `Qty ${total} melebihi output jahit belum terkirim ${batch.group_unsent_ready_qty_pcs}. Kurangi jumlah; server juga akan menolak.`}</span></div> : null}
    <label className="clq-confirm"><input type="checkbox" checked={confirmed} disabled={actionLocked} onChange={(event) => setConfirmed(event.target.checked)}/><span>Saya sudah mencocokkan vendor, batch, ukuran, jumlah, warna, dan waktu dengan serah-terima fisik.</span></label>
    <footer><button className="primary" aria-label="Post pengiriman atomic" disabled={actionLocked || !valid} onClick={() => {
      if (!batch || !physicalIso) return
      void onAction('POST_DELIVERY', {
        distribution_batch_id: batch.distribution_batch_id, vendor_id: vendorId,
        wash_process_id: processId, target_dyeing_color: targetColor.trim(),
        physical_at: physicalIso, reason: reason.trim(), notes: notes.trim() || null,
        lines: selectedLines,
      }, batch.cutting_group_row_version, () => { setBatchId(''); setQuantities({}); setConfirmed(false) })
    }}><Send/> Catat pengiriman</button></footer>
  </section>
}

function ReturnLaundryForm({ workspace, writerLocked, canPost, onAction }: {
  workspace: LaundryQcWorkspace; writerLocked: boolean; canPost: boolean; onAction: RunAction
}) {
  const candidates = workspace.deliveries.filter((row) => ['SENT', 'PARTIAL_RETURN'].includes(row.status)
    && row.physical_outstanding_qty_pcs > 0 && row.active_claim_qty_pcs === 0)
  const blockedByClaim = workspace.deliveries.filter((row) => ['SENT', 'PARTIAL_RETURN'].includes(row.status)
    && row.physical_outstanding_qty_pcs > 0 && row.active_claim_qty_pcs > 0).length
  const [deliveryId, setDeliveryId] = useState('')
  const [processId, setProcessId] = useState('')
  const [physicalAt, setPhysicalAt] = useState('')
  const [reason, setReason] = useState('')
  const [confirmed, setConfirmed] = useState(false)
  const [good, setGood] = useState<Record<string, string>>({})
  const [bs, setBs] = useState<Record<string, string>>({})
  const [products, setProducts] = useState<Record<string, string>>({})
  useEffect(() => setConfirmed(false), [workspace])
  const actionLocked = writerLocked || !canPost
  const delivery = candidates.find((row) => row.delivery_id === deliveryId) ?? null
  const physicalIso = cp6WibPhysicalTimeToIso(physicalAt)
  const rate = delivery ? findLaundryRateAt(workspace, delivery.vendor_id, processId, physicalIso ?? '') : null
  const lines = delivery?.sizes.map((row) => ({
    delivery_batch_size_line_id: row.delivery_batch_size_line_id,
    qty_good_received: quantity(good[row.delivery_batch_size_line_id] ?? '0'),
    qty_bs_laundry: quantity(bs[row.delivery_batch_size_line_id] ?? '0'),
    bs_product_id: products[row.delivery_batch_size_line_id] || null,
  })).filter((row) => row.qty_good_received + row.qty_bs_laundry > 0) ?? []
  const over = delivery?.sizes.some((row) => {
    const key = row.delivery_batch_size_line_id
    return quantity(good[key] ?? '0') + quantity(bs[key] ?? '0') > row.outstanding_qty_pcs
  }) ?? false
  const invalidQuantity = delivery?.sizes.filter((row) => row.outstanding_qty_pcs > 0).some((row) => {
    const key = row.delivery_batch_size_line_id
    return parseQuantity(good[key] ?? '0') === null || parseQuantity(bs[key] ?? '0') === null
  }) ?? false
  const bsInvalidProduct = lines.some((row) => {
    if (row.qty_bs_laundry <= 0 || !row.bs_product_id || !delivery) return row.qty_bs_laundry > 0
    const source = delivery.sizes.find((item) => item.delivery_batch_size_line_id === row.delivery_batch_size_line_id)
    return !source || !workspace.lookups.products.some((product) => product.id === row.bs_product_id
      && product.model_id === delivery.model_id && product.size_id === source.size_id
      && productEffectiveAt(product, physicalIso ?? ''))
  })
  const total = lines.reduce((sum, row) => sum + row.qty_good_received + row.qty_bs_laundry, 0)
  const valid = Boolean(delivery && canPost && workspace.readiness.laundry_writer_ready && processId
    && physicalIso && rate && total > 0 && !invalidQuantity && !over && !bsInvalidProduct
    && reason.trim().length >= 4 && confirmed)
  const reset = () => { setDeliveryId(''); setGood({}); setBs({}); setProducts({}); setConfirmed(false) }

  return <section className="clq-panel">
    <header><div><span>TERIMA FISIK · LAUNDRY → QC / BS</span><h2>Pisahkan barang Good dan BS per ukuran</h2><p>Barang yang belum kembali tidak dicatat sebagai penerimaan. Sisanya tetap terlihat sebagai barang di luar pabrik dan dapat ditangani dari halaman Barang BS & Rework.</p></div><PackageCheck/></header>
    <Cp6ActionBlocked allowed={canPost} action="penerimaan Laundry" requirement="izin Post Laundry"/>
    {blockedByClaim > 0 ? <div className="clq-warning"><AlertTriangle/><span><strong>{blockedByClaim} pengiriman masih punya klaim STUCK/MISSING aktif.</strong> Batalkan atau tolak klaim melalui alur resmi sebelum mencatat barang yang ternyata kembali.</span></div> : null}
    <div className="clq-form-grid">
      <label className="wide"><span>SURAT KIRIM YANG KEMBALI</span><select aria-label="SURAT KIRIM AKTIF" value={deliveryId} disabled={actionLocked} onChange={(event) => { reset(); setDeliveryId(event.target.value) }}><option value="">Pilih pengiriman yang kembali…</option>{candidates.map((row) => <option key={row.delivery_id} value={row.delivery_id}>{row.delivery_number} · {row.vendor_name} · {row.po_number} · belum kembali {row.physical_outstanding_qty_pcs} pcs</option>)}</select></label>
      <label><span>PROSES CUCI SEBENARNYA</span><select aria-label="PROSES AKTUAL" value={processId} disabled={actionLocked} onChange={(event) => { setProcessId(event.target.value); setConfirmed(false) }}><option value="">Pilih hasil proses…</option>{workspace.lookups.wash_processes.map((row) => <option key={row.id} value={row.id}>{row.code} · {row.name}</option>)}</select></label>
      <label><span>WAKTU FISIK KEMBALI · WIB</span><input aria-label="WAKTU FISIK KEMBALI" type="datetime-local" value={physicalAt} disabled={actionLocked} onChange={(event) => { setPhysicalAt(event.target.value); setConfirmed(false) }}/><small>Wajib diisi operator · {CP6_BUSINESS_TIME_LABEL}</small></label>
      <label className="wide"><span>BUKTI / ALASAN PENERIMAAN</span><input aria-label="ALASAN / BUKTI PENERIMAAN" value={reason} disabled={actionLocked} onChange={(event) => { setReason(event.target.value); setConfirmed(false) }} placeholder="Contoh: jumlah dihitung bersama vendor dan surat jalan cocok"/></label>
    </div>
    {delivery ? <div className="clq-return-editor"><header><div><strong>{delivery.delivery_number} · {delivery.vendor_name}</strong><small>{delivery.model_code} · {delivery.group_number} · Batch {delivery.batch_no}</small></div><em>{delivery.physical_outstanding_qty_pcs} pcs belum kembali</em></header>{delivery.sizes.filter((row) => row.outstanding_qty_pcs > 0).map((row) => {
      const key = row.delivery_batch_size_line_id
      const goodQty = quantity(good[key] ?? '0')
      const bsQty = quantity(bs[key] ?? '0')
      const options = workspace.lookups.products.filter((product) => product.model_id === delivery.model_id
        && product.size_id === row.size_id && productEffectiveAt(product, physicalIso ?? ''))
      return <article key={key}><div><b>Ukuran {row.size_code}</b><small>Dikirim {row.qty_sent_pcs} · sudah kembali {row.good_returned_qty_pcs + row.bs_returned_qty_pcs} · belum kembali {row.outstanding_qty_pcs}</small></div><label><span>GOOD</span><input aria-label={`Good kembali size ${row.size_code}`} inputMode="numeric" disabled={actionLocked} value={good[key] ?? '0'} onChange={(event) => { setGood((current) => ({ ...current, [key]: event.target.value })); setConfirmed(false) }}/></label><label><span>BS LAUNDRY</span><input aria-label={`BS Laundry size ${row.size_code}`} inputMode="numeric" disabled={actionLocked} value={bs[key] ?? '0'} onChange={(event) => { setBs((current) => ({ ...current, [key]: event.target.value })); setConfirmed(false) }}/></label><label className="product"><span>MEREK → NOMOR SKU → MODEL UNTUK BS {bsQty > 0 ? '· WAJIB' : ''}</span><select aria-label={`SKU BS size ${row.size_code}`} value={products[key] ?? ''} disabled={actionLocked || bsQty === 0} onChange={(event) => { setProducts((current) => ({ ...current, [key]: event.target.value })); setConfirmed(false) }}><option value="">Pilih Merek · Nomor SKU · Model…</option>{options.map((product) => <option key={product.id} value={product.id}>{product.brand_name} · {product.sku} · {product.model_name} · {product.color}</option>)}</select></label><strong className={goodQty + bsQty > row.outstanding_qty_pcs ? 'bad' : ''}>Belum kembali {Math.max(0, row.outstanding_qty_pcs - goodQty - bsQty)}</strong></article>
    })}</div> : <div className="clq-empty"><PackageCheck/><strong>Pilih surat kirim yang kembali</strong><small>Penerimaan boleh sebagian; jumlah yang belum kembali tetap tercatat dan tidak ditimpa.</small></div>}
    <div className="clq-impact"><ShieldCheck/><span><strong>{total} pcs kembali · tarif {rate ? money(rate.rate_per_pcs) : 'belum tersedia untuk waktu ini'}</strong><small>Server mengecek tarif lagi, memisahkan Good ke antrean QC dan BS ke kasus BS, lalu memperbarui biaya, HPP, jurnal, dan laporan sekaligus.</small></span></div>
    {invalidQuantity || over || bsInvalidProduct ? <div className="clq-warning"><AlertTriangle/><span>{invalidQuantity ? 'Good dan BS harus bilangan bulat pcs. Input mentah tidak diubah; tombol simpan tetap terkunci.' : over ? 'Good + BS melebihi jumlah yang belum kembali pada salah satu ukuran.' : 'Setiap Laundry-BS wajib punya SKU aktif pada waktu fisik dengan model dan ukuran yang sama.'}</span></div> : null}
    <label className="clq-confirm"><input type="checkbox" checked={confirmed} disabled={actionLocked} onChange={(event) => setConfirmed(event.target.checked)}/><span>Saya sudah menghitung fisik per ukuran; Good dan BS benar, sisanya memang belum kembali.</span></label>
    <footer><button className="primary" aria-label="Post penerimaan atomic" disabled={actionLocked || !valid} onClick={() => {
      if (!delivery || !physicalIso) return
      void onAction('POST_RECEIPT', {
        delivery_id: delivery.delivery_id, wash_process_id: processId,
        physical_at: physicalIso, reason: reason.trim(), lines,
      }, delivery.row_version, reset)
    }}><CheckCircle2/> Catat penerimaan</button></footer>
  </section>
}

type FailedWashCustody = '' | 'RETRY_AT_VENDOR' | 'RETURN_UNPROCESSED'

function FailedWashForm({ workspace, writerLocked, canPost, onAction }: {
  workspace: LaundryQcWorkspace; writerLocked: boolean; canPost: boolean; onAction: RunAction
}) {
  const candidates = workspace.deliveries.filter((row) => ['SENT', 'PARTIAL_RETURN'].includes(row.status)
    && row.physical_outstanding_qty_pcs > 0 && row.active_claim_qty_pcs === 0)
  const [deliveryId, setDeliveryId] = useState('')
  const [processId, setProcessId] = useState('')
  const [custodyOutcome, setCustodyOutcome] = useState<FailedWashCustody>('')
  const [physicalAt, setPhysicalAt] = useState('')
  const [reason, setReason] = useState('')
  const [confirmed, setConfirmed] = useState(false)
  const [quantities, setQuantities] = useState<Record<string, string>>({})
  useEffect(() => setConfirmed(false), [workspace])
  const actionLocked = writerLocked || !canPost
  const delivery = candidates.find((row) => row.delivery_id === deliveryId) ?? null
  const physicalIso = cp6WibPhysicalTimeToIso(physicalAt)
  const rate = delivery ? findLaundryRateAt(workspace, delivery.vendor_id, processId, physicalIso ?? '') : null
  const lines = delivery?.sizes.map((row) => ({
    delivery_batch_size_line_id: row.delivery_batch_size_line_id,
    qty_attempted_pcs: quantity(quantities[row.delivery_batch_size_line_id] ?? '0'),
  })).filter((row) => row.qty_attempted_pcs > 0) ?? []
  const total = lines.reduce((sum, row) => sum + row.qty_attempted_pcs, 0)
  const invalidQuantity = delivery?.sizes.some((row) =>
    parseQuantity(quantities[row.delivery_batch_size_line_id] ?? '0') === null) ?? false
  const over = delivery?.sizes.some((row) =>
    quantity(quantities[row.delivery_batch_size_line_id] ?? '0') > row.outstanding_qty_pcs) ?? false
  const fullReturnEligible = Boolean(delivery && delivery.status === 'SENT'
    && delivery.returned_qty_pcs === 0 && delivery.physical_outstanding_qty_pcs === delivery.qty_sent_pcs)
  const fullReturnExact = Boolean(delivery && lines.length === delivery.sizes.length
    && delivery.sizes.every((row) => quantity(quantities[row.delivery_batch_size_line_id] ?? '0') === row.qty_sent_pcs))
  const valid = Boolean(delivery && canPost && workspace.readiness.laundry_writer_ready
    && processId && custodyOutcome && physicalIso && rate && total > 0 && !invalidQuantity && !over
    && (custodyOutcome !== 'RETURN_UNPROCESSED' || fullReturnEligible && fullReturnExact)
    && reason.trim().length >= 4 && confirmed)
  const reset = () => {
    setDeliveryId(''); setProcessId(''); setCustodyOutcome(''); setPhysicalAt('')
    setReason(''); setQuantities({}); setConfirmed(false)
  }
  const fillOutstanding = () => {
    if (!delivery) return
    setQuantities(Object.fromEntries(delivery.sizes.map((row) => [
      row.delivery_batch_size_line_id,
      String(custodyOutcome === 'RETURN_UNPROCESSED' ? row.qty_sent_pcs : row.outstanding_qty_pcs),
    ])))
    setConfirmed(false)
  }

  return <section className="clq-panel">
    <header><div><span>JASA GAGAL CUCI · BIAYA TANPA GOOD / BS PALSU</span><h2>Catat attempt yang benar-benar ditagih vendor</h2><p>Pakai hanya bila vendor memang berhak menagih jasa yang gagal. Sistem menyimpan biaya attempt tanpa memalsukan penerimaan barang.</p></div><AlertTriangle/></header>
    <Cp6ActionBlocked allowed={canPost} action="jasa gagal cuci berbayar" requirement="izin Post Laundry"/>
    <div className="clq-form-grid">
      <label className="wide"><span>SURAT KIRIM YANG MENGALAMI GAGAL CUCI</span><select aria-label="SURAT KIRIM GAGAL CUCI" value={deliveryId} disabled={actionLocked} onChange={(event) => {
        setDeliveryId(event.target.value); setCustodyOutcome(''); setQuantities({}); setConfirmed(false)
      }}><option value="">Pilih pengiriman aktif…</option>{candidates.map((row) => <option key={row.delivery_id} value={row.delivery_id}>{row.delivery_number} · {row.vendor_name} · {row.po_number} · di vendor {row.physical_outstanding_qty_pcs} pcs</option>)}</select></label>
      <label><span>PROSES YANG GAGAL TETAPI DITAGIH</span><select aria-label="PROSES GAGAL CUCI" value={processId} disabled={actionLocked} onChange={(event) => { setProcessId(event.target.value); setConfirmed(false) }}><option value="">Pilih proses/tagihan…</option>{workspace.lookups.wash_processes.map((row) => <option key={row.id} value={row.id}>{row.code} · {row.name}</option>)}</select></label>
      <label><span>POSISI FISIK SETELAH KEJADIAN</span><select aria-label="POSISI FISIK GAGAL CUCI" value={custodyOutcome} disabled={actionLocked || !delivery} onChange={(event) => {
        const next = event.target.value as FailedWashCustody
        setCustodyOutcome(next)
        setQuantities(next === 'RETURN_UNPROCESSED' && delivery
          ? Object.fromEntries(delivery.sizes.map((row) => [row.delivery_batch_size_line_id, String(row.qty_sent_pcs)]))
          : {})
        setConfirmed(false)
      }}><option value="">Pilih posisi fisik…</option><option value="RETRY_AT_VENDOR">Tetap di vendor untuk dicoba lagi</option><option value="RETURN_UNPROCESSED" disabled={!fullReturnEligible}>Seluruh pengiriman kembali tanpa diproses</option></select></label>
      <label><span>WAKTU KEJADIAN FISIK · WIB</span><input aria-label="WAKTU GAGAL CUCI" type="datetime-local" value={physicalAt} disabled={actionLocked} onChange={(event) => { setPhysicalAt(event.target.value); setConfirmed(false) }}/><small>Wajib diisi operator · {CP6_BUSINESS_TIME_LABEL}</small></label>
      <label className="wide"><span>BUKTI / ALASAN TAGIHAN</span><input aria-label="ALASAN TAGIHAN GAGAL CUCI" value={reason} disabled={actionLocked} onChange={(event) => { setReason(event.target.value); setConfirmed(false) }} placeholder="Contoh: kimia habis setelah proses dimulai; vendor menagih satu attempt"/></label>
    </div>
    {delivery ? <div className="clq-line-editor"><header><div><strong>{delivery.delivery_number} · {delivery.vendor_name}</strong><small>{delivery.model_code} · {delivery.group_number} · Batch {delivery.batch_no}</small></div><button type="button" disabled={actionLocked || !custodyOutcome} onClick={fillOutstanding}>{custodyOutcome === 'RETURN_UNPROCESSED' ? 'Isi seluruh kiriman' : 'Isi seluruh yang di vendor'}</button></header>{delivery.sizes.filter((row) => row.outstanding_qty_pcs > 0).map((row) => <label key={row.delivery_batch_size_line_id}><span><b>Ukuran {row.size_code}</b><small>Dikirim {row.qty_sent_pcs} · masih di vendor {row.outstanding_qty_pcs}</small></span><input aria-label={`Qty gagal cuci size ${row.size_code}`} inputMode="numeric" disabled={actionLocked || custodyOutcome === 'RETURN_UNPROCESSED'} value={quantities[row.delivery_batch_size_line_id] ?? '0'} onChange={(event) => {
      setQuantities((current) => ({ ...current, [row.delivery_batch_size_line_id]: event.target.value })); setConfirmed(false)
    }}/></label>)}</div> : <div className="clq-empty"><Waves/><strong>Pilih pengiriman yang gagal dicuci</strong><small>Jumlah dimulai dari nol dan tidak pernah diturunkan otomatis agar input fisik tidak berubah diam-diam.</small></div>}
    <div className="clq-impact"><ShieldCheck/><span><strong>{total} pcs attempt · {rate ? `${money(rate.rate_per_pcs)}/pcs · biaya ${money(total * rate.rate_per_pcs)}` : 'tarif authoritative belum cocok'}</strong><small>{custodyOutcome === 'RETRY_AT_VENDOR' ? 'Fisik tetap tercatat di Laundry. Attempt berikutnya boleh menjadi biaya kedua hanya bila benar-benar terjadi.' : custodyOutcome === 'RETURN_UNPROCESSED' ? 'Seluruh fisik kembali ke Jahit. Pengiriman lama ditutup append-only dan kirim ulang wajib menjadi dokumen baru.' : 'Pilih posisi fisik; biaya dan custody tidak boleh diasumsikan.'}</small></span></div>
    {invalidQuantity || over || custodyOutcome === 'RETURN_UNPROCESSED' && (!fullReturnEligible || !fullReturnExact) ? <div className="clq-warning"><AlertTriangle/><span>{invalidQuantity ? 'Qty attempt harus bilangan bulat pcs; input tidak diubah diam-diam.' : over ? 'Qty attempt melebihi fisik yang masih berada pada vendor.' : 'Kembali tanpa diproses wajib seluruh pengiriman asli, per ukuran, tanpa penerimaan parsial sebelumnya. Gunakan alur penerimaan biasa untuk barang yang hanya kembali sebagian.'}</span></div> : null}
    <label className="clq-confirm"><input type="checkbox" checked={confirmed} disabled={actionLocked} onChange={(event) => setConfirmed(event.target.checked)}/><span>Saya sudah mencocokkan bukti tagihan, proses, jumlah per ukuran, waktu, dan posisi fisik. Tidak ada Good atau BS yang diterima dari attempt ini.</span></label>
    <footer><button className="primary" aria-label="Post jasa gagal cuci atomic" disabled={actionLocked || !valid} onClick={() => {
      if (!delivery || !physicalIso || !custodyOutcome) return
      void onAction('POST_FAILED_WASH', {
        delivery_id: delivery.delivery_id, wash_process_id: processId,
        custody_outcome: custodyOutcome, physical_at: physicalIso,
        reason: reason.trim(), lines,
      }, delivery.row_version, reset)
    }}><ShieldCheck/> Catat attempt berbayar</button></footer>
  </section>
}

function LaundryHistory({ workspace, writerLocked, canReverse, onAction }: {
  workspace: LaundryQcWorkspace; writerLocked: boolean; canReverse: boolean; onAction: RunAction
}) {
  const [reasons, setReasons] = useState<Record<string, string>>({})
  const setReason = (key: string, value: string) => setReasons((current) => ({ ...current, [key]: value }))
  return <section className="clq-history">
    <header><History/><div><span>RIWAYAT TRANSAKSI</span><h2>Dokumen tidak dihapus; kesalahan dibalik dengan catatan baru</h2></div></header>
    <Cp6ActionBlocked allowed={canReverse} action="koreksi riwayat Laundry" requirement="izin Reverse Laundry"/>
    {workspace.deliveries.length === 0 ? <div className="clq-empty"><History/><strong>Belum ada pengiriman CP6</strong><small>Data lama yang belum punya hubungan lengkap tetap dipisahkan dan tidak ditebak.</small></div> : workspace.deliveries.map((delivery) => <article key={delivery.delivery_id}>
      <header><div><small>{formatCp6WibDateTime(delivery.physical_at)} · versi {delivery.row_version}</small><strong>{delivery.delivery_number} · {delivery.vendor_name}</strong><span>{delivery.po_number} · {delivery.group_number} · Batch {delivery.batch_no} · {delivery.qty_sent_pcs} pcs</span></div><em>{delivery.returned_unprocessed_qty_pcs > 0 ? 'Kembali tanpa proses' : status(delivery.status)}</em></header>
      <div className="clq-history-facts"><span><small>GOOD / BS KEMBALI</small><b>{delivery.returned_qty_pcs}</b></span><span><small>KEMBALI TANPA PROSES</small><b>{delivery.returned_unprocessed_qty_pcs}</b></span><span><small>MASIH DI VENDOR</small><b>{delivery.physical_outstanding_qty_pcs}</b></span><span><small>KLAIM AKTIF</small><b>{delivery.active_claim_qty_pcs}</b></span><span><small>TARIF SAAT DIKIRIM</small><b>{money(delivery.estimated_rate_snapshot)}</b></span></div>
      {delivery.receipts.map((receipt) => {
        const failedAttempt = receipt.event_kind === 'FAILED_WASH_ATTEMPT'
        const custody = receipt.custody_outcome === 'RETURN_UNPROCESSED'
          ? 'seluruh fisik kembali tanpa diproses' : 'fisik tetap di vendor'
        return <div className="clq-reversal" key={receipt.id}><span><small>{receipt.number} · versi {receipt.row_version}</small><strong>{failedAttempt ? `Cuci gagal berbayar · ${custody}` : 'Penerimaan fisik'} · {status(receipt.status)} · {formatCp6WibDateTime(receipt.physical_at)}</strong>{failedAttempt ? <small>{receipt.attempted_qty_pcs} pcs · {receipt.process_name} · tarif {receipt.actual_rate === null ? 'tidak ada' : money(receipt.actual_rate)} · biaya {receipt.actual_cost === null ? 'tidak ada' : money(receipt.actual_cost)}</small> : null}<small>{receipt.reversal_blocker ?? (failedAttempt && receipt.custody_outcome === 'RETURN_UNPROCESSED' ? 'Biaya dapat dibalik; fakta fisik kembali tetap dipertahankan.' : 'Siap dibalik secara authoritative.')}</small></span><input aria-label={`Alasan reversal ${receipt.number}`} value={reasons[receipt.id] ?? ''} disabled={writerLocked || !canReverse || !receipt.reversible} onChange={(event) => setReason(receipt.id, event.target.value)} placeholder="Alasan pembatalan · wajib"/><button disabled={writerLocked || !canReverse || !receipt.reversible || (reasons[receipt.id] ?? '').trim().length < 4} onClick={() => void onAction('REVERSE_RECEIPT', { receipt_id: receipt.id, reason: reasons[receipt.id].trim() }, receipt.row_version, () => setReason(receipt.id, ''))}><Undo2/> {failedAttempt ? 'Batalkan biaya attempt' : 'Batalkan penerimaan'}</button></div>
      })}
      <div className="clq-reversal"><span><small>{delivery.returned_unprocessed_qty_pcs > 0 ? 'FAKTA FISIK SUDAH DIKEMBALIKAN' : 'GAGAL CUCI TANPA TAGIHAN'}</small><strong>{delivery.returned_unprocessed_qty_pcs > 0 ? 'Histori pengiriman lama tetap disimpan; kirim ulang dengan dokumen baru' : 'Batalkan surat kirim, lalu buat pengiriman baru'}</strong><small>{delivery.reversal_blocker ?? 'Siap dibalik secara authoritative.'}</small></span><input aria-label={`Alasan reversal ${delivery.delivery_number}`} value={reasons[delivery.delivery_id] ?? ''} disabled={writerLocked || !canReverse || !delivery.reversible} onChange={(event) => setReason(delivery.delivery_id, event.target.value)} placeholder="Bukti seluruh barang kembali"/><button disabled={writerLocked || !canReverse || !delivery.reversible || (reasons[delivery.delivery_id] ?? '').trim().length < 4} onClick={() => void onAction('REVERSE_DELIVERY', { delivery_id: delivery.delivery_id, reason: reasons[delivery.delivery_id].trim() }, delivery.row_version, () => setReason(delivery.delivery_id, ''))}><RotateCcw/> Batalkan pengiriman</button></div>
    </article>)}
  </section>
}

export default function ConnectedLaundryPage() {
  const { identity } = useAuth()
  const access = identity.status === 'AUTHORIZED' ? identity : null
  const canCreate = hasPermission(access, 'production.laundry.create')
  const canPost = hasPermission(access, SENSITIVE_ACTION_PERMISSION.postLaundry)
  const canReverse = hasPermission(access, SENSITIVE_ACTION_PERMISSION.reverseLaundry)
  const roleName = identity.status === 'AUTHORIZED' ? identity.profile.roleName : 'Tanpa role'
  const bridge = useLaundryQcWorkspace('LAUNDRY')
  const collectionTruncated = Boolean(bridge.workspace && (
    bridge.workspace.collection_window.ready_batches_truncated
    || bridge.workspace.collection_window.deliveries_truncated
  ))
  const [tab, setTab] = useState<'SEND' | 'RETURN' | 'FAILED' | 'HISTORY'>('SEND')
  const kpis = useMemo(() => ({
    ready: bridge.workspace ? totalReadyToSend(bridge.workspace.ready_batches) : 0,
    outside: bridge.workspace?.deliveries.reduce((sum, row) => sum + row.physical_outstanding_qty_pcs, 0) ?? 0,
    claims: bridge.workspace?.deliveries.reduce((sum, row) => sum + row.active_claim_qty_pcs, 0) ?? 0,
  }), [bridge.workspace])
  const onAction: RunAction = bridge.runAction

  useEffect(() => {
    if (bridge.committedSequence > 0 && !bridge.workspaceStale) {
      bridge.acknowledgeCommittedFormRetired(bridge.committedSequence)
    }
  }, [bridge.acknowledgeCommittedFormRetired, bridge.committedSequence, bridge.workspaceStale])

  return <div className="connected-laundry-qc-page">
    <section className="clq-hero"><div><span>CP6 · DATA RESMI LAUNDRY</span><h1>Laundry</h1><p>Catat barang yang benar-benar keluar dan kembali per batch serta ukuran. WIP dan biaya hanya berubah setelah transaksi lengkap diterima server.</p></div><div><button disabled={bridge.loading || Boolean(bridge.pending) || bridge.corruptedEnvelope} onClick={() => void bridge.load()}><RefreshCw/> Muat ulang data</button></div></section>
    <div className="clq-boundary"><ShieldCheck/><span><strong>Reliable data adalah dewa.</strong> Laporan, stok, dan HPP adalah raja: server menyimpan semuanya bersamaan atau membatalkan semuanya.</span></div>
    <Cp6PermissionNotice roleName={roleName} capabilities={[
      { label: 'Kirim Laundry', allowed: canCreate && canPost, requirement: 'Buat + Post Laundry' },
      { label: 'Terima Laundry', allowed: canPost, requirement: 'Post Laundry' },
      { label: 'Gagal cuci berbayar', allowed: canPost, requirement: 'Post Laundry' },
      { label: 'Koreksi riwayat', allowed: canReverse, requirement: 'Reverse Laundry' },
    ]}/>
    {bridge.error ? <div className="clq-alert error"><AlertTriangle/><span>{bridge.error}</span>{bridge.pending && !bridge.corruptedEnvelope ? <button aria-label="Reconcile UUID lama" onClick={() => void bridge.reconcile()} disabled={bridge.busy}><RefreshCw/> Cek status transaksi</button> : bridge.committedRefreshRequired || bridge.workspaceStale && !bridge.corruptedEnvelope ? <button onClick={() => void bridge.load()} disabled={bridge.busy}><RefreshCw/> Refetch</button> : null}</div> : null}
    {bridge.notice ? <div className="clq-alert notice"><CheckCircle2/><span>{bridge.notice}</span></div> : null}
    {collectionTruncated ? <div className="clq-warning" role="status"><AlertTriangle/><span><strong>Daftar server dibatasi agar halaman tetap stabil.</strong> Hasil yang tampil bukan seluruh histori. Persempit kata kunci pada kolom Cari sampai peringatan ini hilang sebelum menyimpulkan transaksi tidak ada.</span></div> : null}
    {bridge.busy ? <div className="clq-busy"><LoaderCircle className="spin"/> Menjaga transaksi tetap satu kali…</div> : null}
    <section className="clq-kpis"><article><span>SIAP DIKIRIM</span><strong>{kpis.ready}</strong><small>pcs selesai jahit, belum dikirim</small></article><article><span>DI LUAR PABRIK</span><strong>{kpis.outside}</strong><small>pcs belum kembali</small></article><article><span>TERIKAT KLAIM</span><strong>{kpis.claims}</strong><small>Stuck/Missing aktif</small></article><article><span>DATA LAMA TERPISAH</span><strong>{bridge.workspace?.legacy_unlinked.delivery_count ?? 0}</strong><small>tidak ditebak atau digabung</small></article></section>
    <nav className="clq-tabs"><button className={tab === 'SEND' ? 'active' : ''} onClick={() => setTab('SEND')}>Kirim ke Laundry</button><button className={tab === 'RETURN' ? 'active' : ''} onClick={() => setTab('RETURN')}>Terima kembali</button><button className={tab === 'FAILED' ? 'active' : ''} onClick={() => setTab('FAILED')}>Cuci gagal berbayar</button><button className={tab === 'HISTORY' ? 'active' : ''} onClick={() => setTab('HISTORY')}>Riwayat & koreksi</button><label><Search/><input value={bridge.query} onChange={(event) => bridge.search(event.target.value)} placeholder="Cari PO, Potongan, atau vendor…"/></label></nav>
    {bridge.loading && !bridge.workspace ? <div className="clq-loading"><LoaderCircle className="spin"/> Memuat data resmi…</div> : bridge.workspace ? <>
      {tab === 'SEND' ? <SendLaundryForm key={`send-${bridge.committedSequence}`} workspace={bridge.workspace} writerLocked={bridge.writerLocked} canCreate={canCreate} canPost={canPost} onAction={onAction}/> : null}
      {tab === 'RETURN' ? <ReturnLaundryForm key={`return-${bridge.committedSequence}`} workspace={bridge.workspace} writerLocked={bridge.writerLocked} canPost={canPost} onAction={onAction}/> : null}
      {tab === 'FAILED' ? <FailedWashForm key={`failed-${bridge.committedSequence}`} workspace={bridge.workspace} writerLocked={bridge.writerLocked} canPost={canPost} onAction={onAction}/> : null}
      {tab === 'HISTORY' ? <LaundryHistory workspace={bridge.workspace} writerLocked={bridge.writerLocked} canReverse={canReverse} onAction={onAction}/> : null}
    </> : <div className="clq-loading"><AlertTriangle/> Data belum tersedia; semua tombol transaksi tetap terkunci.</div>}
    <section className="clq-rare-case"><AlertTriangle/><div><strong>Jangan campur dua kejadian cuci gagal.</strong><p>Tanpa tagihan: batalkan surat kirim setelah seluruh fisik kembali. Dengan tagihan: gunakan “Cuci gagal berbayar”; setiap attempt punya biaya sendiri, sementara posisi fisik tetap dicatat terpisah dan tidak pernah dibuat menjadi Good/BS palsu.</p></div></section>
  </div>
}
