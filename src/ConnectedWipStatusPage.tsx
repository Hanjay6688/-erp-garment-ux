import { parseInitialProductionSources, type InitialProductionSource } from './initialProduction'
import { isConnectedRuntime } from './config/runtime'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { AlertTriangle, Check, Clock3, Filter, Flag, RefreshCw, Search, ShieldCheck, SlidersHorizontal, X } from 'lucide-react'
import { useAuth } from './auth/AuthProvider'
import { hasPermission } from './auth/accessCatalog'
import { getUatSupabaseClient } from './lib/supabase'
import { normalizeClientError } from './lib/clientError'
import ConnectedPatternFilter from './ConnectedPatternFilter'
import { useProductionMutation } from './useProductionMutation'
import ProductionRecoveryNotice from './ProductionRecoveryNotice'
import type { ProductionEnvelope } from './productionRecovery'
import './connected-wip-status.css'

export type WipStatusFilter = 'ACTIVE' | 'COMPLETED' | 'ALL'
export type WipStatusSort = 'PATTERN' | 'PRODUCTION' | 'UPDATED'

type OpenFlag = { id: string; type: string; note: string; row_version: number }
type WipDistributionSize = { size_code: string; qty_pcs: number }
type WipDistributionBatch = { id: string; batch_no: number; notes: string | null; qty_pcs: number; sizes: WipDistributionSize[] }
type WipDistribution = {
  pickup_id: string
  contractor_id: string
  contractor_name: string
  picked_up_at: string
  allocation_mode: 'ROLL' | 'SIZE'
  batches: WipDistributionBatch[]
}

export type WipStatusRow = {
  cutting_group_id: string
  po_number: string
  group_number: string
  model_code: string
  model_name: string
  executor_name: string | null
  pattern_id: string | null
  pattern_code: string | null
  pattern_revision: string | null
  pattern_name: string | null
  pattern_sort_order: number | null
  pattern_is_active: boolean | null
  effective_qty_pcs: number
  sewn_qty_pcs: number
  unfinished_sewing_qty_pcs: number
  unsent_ready_qty_pcs: number
  laundry_draft_qty_pcs: number
  laundry_in_transit_qty_pcs: number
  unresolved_laundry_issue_qty_pcs: number
  pending_final_sku_handoff_qty_pcs: number
  remaining_final_sku_qty_pcs: number
  open_bs_count: number
  open_rework_count: number
  open_flag_count: number
  open_flags: OpenFlag[]
  distribution: WipDistribution | null
  control_status: 'ACTIVE' | 'COMPLETED'
  updated_at: string
  row_version: number
}

type WipResponse = { filter: WipStatusFilter; sort: WipStatusSort; pattern_id: string | null; rows: WipStatusRow[]; opening_rows: InitialProductionSource[] }

const blockerLabels: ReadonlyArray<[keyof WipStatusRow, string]> = [
  ['unfinished_sewing_qty_pcs', 'Belum selesai jahit'],
  ['unsent_ready_qty_pcs', 'Siap tapi belum dikirim'],
  ['laundry_draft_qty_pcs', 'Draft Laundry'],
  ['laundry_in_transit_qty_pcs', 'Di perjalanan/Laundry'],
  ['unresolved_laundry_issue_qty_pcs', 'Stuck/Missing'],
  ['pending_final_sku_handoff_qty_pcs', 'Menunggu handoff QC'],
  ['remaining_final_sku_qty_pcs', 'Belum Final SKU'],
  ['open_bs_count', 'BS terbuka'],
  ['open_rework_count', 'Rework terbuka'],
  ['open_flag_count', 'Tindakan operator'],
]

