import { useEffect, useRef } from 'react'
import { formatFact } from './cp7/workspace'
import { formatCp6WibDateTime } from './cp6BusinessTime'
import { analysisProductLabel, type NativeAnalysis } from './nativeAnalysis'
import NativeMaterialNeedsView from './NativeMaterialNeedsView'
import type { FactValue } from './cp7/contract'

function Fact({ name, value }: { name: string; value: FactValue }) {
  return <span data-fact={name} data-native-fact={JSON.stringify(value)}>{formatFact(value)}</span>
}

// Render the already validated global Original. Filtering only changes rows.
export default function NativeStockAnalysisView({ data, visibleTargets, detailTarget, blocked, onInspect, onClose }: {
  data: NativeAnalysis; visibleTargets: string[]; detailTarget: string | null; blocked: boolean
  onInspect: (key: string) => void; onClose: () => void
}) {
  const dialog = useRef<HTMLDialogElement>(null)
  const rows = data.analysis.recommendations.filter(r => visibleTargets.includes(r.target.key))
  const detail = detailTarget ? data.analysis.recommendations.find(r => r.target.key === detailTarget) : null
  useEffect(() => {
    if (detail && dialog.current && !dialog.current.open) dialog.current.showModal()
  }, [detail])
  return <section aria-label="Stok dari analisis bersama" data-run-id={data.runId}
    data-source-hash={data.analysis.snapshot.source_hash} data-semantic-hash={data.analysis.semantic_hash}>
    <h3>Stok dan kebutuhan produksi</h3>
    <p>Angka mengikuti analisis seluruh produk yang sudah diperiksa. Stok proses dan usulan produksi ditampilkan terpisah dari barang jadi yang sudah ada.</p>
    <p>{rows.length} dari {data.analysis.recommendations.length} produk. Pencarian hanya menyaring tampilan.</p>
    <div className="responsive-table"><table><thead><tr><th>Produk</th><th>Stok fisik</th><th>Target</th><th>Kurang setelah stok proses terikat</th><th>Kurang setelah pembagian global</th><th>Rincian</th></tr></thead>
      <tbody>{rows.map(r => <tr key={r.target.key} data-analysis-target={r.target.key}>
        <td><strong>{analysisProductLabel(r, data)}</strong></td><td data-label="Stok fisik"><Fact name="actual_fg" value={r.actual_fg}/></td>
        <td data-label="Target"><Fact name="target_qty" value={r.target_qty}/></td>
        <td data-label="Kurang setelah stok proses terikat"><Fact name="q_base" value={r.q_base}/></td>
        <td data-label="Kurang setelah pembagian global"><Fact name="q_conditional" value={r.q_conditional}/></td>
        <td><button disabled={blocked || data.state !== 'UNCHANGED'} onClick={() => onInspect(r.target.key)}>Periksa rincian stok {analysisProductLabel(r, data)}</button></td>
      </tr>)}</tbody></table></div>
    {detail ? <dialog ref={dialog} className="native-analysis-popup" aria-label={`Rincian stok ${analysisProductLabel(detail, data)}`}
      data-run-id={data.runId} data-source-hash={data.analysis.snapshot.source_hash} data-semantic-hash={data.analysis.semantic_hash}
      data-analysis-target={detail.target.key} onCancel={onClose} onClose={onClose}>
      <header><h3>{analysisProductLabel(detail, data)}</h3><button autoFocus type="button" onClick={onClose}>Tutup rincian stok</button></header>
      <p>Analisis diperiksa kembali sebelum rincian dibuka. Data per {formatCp6WibDateTime(data.analysis.snapshot.effective_as_of)} dalam WIB.</p>
      <p>Stok fisik: <strong><Fact name="actual_fg" value={detail.actual_fg}/></strong>. Target: <strong><Fact name="target_qty" value={detail.target_qty}/></strong>.</p>
      <p>Kurang setelah stok proses terikat: <strong><Fact name="q_base" value={detail.q_base}/></strong>.</p>
      <p>Kurang setelah pembagian global: <strong><Fact name="q_conditional" value={detail.q_conditional}/></strong>.</p>
      <p>Produksi baru layak: <strong><Fact name="feasible_new" value={detail.feasible_new}/></strong>. Status produksi: {detail.production_state === 'ACTIVE' ? 'aktif' : detail.production_state === 'PAUSED' ? 'ditunda' : 'dihentikan'}.</p>
      <NativeMaterialNeedsView data={data} visibleTargets={[detail.target.key]}/>
      <details><summary>Sumber dan asumsi rincian</summary><p>Analisis {data.runId} · sumber {data.analysis.snapshot.source_hash}.</p>
        {data.analysis.assumptions.map(a => <p key={a.id}>{a.label}</p>)}</details>
    </dialog> : null}
  </section>
}
