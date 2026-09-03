import { useCallback, useEffect, useMemo, useState } from 'react'
import { AlertTriangle, Check, Clock3, Filter, Flag, RefreshCw, Search, ShieldCheck, SlidersHorizontal, X } from 'lucide-react'
import { useAuth } from './auth/AuthProvider'
import { hasPermission } from './auth/accessCatalog'
import { getUatSupabaseClient } from './lib/supabase'
import { normalizeClientError } from './lib/clientError'
import ConnectedPatternFilter from './ConnectedPatternFilter'
import './connected-wip-status.css'

export type WipStatusFilter = 'ACTIVE' | 'COMPLETED' | 'ALL'
export type WipStatusSort = 'PATTERN' | 'PRODUCTION' | 'UPDATED'

type OpenFlag = { id: string; type: string; note: string; row_version: number }

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
  control_status: 'ACTIVE' | 'COMPLETED'
  updated_at: string
  row_version: number
}

type WipResponse = { filter: WipStatusFilter; sort: WipStatusSort; pattern_id: string | null; rows: WipStatusRow[] }

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

function number(value: unknown) { const parsed = Number(value); return Number.isFinite(parsed) ? parsed : 0 }

export function parseWipResponse(value: unknown): WipResponse {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error('Respons WIP tidak valid.')
  const raw = value as Record<string, unknown>
  if (!['ACTIVE', 'COMPLETED', 'ALL'].includes(String(raw.filter)) || !['PATTERN', 'PRODUCTION', 'UPDATED'].includes(String(raw.sort)) || !Array.isArray(raw.rows)) throw new Error('Metadata respons WIP tidak valid.')
  const rows = raw.rows.map((candidate) => {
    if (!candidate || typeof candidate !== 'object' || Array.isArray(candidate)) throw new Error('Baris WIP tidak valid.')
    const row = candidate as Record<string, unknown>
    if (typeof row.cutting_group_id !== 'string' || !['ACTIVE', 'COMPLETED'].includes(String(row.control_status))) throw new Error('Identitas/status WIP tidak valid.')
    return {
      ...row,
      effective_qty_pcs: number(row.effective_qty_pcs),
      sewn_qty_pcs: number(row.sewn_qty_pcs),
      unfinished_sewing_qty_pcs: number(row.unfinished_sewing_qty_pcs),
      unsent_ready_qty_pcs: number(row.unsent_ready_qty_pcs),
      laundry_draft_qty_pcs: number(row.laundry_draft_qty_pcs),
      laundry_in_transit_qty_pcs: number(row.laundry_in_transit_qty_pcs),
      unresolved_laundry_issue_qty_pcs: number(row.unresolved_laundry_issue_qty_pcs),
      pending_final_sku_handoff_qty_pcs: number(row.pending_final_sku_handoff_qty_pcs),
      remaining_final_sku_qty_pcs: number(row.remaining_final_sku_qty_pcs),
      open_bs_count: number(row.open_bs_count),
      open_rework_count: number(row.open_rework_count),
      open_flag_count: number(row.open_flag_count),
      open_flags: Array.isArray(row.open_flags) ? row.open_flags : [],
      row_version: number(row.row_version),
    } as WipStatusRow
  })
  return { filter: raw.filter as WipStatusFilter, sort: raw.sort as WipStatusSort, pattern_id: typeof raw.pattern_id === 'string' ? raw.pattern_id : null, rows }
}

export function activeBlockerLabels(row: WipStatusRow) {
  return blockerLabels.filter(([key]) => number(row[key]) > 0).map(([, label]) => label)
}

