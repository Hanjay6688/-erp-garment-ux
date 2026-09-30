import { useEffect, useRef, useState } from 'react'
import { guardYieldReview, sizeMixLabel, yieldInputKey, type YieldContext, type YieldInput, type YieldReview } from './cuttingYieldContract'
import { mixes, readYieldFixture, yieldFixtureInput, type MixChoice, type YieldExample } from './cuttingYieldFixtures'
import type { PreviewContext } from './model'

export type YieldReadPort = (input: YieldInput, context: YieldContext, mix: MixChoice, example: YieldExample) => Promise<YieldReview>
export function CuttingYieldAnalyzer({ view, stale, read = readYieldFixture }: PreviewContext & { read?: YieldReadPort }) {
  const [mix, setMix] = useState<MixChoice>('small')
  const [example, setExample] = useState<YieldExample>('NORMAL')
  const [widthInput, setWidthInput] = useState('')
  const [result, setResult] = useState<{ key: string; port: YieldReadPort; value: YieldReview } | null>(null)
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('Belum ada analisis hasil potong. Pilih contoh secara eksplisit.')
  const sequence = useRef(0)
  const width = widthInput.trim() || null
  const widthInvalid = width !== null && !/^[1-9]\d*(?:\.\d+)?$/.test(width)
  const input = yieldFixtureInput(mix, example, width)
  const analysis = view.analysis!
  const context = { runId: analysis.run_id, actorScope: analysis.scope.actor_scope_id, accessEpoch: analysis.versions.access_epoch }
  const key = JSON.stringify([yieldInputKey(input), context, example, stale])
  useEffect(() => { sequence.current += 1; setBusy(false); return () => { sequence.current += 1 } }, [key, read])
  async function load() {
    if (stale || widthInvalid) return
    const id = ++sequence.current; setBusy(true); setResult(null); setMessage('Membaca contoh analyzer…')
    try { const value = guardYieldReview(await read(input, context, mix, example), input, context); if (sequence.current === id) { setResult({ key, port: read, value }); setMessage('Contoh hasil dimuat. Tidak membaca riwayat ERP.') } }
    catch { if (sequence.current === id) setMessage('Hasil analyzer gagal atau konteks tidak cocok. Rentang ditahan.') }
    finally { if (sequence.current === id) setBusy(false) }
  }
  const visible = !stale && !busy && result?.key === key && result.port === read ? result.value : null
  const title = visible?.status === 'READY' ? { NORMAL: 'Normal · dalam rentang contoh', LOW: 'Abnormal rendah · perlu diperiksa', HIGH: 'Kelebihan · perlu diperiksa' }[visible.assessment] : stale ? 'Snapshot berubah · hasil ditahan' : 'Belum dapat dinilai'
  function change() { setResult(null); setMessage('Input berubah. Rentang dan penilaian lama ditahan sampai dibaca ulang.') }
  return <aside className="f05-yield" aria-label="Analyzer hasil potong"><div className="f05-section-heading"><div><span className="f05-kicker">ANALYZER PER ROLL · DATA CONTOH</span><h4>Wajar nggak hasil potongnya?</h4></div><span className="f05-badge">Cangkang · belum belajar data ERP</span></div>
    <div className="f05-grid"><label>Kombinasi ukuran contoh<select value={mix} onChange={event => { setMix(event.target.value as MixChoice); change() }}>{Object.entries(mixes).map(([id, slots]) => <option key={id} value={id}>{sizeMixLabel(slots)}</option>)}</select></label><label>Kondisi analyzer contoh<select value={example} onChange={event => { setExample(event.target.value as YieldExample); change() }}><option value="NORMAL">Normal</option><option value="LOW">Rendah walau meter/lebar sama</option><option value="HIGH">Kelebihan</option><option value="SHORT_ROLL">Meter terukur lebih pendek</option><option value="NARROW_BATCH">Lebar batch lebih sempit</option><option value="INSUFFICIENT">Riwayat belum cukup</option><option value="INCOMPLETE">Data roll belum lengkap</option><option value="UNSEEN_COMBINATION">Kombinasi belum dikenal</option><option value="ERROR">Gagal membaca</option></select></label></div>
    <label>Lebar efektif (cm) · opsional<input value={widthInput} inputMode="decimal" aria-invalid={widthInvalid} onChange={event => { setWidthInput(event.target.value); change() }} placeholder="Boleh kosong; contoh tersedia 140 atau 150" /></label>
    {widthInvalid ? <p>Isi lebar sebagai angka positif atau kosongkan. Isian ini tidak menjadi syarat menyimpan potongan.</p> : null}
    <p className="f05-note">Lebar tidak wajib. Analyzer tanpa lebar memakai kebiasaan bahan; rentangnya mengakomodasi variasi batch yang belum diketahui.</p>
    <p className="f05-note">Roll contoh terpisah dari draft: {input.consumed.value} {input.consumed.unit} terpakai · lebar {input.usableWidthCm === null ? 'belum dicatat' : `${input.usableWidthCm} cm`} · hasil potong {input.observedCutPcs ?? 'belum diisi'} PCS. Bukan GOOD/FG.</p>
    <div className="f05-actions"><strong data-yield-status>{title}</strong><button disabled={stale || busy || widthInvalid} onClick={() => void load()}>{busy ? 'Membaca…' : 'Muat contoh analyzer'}</button></div>
    {visible?.status === 'READY' ? <><p data-yield-range>Rentang contoh untuk input ini: <strong>{visible.interval.lower}–{visible.interval.upper} PCS</strong>. Belum menjadi range normal pabrik.</p><p>{visible.interval.basis === 'WITHOUT_WIDTH' ? 'Basis: tanpa lebar. Penyebab selisih belum bisa dipisahkan menurut lebar batch.' : 'Basis: dengan lebar yang diisi. Angka yang dicatat belum membuktikan hasil ukur fisik.'}</p><details><summary>Kenapa & apa yang perlu dicek?</summary><dl className="f05-meta"><div><dt>Campuran ukuran</dt><dd>{sizeMixLabel(input.sizeSlots)}</dd></div><div><dt>Keluarga bahan</dt><dd>{input.materialId} · {input.materialFamily.brandId} · {input.materialFamily.millId}</dd></div><div><dt>Meter tercatat / terukur</dt><dd>{input.measurements.issuedDeclaredM} / {input.measurements.issuedMeasuredM ?? 'unknown'} M</dd></div><div><dt>Lebar keluarga / batch</dt><dd>{input.measurements.familyWidthCm} / {input.usableWidthCm ?? 'belum dicatat'} cm</dd></div><div><dt>Sisa fisik terukur</dt><dd>{input.measurements.remainingMeasuredM ?? 'unknown'} M</dd></div><div><dt>Pembanding</dt><dd>{visible.peers.length} roll contoh · {visible.periodStart} → {visible.periodEnd}</dd></div><div><dt>Model / validasi</dt><dd>{visible.modelVersion} · belum dikalibrasi</dd></div><div><dt>Bahan / pola / marker</dt><dd>{input.materialId} / {input.patternRevision} / {input.markerRevision}</dd></div></dl><h4>Apa yang sudah diketahui?</h4><ul>{visible.findings.map(finding => <li key={finding}>{finding}</li>)}</ul><p>Perilaku susut memakai keluarga bahan sebagai basis awal; tetap perlu riwayat ukur. Bukti ukur kartu ini semuanya contoh.</p><ul>{visible.reasons.map(reason => <li key={reason}>{reason}</li>)}</ul><h4>Pemeriksaan lapangan</h4><ul>{visible.checks.map(check => <li key={check}>{check}</li>)}</ul><details><summary>Sumber pembanding & bukti ukur contoh</summary><ul>{input.measurements.refs.map(ref => <li key={ref}>{ref}</li>)}{visible.peers.map(peer => <li key={peer.rollId}>{peer.rollId}@{peer.sourceRevision}</li>)}</ul></details><p className="f05-mono">{visible.context.runId} · {visible.context.actorScope} · {visible.policyVersion}</p></details></> : visible ? <p>{visible.reason}</p> : <p className="f05-note">{stale ? 'Snapshot harus diperbarui. Penilaian lama tidak berlaku untuk input baru.' : 'Tidak ada rentang yang layak ditampilkan.'}</p>}
    <p className="f05-note" role="status">{message}</p><p className="f05-note">Selisih adalah tanda untuk diperiksa. Tidak otomatis membuktikan bahan diambil atau BS tertentu.</p>
  </aside>
}
