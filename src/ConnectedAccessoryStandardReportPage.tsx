import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useAuth } from './auth/AuthProvider'
import { isConnectedRuntime } from './config/runtime'
import { getUatSupabaseClient } from './lib/supabase'
import { formatCp6WibDateTime } from './cp6BusinessTime'
import { accessoryReportNumber as number, accessoryReportPeriod, accessoryReportReason, parseAccessoryReportWorkspace,
  type AccessoryReportQuery, type AccessoryReportWorkspace, type AccessoryPeriodReport } from './accessoryStandardReport'
import './accessory-standard-report.css'

// Additive standalone page. The integrator chooses its menu/tab after the SKU
// stage is qualified; no existing route, parent writer or shared RPC type moves.
// Use the application's one authenticated client. This narrow adapter declares
// only the new read; it does not expose arbitrary RPCs or create another client.
type ReadRpc = (name: 'erp_cp7_get_accessory_standard_report_v1', args: { p_start: string; p_end: string; p_contractor: string | null;
  p_po: string | null; p_query: string; p_offset: number; p_limit: number }) => PromiseLike<{ data: unknown; error: unknown }>
const PAGE = 30
function todayWib() { return new Date(Date.now() + 7 * 3600000).toISOString().slice(0, 10) }
function failureText(failure: unknown) {
  const r = failure && typeof failure === 'object' ? failure as Record<string, unknown> : {}
  const m = typeof r.message === 'string' ? r.message : ''
  if (r.code === '42501' || r.status === 401 || r.status === 403 || m.includes('CP7_ACCESSORY_REPORT_DENIED') || m.includes('CP7_ACCESSORY_REPORT_ACCESS_CHANGED')) return 'Hak akses laporan sudah berubah atau sesi berakhir. Periksa akun dan muat ulang.'
  if (m.includes('CP7_ACCESSORY_REPORT_TOO_LARGE')) return 'Sumber melebihi batas pembaca. Persempit periode atau pilih PO; angka belum ditampilkan.'
  if (m.includes('CP7_ACCESSORY_REPORT_FIELDS')) return 'Periode, mandor atau PO tidak sah. Periksa pilihan lalu muat ulang.'
  if (failure instanceof Error) return failure.message
  return 'Laporan belum berhasil dibaca. Muat ulang untuk memperoleh angka terbaru.'
}
const qty = (value: string | null, unit: string | null) => value === null ? 'Belum diketahui' : `${number(value)} ${unit ?? '(satuan belum diketahui)'}`

