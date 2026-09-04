import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  AlertTriangle, ArchiveX, Check, ChevronRight, CircleDollarSign, Clock3,
  FileWarning, History, LoaderCircle, PackageCheck, Plus, RefreshCw, RotateCcw,
  Save, Search, ShieldCheck, Shirt, Undo2, UserRound, Waves, Wrench, X,
} from 'lucide-react'
import { useAuth } from './auth/AuthProvider'
import { SENSITIVE_ACTION_PERMISSION, hasPermission } from './auth/accessCatalog'
import {
  bsPatternLabel, cleanBsQuantity, exactReworkCompletion, parseBsResolutionWorkspace,
  type BsResolutionAction, type BsResolutionRow, type BsResolutionWorkspace,
  type BsWorkspaceFilter, type BsWorkspaceKind, type ReworkOrder,
} from './bsResolutionModel'
import ConnectedPatternFilter from './ConnectedPatternFilter'
import { normalizeClientError } from './lib/clientError'
import { getUatSupabaseClient } from './lib/supabase'
import type { Json } from './types/database.preconnect'
import './connected-bs-resolution.css'

type RunAction = (
  action: BsResolutionAction, payload: Json, expectedVersion: number | null,
) => Promise<boolean>
type ClaimType = 'STUCK' | 'MISSING' | 'DAMAGE'

const nowInput = () => {
  const now = new Date()
  return new Date(now.getTime() - now.getTimezoneOffset() * 60_000).toISOString().slice(0, 16)
}
const toIso = (value: string) => new Date(value).toISOString()
const qty = (value: string) => Math.max(0, Math.floor(Number(value) || 0))
const money = (value: number) => `Rp${Math.round(value).toLocaleString('id-ID')}`
const statusLabel = (status: string) => status.replaceAll('_', ' ')

function CreateManualBs({ workspace, onClose, onAction }: {
  workspace: BsResolutionWorkspace; onClose: () => void; onAction: RunAction
}) {
  const [number, setNumber] = useState('')
  const [legacyReference, setLegacyReference] = useState('')
  const [productId, setProductId] = useState('')
  const [quantity, setQuantity] = useState('')
  const [physicalAt, setPhysicalAt] = useState(nowInput)
  const [reason, setReason] = useState('')
  const [notes, setNotes] = useState('')
  const [componentIds, setComponentIds] = useState<string[]>([])
  const [completedBefore, setCompletedBefore] = useState<Record<string, string>>({})
  const componentQuantitiesValid = componentIds.every((id) => qty(completedBefore[id] ?? '0') <= qty(quantity))
  const valid = Boolean(legacyReference.trim() && qty(quantity) > 0 && componentQuantitiesValid && physicalAt && reason.trim().length >= 4)
  return <div className="cbsr-modal-layer" role="presentation"><section role="dialog" aria-modal="true" aria-labelledby="manual-bs-title">
    <header><div><span>SUMBER TIDAK TERLACAK</span><h2 id="manual-bs-title">Catat BS legacy / out-of-nowhere</h2><p>Jalur ini wajib menyimpan referensi fisik dan tidak mengarang PO atau Pola.</p></div><button aria-label="Tutup" onClick={onClose}><X/></button></header>
    <div className="cbsr-form-grid">
      <label><span>NOMOR BS · OPSIONAL</span><input value={number} onChange={(event) => setNumber(event.target.value)} placeholder="Otomatis bila kosong"/></label>
      <label><span>REFERENSI LEGACY · WAJIB</span><input value={legacyReference} onChange={(event) => setLegacyReference(event.target.value)} placeholder="Nota / buku / foto fisik"/></label>
      <label><span>PRODUK · OPSIONAL</span><select value={productId} onChange={(event) => setProductId(event.target.value)}><option value="">Belum dapat diidentifikasi</option>{workspace.lookups.products.map((item) => <option value={item.id} key={item.id}>{item.sku} · {item.name}</option>)}</select></label>
      <label><span>QTY PCS</span><input inputMode="numeric" value={quantity} onChange={(event) => setQuantity(cleanBsQuantity(event.target.value, 999_999))}/></label>
      <label><span>WAKTU FISIK DITEMUKAN</span><input type="datetime-local" value={physicalAt} onChange={(event) => setPhysicalAt(event.target.value)}/></label>
      <label className="wide"><span>ALASAN PENCATATAN · WAJIB</span><input value={reason} onChange={(event) => setReason(event.target.value)} placeholder="Mengapa baru dicatat sekarang?"/></label>
      <label className="wide"><span>CATATAN KONDISI</span><textarea value={notes} onChange={(event) => setNotes(event.target.value)} placeholder="Kondisi barang dan lokasi fisik"/></label>
    </div>
    <fieldset className="cbsr-checks component-quantities"><legend>KOMPONEN TERKAIT · CATAT QTY YANG SUDAH SELESAI SEBELUM BS</legend>{workspace.lookups.work_components.map((item) => {
      const selected = componentIds.includes(item.id)
      return <div className={selected ? 'selected' : ''} key={item.id}><label><input type="checkbox" checked={selected} onChange={(event) => {
        setComponentIds((current) => event.target.checked ? [...current, item.id] : current.filter((id) => id !== item.id))
        setCompletedBefore((current) => {
          const next = { ...current }
          if (event.target.checked) next[item.id] = next[item.id] ?? '0'
          else delete next[item.id]
          return next
        })
      }}/><span><strong>{item.code}</strong>{item.name}</span></label>{selected ? <label className="component-before"><span>SUDAH SELESAI</span><input aria-label={`Qty ${item.name} sudah selesai sebelum BS`} inputMode="numeric" value={completedBefore[item.id] ?? '0'} onChange={(event) => setCompletedBefore((current) => ({ ...current, [item.id]: cleanBsQuantity(event.target.value, qty(quantity)) }))}/><small>/ {qty(quantity)} pcs</small></label> : null}</div>
    })}</fieldset>
    <footer><button onClick={onClose}>Batal</button><button className="primary" disabled={!valid} onClick={async () => {
      const ok = await onAction('CREATE_MANUAL_BS', {
        bs_number: number.trim() || undefined, untracked_type: 'LEGACY', legacy_reference: legacyReference.trim(),
        product_id: productId || undefined, qty_pcs: qty(quantity), physical_at: toIso(physicalAt),
        change_reason: reason.trim(), notes: notes.trim() || undefined,
        components: componentIds.map((work_component_id) => ({
          work_component_id, completed_before_bs_qty: qty(completedBefore[work_component_id] ?? '0'),
        })),
      }, null)
      if (ok) onClose()
    }}><Save/> Simpan kasus authoritative</button></footer>
  </section></div>
}

