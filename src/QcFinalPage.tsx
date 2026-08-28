import { useMemo, useState } from 'react'
import { ArrowLeft, ArrowRight, ClipboardCheck, Info, PackageCheck, Shirt, Waves } from 'lucide-react'
import './finalization-flow.css'

export type QcSeed = {
  parentId: string
  batchId: string
  model: string
  material: string
  mandor: string
  laundry: string
  sizes: [string, string, string]
  expected: [number, number, number]
  returnedGood: number
  returnedBs: number
  stuck: number
}

export type QcFinalResult = QcSeed & {
  qcGood: [number, number, number]
  qcBs: [number, number, number]
  rewash: [number, number, number]
  stuckBySize: [number, number, number]
  finalSku: string
  destination: string
}

const asTuple = <T,>(values: T[]): [T, T, T] => [values[0], values[1], values[2]]

function allocate(total: number, capacity: [number, number, number]) {
  let remaining = Math.max(0, total)
  const output = capacity.map((limit) => {
    const value = Math.min(limit, remaining)
    remaining -= value
    return value
  })
  return asTuple(output)
}

const cleanNumber = (raw: string, max: number) => {
  const digits = raw.replace(/\D/g, '').replace(/^0+(?=\d)/, '')
  return digits === '' ? '' : String(Math.min(max, Number(digits)))
}

