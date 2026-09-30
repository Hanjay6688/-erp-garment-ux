import { useState } from 'react'
import { formatFact, reasonLabel, targetLabel } from '../../../../../src/cp7/workspace'
import type { PreviewContext } from './model'
import { Fact, Empty } from './Common'
import { CuttingYieldAnalyzer, type YieldReadPort } from './CuttingYieldAnalyzer'

export function ProductionPanel({ view, stale, yieldReadPort }: PreviewContext & { yieldReadPort?: YieldReadPort }) {
  const [filter, setFilter] = useState('')
  const [selected, setSelected] = useState<string | null>(null)
  const [entry, setEntry] = useState<'Buat' | 'Bagi'>('Buat')
  const [note, setNote] = useState('')
  const [quantity, setQuantity] = useState('')
  const [panelOpen, setPanelOpen] = useState(false)
  const rows = view.rows.filter(row => targetLabel(row.target).toLowerCase().includes(filter.toLowerCase()))
  const detail = view.rows.find(row => row.target.key === selected)
  const analysis = view.analysis!
  return <>
    <div className="f05-section-heading"><div><span className="f05-kicker">P14 · PLANNER</span><h2>Periksa dulu, lalu rencanakan.</h2><p>Urutan, angka, dan alasan berasal dari satu hasil analisis.</p></div><label>Cari SKU / ukuran<input value={filter} onChange={event => setFilter(event.target.value)} placeholder="Cari identitas fisik…" /></label></div>
    <div className="f05-grid"><article className="f05-card"><h3>Prioritas dari mesin</h3>{view.actions.map(action => <div className="f05-priority" key={action.key}><span className="f05-rank">{action.display_priority.rank ?? '—'}</span><div><strong>{reasonLabel(action.primary_reason)}</strong><p>{action.display_priority.basis.join(' · ')}</p><small>{action.intent} · {action.conditional ? 'Jika asumsi dikonfirmasi' : 'Basis snapshot'} · {action.display_priority.rule_version}</small></div></div>)}<p className="f05-note">Filter tampilan tidak mengubah alokasi sumber atau prioritas mesin.</p></article>
      <article className="f05-card"><h3>Mutu data</h3><dl className="f05-meta">{Object.entries(analysis.quality).map(([key, value]) => <div key={key}><dt>{key}</dt><dd>{value}</dd></div>)}</dl></article></div>
    <div className="f05-grid">{rows.map(row => <article className="f05-card" key={row.target.key}><span className="f05-kicker">{row.production_state} · UKURAN {row.target.size_id}</span><h3>{targetLabel(row.target)}</h3><dl className="f05-facts"><Fact label="FG aktual" fact={row.actual_fg} /><Fact label="Kebutuhan dasar" fact={row.q_base} /><Fact label="Kebutuhan bersyarat" fact={row.q_conditional} /><Fact label="Produksi baru yang layak" fact={row.feasible_new} /></dl><p>{row.reason_codes.map(reasonLabel).join('. ')}</p><button onClick={() => setSelected(row.target.key)}>Lihat alasan & sumber</button></article>)}</div>
    {rows.length === 0 ? <Empty title="Tidak ada SKU yang cocok" text="Hasil analisis dan alokasi sumber tetap utuh." /> : null}
    {detail ? <article className="f05-card f05-detail" aria-label="Rincian SKU"><div className="f05-section-heading"><h3>Alasan & sumber · ukuran {detail.target.size_id}</h3><button onClick={() => setSelected(null)}>Tutup rincian</button></div><p className="f05-mono">{detail.target.key}</p>
      {detail.target.kind === 'PRODUCT' ? <p>Versi produk: {detail.target.product_version_id} · SKU: {detail.target.commercial_identity.sku_version_id ?? 'belum tertaut'} · membership: {detail.target.commercial_identity.membership_version_id ?? 'belum tertaut'}</p> : null}
      <dl className="f05-facts"><Fact label="Target" fact={detail.target_qty} /><Fact label="Saran sebelum kelayakan" fact={detail.suggested_new} /><Fact label="Tambahan pembulatan" fact={detail.rounding_extra} /><Fact label="Belum terpenuhi" fact={detail.unresolved_qty} /></dl>
      <h4>Jejak alokasi WIP</h4>{analysis.allocation_edges.filter(edge => edge.target_key === detail.target.key).map(edge => { const source = analysis.sources.find(item => item.source_key === edge.source_key); return <div className="f05-source" key={`${edge.source_key}/${edge.target_key}`}><strong>{edge.source_key}</strong><p>{edge.match} · ukuran {edge.size_id} · input {formatFact(edge.input_qty)} → proyeksi {formatFact(edge.projected_output_qty)}</p><p>ETA {source?.eta ?? 'belum diketahui'} · basis {source?.eta_basis ?? 'UNKNOWN'} · tahap {source?.stage}</p>{source ? <dl className="f05-facts"><Fact label="Fisik WIP tersisa" fact={source.physical_remaining} /><Fact label="Sudah dialokasikan" fact={source.allocated} /></dl> : null}</div> })}
      <h4>Asumsi yang belum menjadi fakta</h4><ul>{analysis.assumptions.filter(item => detail.assumption_ids.includes(item.id)).map(item => <li key={item.id}>{item.label}</li>)}</ul>
      <h4>Kebutuhan bahan</h4>{analysis.material_needs.filter(item => item.target_key === detail.target.key).map((item, index) => <dl className="f05-facts" key={index}><Fact label="Kebutuhan kotor" fact={item.gross} /><Fact label="Terpasang terbukti" fact={item.installed_proven} /><Fact label="Sisa dialokasi terbukti" fact={item.unused_allocated_proven} /><Fact label="Tambahan dari luar" fact={item.additional_external} /></dl>)}
      <label>Status produksi<select disabled value={detail.production_state}><option>{detail.production_state}</option></select></label><p className="f05-note">Perubahan status dan penerapan produksi menunggu command bridge P08/P11.</p><button disabled>Terapkan rencana</button>
    </article> : null}
    <article className="f05-card"><span className="f05-kicker">FORM UJI · BELUM DISIMPAN</span><h3>Panel bersama Buat / Bagi</h3><div className="f05-actions"><button aria-pressed={entry === 'Buat'} onClick={() => setEntry('Buat')}>Buat Potongan</button><button aria-pressed={entry === 'Bagi'} onClick={() => setEntry('Bagi')}>Bagi Potongan</button></div><div className="f05-grid"><label>Jumlah draft {entry}<input value={quantity} inputMode="numeric" onChange={event => setQuantity(event.target.value)} /></label><label>Catatan draft<input value={note} onChange={event => setNote(event.target.value)} /></label></div><p className="f05-note">Draft lokal {quantity || note ? 'sudah diubah' : 'kosong'}. Membuka panel tidak menimpa isian.</p><button onClick={() => setPanelOpen(open => !open)}>{panelOpen ? 'Tutup panel bersama' : 'Buka panel bersama'}</button>{panelOpen ? <div className="f05-source"><h4>Rekomendasi dari run yang sama</h4>{view.actions.map(action => <p key={action.key}>{reasonLabel(action.primary_reason)} · {action.display_priority.basis.join('; ')}</p>)}<p>{stale ? 'Snapshot kedaluwarsa. Tinjau ulang sebelum menerapkan.' : 'Cangkang panel. Tidak ada draft transaksi yang dikirim.'}</p></div> : null}<button disabled>Simpan transaksi</button></article>
    <CuttingYieldAnalyzer view={view} stale={stale} read={yieldReadPort} />
  </>
}