function CreateClaim({ workspace, onClose, onAction }: {
  workspace: BsResolutionWorkspace; onClose: () => void; onAction: RunAction
}) {
  const initialDelivery = workspace.lookups.laundry_sources.find((item) => item.qty_claimable_pcs > 0)
  const [sourceId, setSourceId] = useState(initialDelivery?.id ?? '')
  const [number, setNumber] = useState('')
  const [claimType, setClaimType] = useState<ClaimType>('STUCK')
  const [quantity, setQuantity] = useState('')
  const [compensation, setCompensation] = useState('0')
  const [openedAt, setOpenedAt] = useState(nowInput)
  const [reason, setReason] = useState('')
  const deliverySources = workspace.lookups.laundry_sources.filter((item) => item.qty_claimable_pcs > 0)
  const receiptSources = workspace.lookups.laundry_receipt_sources
  const deliverySource = deliverySources.find((item) => item.id === sourceId)
  const receiptSource = receiptSources.find((item) => item.id === sourceId)
  const source = claimType === 'DAMAGE' ? receiptSource : deliverySource
  const maxQuantity = claimType === 'DAMAGE'
    ? receiptSource?.qty_claimable_pcs ?? 0
    : deliverySource?.qty_claimable_pcs ?? 0
  const valid = Boolean(source && number.trim() && qty(quantity) > 0 && qty(quantity) <= maxQuantity && openedAt && reason.trim().length >= 4)
  return <div className="cbsr-modal-layer" role="presentation"><section role="dialog" aria-modal="true" aria-labelledby="new-claim-title">
    <header><div><span>LAUNDRY EXCEPTION</span><h2 id="new-claim-title">Buat claim Laundry</h2><p>Stuck/Missing mengikuti surat kirim; Damage wajib mengikuti baris penerimaan BS. Vendor dan PO tidak diketik ulang.</p></div><button aria-label="Tutup" onClick={onClose}><X/></button></header>
    <div className="cbsr-form-grid">
      <label className="wide"><span>{claimType === 'DAMAGE' ? 'BARIS PENERIMAAN BS' : 'SURAT KIRIM'}</span><select value={sourceId} onChange={(event) => { setSourceId(event.target.value); setQuantity('') }}><option value="">Pilih sumber…</option>{claimType === 'DAMAGE' ? receiptSources.map((item) => <option value={item.id} key={item.id}>{item.number} · {item.delivery_number} · {item.vendor_name} · {item.qty_claimable_pcs}/{item.qty_bs_laundry} pcs bisa diclaim</option>) : deliverySources.map((item) => <option value={item.id} key={item.id}>{item.number} · {item.vendor_name} · {item.po_number} · {item.qty_claimable_pcs} pcs outstanding</option>)}</select>{(claimType === 'DAMAGE' ? receiptSources : deliverySources).length === 0 ? <small className="cbsr-field-warning">Belum ada sumber fisik yang masih memiliki kapasitas claim jenis ini.</small> : null}</label>
      <label><span>NOMOR CLAIM</span><input value={number} onChange={(event) => setNumber(event.target.value)} placeholder="CLM-LDR-…"/></label>
      <label><span>JENIS</span><select value={claimType} onChange={(event) => {
        const next = event.target.value as ClaimType
        setClaimType(next); setQuantity('')
        setSourceId(next === 'DAMAGE'
          ? workspace.lookups.laundry_receipt_sources[0]?.id ?? ''
          : workspace.lookups.laundry_sources.find((item) => item.qty_claimable_pcs > 0)?.id ?? '')
      }}><option>STUCK</option><option>MISSING</option><option>DAMAGE</option></select></label>
      <label><span>QTY CLAIM · MAKS {maxQuantity}</span><input inputMode="numeric" value={quantity} onChange={(event) => setQuantity(cleanBsQuantity(event.target.value, maxQuantity))}/></label>
      <label><span>NILAI KOMPENSASI</span><input inputMode="numeric" value={compensation} onChange={(event) => setCompensation(cleanBsQuantity(event.target.value, 999_999_999))}/></label>
      <label><span>WAKTU DIBUKA</span><input type="datetime-local" value={openedAt} onChange={(event) => setOpenedAt(event.target.value)}/></label>
      <label className="wide"><span>ALASAN / BUKTI · WAJIB</span><textarea value={reason} onChange={(event) => setReason(event.target.value)} placeholder="Jelaskan kekurangan, kerusakan, atau barang tertahan"/></label>
    </div>
    <footer><button onClick={onClose}>Batal</button><button className="primary" disabled={!valid} onClick={async () => {
      if (!source) return
      const ok = await onAction('SAVE_CLAIM', {
        action: 'SAVE', claim_number: number.trim(), vendor_id: source.vendor_id,
        delivery_id: claimType === 'DAMAGE' ? receiptSource?.delivery_id : deliverySource?.id,
        receipt_line_id: claimType === 'DAMAGE' ? receiptSource?.id : null,
        qty_claimed: qty(quantity), claim_type: claimType, compensation_amount: qty(compensation),
        opened_at: toIso(openedAt), notes: reason.trim(), change_reason: reason.trim(),
      }, null)
      if (ok) onClose()
    }}><Save/> Simpan claim</button></footer>
  </section></div>
}