export default function QcFinalPage({ seed, onBack, onFinish }: {
  seed: QcSeed
  onBack: () => void
  onFinish: (result: QcFinalResult) => void
}) {
  const returnedBySize = useMemo(() => allocate(seed.returnedGood + seed.returnedBs, seed.expected), [seed])
  const laundryBsBySize = useMemo(() => allocate(seed.returnedBs, returnedBySize), [seed, returnedBySize])
  const stuckBySize = useMemo(() => asTuple(seed.expected.map((qty, index) => Math.max(0, qty - returnedBySize[index]))), [seed, returnedBySize])
  const [bsInputs, setBsInputs] = useState<[string, string, string]>(() => asTuple(laundryBsBySize.map(String)) as [string, string, string])
  const [rewashInputs, setRewashInputs] = useState<[string, string, string]>(['0', '0', '0'])
  const [finalSku, setFinalSku] = useState('73002')
  const [destination, setDestination] = useState('Gudang FG Utama')
  const [reviewing, setReviewing] = useState(false)

  const qcBs = asTuple(bsInputs.map((value) => Number(value) || 0))
  const rewash = asTuple(rewashInputs.map((value) => Number(value) || 0))
  const qcGood = asTuple(returnedBySize.map((qty, index) => Math.max(0, qty - qcBs[index] - rewash[index])))
  const total = (values: [number, number, number]) => values.reduce((sum, value) => sum + value, 0)
  const totalGood = total(qcGood)
  const totalBs = total(qcBs)
  const totalRewash = total(rewash)
  const totalStuck = total(stuckBySize)

  const updateException = (kind: 'bs' | 'rewash', index: number, raw: string) => {
    const other = kind === 'bs' ? rewash[index] : qcBs[index]
    const next = cleanNumber(raw, Math.max(0, returnedBySize[index] - other))
    if (kind === 'bs') setBsInputs((current) => asTuple(current.map((value, row) => row === index ? next : value)) as [string, string, string])
    else setRewashInputs((current) => asTuple(current.map((value, row) => row === index ? next : value)) as [string, string, string])
    setReviewing(false)
  }

  const finish = () => onFinish({ ...seed, qcGood, qcBs, rewash, stuckBySize, finalSku, destination })

  return <>
    <section className="hero-copy compact qc-flow-hero">
      <div><div className="eyebrow">PRODUKSI · SETELAH LAUNDRY</div><h1>QC & Final SKU</h1><p>Barang yang sudah kembali diperiksa di sini. Selisih yang belum pulang otomatis tetap tercatat sebagai Stuck Laundry.</p></div>
      <button type="button" className="soft-btn" onClick={onBack}><ArrowLeft /> Kembali ke WIP</button>
    </section>

    <div className="final-flow-strip"><span className="done"><b>1</b>Laundry kembali</span><i/><span className="active"><b>2</b>QC & Final SKU</span><i/><span><b>3</b>Serah FG</span><i/><span><b>4</b>Gajian</span></div>

    <section className="panel qc-source-card">
      <span className="qc-source-order"><Shirt /></span><div><small>POTONGAN INDUK · CHILD BATCH</small><h2>{seed.parentId} · Batch {seed.batchId}</h2><p>{seed.model} · {seed.material} · {seed.mandor}</p></div>
      <div><small>LAUNDRY</small><strong>{seed.laundry || 'Belum tercatat'}</strong></div><div><small>KEMBALI / DIKIRIM</small><strong>{seed.returnedGood + seed.returnedBs} / {total(seed.expected)} pcs</strong></div>
    </section>

    <section className="qc-flow-layout">
      <div className="panel qc-size-workbench">
        <header><div><span>01 · HASIL FISIK PER SIZE</span><h2>Good dihitung otomatis</h2><p>Isi hanya pengecualian. Stuck berasal dari selisih kirim–kembali, bukan input bebas.</p></div><ClipboardCheck /></header>
        <div className="qc-size-head"><span>Size</span><span>Potongan</span><span>Kembali</span><span>BS</span><span>Cuci ulang</span><span>Stuck Laundry</span><span>Good</span></div>
        <div className="qc-size-rows">{seed.sizes.map((size, index) => <div className="qc-size-row" key={size}>
          <strong>{size}</strong><span>{seed.expected[index]}</span><span>{returnedBySize[index]}</span>
          <label><input inputMode="numeric" value={bsInputs[index]} onFocus={(event) => event.currentTarget.select()} onChange={(event) => updateException('bs', index, event.target.value)} /></label>
          <label><input inputMode="numeric" value={rewashInputs[index]} onFocus={(event) => event.currentTarget.select()} onChange={(event) => updateException('rewash', index, event.target.value)} /></label>
          <span className={stuckBySize[index] > 0 ? 'stuck' : ''}>{stuckBySize[index]}</span><strong className="good">{qcGood[index]}</strong>
        </div>)}</div>
        <div className="qc-equation"><span><small>POTONGAN</small><strong>{total(seed.expected)}</strong></span><b>=</b><span><small>GOOD</small><strong>{totalGood}</strong></span><b>+</b><span><small>BS</small><strong>{totalBs}</strong></span><b>+</b><span><small>CUCI ULANG</small><strong>{totalRewash}</strong></span><b>+</b><span className="stuck"><small>STUCK</small><strong>{totalStuck}</strong></span></div>
        {totalStuck > 0 && <div className="qc-auto-stuck"><Waves /><div><strong>{totalStuck} pcs otomatis Stuck Laundry</strong><span>Dihitung dari qty dikirim dikurangi seluruh barang yang sudah dicatat kembali. Tidak diputuskan sebagai BS sampai fisiknya pulang dan diperiksa.</span></div></div>}

        <div className="qc-final-fields"><label><span>FINAL SKU</span><select value={finalSku} onChange={(event) => { setFinalSku(event.target.value); setReviewing(false) }}><option>73002</option><option>73001</option><option>73005</option></select></label><label><span>TUJUAN FG</span><select value={destination} onChange={(event) => { setDestination(event.target.value); setReviewing(false) }}><option>Gudang FG Utama</option><option>Gudang FG Cadangan</option></select></label></div>
      </div>

      <aside className="panel qc-review-ticket">
        <div className="qc-review-title"><span>REVIEW FINISHING</span><h2>{seed.material} · SKU {finalSku}</h2><p>{seed.parentId} · Batch {seed.batchId}</p></div>
        <div className="qc-review-totals"><p><span>Lolos QC / serah FG</span><strong>{totalGood} pcs</strong></p><p><span>BS final</span><strong>{totalBs} pcs</strong></p><p><span>Cuci ulang</span><strong>{totalRewash} pcs</strong></p><p className="stuck"><span>Masih di laundry</span><strong>{totalStuck} pcs</strong></p></div>
        <div className="qc-review-rule"><Info /><span><strong>Serah FG hanya memakai Good.</strong><small>BS, cuci ulang, dan stuck tidak menambah stok FG.</small></span></div>
        {!reviewing ? <button className="primary-btn qc-review-button" onClick={() => setReviewing(true)}>Review finishing <ArrowRight /></button> : <div className="qc-final-confirm"><PackageCheck /><div><strong>Komposisi sudah cocok</strong><span>{totalGood + totalBs + totalRewash + totalStuck}/{total(seed.expected)} pcs terjelaskan.</span></div><button className="primary-btn" disabled={totalGood <= 0} onClick={finish}>Finalkan QC & lanjut <ArrowRight /></button></div>}
        <small className="qc-prototype-note">Prototype frontend: belum menulis stok, QC, BS, payroll, atau jurnal backend.</small>
      </aside>
    </section>
  </>
}
