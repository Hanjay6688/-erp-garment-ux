import { useEffect, useMemo, useState } from 'react'
import {
  AlertTriangle, CheckCircle2, ClipboardCheck, History, LoaderCircle, PackageCheck,
  RefreshCw, Search, ShieldCheck, Undo2,
} from 'lucide-react'
import { useAuth } from './auth/AuthProvider'
import { SENSITIVE_ACTION_PERMISSION, hasPermission } from './auth/accessCatalog'
import { Cp6ActionBlocked, Cp6PermissionNotice } from './Cp6PermissionNotice'
import { CP6_BUSINESS_TIME_LABEL, cp6WibPhysicalTimeToIso, formatCp6WibDateTime } from './cp6BusinessTime'
import { productEffectiveAt, type Cp6QcQueueRow, type LaundryQcWorkspace } from './laundryQcModel'
import { useLaundryQcWorkspace } from './useLaundryQcWorkspace'
import type { Json } from './types/database.preconnect'
import './connected-laundry-qc.css'

type RunAction = (
  action: 'POST_FINAL_SKU' | 'REVERSE_FINAL_SKU', payload: Json,
  expectedVersion: number | null, retireCommittedForm: () => void,
) => Promise<boolean>

const parseQuantity = (value: string) => {
  if (!value.trim()) return 0
  const parsed = Number(value)
  return /^\d+$/.test(value.trim()) && Number.isSafeInteger(parsed)
    ? parsed
    : null
}
const quantity = (value: string) => parseQuantity(value) ?? 0
const statusLabel: Record<string, string> = {
  READY_FOR_QC: 'Siap QC', PARTIAL: 'Sebagian selesai', COMPLETE: 'Selesai',
  POSTED: 'Tersimpan', REVERSED: 'Dibatalkan',
}
const status = (value: string) => statusLabel[value] ?? value.replaceAll('_', ' ')

type QueueGroup = {
  id: string; poNumber: string; groupNumber: string; modelCode: string; modelName: string
  rowVersion: number; remaining: number; completionStatus: string; rows: Cp6QcQueueRow[]
}

function groupQueue(rows: Cp6QcQueueRow[]): QueueGroup[] {
  const groups = new Map<string, QueueGroup>()
  rows.forEach((row) => {
    const existing = groups.get(row.cutting_group_id)
    if (existing) {
      if (existing.rowVersion !== row.cutting_group_row_version || existing.poNumber !== row.po_number) {
        throw new Error('Antrean QC memuat versi Potongan yang tidak konsisten.')
      }
      existing.rows.push(row)
      return
    }
    groups.set(row.cutting_group_id, {
      id: row.cutting_group_id, poNumber: row.po_number, groupNumber: row.group_number,
      modelCode: row.model_code, modelName: row.model_name,
      rowVersion: row.cutting_group_row_version, remaining: row.remaining_qc_qty_pcs,
      completionStatus: row.completion_status, rows: [row],
    })
  })
  return [...groups.values()]
}