function ClassificationPanel({ row, workspace, canCreate, onAction }: {
  row: BsResolutionRow; workspace: BsResolutionWorkspace; canCreate: boolean; onAction: RunAction
}) {
  const [cause, setCause] = useState(row.cause_source)
  const [contractorId, setContractorId] = useState(row.responsible_contractor_id ?? '')
  const [vendorId, setVendorId] = useState(row.responsible_vendor_id ?? '')
  const [notes, setNotes] = useState(row.notes ?? '')
  const [reason, setReason] = useState('')
  const [componentIds, setComponentIds] = useState(row.components.map((item) => item.work_component_id))
  const [completedBefore, setCompletedBefore] = useState<Record<string, string>>(() => Object.fromEntries(
    row.components.map((item) => [item.work_component_id, String(item.completed_before_bs_qty)]),
  ))
  const componentsFrozen = row.rework_orders.some((order) => order.components.length > 0)
  const validOwner = cause === 'UNKNOWN' || (cause === 'SEWING' ? contractorId : vendorId)
  return <details className="cbsr-fold"><summary><span><UserRound/> Klasifikasi & tanggung jawab</span><ChevronRight/></summary><div className="cbsr-fold-body">
    <div className="cbsr-form-grid compact">
      <label><span>SUMBER PENYEBAB</span><select value={cause} disabled={!canCreate || row.status === 'ON_HOLD' || row.is_closed} onChange={(event) => setCause(event.target.value)}><option>UNKNOWN</option><option>SEWING</option><option>LAUNDRY</option></select></label>
      {cause === 'SEWING' ? <label><span>MANDOR TANGGUNG JAWAB</span><select value={contractorId} onChange={(event) => setContractorId(event.target.value)}><option value="">Pilih Mandor…</option>{workspace.lookups.contractors.map((item) => <option value={item.id} key={item.id}>{item.code} · {item.name}</option>)}</select></label> : cause === 'LAUNDRY' ? <label><span>VENDOR TANGGUNG JAWAB</span><select value={vendorId} onChange={(event) => setVendorId(event.target.value)}><option value="">Pilih Laundry…</option>{workspace.lookups.vendors.map((item) => <option value={item.id} key={item.id}>{item.code} · {item.name}</option>)}</select></label> : null}
      <label className="wide"><span>CATATAN KASUS</span><textarea value={notes} onChange={(event) => setNotes(event.target.value)}/></label>
      <label className="wide"><span>ALASAN PERUBAHAN · WAJIB</span><input value={reason} onChange={(event) => setReason(event.target.value)} placeholder="Dasar hasil pemeriksaan fisik"/></label>
    </div>
    <fieldset className="cbsr-checks component-quantities" disabled={componentsFrozen || !canCreate}><legend>KOMPONEN TERKAIT · QTY SUDAH SELESAI SEBELUM BS {componentsFrozen ? '· TERKUNCI SETELAH REWORK' : ''}</legend>{workspace.lookups.work_components.map((item) => {
      const selected = componentIds.includes(item.id)
      return <div className={selected ? 'selected' : ''} key={item.id}><label><input type="checkbox" checked={selected} onChange={(event) => {
        setComponentIds((current) => event.target.checked ? [...current, item.id] : current.filter((id) => id !== item.id))
        setCompletedBefore((current) => {
          const next = { ...current }
          if (event.target.checked) next[item.id] = next[item.id] ?? '0'
          else delete next[item.id]
          return next
        })
      }}/><span><strong>{item.code}</strong>{item.name}</span></label>{selected ? <label className="component-before"><span>SUDAH SELESAI</span><input aria-label={`Qty ${item.name} sudah selesai sebelum BS`} inputMode="numeric" value={completedBefore[item.id] ?? '0'} onChange={(event) => setCompletedBefore((current) => ({ ...current, [item.id]: cleanBsQuantity(event.target.value, row.qty_pcs) }))}/><small>/ {row.qty_pcs} pcs</small></label> : null}</div>
    })}</fieldset>
    <button className="cbsr-submit" disabled={!canCreate || row.status === 'ON_HOLD' || row.is_closed || !validOwner || reason.trim().length < 4} onClick={() => void onAction('CLASSIFY_BS', {
      bs_case_id: row.id, cause_source: cause,
      responsible_contractor_id: cause === 'SEWING' ? contractorId : null,
      responsible_vendor_id: cause === 'LAUNDRY' ? vendorId : null,
      notes: notes.trim() || null, change_reason: reason.trim(),
      ...(componentsFrozen ? {} : { components: componentIds.map((work_component_id) => ({
        work_component_id,
        completed_before_bs_qty: qty(completedBefore[work_component_id] ?? '0'),
      })) }),
    }, row.row_version)}><Save/> Simpan klasifikasi</button>
  </div></details>
}

function ReworkCompletion({ order, workspace, canCreate, canPost, canReverse, ownerAdmin, onAction }: {
  order: ReworkOrder; workspace: BsResolutionWorkspace; canCreate: boolean; canPost: boolean
  canReverse: boolean; ownerAdmin: boolean; onAction: RunAction
}) {
  const [good, setGood] = useState(String(order.qty_good_returned))
  const [bad, setBad] = useState(String(order.qty_bs_returned))
  const [completedAt, setCompletedAt] = useState(nowInput)
  const [locationId, setLocationId] = useState(order.return_fg_location_id ?? workspace.lookups.fg_locations[0]?.id ?? '')
  const [reason, setReason] = useState('')
  const returned = qty(good) + qty(bad)
  const previousReturned = order.qty_good_returned + order.qty_bs_returned
  const exact = exactReworkCompletion(qty(good), qty(bad), order.qty_sent)
  const cumulative = qty(good) >= order.qty_good_returned && qty(bad) >= order.qty_bs_returned
  const newPartial = cumulative && returned > previousReturned && returned < order.qty_sent
  const canCancel = order.qty_good_returned + order.qty_bs_returned === 0
  if (order.status === 'COMPLETED' && order.cost_posted) return <div className="cbsr-rework-complete"><PackageCheck/><span><strong>{order.qty_good_returned} Good · {order.qty_bs_returned} BS</strong><small>Biaya posted {order.good_fg_lot_id ? '· lot FG terbentuk' : '· tanpa Good FG'}</small></span><button disabled={!canReverse || !ownerAdmin || reason.trim().length < 4} onClick={() => void onAction('REVERSE_REWORK_COMPLETION', { rework_order_id: order.id, change_reason: reason.trim() }, order.row_version)}><Undo2/> Reverse</button><input value={reason} onChange={(event) => setReason(event.target.value)} placeholder="Alasan reversal Owner/Admin"/></div>
  if (order.status === 'CANCELLED') return <div className="cbsr-muted">Order dibatalkan; histori tetap dipertahankan.</div>
  return <div className="cbsr-completion-form"><header><span>HASIL KUMULATIF · {previousReturned} MASUK · {order.qty_sent - previousReturned} BELUM KEMBALI</span><strong>{order.rework_number}</strong></header><div>
    <label><span>GOOD KUMULATIF</span><input inputMode="numeric" value={good} onChange={(event) => setGood(cleanBsQuantity(event.target.value, order.qty_sent))}/></label>
    <label><span>BS KUMULATIF</span><input inputMode="numeric" value={bad} onChange={(event) => setBad(cleanBsQuantity(event.target.value, order.qty_sent))}/></label>
    <label><span>WAKTU SELESAI</span><input type="datetime-local" value={completedAt} onChange={(event) => setCompletedAt(event.target.value)}/></label>
    <label><span>GUDANG GOOD FG</span><select value={locationId} disabled={qty(good) === 0} onChange={(event) => setLocationId(event.target.value)}><option value="">Pilih lokasi…</option>{workspace.lookups.fg_locations.map((item) => <option value={item.id} key={item.id}>{item.code} · {item.name}</option>)}</select></label>
    <label className="wide"><span>ALASAN HASIL FISIK</span><input value={reason} onChange={(event) => setReason(event.target.value)} placeholder="Barang yang benar-benar kembali dan hasil pemeriksaannya"/></label>
  </div><p className="cbsr-partial-note">Simpan partial hanya memperbarui custody/WIP. FG, HPP, reimbursement, dan hutang baru diposting setelah seluruh {order.qty_sent} pcs kembali.</p><footer><span className={exact && cumulative ? 'ok' : 'bad'}>{qty(good)} + {qty(bad)} = {returned} / {order.qty_sent}{!cumulative ? ' · tidak boleh turun' : ''}</span><div>{canCancel ? <button className="danger" disabled={!canCreate || reason.trim().length < 4} onClick={() => {
    if (!globalThis.confirm(`Batalkan ${order.rework_number}? Histori order tetap disimpan sebagai CANCELLED.`)) return
    void onAction('SAVE_REWORK', { id: order.id, action: 'CANCEL', change_reason: reason.trim() }, order.row_version)
  }}><X/> Batalkan order</button> : null}{newPartial ? <button disabled={!canCreate || qty(good) > 0 && !locationId || reason.trim().length < 4} onClick={() => void onAction('SAVE_REWORK', {
    id: order.id, action: 'SAVE', qty_good_returned: qty(good), qty_bs_returned: qty(bad),
    return_fg_location_id: qty(good) > 0 ? locationId : null, change_reason: reason.trim(),
  }, order.row_version)}><Save/> Simpan partial</button> : null}<button disabled={!canPost || !exact || !cumulative || qty(good) > 0 && !locationId || !completedAt || reason.trim().length < 4} onClick={() => void onAction('COMPLETE_REWORK', {
    rework_order_id: order.id, qty_good: qty(good), qty_bs: qty(bad), completed_at: toIso(completedAt),
    return_fg_location_id: qty(good) > 0 ? locationId : null, change_reason: reason.trim(),
  }, order.row_version)}><PackageCheck/> Post hasil & recovery</button></div></footer></div>
}