function object(value: unknown, name: string): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error(`${name} WIP tidak valid.`)
  return value as Record<string, unknown>
}
function list(value: unknown, name: string): unknown[] {
  if (!Array.isArray(value)) throw new Error(`${name} WIP tidak lengkap.`)
  return value
}
function text(value: unknown, name: string): string {
  if (typeof value !== 'string' || value.trim().length === 0) throw new Error(`${name} WIP tidak lengkap.`)
  return value
}
function nullableText(value: unknown, name: string): string | null {
  if (value === null) return null
  if (typeof value !== 'string') throw new Error(`${name} WIP tidak lengkap.`)
  return value
}
function count(value: unknown, name: string, min = 0): number {
  if (typeof value !== 'number' || !Number.isSafeInteger(value) || value < min) throw new Error(`${name} WIP harus bilangan bulat yang valid.`)
  return value
}
function timestamp(value: unknown, name: string): string {
  const result = text(value, name)
  if (!Number.isFinite(Date.parse(result))) throw new Error(`${name} WIP tidak valid.`)
  return result
}
function unique(values: readonly (string | number)[], name: string) {
  if (new Set(values).size !== values.length) throw new Error(`${name} WIP duplikat.`)
}
function parseDistribution(value: unknown): WipDistribution | null {
  if (value === null) return null
  const raw = object(value, 'Lineage distribusi')
  if (raw.allocation_mode !== 'ROLL' && raw.allocation_mode !== 'SIZE') throw new Error('Mode distribusi WIP tidak valid.')
  const batches = list(raw.batches, 'Batch distribusi').map((candidate) => {
    const batch = object(candidate, 'Batch')
    const sizes = list(batch.sizes, 'Size batch').map((candidate) => {
      const size = object(candidate, 'Size')
      return { size_code: text(size.size_code, 'Kode size'), qty_pcs: count(size.qty_pcs, 'Qty size', 1) }
    })
    unique(sizes.map((size) => size.size_code), 'Size batch')
    const qty_pcs = count(batch.qty_pcs, 'Qty batch', 1)
    if (sizes.reduce((sum, size) => sum + size.qty_pcs, 0) !== qty_pcs) throw new Error('Total size dan batch WIP tidak cocok.')
    return { id: text(batch.id, 'ID batch'), batch_no: count(batch.batch_no, 'Nomor batch', 1),
      notes: batch.notes === null || batch.notes === '' ? batch.notes : text(batch.notes, 'Catatan batch'), qty_pcs, sizes }
  })
  if (batches.length === 0) throw new Error('Distribusi WIP tanpa batch.')
  unique(batches.map((batch) => batch.id), 'ID batch')
  unique(batches.map((batch) => batch.batch_no), 'Nomor batch')
  return {
    pickup_id: text(raw.pickup_id, 'ID pickup'), contractor_id: text(raw.contractor_id, 'ID Mandor'),
    contractor_name: text(raw.contractor_name, 'Nama Mandor'), picked_up_at: timestamp(raw.picked_up_at, 'Waktu pickup'),
    allocation_mode: raw.allocation_mode, batches,
  }
}

export function parseWipResponse(value: unknown): WipResponse {
  const raw = object(value, 'Respons')
  if (!['ACTIVE', 'COMPLETED', 'ALL'].includes(String(raw.filter)) || !['PATTERN', 'PRODUCTION', 'UPDATED'].includes(String(raw.sort))) throw new Error('Metadata respons WIP tidak valid.')
  const rows: WipStatusRow[] = list(raw.rows, 'Daftar baris').map((candidate) => {
    const row = object(candidate, 'Baris')
    if (row.control_status !== 'ACTIVE' && row.control_status !== 'COMPLETED') throw new Error('Status WIP tidak valid.')
    if (row.pattern_is_active !== null && typeof row.pattern_is_active !== 'boolean') throw new Error('Status Pola WIP tidak valid.')
    const open_flags = list(row.open_flags, 'Daftar flag').map((candidate) => {
      const flag = object(candidate, 'Flag')
      const type = text(flag.type, 'Jenis flag')
      if (!['PENDING_CORRECTION', 'PENDING_REVERSAL', 'PENDING_HANDOFF', 'OPERATOR_ACTION'].includes(type)) throw new Error('Jenis flag WIP tidak valid.')
      return { id: text(flag.id, 'ID flag'), type, note: text(flag.note, 'Catatan flag'), row_version: count(flag.row_version, 'Versi flag', 1) }
    })
    const open_flag_count = count(row.open_flag_count, 'Jumlah flag')
    if (open_flag_count !== open_flags.length) throw new Error('Jumlah flag WIP tidak cocok.')
    unique(open_flags.map((flag) => flag.id), 'ID flag')
    return {
      cutting_group_id: text(row.cutting_group_id, 'ID Potongan'), po_number: text(row.po_number, 'Nomor PO'),
      group_number: text(row.group_number, 'Nomor Potongan'), model_code: text(row.model_code, 'Kode model'), model_name: text(row.model_name, 'Nama model'),
      executor_name: row.executor_name === '' ? '' : nullableText(row.executor_name, 'Pelaksana'),
      pattern_id: nullableText(row.pattern_id, 'ID Pola'), pattern_code: nullableText(row.pattern_code, 'Kode Pola'),
      pattern_revision: nullableText(row.pattern_revision, 'Revisi Pola'), pattern_name: nullableText(row.pattern_name, 'Nama Pola'),
      pattern_sort_order: row.pattern_sort_order === null ? null : count(row.pattern_sort_order, 'Urutan Pola', -Number.MAX_SAFE_INTEGER),
      pattern_is_active: row.pattern_is_active,
      effective_qty_pcs: count(row.effective_qty_pcs, 'Qty efektif'), sewn_qty_pcs: count(row.sewn_qty_pcs, 'Qty jahit'),
      unfinished_sewing_qty_pcs: count(row.unfinished_sewing_qty_pcs, 'Belum jahit'),
      unsent_ready_qty_pcs: count(row.unsent_ready_qty_pcs, 'Siap belum dikirim'), laundry_draft_qty_pcs: count(row.laundry_draft_qty_pcs, 'Draft Laundry'),
      laundry_in_transit_qty_pcs: count(row.laundry_in_transit_qty_pcs, 'Dalam perjalanan'),
      unresolved_laundry_issue_qty_pcs: count(row.unresolved_laundry_issue_qty_pcs, 'Masalah Laundry'),
      pending_final_sku_handoff_qty_pcs: count(row.pending_final_sku_handoff_qty_pcs, 'Handoff QC'),
      remaining_final_sku_qty_pcs: count(row.remaining_final_sku_qty_pcs, 'Belum Final SKU'),
      open_bs_count: count(row.open_bs_count, 'BS terbuka'), open_rework_count: count(row.open_rework_count, 'Rework terbuka'),
      open_flag_count, open_flags, distribution: parseDistribution(row.distribution), control_status: row.control_status,
      updated_at: timestamp(row.updated_at, 'Waktu pembaruan'), row_version: count(row.row_version, 'Versi baris', 1),
    }
  })
  unique(rows.map((row) => row.cutting_group_id), 'ID Potongan')
  return { filter: raw.filter as WipStatusFilter, sort: raw.sort as WipStatusSort, pattern_id: nullableText(raw.pattern_id, 'Filter Pola'), rows, opening_rows:parseInitialProductionSources(raw.opening_rows) }
}