function FinalSkuForm({ workspace, writerLocked, canPost, onAction }: {
  workspace: LaundryQcWorkspace; writerLocked: boolean; canPost: boolean; onAction: RunAction
}) {
  const groups = useMemo(() => groupQueue(workspace.qc_queue), [workspace.qc_queue])
  const [groupId, setGroupId] = useState('')
  const [locationId, setLocationId] = useState('')
  const [physicalAt, setPhysicalAt] = useState('')
  const [reason, setReason] = useState('')
  const [confirmed, setConfirmed] = useState(false)
  const [good, setGood] = useState<Record<string, string>>({})
  const [bs, setBs] = useState<Record<string, string>>({})
  const [products, setProducts] = useState<Record<string, string>>({})
  useEffect(() => setConfirmed(false), [workspace])
  const actionLocked = writerLocked || !canPost
  const group = groups.find((row) => row.id === groupId) ?? null
  const physicalIso = cp6WibPhysicalTimeToIso(physicalAt)
  const lines = group?.rows.map((row) => ({
    final_product_id: products[row.source_batch_size_line_id] || null,
    qty_good_pcs: quantity(good[row.source_batch_size_line_id] ?? '0'),
    qty_bs_pcs: quantity(bs[row.source_batch_size_line_id] ?? '0'),
    source_laundry_receipt_line_id: row.receipt_line_id,
    source_laundry_receipt_batch_size_line_id: row.source_batch_size_line_id,
    notes: `CP6 ${row.receipt_number} · batch ${row.batch_no} · size ${row.size_code}`,
  })).filter((row) => row.qty_good_pcs + row.qty_bs_pcs > 0) ?? []
  const selected = lines.reduce((sum, row) => sum + row.qty_good_pcs + row.qty_bs_pcs, 0)
  const declaredGood = lines.reduce((sum, row) => sum + row.qty_good_pcs, 0)
  const declaredBs = lines.reduce((sum, row) => sum + row.qty_bs_pcs, 0)
  const allReady = group?.rows.reduce((sum, row) => sum + row.available_for_qc_qty_pcs, 0) ?? 0
  const over = group?.rows.some((row) => {
    const key = row.source_batch_size_line_id
    return quantity(good[key] ?? '0')
      + quantity(bs[key] ?? '0') > row.available_for_qc_qty_pcs
  }) ?? false
  const invalidQuantity = group?.rows.some((row) => {
    const key = row.source_batch_size_line_id
    return parseQuantity(good[key] ?? '0') === null || parseQuantity(bs[key] ?? '0') === null
  }) ?? false
  const invalidProduct = lines.some((line) => {
    const source = group?.rows.find((row) => row.source_batch_size_line_id === line.source_laundry_receipt_batch_size_line_id)
    return !source || !line.final_product_id || !workspace.lookups.products.some((product) =>
      product.id === line.final_product_id && product.model_id === source.model_id
      && product.size_id === source.size_id && productEffectiveAt(product, physicalIso ?? ''))
  })
  const sourceAfterPhysical = group?.rows.some((row) => {
    const isSelected = lines.some((line) => line.source_laundry_receipt_batch_size_line_id === row.source_batch_size_line_id)
    return Boolean(isSelected && physicalIso
      && new Date(row.receipt_physical_at).getTime() > new Date(physicalIso).getTime())
  }) ?? false
  const valid = Boolean(group && workspace.readiness.qc_writer_ready && canPost && locationId && physicalIso
    && selected > 0 && !invalidQuantity && !over && !invalidProduct && !sourceAfterPhysical
    && reason.trim().length >= 4 && confirmed)
  const reset = () => { setGroupId(''); setGood({}); setBs({}); setProducts({}); setConfirmed(false) }
  const fillAllGood = () => {
    if (!group) return
    setGood(Object.fromEntries(group.rows.map((row) => [row.source_batch_size_line_id, String(row.available_for_qc_qty_pcs)])))
    setBs({}); setConfirmed(false)
  }

  return <section className="clq-panel">
    <header><div><span>QC → FINAL SKU / BS</span><h2>Tentukan hasil fisik dan SKU per ukuran</h2><p>Jumlah dimulai dari nol. Good menambah stok barang jadi; BS membuka kasus BS. Keduanya disimpan server dalam satu transaksi.</p></div><ClipboardCheck/></header>
    <Cp6ActionBlocked allowed={canPost} action="finalisasi QC" requirement="izin Post Final SKU"/>
    {!workspace.readiness.qc_writer_ready ? <div className="clq-warning"><AlertTriangle/><span><strong>Master Final SKU atau lokasi FG belum lengkap.</strong> Tombol simpan tetap mati; sistem tidak memakai katalog contoh.</span></div> : null}
    <div className="clq-form-grid">
      <label className="wide"><span>POTONGAN DENGAN GOOD LAUNDRY SIAP QC</span><select value={groupId} disabled={actionLocked} onChange={(event) => { reset(); setGroupId(event.target.value) }}><option value="">Pilih Potongan…</option>{groups.map((row) => <option key={row.id} value={row.id}>{row.poNumber} · {row.groupNumber} · {row.modelCode} · siap {row.rows.reduce((sum, item) => sum + item.available_for_qc_qty_pcs, 0)} pcs</option>)}</select></label>
      <label><span>GUDANG BARANG JADI TUJUAN</span><select aria-label="LOKASI FG TUJUAN" value={locationId} disabled={actionLocked} onChange={(event) => { setLocationId(event.target.value); setConfirmed(false) }}><option value="">Pilih gudang FG…</option>{workspace.lookups.fg_locations.map((row) => <option key={row.id} value={row.id}>{row.code} · {row.name}</option>)}</select></label>
      <label><span>WAKTU FISIK QC · WIB</span><input aria-label="WAKTU FISIK QC" type="datetime-local" value={physicalAt} disabled={actionLocked} onChange={(event) => { setPhysicalAt(event.target.value); setConfirmed(false) }}/><small>Wajib diisi operator · {CP6_BUSINESS_TIME_LABEL}</small></label>
      <label className="wide"><span>BUKTI / ALASAN HASIL QC</span><input aria-label="ALASAN / BUKTI HASIL QC" value={reason} disabled={actionLocked} onChange={(event) => { setReason(event.target.value); setConfirmed(false) }} placeholder="Contoh: hitung fisik dan label SKU sudah cocok"/></label>
    </div>
    {group ? <div className="clq-qc-editor"><header><div><strong>{group.modelCode} · {group.groupNumber}</strong><small>{group.poNumber} · {status(group.completionStatus)} · belum selesai {group.remaining} pcs</small></div><button type="button" disabled={actionLocked} onClick={fillAllGood}>Isi semua sebagai Good</button></header>{group.rows.map((row) => {
      const key = row.source_batch_size_line_id
      const goodQty = quantity(good[key] ?? '0')
      const bsQty = quantity(bs[key] ?? '0')
      const productOptions = workspace.lookups.products.filter((product) => product.model_id === row.model_id
        && product.size_id === row.size_id && productEffectiveAt(product, physicalIso ?? ''))
      return <article key={key}><div><b>Batch {row.batch_no} · Ukuran {row.size_code}</b><small>{row.receipt_number} · {row.vendor_name}</small><small>Good diterima {row.qty_good_received} · sudah QC {row.qc_accounted_qty_pcs} · tersedia {row.available_for_qc_qty_pcs}</small></div><label><span>GOOD FINAL</span><input aria-label={`Good final size ${row.size_code}`} inputMode="numeric" disabled={actionLocked} value={good[key] ?? '0'} onChange={(event) => { setGood((current) => ({ ...current, [key]: event.target.value })); setConfirmed(false) }}/></label><label><span>BS QC</span><input aria-label={`BS QC size ${row.size_code}`} inputMode="numeric" disabled={actionLocked} value={bs[key] ?? '0'} onChange={(event) => { setBs((current) => ({ ...current, [key]: event.target.value })); setConfirmed(false) }}/></label><label className="product"><span>MEREK → NOMOR SKU → MODEL {goodQty + bsQty > 0 ? '· WAJIB' : ''}</span><select aria-label={`Final SKU size ${row.size_code}`} value={products[key] ?? ''} disabled={actionLocked || goodQty + bsQty === 0} onChange={(event) => { setProducts((current) => ({ ...current, [key]: event.target.value })); setConfirmed(false) }}><option value="">Pilih Merek · Nomor SKU · Model…</option>{productOptions.map((product) => <option key={product.id} value={product.id}>{product.brand_name} · {product.sku} · {product.model_name} · {product.color}</option>)}</select></label><strong className={goodQty + bsQty > row.available_for_qc_qty_pcs ? 'bad' : ''}>Sisa {Math.max(0, row.available_for_qc_qty_pcs - goodQty - bsQty)}</strong></article>
    })}</div> : <div className="clq-empty"><PackageCheck/><strong>Pilih Potongan yang akan difinalkan</strong><small>Sumber hanya Good Laundry yang sudah tersimpan dan belum pernah dipakai QC.</small></div>}
    <div className="clq-impact"><ShieldCheck/><span><strong>Good {declaredGood} · BS {declaredBs} · dipilih {selected} dari {allReady} pcs</strong><small>{selected > 0 && selected === allReady ? 'Semua barang siap dipilih.' : 'Sebagian barang siap dipilih.'} Server membuat lot FG, stok, kasus BS, reimbursement, HPP, jurnal, dan laporan sekaligus.</small></span></div>
    {invalidQuantity || over || invalidProduct || sourceAfterPhysical ? <div className="clq-warning"><AlertTriangle/><span>{invalidQuantity ? 'Good dan BS harus bilangan bulat pcs. Input mentah tidak diubah; tombol simpan tetap terkunci.' : over ? 'Good + BS melebihi jumlah yang tersedia pada sumber penerimaan, batch, atau ukuran.' : invalidProduct ? 'Setiap baris yang dipilih wajib punya Final SKU aktif dengan model dan ukuran yang cocok pada waktu fisik.' : 'Waktu QC tidak boleh lebih awal dari penerimaan Laundry sumber.'}</span></div> : null}
    <label className="clq-confirm"><input type="checkbox" checked={confirmed} disabled={actionLocked} onChange={(event) => setConfirmed(event.target.checked)}/><span>Saya sudah mencocokkan hasil QC fisik, ukuran, Merek/Nomor SKU/Model, jumlah Good/BS, lokasi, dan waktu.</span></label>
    <footer><button className="primary" aria-label="Post QC + Final SKU atomic" disabled={actionLocked || !valid} onClick={() => {
      if (!group || !physicalIso) return
      void onAction('POST_FINAL_SKU', {
        cutting_group_id: group.id, destination_location_id: locationId,
        physical_at: physicalIso, reason: reason.trim(), good_qty_pcs: declaredGood,
        completion_mode: selected === allReady ? 'ALL_READY' : 'PARTIAL_SELECTION', lines,
      }, group.rowVersion, reset)
    }}><CheckCircle2/> Simpan hasil QC & Final SKU</button></footer>
  </section>
}