function BsActionPanel({ row, workspace, canCreate, canPost, canReverse, ownerAdmin, onAction }: {
  row: BsResolutionRow; workspace: BsResolutionWorkspace; canCreate: boolean; canPost: boolean
  canReverse: boolean; ownerAdmin: boolean; onAction: RunAction
}) {
  const [route, setRoute] = useState<'REWORK' | 'REWASH' | 'HOLD' | 'DISPOSITION' | 'COMPENSATION'>('REWORK')
  const [quantity, setQuantity] = useState(String(row.available_qty))
  const [partyId, setPartyId] = useState('')
  const [number, setNumber] = useState('')
  const [physicalAt, setPhysicalAt] = useState(nowInput)
  const [reason, setReason] = useState('')
  const [locationId, setLocationId] = useState(workspace.lookups.fg_locations[0]?.id ?? '')
  const [resolutionType, setResolutionType] = useState('SCRAP')
  const [claimId, setClaimId] = useState('')
  const [compensation, setCompensation] = useState('0')
  const [componentIds, setComponentIds] = useState(row.components.filter((item) => item.default_selected).map((item) => item.id))
  const accessoryBom = row.accessory_bom
  const [accessoryIds, setAccessoryIds] = useState(
    accessoryBom?.state === 'AVAILABLE' ? accessoryBom.items.filter((item) => item.default_selected).map((item) => item.id) : [],
  )
  const activeOrders = row.rework_orders.filter((item) => ['OPEN', 'IN_PROGRESS', 'PARTIAL'].includes(item.status))
  const canStart = ['OPEN', 'PARTIAL'].includes(row.status) && row.available_qty > 0 && activeOrders.length === 0
  const nativeBomMissing = Boolean(row.po_id && row.product_id && accessoryBom?.state === 'UNAVAILABLE')
  const settledClaims = workspace.lookups.settled_claims.filter((item) => Boolean(
    row.responsible_vendor_id && item.vendor_id === row.responsible_vendor_id
    && (!row.laundry_receipt_line_id
      || item.receipt_line_id === row.laundry_receipt_line_id
      || Boolean(row.laundry_delivery_id && item.delivery_id === row.laundry_delivery_id))
    && (!row.laundry_delivery_id || row.laundry_receipt_line_id || item.delivery_id === row.laundry_delivery_id),
  ))
  const selectedClaim = settledClaims.find((item) => item.id === claimId)
  const sendQty = Math.min(row.available_qty, qty(quantity))
  const routeOptions = [
    ['REWORK', 'Rework', Wrench], ['REWASH', 'Rewash', Waves], ['HOLD', 'Hold', Clock3],
    ['DISPOSITION', 'Scrap / write-off', ArchiveX], ['COMPENSATION', 'Kompensasi', CircleDollarSign],
  ] as const
  return <section className="cbsr-actions"><header><div><span>CP5 · RESOLUTION ROUTE</span><h3>Pilih tindakan fisik yang benar</h3></div><ShieldCheck/></header>
    <div className="cbsr-route-tabs">{routeOptions.map(([id, label, Icon]) => <button type="button" key={id} className={route === id ? 'active' : ''} onClick={() => { setRoute(id); setReason(''); setPartyId('') }}><Icon/><span>{label}</span></button>)}</div>
    {route === 'HOLD' ? <div className="cbsr-route-form"><div className="cbsr-route-note"><Clock3/><span><strong>{row.status === 'ON_HOLD' ? 'Lepas HOLD ke status hasil reducer' : 'HOLD membekukan keputusan'}</strong><small>Qty tidak menjadi FG, Scrap, atau rework. Semua transisi masuk histori append-only.</small></span></div><div className="cbsr-form-grid compact"><label><span>WAKTU FISIK</span><input type="datetime-local" value={physicalAt} onChange={(event) => setPhysicalAt(event.target.value)}/></label><label className="wide"><span>ALASAN · WAJIB</span><textarea value={reason} onChange={(event) => setReason(event.target.value)}/></label></div><button className="cbsr-submit" disabled={!canPost || row.is_closed || (row.status === 'ON_HOLD' ? false : !canStart) || !physicalAt || reason.trim().length < 4} onClick={() => void onAction(row.status === 'ON_HOLD' ? 'RELEASE_HOLD' : 'HOLD_BS', { bs_case_id: row.id, physical_at: toIso(physicalAt), change_reason: reason.trim() }, row.row_version)}><Clock3/> {row.status === 'ON_HOLD' ? 'Release HOLD' : 'Simpan HOLD'}</button></div> : null}
    {(route === 'REWORK' || route === 'REWASH') ? <div className="cbsr-route-form"><div className="cbsr-form-grid compact">
      <label><span>NOMOR ORDER · WAJIB</span><input value={number} onChange={(event) => setNumber(event.target.value)} placeholder={route === 'REWORK' ? `RW-${row.number}` : `RWL-${row.number}`}/></label>
      <label><span>{route === 'REWORK' ? 'MANDOR REWORK' : 'VENDOR REWASH'}</span><select value={partyId} onChange={(event) => setPartyId(event.target.value)}><option value="">Pilih…</option>{(route === 'REWORK' ? workspace.lookups.contractors : workspace.lookups.vendors).map((item) => <option value={item.id} key={item.id}>{item.code} · {item.name}</option>)}</select></label>
      <label><span>QTY DIKIRIM</span><input inputMode="numeric" value={quantity} onChange={(event) => setQuantity(cleanBsQuantity(event.target.value, row.available_qty))}/></label>
      <label><span>WAKTU FISIK</span><input type="datetime-local" value={physicalAt} onChange={(event) => setPhysicalAt(event.target.value)}/></label>
      <label><span>GUDANG FG BILA GOOD</span><select value={locationId} onChange={(event) => setLocationId(event.target.value)}><option value="">Pilih saat completion</option>{workspace.lookups.fg_locations.map((item) => <option value={item.id} key={item.id}>{item.code} · {item.name}</option>)}</select></label>
      <label className="wide"><span>CATATAN / ALASAN</span><textarea value={reason} onChange={(event) => setReason(event.target.value)} placeholder="Kerusakan dan instruksi fisik"/></label>
    </div>{route === 'REWORK' ? <fieldset className="cbsr-checks"><legend>KOMPONEN KERJA YANG DIULANG · DASAR UPAH REWORK</legend><p>Server hanya mencentang komponen yang masih punya entitlement kerja baru. Counter, bukan status pembayaran kas, menjadi batas anti-bayar-ganda.</p>{row.components.map((item) => <label key={item.id}><input type="checkbox" checked={componentIds.includes(item.id)} onChange={(event) => setComponentIds((current) => event.target.checked ? [...current, item.id] : current.filter((id) => id !== item.id))}/><span><strong>{item.code}</strong>{item.name} · sisa hak baru {item.remaining_new_work_qty_pcs} pcs</span></label>)}</fieldset> : <p className="cbsr-zero-fee"><Waves/> Vendor Rewash tidak mendapat fee kerja komponen. Reimbursement aksesori terpilih tetap menuju Mandor PO.</p>}
    {accessoryBom?.state === 'AVAILABLE' ? <fieldset className="cbsr-checks cbsr-accessories"><legend>AKSESORI YANG BENAR-BENAR DIPASANG · DASAR REIMBURSEMENT</legend><p>Server otomatis mencentang baseline yang belum menjadi entitlement. Yang pernah menjadi entitlement atau tidak bisa dibuktikan akan off; centang manual hanya bila benar-benar ada penggantian tambahan. Pilihan final terkunci saat order dibuat.</p>{accessoryBom.items.map((item) => <label key={item.id}><input type="checkbox" checked={accessoryIds.includes(item.id)} onChange={(event) => setAccessoryIds((current) => event.target.checked ? [...current, item.id] : current.filter((id) => id !== item.id))}/><span><strong>{item.code} · {item.name}</strong>{item.qty_per_good_fg_base} {item.base_uom_code}/pcs · {money(item.reimbursement_rate)}/{item.reimbursement_uom_code} · {item.default_selected ? `${item.remaining_unentitled_good_qty_pcs} pcs baseline belum entitlement` : 'default off · manual bila penggantian nyata'}</span></label>)}</fieldset> : accessoryBom?.state === 'NONE' ? <p className="cbsr-zero-fee"><Check/> BOM produk menyatakan tanpa aksesori. Keputusan kosong tetap disimpan secara immutable.</p> : <p className={nativeBomMissing ? 'cbsr-bom-warning' : 'cbsr-zero-fee'}><AlertTriangle/> {nativeBomMissing ? 'BOM aksesori produk belum tersedia. Setup BOM—termasuk BOM kosong—sebelum membuat order.' : 'Kasus legacy ini tidak punya PO/SKU; pilihan aksesori kosong akan dicatat sebagai UNAVAILABLE dan hasil GOOD tetap tidak dapat diposting.'}</p>}
    <button className="cbsr-submit" disabled={!canCreate || !canStart || nativeBomMissing || !number.trim() || !partyId || sendQty <= 0 || !physicalAt || reason.trim().length < 4 || route === 'REWORK' && componentIds.length === 0} onClick={() => void onAction('SAVE_REWORK', {
      rework_number: number.trim(),
      bs_case_id: row.id, destination_type: route === 'REWORK' ? 'CONTRACTOR' : 'LAUNDRY',
      contractor_id: route === 'REWORK' ? partyId : null, vendor_id: route === 'REWASH' ? partyId : null,
      qty_sent: sendQty, qty_good_returned: 0, qty_bs_returned: 0, physical_sent_at: toIso(physicalAt),
      status: 'IN_PROGRESS', return_fg_location_id: locationId || null, change_reason: reason.trim(), notes: reason.trim(),
      accessory_bom_version_id: accessoryBom?.bom_version_id ?? null,
      accessory_bom_item_ids: accessoryIds,
      components: route === 'REWORK' ? componentIds.map((bs_case_component_id) => ({ bs_case_component_id, qty_performed: sendQty, notes: reason.trim() })) : [],
    }, null)}><Wrench/> Buat order {route === 'REWORK' ? 'rework' : 'rewash'}</button></div> : null}
    {(route === 'DISPOSITION' || route === 'COMPENSATION') ? <div className="cbsr-route-form"><div className="cbsr-form-grid compact">
      {route === 'DISPOSITION' ? <label><span>DISPOSITION</span><select value={resolutionType} onChange={(event) => setResolutionType(event.target.value)}><option>SCRAP</option><option>WRITE_OFF</option><option>OTHER</option></select></label> : <label><span>CLAIM SETTLED · SALDO TERSEDIA</span><select value={claimId} onChange={(event) => { setClaimId(event.target.value); setQuantity(''); setCompensation('0') }}><option value="">Pilih claim…</option>{settledClaims.map((item) => <option value={item.id} key={item.id}>{item.number} · {item.vendor_name} · {item.available_qty} pcs / {money(item.available_amount)}</option>)}</select>{settledClaims.length === 0 ? <small className="cbsr-field-warning">Klasifikasikan vendor penanggung jawab dan settle claim bernilai positif yang masih bersaldo.</small> : null}</label>}
      <label><span>QTY{selectedClaim ? ` · MAKS ${Math.min(row.available_qty, selectedClaim.available_qty)}` : ''}</span><input inputMode="numeric" value={quantity} onChange={(event) => setQuantity(cleanBsQuantity(event.target.value, route === 'COMPENSATION' ? Math.min(row.available_qty, selectedClaim?.available_qty ?? 0) : row.available_qty))}/></label>
      {route === 'COMPENSATION' ? <label><span>NILAI DIPAKAI · MAKS {money(selectedClaim?.available_amount ?? 0)}</span><input inputMode="numeric" value={compensation} onChange={(event) => setCompensation(cleanBsQuantity(event.target.value, Math.floor(selectedClaim?.available_amount ?? 0)))}/></label> : null}
      <label><span>WAKTU FISIK</span><input type="datetime-local" value={physicalAt} onChange={(event) => setPhysicalAt(event.target.value)}/></label>
      <label className="wide"><span>ALASAN · WAJIB</span><textarea value={reason} onChange={(event) => setReason(event.target.value)}/></label>
    </div><button className="cbsr-submit danger" disabled={!canPost || !canStart || sendQty <= 0 || !physicalAt || reason.trim().length < 4 || route === 'COMPENSATION' && (!selectedClaim || sendQty > selectedClaim.available_qty || qty(compensation) <= 0 || qty(compensation) > selectedClaim.available_amount)} onClick={() => void onAction('DISPOSE_BS', {
      bs_case_id: row.id, resolution_type: route === 'COMPENSATION' ? 'CASH_COMPENSATION' : resolutionType,
      qty_pcs: sendQty, compensation_amount: route === 'COMPENSATION' ? qty(compensation) : 0,
      source_laundry_claim_id: route === 'COMPENSATION' ? claimId : null,
      physical_at: toIso(physicalAt), change_reason: reason.trim(),
    }, row.row_version)}><ArchiveX/> Post disposition</button></div> : null}
    {activeOrders.map((order) => <ReworkCompletion key={order.id} order={order} workspace={workspace} canCreate={canCreate} canPost={canPost} canReverse={canReverse} ownerAdmin={ownerAdmin} onAction={onAction}/>)}
  </section>
}