export function activeBlockerLabels(row: WipStatusRow) {
  return blockerLabels.filter(([key]) => typeof row[key] === 'number' && (row[key] as number) > 0).map(([, label]) => label)
}

export default function ConnectedWipStatusPage() {
  const { runtime, identity } = useAuth()
  if (!isConnectedRuntime(runtime)) throw new Error('ConnectedWipStatusPage hanya untuk ERP Enteng UAT.')
  const client = useMemo(() => getUatSupabaseClient(runtime), [runtime])
  const canAdjust = identity.status === 'AUTHORIZED' && hasPermission(identity, 'production.wip.adjust')
  const [filter, setFilter] = useState<WipStatusFilter>('ACTIVE')
  const [sort, setSort] = useState<WipStatusSort>('PATTERN')
  const [patternId, setPatternId] = useState('')
  const [query, setQuery] = useState('')
  const [response, setResponse] = useState<WipResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const mutation = useProductionMutation('WIP')
  const { beginRead, finishRead, run, reconcile } = mutation
  const flagging = mutation.writerLocked
  const [error, setError] = useState('')
  const loadRequestRef = useRef(0)
  const viewRef = useRef({ filter, sort, patternId, query })
  viewRef.current = { filter, sort, patternId, query }

  const load = useCallback(async (nextFilter = filter, nextSort = sort, nextPattern = patternId, nextQuery = query) => {
    const ticket = beginRead()
    const requestId = ++loadRequestRef.current
    setLoading(true)
    setError('')
    try {
      const { data, error: loadError } = await client.rpc('erp_get_wip_control_v1', {
        p_filter: nextFilter,
        p_pattern_id: nextPattern || null,
        p_sort: nextSort,
        p_query: nextQuery.trim() || null,
      })
      if (requestId !== loadRequestRef.current) return false
      if (loadError) {
        setError(normalizeClientError(loadError).message)
        return false
      }
      try {
        const parsed = parseWipResponse(data)
        if (parsed.filter !== nextFilter || parsed.sort !== nextSort || parsed.pattern_id !== (nextPattern || null)) throw new Error('Respons WIP tidak cocok dengan filter yang diminta.')
        setResponse(parsed)
        return finishRead(ticket)
      } catch (parseError) {
        setError(parseError instanceof Error ? parseError.message : String(parseError))
        return false
      }
    } catch (loadFailure) {
      if (requestId === loadRequestRef.current) setError(normalizeClientError(loadFailure).message)
      return false
    } finally {
      if (requestId === loadRequestRef.current) setLoading(false)
    }
  }, [beginRead, finishRead, client, filter, patternId, query, sort])

  useEffect(() => { void load(); return () => { loadRequestRef.current += 1 } }, [mutation.scope]) // eslint-disable-line react-hooks/exhaustive-deps
  const changeFilter = (next: WipStatusFilter) => { setFilter(next); void load(next, sort, patternId, query) }
  const changeSort = (next: WipStatusSort) => { setSort(next); void load(filter, next, patternId, query) }
  const changePattern = (next: string) => { setPatternId(next); void load(filter, sort, next, query) }

  const handlers = {
    send: (envelope: ProductionEnvelope) => client.rpc('erp_set_wip_control_flag_v1', {
      p_payload: envelope.payload, p_client_request_id: envelope.id, p_expected_version: envelope.expectedVersion,
    }),
    validate: (data: unknown, envelope: ProductionEnvelope) => {
      const result = object(data, 'Respons flag')
      text(result.flag_id, 'ID flag'); count(result.row_version, 'Versi flag', 1)
      if (result.status !== envelope.action) throw new Error('Status flag tidak cocok')
    },
    retire: () => setResponse(null),
    reload: () => {
      const view = viewRef.current
      return load(view.filter, view.sort, view.patternId, view.query)
    },
  }
  const flag = async (row: WipStatusRow) => {
    if (!canAdjust || mutation.writerLocked) return
    const note = globalThis.prompt('Tindak lanjut WIP yang masih diperlukan:')?.trim()
    if (!note) return
    setError('')
    await run('OPEN', { cutting_group_id: row.cutting_group_id, flag_type: 'OPERATOR_ACTION', status: 'OPEN', note,
      change_reason: 'Tindak lanjut operator dari WIP control' }, null, handlers)
  }

  const rows = response?.rows ?? []
  const openingRows = response?.opening_rows ?? []
  const qty = rows.reduce((sum, row) => sum + row.effective_qty_pcs, 0) + openingRows.reduce((sum, row) => sum + row.qty_pcs, 0)
  const totalsKnown = response !== null && !mutation.workspaceStale
  const blocked = rows.filter((row) => activeBlockerLabels(row).length > 0).length + openingRows.filter(row => row.remaining_qty_pcs > 0).length

  return <section className="connected-wip-page">
    <ProductionRecoveryNotice recovery={mutation} onReconcile={() => reconcile(handlers)} className="cwip-error"/>
    <header className="cwip-hero"><div><span>PRODUKSI · AUTHORITATIVE CONTROL</span><h1>WIP & Sewing</h1><p>Status Aktif/Selesai dihitung backend dari seluruh fakta sewing, Laundry, QC, BS/Rework, dan tindakan operator.</p></div><button onClick={() => void load()}><RefreshCw/> Refetch</button></header>
    <div className="cwip-truth"><ShieldCheck/><strong>UAT BACKEND CONNECTED</strong><span>Merek belum ditentukan sampai Good dialokasikan ke Final SKU.</span></div>
    {error && <div className="cwip-error" role="alert"><AlertTriangle/><span>{error}</span><button onClick={() => setError('')}><X/></button></div>}

    <section className="cwip-kpis"><article><span>BARIS TAMPIL</span><strong>{totalsKnown ? rows.length + openingRows.length : '—'}</strong><small>{filter === 'ACTIVE' ? 'Selesai disembunyikan' : filter === 'COMPLETED' ? 'Riwayat selesai' : 'Aktif + selesai'}</small></article><article><span>KUANTITAS</span><strong>{totalsKnown ? `${qty} pcs` : '—'}</strong><small>Read-only control total</small></article><article><span>MASIH ADA AKSI</span><strong>{totalsKnown ? blocked : '—'}</strong><small>Gabungan seluruh blocker</small></article></section>

    {!loading && openingRows.length > 0 && <section className="cwip-workspace" aria-label="WIP saldo awal"><h2>Produksi yang dibawa saat saldo awal</h2><div className="cwip-list">{openingRows.map(s => <article key={s.opening_item_id}><header><div><small>{s.po_number} · {s.source_key}</small><h3>{s.balance_type} · Ukuran {s.size_code}</h3><p>Tahap saat saldo awal: {s.stage} · {(s.stage === 'LAUNDRY' ? s.vendor_name : s.contractor_name ?? s.vendor_name) ?? 'Pemegang mengikuti saldo awal'}</p></div></header><div className="cwip-facts"><span><small>AWAL</small><strong>{s.qty_pcs} pcs</strong></span><span><small>TERSISA</small><strong>{s.remaining_qty_pcs} pcs</strong></span></div><p>{s.balance_type === 'BS' ? 'Lanjutkan melalui BS/Rework.' : 'Hasil saldo awal dicatat owner/admin pada rincian impor awal.'}</p></article>)}</div></section>}
    <section className="cwip-workspace"><header><div className="cwip-tabs" role="tablist" aria-label="Status WIP">{(['ACTIVE', 'COMPLETED', 'ALL'] as const).map((value) => <button className={filter === value ? 'active' : ''} onClick={() => changeFilter(value)} key={value}>{value === 'ACTIVE' ? 'Aktif' : value === 'COMPLETED' ? 'Selesai' : 'Semua'}</button>)}</div><label className="cwip-search"><Search/><input value={query} onChange={(event) => setQuery(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter') void load() }} placeholder="Nomor produksi, model, Pola, mandor, status…"/><button onClick={() => void load()}><Filter/> Terapkan</button></label><ConnectedPatternFilter value={patternId} onChange={changePattern}/><select aria-label="Urutan WIP" value={sort} onChange={(event) => changeSort(event.target.value as WipStatusSort)}><option value="PATTERN">Urutan Pola</option><option value="PRODUCTION">Kronologi produksi</option><option value="UPDATED">Terakhir diperbarui</option></select></header>
      {loading ? <div className="cwip-empty"><RefreshCw className="spin"/><strong>Mengambil status authoritative…</strong></div> : <div className="cwip-list">{rows.map((row) => {
        const blockers = activeBlockerLabels(row)
        return <article key={row.cutting_group_id} className={row.control_status.toLowerCase()}>
          <header><span className="cwip-order">{row.pattern_sort_order ?? '—'}</span><div><small>{row.po_number} · {row.group_number}</small><h2>{row.model_code} · {row.model_name}</h2><p>{row.executor_name || 'Mandor belum ditentukan'} · Merek belum ditentukan</p></div><em>{row.control_status === 'COMPLETED' ? <><Check/> SELESAI</> : <><Clock3/> AKTIF</>}</em></header>
          <div className="cwip-facts"><span><small>POLA · SNAPSHOT</small><strong>{row.pattern_code ? `${row.pattern_code} · ${row.pattern_revision || 'R1'} · ${row.pattern_name}` : 'Belum ditentukan'}</strong></span><span><small>EFEKTIF</small><strong>{row.effective_qty_pcs} pcs</strong></span><span><small>SELESAI DIJAHIT</small><strong>{row.sewn_qty_pcs} pcs</strong></span><span><small>FINAL SKU TERSISA</small><strong>{row.remaining_final_sku_qty_pcs} pcs</strong></span></div>
          {row.distribution && <section className="cwip-distribution">
            <header><div><small>BATCH DISTRIBUSI · LINEAGE TERKUNCI</small><strong>{row.distribution.contractor_name}</strong><span>Pickup {new Date(row.distribution.picked_up_at).toLocaleString('id-ID')} · susun {row.distribution.allocation_mode === 'ROLL' ? 'per roll' : 'per size'}</span></div><b>{row.distribution.batches.length} batch</b></header>
            <div>{row.distribution.batches.map((batch) => <article key={batch.id}><span>#{String(batch.batch_no).padStart(2, '0')}</span><div><strong>{batch.qty_pcs} pcs</strong><small>{batch.notes || 'Tanpa catatan jahitan'}</small></div><p>{batch.sizes.map((size) => <em key={size.size_code}>{size.size_code} · {size.qty_pcs}</em>)}</p></article>)}</div>
          </section>}
          <div className="cwip-blockers">{blockers.length ? blockers.map((label) => <span key={label}><AlertTriangle/>{label}</span>) : <span className="clear"><Check/> Tidak ada aksi WIP tersisa</span>}</div>
          {row.open_flags.length > 0 && <div className="cwip-flags">{row.open_flags.map((openFlag) => <span key={openFlag.id}><Flag/><strong>{openFlag.type.replaceAll('_', ' ')}</strong>{openFlag.note}</span>)}</div>}
          <footer><span><SlidersHorizontal/> Row version {row.row_version} · diperbarui {new Date(row.updated_at).toLocaleString('id-ID')}</span>{row.control_status === 'ACTIVE' && <button disabled={!canAdjust || flagging} onClick={() => void flag(row)}><Flag/> {flagging ? 'Menyimpan…' : 'Tandai tindak lanjut'}</button>}</footer>
        </article>
      })}{rows.length === 0 && openingRows.length === 0 && <div className="cwip-empty"><Check/><strong>{filter === 'ACTIVE' ? 'Tidak ada WIP aktif.' : 'Tidak ada data pada filter ini.'}</strong><span>Filter tidak mengubah state bisnis.</span></div>}</div>}
    </section>
  </section>
}