function QcHistory({ workspace, writerLocked, canReverse, onAction }: {
  workspace: LaundryQcWorkspace; writerLocked: boolean; canReverse: boolean; onAction: RunAction
}) {
  const [reasons, setReasons] = useState<Record<string, string>>({})
  return <section className="clq-history">
    <header><History/><div><span>RIWAYAT FINAL SKU</span><h2>Stok dan HPP tidak diedit; koreksi membuat catatan pembalik</h2></div></header>
    <Cp6ActionBlocked allowed={canReverse} action="koreksi Final SKU" requirement="izin Reverse Final SKU"/>
    {workspace.qc_history.length === 0 ? <div className="clq-empty"><History/><strong>Belum ada finalisasi CP6</strong><small>QC lama yang belum punya hubungan lengkap tetap dipisahkan dan tidak ditebak.</small></div> : workspace.qc_history.map((row) => <article key={row.qc_inspection_id}><header><div><small>{formatCp6WibDateTime(row.physical_at)} · versi {row.row_version}</small><strong>{row.inspection_number} · {row.po_number}</strong><span>{row.location_name} · Good {row.good_qty_pcs} · BS {row.bs_qty_pcs}</span></div><em>{status(row.status)}</em></header><div className="clq-reversal"><span><small>KOREKSI TRANSAKSI TERSIMPAN</small><strong>Membalik stok, reimbursement, HPP, jurnal, dan laporan sebagai riwayat baru</strong><small>{row.reversal_blocker ?? 'Siap dibalik secara authoritative.'}</small></span><input aria-label={`Alasan reversal ${row.inspection_number}`} value={reasons[row.qc_inspection_id] ?? ''} disabled={writerLocked || !canReverse || !row.reversible} onChange={(event) => setReasons((current) => ({ ...current, [row.qc_inspection_id]: event.target.value }))} placeholder="Alasan pembatalan · wajib"/><button disabled={writerLocked || !canReverse || !row.reversible || (reasons[row.qc_inspection_id] ?? '').trim().length < 4} onClick={() => void onAction('REVERSE_FINAL_SKU', { qc_inspection_id: row.qc_inspection_id, reason: reasons[row.qc_inspection_id].trim() }, row.row_version, () => setReasons((current) => ({ ...current, [row.qc_inspection_id]: '' }))) }><Undo2/> Batalkan finalisasi</button></div></article>)}
  </section>
}