function ClaimActionPanel({ row, canCreate, canPost, canReverse, ownerAdmin, onAction }: {
  row: BsResolutionRow; canCreate: boolean; canPost: boolean; canReverse: boolean; ownerAdmin: boolean; onAction: RunAction
}) {
  const [reason, setReason] = useState('')
  const [resolution, setResolution] = useState<'SETTLED' | 'WRITTEN_OFF'>('SETTLED')
  const active = ['OPEN', 'ACCEPTED'].includes(row.status)
  return <section className="cbsr-actions claim"><header><div><span>LAUNDRY CLAIM LIFECYCLE</span><h3>{row.claim_type} · {money(row.compensation_amount)}</h3></div><Waves/></header><div className="cbsr-route-note"><FileWarning/><span><strong>{row.qty_pcs} pcs ditahan oleh claim</strong><small>Settlement dengan kompensasi memeriksa saldo hutang vendor; write-off harus bernilai Rp0.</small></span></div><label className="cbsr-reason"><span>ALASAN / BUKTI · WAJIB</span><textarea value={reason} onChange={(event) => setReason(event.target.value)}/></label>
    {active ? <div className="cbsr-claim-actions"><button disabled={!canCreate || row.status === 'ACCEPTED' || reason.trim().length < 4} onClick={() => void onAction('SAVE_CLAIM', { id: row.id, action: 'SAVE', status: 'ACCEPTED', change_reason: reason.trim() }, row.row_version)}><Check/> Terima claim</button><button disabled={!canCreate || reason.trim().length < 4} onClick={() => void onAction('SAVE_CLAIM', { id: row.id, action: 'REJECT', change_reason: reason.trim() }, row.row_version)}><X/> Tolak claim</button><select value={resolution} onChange={(event) => setResolution(event.target.value as typeof resolution)}><option>SETTLED</option><option>WRITTEN_OFF</option></select><button className="primary" disabled={!canPost || !ownerAdmin || reason.trim().length < 4 || resolution === 'WRITTEN_OFF' && row.compensation_amount > 0} onClick={() => void onAction('RESOLVE_CLAIM', { laundry_claim_id: row.id, resolution, change_reason: reason.trim() }, row.row_version)}><CircleDollarSign/> Resolve</button></div> : <div className="cbsr-claim-actions"><button disabled={!canCreate || !ownerAdmin || row.status !== 'REJECTED' || reason.trim().length < 4} onClick={() => void onAction('SAVE_CLAIM', { id: row.id, action: 'REOPEN', change_reason: reason.trim() }, row.row_version)}><RotateCcw/> Reopen</button><button className="danger" disabled={!canReverse || !ownerAdmin || !['SETTLED', 'WRITTEN_OFF'].includes(row.status) || reason.trim().length < 4} onClick={() => void onAction('REVERSE_CLAIM_RESOLUTION', { laundry_claim_id: row.id, change_reason: reason.trim() }, row.row_version)}><Undo2/> Reverse resolution</button></div>}
  </section>
}