export default function ConnectedAccessoryStandardReportPage({ refresh = 0 }: { refresh?: number }) {
  const { runtime, identity } = useAuth()
  if (!isConnectedRuntime(runtime) || identity.status !== 'AUTHORIZED') return <section className="panel"><h1>Aksesori mandor vs standar</h1><p>Masuk ke ERP yang tersambung untuk membaca laporan.</p></section>
  const allowed = ['OWNER', 'ADMIN'].includes(identity.profile.role) && identity.permissions.includes('finance.contractor_accessory.view') && identity.permissions.includes('finance.hpp.view')
  if (!allowed) return <section className="panel" role="alert"><h1>Aksesori mandor vs standar</h1><p>Laporan ini memerlukan Owner/Admin, hak melihat nota aksesori dan HPP.</p></section>
  return <AccessoryStandardWorkspace key={`${runtime.projectRef}:${identity.profile.id}:${identity.profile.rowVersion}:${identity.profile.roleRowVersion}:${identity.profile.role}:${identity.permissions.join('|')}`} refresh={refresh}/>
}
function AccessoryStandardWorkspace({ refresh }: { refresh: number }) {
  const { runtime } = useAuth()
  if (!isConnectedRuntime(runtime)) throw new Error('Sesi laporan belum siap.')
  const client = useMemo(() => getUatSupabaseClient(runtime), [runtime])
  const rpc = useMemo(() => client.rpc.bind(client) as unknown as ReadRpc, [client])
  const [start, setStart] = useState(() => todayWib().slice(0, 8) + '01'), [end, setEnd] = useState(todayWib)
  const [search, setSearch] = useState(''), [contractorId, setContractorId] = useState<string | null>(null), [poId, setPoId] = useState<string | null>(null)
  const [data, setData] = useState<AccessoryReportWorkspace | null>(null), [loading, setLoading] = useState(false), [error, setError] = useState('')
  const current = useRef<AccessoryReportQuery>({ period_start: start, period_end: end, contractor_id: null, po_id: null, q: '', offset: 0, limit: PAGE })
  const serial = useRef(0)
  current.current = { ...current.current, period_start: start, period_end: end, contractor_id: contractorId, po_id: poId, q: search }
  const retire = () => { ++serial.current; current.current.offset = 0; setData(null); setLoading(false); setError('') }
  const load = useCallback(async (q: AccessoryReportQuery) => {
    const mine = ++serial.current
    current.current = q; setData(null); setError(''); setLoading(true)
    try {
      const r = await rpc('erp_cp7_get_accessory_standard_report_v1', { p_start: q.period_start, p_end: q.period_end, p_contractor: q.contractor_id,
        p_po: q.po_id, p_query: q.q, p_offset: q.offset, p_limit: q.limit })
      if (mine !== serial.current) return
      if (r.error) throw r.error
      setData(parseAccessoryReportWorkspace(r.data, q))
    } catch (failure) { if (mine === serial.current) setError(failureText(failure)) }
    finally { if (mine === serial.current) setLoading(false) }
  }, [rpc])
  useEffect(() => { if (accessoryReportPeriod(current.current.period_start, current.current.period_end)) void load(current.current); return () => { ++serial.current } }, [load, refresh])
  const valid = accessoryReportPeriod(start, end)
  const read = (contractor = contractorId, po = poId, offset = 0) => {
    if (!valid) return
    void load({ period_start: start, period_end: end, contractor_id: contractor, po_id: po, q: search, offset, limit: PAGE })
  }
  return <section className="panel asr-report" aria-label="Laporan aksesori mandor">
    <h1>Aksesori mandor vs standar</h1>
    <p>Pengambilan memakai tanggal fisik nota yang sudah diposting. Standar memakai tanggal hasil GOOD dan jumlah pada snapshot BOM kategori. Kedua tanggal mengikuti WIB.</p>
    <p>Selisih menunjukkan dua kelompok transaksi dalam periode pilihan. Penilaian pemakaian per PO memerlukan penelusuran sumber dan waktu pengambilannya.</p>
    <form onSubmit={e => { e.preventDefault(); read() }} className="asr-filters" aria-label="Filter laporan aksesori">
      <label>Mulai periode<input aria-label="Mulai periode aksesori" type="date" value={start} onChange={e => { retire(); setStart(e.target.value) }}/></label>
      <label>Akhir periode<input aria-label="Akhir periode aksesori" type="date" value={end} onChange={e => { retire(); setEnd(e.target.value) }}/></label>
      <label>Cari mandor<input aria-label="Cari mandor laporan" value={search} maxLength={100} onChange={e => { retire(); setSearch(e.target.value); setContractorId(null); setPoId(null) }}/></label>
      <button type="submit" disabled={!valid || loading}>Muat laporan</button>
    </form>
    {!valid && <p role="alert">Isi tanggal yang sah; akhir periode harus sesudah atau sama dengan awal, maksimal 367 hari.</p>}
    {loading && <p role="status">Membaca sumber aksesori…</p>}
    {error && <p role="alert">{error}</p>}
    {data && <>
      <section aria-label="Pilih mandor laporan" className="asr-contractors">
        <h2>Mandor{data.selected_contractor ? `: ${data.selected_contractor.name}` : ''}</h2>
        {data.contractors.rows.length === 0 ? <p>Mandor tidak ditemukan.</p> : <ul>{data.contractors.rows.map(c => <li key={c.id}>
          <button type="button" aria-pressed={c.id === contractorId} onClick={() => { setContractorId(c.id); setPoId(null); read(c.id, null) }}>{c.name}{c.active ? '' : ' (nonaktif)'}</button>
        </li>)}</ul>}
        <p>{data.contractors.total} mandor cocok · halaman {Math.floor(data.contractors.offset / PAGE) + 1}</p>
        <button type="button" disabled={data.contractors.offset === 0} onClick={() => read(contractorId, poId, Math.max(0, data.contractors.offset - PAGE))}>Mandor sebelumnya</button>{' '}
        <button type="button" disabled={data.contractors.next_offset === null} onClick={() => read(contractorId, poId, data.contractors.next_offset ?? 0)}>Mandor berikutnya</button>
      </section>
      {data.selected_contractor && <label className="asr-po">PO dalam laporan<select aria-label="PO laporan aksesori" value={poId ?? ''} onChange={e => { const id = e.target.value || null; setPoId(id); read(contractorId, id) }}>
        <option value="">Semua PO dan pengambilan tanpa PO</option>{data.po_options.map(po => <option value={po.id} key={po.id}>{po.number}</option>)}
      </select></label>}
      {!data.report && <p>Pilih satu mandor untuk membaca jumlah dan sumbernya.</p>}
      {data.report && <Report report={data.report}/>}
      <p className="asr-captured">Dibaca {formatCp6WibDateTime(data.captured_at)}. Angka biaya mengikuti nilai tersimpan beserta revisi yang telah tercatat.</p>
    </>}
  </section>
}
function Report({ report: r }: { report: AccessoryPeriodReport }) {
  return <section aria-label="Hasil laporan aksesori">
    <h2>Periode {r.period_start} sampai {r.period_end} WIB</h2>
    <p role="status">{r.status === 'KNOWN' ? 'Sumber standar yang dibaca lengkap.' : r.status === 'NO_GOOD_OUTPUT' ? 'Belum ada hasil GOOD pada periode ini.' : 'Perbandingan belum lengkap. Periksa sumber yang belum diketahui.'}</p>
    <p>{r.counts.issue_items} detail pengambilan · {r.counts.lots} lot GOOD · {r.counts.snapshots} snapshot standar.</p>
    {r.counts.issues_without_po > 0 && <p>{r.counts.issues_without_po} detail pengambilan belum terhubung ke PO. Jumlah tetap masuk ke mandor dan kategorinya.</p>}
    {r.counts.unallocated_lots > 0 && <p role="alert">{r.counts.unallocated_lots} lot GOOD pada periode ini belum memiliki penerima mandor yang terbukti. Selisih ditahan sampai sumbernya jelas.</p>}
    {r.rows.length === 0 ? <p>Tidak ada baris kategori untuk dibandingkan.{r.lot_sources.some(l => l.explicit_zero) ? ' Ada sumber BOM kosong atau rework tanpa aksesori yang dinyatakan secara eksplisit.' : ''}</p> : <div className="asr-scroll"><table>
      <caption>Jumlah pengambilan dan standar per kategori dalam periode</caption>
      <thead><tr><th>Kategori</th><th>Diambil</th><th>Standar GOOD</th><th>Selisih jumlah periode</th><th>Nilai stok diambil</th><th>Tagihan nota</th><th>HPP standar tersedia</th><th>Penggantian standar tersedia</th></tr></thead>
      <tbody>{r.rows.map(row => <tr key={row.category_id ?? 'unknown'}>
        <th scope="row">{row.category_name}<small>{row.reasons.map(accessoryReportReason).join('; ')}</small></th>
        <td>{qty(row.actual_qty, row.unit)}</td><td>{qty(row.standard_qty, row.unit)}</td><td>{qty(row.delta_qty, row.unit)}</td>
        <td>{number(row.actual_inventory_cost, true)}</td><td>{number(row.actual_receivable, true)}</td>
        <td>{number(row.standard_hpp_cost, true)}</td><td>{number(row.standard_reimbursement, true)}</td>
      </tr>)}</tbody>
    </table></div>}
    <p>Nilai stok diambil, tagihan nota, HPP standar dan penggantian mandor mengikuti dasar masing-masing. Nilai tersedia dari sumber parsial tetap diberi status belum lengkap.</p>
    <details className="asr-source"><summary>Jejak sumber pengambilan ({r.actual_sources.length})</summary>
      {r.actual_sources.map(s => <article key={s.id} aria-label={`Sumber pengambilan ${s.issue_number}`}>
        <h3>{s.issue_number} · {s.material_name} ({s.material_sku})</h3>
        <p>{formatCp6WibDateTime(s.physical_at)} · PO {s.po_number ?? 'belum terkait'} · {qty(s.qty, s.unit)}</p>
        <p>Transaksi {qty(s.transaction_qty, s.transaction_uom)} · faktor ke satuan dasar {number(s.base_qty_per_transaction_uom)} · biaya per satuan dasar {number(s.inventory_unit_cost, true)} · nilai stok {number(s.inventory_cost, true)} · harga per satuan transaksi {number(s.selling_unit_price, true)} · tagihan {number(s.receivable, true)}</p>
        <dl><dt>Detail nota / nota</dt><dd>{s.id} / {s.issue_id}</dd><dt>Varian fisik / kategori / lokasi</dt><dd>{s.material_id} / {s.category_id ?? 'belum diketahui'} / {s.location_id}</dd>
          <dt>PO</dt><dd>{s.po_id ?? 'belum terkait'}</dd><dt>Versi harga aksesori / material</dt><dd>{s.accessory_price_version_id ?? 'manual'} / {s.material_price_version_id ?? 'manual'}</dd><dt>Mutasi fisik</dt><dd>{s.movement_ids.join(', ') || 'belum terbukti'}</dd></dl>
      </article>)}
    </details>
    <details className="asr-source"><summary>Jejak standar GOOD ({r.lot_sources.length} lot)</summary>
      {r.lot_sources.map(l => <article key={l.id} aria-label={`Sumber GOOD ${l.lot_number}`}>
        <h3>{l.lot_number} · {l.sku} · {number(l.good_qty_pcs)} pcs GOOD</h3>
        <p>{formatCp6WibDateTime(l.produced_at)} · PO {l.po_number ?? 'belum terkait'} · {l.recipient_basis === 'REWORK_DECISION' ? 'penerima dari keputusan rework' : 'mandor dari PO dengan penjaga transaksi terkait'}</p>
        <p>{l.reasons.length ? l.reasons.map(accessoryReportReason).join('; ') : l.explicit_zero ? 'Standar nol: BOM kosong atau rework tanpa aksesori dinyatakan eksplisit.' : 'Snapshot standar lengkap.'}</p>
        <dl><dt>Lot / produk fisik / PO</dt><dd>{l.id} / {l.product_id} / {l.po_id ?? 'belum terkait'}</dd><dt>Penerima mandor</dt><dd>{l.contractor_id ?? 'belum diketahui'}</dd>
          <dt>Komitmen / versi BOM</dt><dd>{l.commitment_id ?? 'belum tersedia'} / {l.committed_bom ?? 'belum tersedia'}</dd><dt>Rework / keputusan</dt><dd>{l.rework_order_id ?? '—'} / {l.decision_id ?? '—'}{l.decision_state ? ` (${l.decision_state})` : ''}</dd>
          <dt>Snapshot tersedia / diwajibkan</dt><dd>{l.snapshot_count} / {l.expected_snapshot_count ?? 'belum diketahui'}</dd></dl>
        {r.standard_sources.filter(s => s.lot_id === l.id).map(s => <section key={s.id} className="asr-snapshot" aria-label={`Snapshot standar ${s.id}`}>
          <p>{number(s.good_qty_pcs)} pcs GOOD × {qty(s.qty_per_good_fg_base, s.unit)} = {qty(s.standard_qty, s.unit)}.</p>
          {!s.unit_known && <p role="alert">Satuan historis belum terbukti. Satuan kategori saat dibaca: {s.unit_reference ?? 'belum tersedia'}.</p>}
          <p>HPP {number(s.hpp_cost, true)} ({number(s.hpp_unit_cost, true)} per satuan dasar) · penggantian {number(s.reimbursement, true)} ({number(s.reimbursement_unit_rate, true)} per satuan dasar).</p>
          {!s.entitlement_known && <p role="alert">Hak penggantian belum cocok dengan snapshot.</p>}
          <dl><dt>Snapshot / baris BOM / kategori</dt><dd>{s.id} / {s.bom_item_id} / {s.category_id}</dd><dt>Versi BOM tersimpan</dt><dd>{s.bom_version_id}</dd>
            <dt>Metode / dasar biaya / waktu snapshot</dt><dd>{s.hpp_method} / {s.costing_basis_source} {formatCp6WibDateTime(s.costing_basis_at)} / {formatCp6WibDateTime(s.snapshotted_at)}</dd>
            <dt>Hak penggantian</dt><dd>{s.entitlement_ids.join(', ') || (s.reimbursement === '0' || /^0\.0+$/.test(s.reimbursement) ? 'Nol, tidak memerlukan hak penggantian' : 'belum tersedia')}</dd><dt>Audit satuan kategori</dt><dd>{s.unit_basis_audit_ids.join(', ') || 'belum tersedia'}</dd></dl>
          {s.revisions.length > 0 && <ul aria-label="Revisi biaya snapshot">{s.revisions.map(v => <li key={v.id}>Revisi {v.id}, {formatCp6WibDateTime(v.changed_at)}: biaya per satuan {number(v.old_hpp_unit_cost, true)} → {number(v.new_hpp_unit_cost, true)}; {v.reason}{v.material_id ? `; varian ${v.material_id}` : ''}.</li>)}</ul>}
        </section>)}
      </article>)}
    </details>
  </section>
}