export default function ConnectedQcFinalPage() {
  const { identity } = useAuth()
  const access = identity.status === 'AUTHORIZED' ? identity : null
  const canPost = hasPermission(access, SENSITIVE_ACTION_PERMISSION.postFinalSku)
  const canReverse = hasPermission(access, SENSITIVE_ACTION_PERMISSION.reverseFinalSku)
  const roleName = identity.status === 'AUTHORIZED' ? identity.profile.roleName : 'Tanpa role'
  const bridge = useLaundryQcWorkspace('QC')
  const [tab, setTab] = useState<'QUEUE' | 'HISTORY'>('QUEUE')
  const queueQty = bridge.workspace?.qc_queue.reduce((sum, row) => sum + row.available_for_qc_qty_pcs, 0) ?? 0
  const onAction: RunAction = bridge.runAction

  useEffect(() => {
    if (bridge.committedSequence > 0 && !bridge.workspaceStale) {
      bridge.acknowledgeCommittedFormRetired(bridge.committedSequence)
    }
  }, [bridge.acknowledgeCommittedFormRetired, bridge.committedSequence, bridge.workspaceStale])

  return <div className="connected-laundry-qc-page">
    <section className="clq-hero"><div><span>CP6 · DATA RESMI QC</span><h1>QC & Final SKU</h1><p>Catat hasil Good/BS dari penerimaan Laundry yang tepat, lalu pilih Merek → Nomor SKU → Model untuk setiap ukuran.</p></div><div><button disabled={bridge.loading || Boolean(bridge.pending) || bridge.corruptedEnvelope} onClick={() => void bridge.load()}><RefreshCw/> Muat ulang data</button></div></section>
    <div className="clq-boundary"><ShieldCheck/><span><strong>Reliable data adalah dewa.</strong> Laporan, stok, dan HPP adalah raja: hasil fisik hanya dinyatakan browser, seluruh dampaknya dimiliki server.</span></div>
    <Cp6PermissionNotice roleName={roleName} capabilities={[
      { label: 'Finalisasi QC', allowed: canPost, requirement: 'Post Final SKU' },
      { label: 'Koreksi finalisasi', allowed: canReverse, requirement: 'Reverse Final SKU' },
    ]}/>
    {bridge.error ? <div className="clq-alert error"><AlertTriangle/><span>{bridge.error}</span>{bridge.pending && !bridge.corruptedEnvelope ? <button aria-label="Reconcile UUID lama" onClick={() => void bridge.reconcile()} disabled={bridge.busy}><RefreshCw/> Cek status transaksi</button> : bridge.committedRefreshRequired || bridge.workspaceStale && !bridge.corruptedEnvelope ? <button onClick={() => void bridge.load()} disabled={bridge.busy}><RefreshCw/> Refetch</button> : null}</div> : null}
    {bridge.notice ? <div className="clq-alert notice"><CheckCircle2/><span>{bridge.notice}</span></div> : null}
    {bridge.busy ? <div className="clq-busy"><LoaderCircle className="spin"/> Menjaga finalisasi tetap satu kali…</div> : null}
    <section className="clq-kpis"><article><span>GOOD SIAP QC</span><strong>{queueQty}</strong><small>pcs dari sumber yang tepat</small></article><article><span>BARIS UKURAN</span><strong>{bridge.workspace?.qc_queue.length ?? 0}</strong><small>penerimaan · batch · ukuran</small></article><article><span>FINALISASI AKTIF</span><strong>{bridge.workspace?.qc_history.filter((row) => row.status === 'POSTED').length ?? 0}</strong><small>transaksi CP6 tersimpan</small></article><article><span>DATA LAMA TERPISAH</span><strong>{bridge.workspace?.legacy_unlinked.receipt_count ?? 0}</strong><small>tidak ditebak atau digabung</small></article></section>
    <nav className="clq-tabs qc"><button className={tab === 'QUEUE' ? 'active' : ''} onClick={() => setTab('QUEUE')}>Antrean finalisasi</button><button className={tab === 'HISTORY' ? 'active' : ''} onClick={() => setTab('HISTORY')}>Riwayat & koreksi</button><label><Search/><input value={bridge.query} onChange={(event) => bridge.search(event.target.value)} placeholder="Cari PO, Potongan, atau SKU…"/></label></nav>
    {bridge.loading && !bridge.workspace ? <div className="clq-loading"><LoaderCircle className="spin"/> Memuat data resmi…</div> : bridge.workspace ? <>
      {tab === 'QUEUE' ? <FinalSkuForm key={`qc-${bridge.committedSequence}`} workspace={bridge.workspace} writerLocked={bridge.writerLocked} canPost={canPost} onAction={onAction}/> : null}
      {tab === 'HISTORY' ? <QcHistory workspace={bridge.workspace} writerLocked={bridge.writerLocked} canReverse={canReverse} onAction={onAction}/> : null}
    </> : <div className="clq-loading"><AlertTriangle/> Data belum tersedia; semua tombol transaksi tetap terkunci.</div>}
    <section className="clq-rare-case"><AlertTriangle/><div><strong>Cuci ulang tidak boleh dicatat sebagai hasil QC palsu</strong><p>Jika hasil cuci gagal, koreksi penerimaan/pengiriman dari riwayat lalu buat pengiriman baru. Kasus cuci ulang berbayar tetap ditahan sampai alur hutang vendor dan HPP-nya tersedia.</p></div></section>
  </div>
}