function CaseDetail({ row, workspace, canCreate, canPost, canReverse, ownerAdmin, onAction }: {
  row: BsResolutionRow; workspace: BsResolutionWorkspace; canCreate: boolean; canPost: boolean
  canReverse: boolean; ownerAdmin: boolean; onAction: RunAction
}) {
  const [reverseReason, setReverseReason] = useState('')
  return <main className="cbsr-detail"><header><div><span>{row.kind === 'BS' ? 'BARANG BS' : 'LAUNDRY CLAIM'} · ROW VERSION {row.row_version}</span><h2>{row.number}</h2><p>{row.po_number ?? 'Tanpa PO'} · {row.model_name ?? row.product_name ?? 'Identitas produk belum lengkap'}</p></div><em className={row.is_closed ? 'closed' : row.status === 'ON_HOLD' ? 'hold' : 'active'}>{statusLabel(row.status)}</em></header>
    <section className="cbsr-truth"><ShieldCheck/><div><small>POLA · SNAPSHOT SUMBER</small><strong>{bsPatternLabel(row)}</strong></div></section>
    <section className="cbsr-facts"><span><small>QTY KASUS</small><strong>{row.qty_pcs} pcs</strong></span><span><small>RESOLVED</small><strong>{row.resolved_qty} pcs</strong></span><span><small>REWORK AKTIF</small><strong>{row.active_rework_qty} pcs</strong></span><span><small>TERSEDIA</small><strong>{row.available_qty} pcs</strong></span></section>
    <section className="cbsr-lineage"><span><small>POTONGAN</small><strong>{row.group_number ?? 'Tidak terlacak'}</strong></span><span><small>SUMBER / PIHAK</small><strong>{row.contractor_name ?? row.vendor_name ?? row.cause_source}</strong></span><span><small>WAKTU FISIK</small><strong>{new Date(row.opened_at).toLocaleString('id-ID')}</strong></span><span><small>REFERENSI</small><strong>{row.legacy_reference ?? row.laundry_delivery_id ?? row.sku ?? '—'}</strong></span></section>
    {row.notes ? <p className="cbsr-case-note"><FileWarning/>{row.notes}</p> : null}
    {row.kind === 'BS' ? <ClassificationPanel key={`classification-${row.id}-${row.row_version}`} row={row} workspace={workspace} canCreate={canCreate} onAction={onAction}/> : null}
    {row.kind === 'BS' ? <BsActionPanel key={`actions-${row.id}-${row.row_version}`} row={row} workspace={workspace} canCreate={canCreate} canPost={canPost} canReverse={canReverse} ownerAdmin={ownerAdmin} onAction={onAction}/> : <ClaimActionPanel key={`claim-${row.id}-${row.row_version}`} row={row} canCreate={canCreate} canPost={canPost} canReverse={canReverse} ownerAdmin={ownerAdmin} onAction={onAction}/>}
    <section className="cbsr-history"><header><History/><div><span>AUTHORITATIVE HISTORY</span><strong>Rework, resolution, dan HOLD tidak ditimpa</strong></div></header>
      {row.rework_orders.map((order) => <article key={order.id}><Wrench/><div><small>{order.destination_type} · {new Date(order.physical_sent_at).toLocaleString('id-ID')}</small><strong>{order.rework_number} · {order.qty_sent} pcs</strong><span>{order.contractor_name ?? order.vendor_name} · {statusLabel(order.status)} · {order.components.length} komponen kerja · {order.accessory_decision.selected_item_count} aksesori</span><span>{order.accessory_decision.selected_items.map((item) => item.name).join(', ') || `Pilihan aksesori ${order.accessory_decision.state}`}</span>{order.status === 'COMPLETED' ? <ReworkCompletion order={order} workspace={workspace} canCreate={canCreate} canPost={canPost} canReverse={canReverse} ownerAdmin={ownerAdmin} onAction={onAction}/> : null}</div></article>)}
      {row.resolutions.map((resolution) => <article key={resolution.id}><PackageCheck/><div><small>{new Date(resolution.physical_at).toLocaleString('id-ID')}</small><strong>{statusLabel(resolution.resolution_type)} · {resolution.qty_pcs} pcs</strong><span>{money(resolution.compensation_amount)} · {resolution.notes ?? 'Tanpa catatan'}</span>{row.kind === 'BS' && !resolution.source_rework_order_id ? <div className="cbsr-inline-reverse"><input value={reverseReason} onChange={(event) => setReverseReason(event.target.value)} placeholder="Alasan reversal Owner/Admin"/><button disabled={!canReverse || !ownerAdmin || reverseReason.trim().length < 4} onClick={() => void onAction('REVERSE_DISPOSITION', { resolution_id: resolution.id, change_reason: reverseReason.trim() }, row.row_version)}><Undo2/> Reverse</button></div> : null}</div></article>)}
      {row.hold_events.map((event) => <article key={event.id}><Clock3/><div><small>{event.actor_name ?? 'System'} · {new Date(event.physical_at).toLocaleString('id-ID')}</small><strong>{event.action} · {statusLabel(event.previous_status)} → {statusLabel(event.resulting_status)}</strong><span>{event.reason}</span></div></article>)}
      {row.rework_orders.length + row.resolutions.length + row.hold_events.length === 0 ? <div className="cbsr-empty-history">Belum ada lifecycle event sesudah kasus dibuat.</div> : null}
    </section>
  </main>
}