export default function ConnectedWipStatusPage() {
  const { runtime, identity } = useAuth()
  if (runtime.mode !== 'UAT_AUTH_SIMULATION') throw new Error('ConnectedWipStatusPage hanya untuk ERP Enteng UAT.')
  const client = useMemo(() => getUatSupabaseClient(runtime), [runtime])
  const canAdjust = identity.status === 'AUTHORIZED' && hasPermission(identity, 'production.wip.adjust')
  const [filter, setFilter] = useState<WipStatusFilter>('ACTIVE')
  const [sort, setSort] = useState<WipStatusSort>('PATTERN')
  const [patternId, setPatternId] = useState('')
  const [query, setQuery] = useState('')
  const [response, setResponse] = useState<WipResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = useCallback(async (
    nextFilter: WipStatusFilter,
    nextSort: WipStatusSort,
    nextPattern: string,
    nextQuery: string,
  ) => {
    setLoading(true)
    setError('')
    const { data, error: loadError } = await client.rpc('erp_get_wip_control_v1', {
      p_filter: nextFilter,
      p_pattern_id: nextPattern || null,
      p_sort: nextSort,
      p_query: nextQuery.trim() || null,
    })
    if (loadError) setError(normalizeClientError(loadError).message)
    else {
      try { setResponse(parseWipResponse(data)) } catch (parseError) { setError(String(parseError)) }
    }
    setLoading(false)
  }, [client])

  useEffect(() => { void load('ACTIVE', 'PATTERN', '', '') }, [load])
  const changeFilter = (next: WipStatusFilter) => { setFilter(next); void load(next, sort, patternId, query) }
  const changeSort = (next: WipStatusSort) => { setSort(next); void load(filter, next, patternId, query) }
  const changePattern = (next: string) => { setPatternId(next); void load(filter, sort, next, query) }

  const flag = async (row: WipStatusRow) => {
    if (!canAdjust) return
    const note = globalThis.prompt('Tindak lanjut WIP yang masih diperlukan:')?.trim()
    if (!note) return
    const { error: flagError } = await client.rpc('erp_set_wip_control_flag_v1', {
      p_payload: {
        cutting_group_id: row.cutting_group_id,
        flag_type: 'OPERATOR_ACTION', status: 'OPEN', note,
        change_reason: 'Tindak lanjut operator dari WIP control',
      },
      p_client_request_id: globalThis.crypto.randomUUID(),
      p_expected_version: null,
    })
    if (flagError) setError(normalizeClientError(flagError).message)
    else await load(filter, sort, patternId, query)
  }

  const rows = response?.rows ?? []
  const qty = rows.reduce((sum, row) => sum + row.effective_qty_pcs, 0)
  const blocked = rows.filter((row) => activeBlockerLabels(row).length > 0).length

  return <section className="connected-wip-page">
    <header className="cwip-hero"><div><span>PRODUKSI · AUTHORITATIVE CONTROL</span><h1>WIP & Sewing</h1><p>Status Aktif/Selesai dihitung backend dari seluruh fakta sewing, Laundry, QC, BS/Rework, dan tindakan operator.</p></div><button onClick={() => void load(filter, sort, patternId, query)}><RefreshCw/> Refetch</button></header>
    <div className="cwip-truth"><ShieldCheck/><strong>UAT BACKEND CONNECTED</strong><span>Merek belum ditentukan sampai Good dialokasikan ke Final SKU.</span></div>
    {error && <div className="cwip-error" role="alert"><AlertTriangle/><span>{error}</span><button onClick={() => setError('')}><X/></button></div>}

    <section className="cwip-kpis"><article><span>BARIS TAMPIL</span><strong>{rows.length}</strong><small>{filter === 'ACTIVE' ? 'Selesai disembunyikan' : filter === 'COMPLETED' ? 'Riwayat selesai' : 'Aktif + selesai'}</small></article><article><span>KUANTITAS</span><strong>{qty} pcs</strong><small>Read-only control total</small></article><article><span>MASIH ADA AKSI</span><strong>{blocked}</strong><small>Gabungan seluruh blocker</small></article></section>

    <section className="cwip-workspace"><header><div className="cwip-tabs" role="tablist" aria-label="Status WIP">{(['ACTIVE', 'COMPLETED', 'ALL'] as const).map((value) => <button className={filter === value ? 'active' : ''} onClick={() => changeFilter(value)} key={value}>{value === 'ACTIVE' ? 'Aktif' : value === 'COMPLETED' ? 'Selesai' : 'Semua'}</button>)}</div><label className="cwip-search"><Search/><input value={query} onChange={(event) => setQuery(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter') void load(filter, sort, patternId, query) }} placeholder="Nomor produksi, model, Pola, mandor, status…"/><button onClick={() => void load(filter, sort, patternId, query)}><Filter/> Terapkan</button></label><ConnectedPatternFilter value={patternId} onChange={changePattern}/><select aria-label="Urutan WIP" value={sort} onChange={(event) => changeSort(event.target.value as WipStatusSort)}><option value="PATTERN">Urutan Pola</option><option value="PRODUCTION">Kronologi produksi</option><option value="UPDATED">Terakhir diperbarui</option></select></header>
      {loading ? <div className="cwip-empty"><RefreshCw className="spin"/><strong>Mengambil status authoritative…</strong></div> : <div className="cwip-list">{rows.map((row) => {
        const blockers = activeBlockerLabels(row)
        return <article key={row.cutting_group_id} className={row.control_status.toLowerCase()}><header><span className="cwip-order">{row.pattern_sort_order ?? '—'}</span><div><small>{row.po_number} · {row.group_number}</small><h2>{row.model_code} · {row.model_name}</h2><p>{row.executor_name || 'Mandor belum ditentukan'} · Merek belum ditentukan</p></div><em>{row.control_status === 'COMPLETED' ? <><Check/> SELESAI</> : <><Clock3/> AKTIF</>}</em></header><div className="cwip-facts"><span><small>POLA · SNAPSHOT</small><strong>{row.pattern_code ? `${row.pattern_code} · ${row.pattern_revision || 'R1'} · ${row.pattern_name}` : 'Belum ditentukan'}</strong></span><span><small>EFEKTIF</small><strong>{row.effective_qty_pcs} pcs</strong></span><span><small>SELESAI DIJAHIT</small><strong>{row.sewn_qty_pcs} pcs</strong></span><span><small>FINAL SKU TERSISA</small><strong>{row.remaining_final_sku_qty_pcs} pcs</strong></span></div><div className="cwip-blockers">{blockers.length ? blockers.map((label) => <span key={label}><AlertTriangle/>{label}</span>) : <span className="clear"><Check/> Tidak ada aksi WIP tersisa</span>}</div>{row.open_flags.length > 0 && <div className="cwip-flags">{row.open_flags.map((openFlag) => <span key={openFlag.id}><Flag/><strong>{openFlag.type.replaceAll('_', ' ')}</strong>{openFlag.note}</span>)}</div>}<footer><span><SlidersHorizontal/> Row version {row.row_version} · diperbarui {new Date(row.updated_at).toLocaleString('id-ID')}</span>{row.control_status === 'ACTIVE' && <button disabled={!canAdjust} onClick={() => void flag(row)}><Flag/> Tandai tindak lanjut</button>}</footer></article>
      })}{rows.length === 0 && <div className="cwip-empty"><Check/><strong>{filter === 'ACTIVE' ? 'Tidak ada WIP aktif.' : 'Tidak ada data pada filter ini.'}</strong><span>Filter tidak mengubah state bisnis.</span></div>}</div>}
    </section>
  </section>
}