export default function ConnectedBsResolutionPage() {
  const { runtime, identity } = useAuth()
  if (runtime.mode !== 'UAT_AUTH_SIMULATION') throw new Error('ConnectedBsResolutionPage hanya untuk ERP Enteng UAT.')
  const client = useMemo(() => getUatSupabaseClient(runtime), [runtime])
  const access = identity.status === 'AUTHORIZED' ? identity : null
  const canCreate = hasPermission(access, 'production.bs_rework.create')
  const canPost = hasPermission(access, SENSITIVE_ACTION_PERMISSION.postBsResolution)
  const canReverse = hasPermission(access, SENSITIVE_ACTION_PERMISSION.reverseBsResolution)
  const ownerAdmin = Boolean(access && ['OWNER', 'ADMIN'].includes(access.profile.role))
  const [filter, setFilter] = useState<BsWorkspaceFilter>('ACTIVE')
  const [kind, setKind] = useState<BsWorkspaceKind>('ALL')
  const [patternId, setPatternId] = useState('')
  const [query, setQuery] = useState('')
  const [offset, setOffset] = useState(0)
  const [workspace, setWorkspace] = useState<BsResolutionWorkspace | null>(null)
  const [selectedKey, setSelectedKey] = useState('')
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const busyRef = useRef(false)
  const actionRequestRef = useRef<{ fingerprint: string; id: string }>({ fingerprint: '', id: '' })
  const loadRequestRef = useRef(0)
  const viewRef = useRef({ filter, kind, patternId, query })
  viewRef.current = { filter, kind, patternId, query }
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [workspaceStale, setWorkspaceStale] = useState(false)
  const [createMode, setCreateMode] = useState<'BS' | 'CLAIM' | null>(null)

  const load = useCallback(async (
    nextFilter = filter, nextKind = kind, nextPattern = patternId, nextQuery = query,
    nextOffset = offset,
  ) => {
    const requestId = ++loadRequestRef.current
    setLoading(true); setError('')
    try {
      const { data, error: loadError } = await client.rpc('erp_get_bs_resolution_workspace_v1', {
        p_filter: nextFilter, p_kind: nextKind, p_pattern_id: nextPattern || null,
        p_query: nextQuery.trim() || null, p_limit: 50, p_offset: nextOffset,
      })
      if (requestId !== loadRequestRef.current) return false
      if (loadError) {
        setError(normalizeClientError(loadError).message)
        return false
      }
      try {
        const parsed = parseBsResolutionWorkspace(data)
        setWorkspace(parsed)
        setWorkspaceStale(false)
        setOffset(parsed.offset)
        setSelectedKey((current) => parsed.rows.some((row) => row.case_key === current) ? current : parsed.rows[0]?.case_key ?? '')
        return true
      } catch (parseError) { setError(parseError instanceof Error ? parseError.message : String(parseError)); return false }
    } catch (loadFailure) {
      if (requestId === loadRequestRef.current) setError(normalizeClientError(loadFailure).message)
      return false
    } finally {
      if (requestId === loadRequestRef.current) setLoading(false)
    }
  }, [client, filter, kind, offset, patternId, query])

  useEffect(() => { void load() }, []) // eslint-disable-line react-hooks/exhaustive-deps
  const runAction: RunAction = useCallback(async (action, payload, expectedVersion) => {
    if (busyRef.current) return false
    if (workspaceStale) {
      setError('Workspace belum authoritative. Refetch wajib berhasil sebelum aksi lain dijalankan.')
      return false
    }
    busyRef.current = true
    setBusy(true); setError(''); setNotice('')
    try {
      const fingerprint = JSON.stringify({ action, payload, expectedVersion })
      if (actionRequestRef.current.fingerprint !== fingerprint) {
        actionRequestRef.current = { fingerprint, id: globalThis.crypto.randomUUID() }
      }
      const { error: actionError } = await client.rpc('erp_save_bs_resolution_action_v1', {
        p_action: action, p_payload: payload, p_client_request_id: actionRequestRef.current.id,
        p_expected_version: expectedVersion,
      })
      if (actionError) throw normalizeClientError(actionError)
      actionRequestRef.current = { fingerprint: '', id: '' }
      setWorkspaceStale(true)
      const currentView = viewRef.current
      const refetched = await load(currentView.filter, currentView.kind, currentView.patternId, currentView.query, 0)
      if (refetched) setNotice(`${statusLabel(action)} tersimpan. Workspace authoritative sudah dimuat ulang.`)
      else setError('Aksi sudah tersimpan, tetapi refresh authoritative gagal. Jangan ulangi aksi. Semua writer dibekukan sampai Refetch berhasil.')
      return true
    } catch (actionFailure) {
      setError(actionFailure instanceof Error ? actionFailure.message : String(actionFailure))
      return false
    } finally {
      busyRef.current = false
      setBusy(false)
    }
  }, [client, load, workspaceStale])

  const rows = workspace?.rows ?? []
  const selected = rows.find((row) => row.case_key === selectedKey) ?? rows[0]
  const activeQty = rows.reduce((sum, row) => sum + row.available_qty + row.active_rework_qty, 0)
  const hasClaimSource = Boolean(workspace && (
    workspace.lookups.laundry_sources.length > 0 || workspace.lookups.laundry_receipt_sources.length > 0
  ))
  const canPageBack = offset > 0
  const canPageForward = Boolean(workspace && offset + workspace.rows.length < workspace.total)
  const effectiveCanCreate = canCreate && !workspaceStale
  const effectiveCanPost = canPost && !workspaceStale
  const effectiveCanReverse = canReverse && !workspaceStale
  const selectedContractKey = selected ? [
    selected.case_key, selected.row_version, selected.status, selected.available_qty,
    selected.accessory_bom?.bom_version_id ?? 'NO_BOM',
    selected.accessory_bom?.items.map((item) => (
      `${item.id}.${item.default_selected}.${item.remaining_unentitled_good_qty_pcs}`
    )).join(',') ?? 'NO_ACCESSORY',
    selected.components.map((item) => (
      `${item.id}.${item.default_selected}.${item.remaining_new_work_qty_pcs}`
    )).join(','),
    selected.rework_orders.map((order) => `${order.id}.${order.row_version}`).join(','),
  ].join(':') : ''
  return <section className="connected-bs-resolution-page">
    <header className="cbsr-hero"><div><span>CP5 · AUTHORITATIVE RECOVERY</span><h1>Barang BS & Rework</h1><p>Resolve fisik, biaya, FG, dan claim dari satu lineage; browser tidak menulis tabel atau jurnal langsung.</p></div><div><button disabled={!effectiveCanCreate || !hasClaimSource} title={hasClaimSource ? 'Buat claim dari sumber fisik Laundry' : 'Belum ada surat kirim atau penerimaan BS yang dapat dijadikan sumber'} onClick={() => setCreateMode('CLAIM')}><Plus/> Claim Laundry</button><button className="primary" disabled={!effectiveCanCreate || !workspace} onClick={() => setCreateMode('BS')}><Plus/> BS legacy</button><button disabled={loading} onClick={() => void load()}><RefreshCw/> Refetch</button></div></header>
    <div className="cbsr-boundary"><ShieldCheck/><strong>UAT BACKEND CONNECTED</strong><span>Rework, rewash, HOLD, disposition, claim, HPP, dan reversal memakai fungsi kanonik server.</span></div>
    {error ? <div className="cbsr-alert error" role="alert"><AlertTriangle/><span>{error}</span><button onClick={() => setError('')}><X/></button></div> : null}
    {notice ? <div className="cbsr-alert notice"><Check/><span>{notice}</span><button onClick={() => setNotice('')}><X/></button></div> : null}
    {workspaceStale ? <div className="cbsr-alert error" role="alert"><AlertTriangle/><span>State layar stale setelah mutasi tersimpan. Jangan ulangi aksi; seluruh writer terkunci sampai Refetch authoritative berhasil.</span></div> : null}
    {busy ? <div className="cbsr-busy"><LoaderCircle className="spin"/> Mengunci transaksi dan memuat ulang state…</div> : null}
    <section className="cbsr-kpis"><article><span>TOTAL KASUS FILTER</span><strong>{workspace?.total ?? 0}</strong><small>{filter === 'ACTIVE' ? 'Closed disembunyikan' : filter}</small></article><article><span>QTY HALAMAN INI</span><strong>{activeQty} pcs</strong><small>Available + active rework</small></article><article><span>ON HOLD · HALAMAN</span><strong>{rows.filter((row) => row.status === 'ON_HOLD').length}</strong><small>Keputusan dibekukan eksplisit</small></article><article><span>CLAIM · HALAMAN</span><strong>{rows.filter((row) => row.kind === 'LAUNDRY_CLAIM').length}</strong><small>Filter halaman aktif</small></article></section>
    <section className="cbsr-workspace"><aside><header><div className="cbsr-tabs">{(['ACTIVE', 'CLOSED', 'ALL'] as const).map((value) => <button className={filter === value ? 'active' : ''} key={value} onClick={() => { setFilter(value); setOffset(0); void load(value, kind, patternId, query, 0) }}>{value === 'ACTIVE' ? 'Aktif' : value === 'CLOSED' ? 'Selesai' : 'Semua'}</button>)}</div><select aria-label="Jenis kasus CP5" value={kind} onChange={(event) => { const next = event.target.value as BsWorkspaceKind; setKind(next); setOffset(0); void load(filter, next, patternId, query, 0) }}><option value="ALL">BS + Claim</option><option value="BS">Barang BS</option><option value="LAUNDRY_CLAIM">Claim Laundry</option></select></header><label className="cbsr-search"><Search/><input value={query} onChange={(event) => setQuery(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter') { setOffset(0); void load(filter, kind, patternId, query, 0) } }} placeholder="Nomor, PO, model, Pola, pihak…"/><button onClick={() => { setOffset(0); void load(filter, kind, patternId, query, 0) }}>Cari</button></label><ConnectedPatternFilter label="FILTER POLA CP5" value={patternId} onChange={(next) => { setPatternId(next); setOffset(0); void load(filter, kind, next, query, 0) }}/>
      <div className="cbsr-list">{loading ? <div className="cbsr-empty"><LoaderCircle className="spin"/> Memuat kasus…</div> : rows.map((row) => <button type="button" className={`${row.case_key === selected?.case_key ? 'active ' : ''}${row.status === 'ON_HOLD' ? 'hold' : ''}`} key={row.case_key} onClick={() => setSelectedKey(row.case_key)}><span className={row.kind === 'BS' ? 'bs' : 'claim'}>{row.kind === 'BS' ? <Shirt/> : <Waves/>}</span><div><small>{row.po_number ?? row.legacy_reference ?? 'TANPA PO'} · {row.group_number ?? row.claim_type ?? 'UNTRACKED'}</small><strong>{row.number}</strong><em>{bsPatternLabel(row)}</em><p>{row.available_qty} tersedia · {row.active_rework_qty} rework</p></div><b>{statusLabel(row.status)}</b></button>)}{!loading && rows.length === 0 ? <div className="cbsr-empty"><Search/><strong>Tidak ada kasus pada filter ini</strong><small>Filter tidak mengubah transaksi.</small></div> : null}</div><footer className="cbsr-pagination"><span>{workspace?.total ? `${offset + 1}–${offset + rows.length} dari ${workspace.total}` : '0 kasus'}</span><div><button disabled={loading || !canPageBack} onClick={() => void load(filter, kind, patternId, query, Math.max(0, offset - 50))}>Sebelumnya</button><button disabled={loading || !canPageForward} onClick={() => void load(filter, kind, patternId, query, offset + 50)}>Berikutnya</button></div></footer>
    </aside>{selected && workspace ? <CaseDetail key={selectedContractKey} row={selected} workspace={workspace} canCreate={effectiveCanCreate} canPost={effectiveCanPost} canReverse={effectiveCanReverse} ownerAdmin={ownerAdmin} onAction={runAction}/> : <main className="cbsr-no-selection"><PackageCheck/><strong>Tidak ada detail</strong><small>Ubah filter atau buat kasus yang memang punya sumber fisik.</small></main>}</section>
    {createMode === 'BS' && workspace ? <CreateManualBs workspace={workspace} onClose={() => setCreateMode(null)} onAction={runAction}/> : null}
    {createMode === 'CLAIM' && workspace ? <CreateClaim workspace={workspace} onClose={() => setCreateMode(null)} onAction={runAction}/> : null}
  </section>
}
