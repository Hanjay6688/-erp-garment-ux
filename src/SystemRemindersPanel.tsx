import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useAuth } from './auth/AuthProvider'
import { isConnectedRuntime } from './config/runtime'
import { getUatSupabaseClient } from './lib/supabase'
import { formatCp6WibDateTime } from './cp6BusinessTime'
import {
  ALERTS_RESOLVED_DAYS, alertAnalysisLine, alertKindOrder, alertSummary, formatWaDay, formatWaNumber, isAnalysisKind, parseSystemAlerts, resolutionLabel,
  tickOutcomeLabel, waChip, waErrorText, waKindLabel, type AlertSource, type AnalysisStatus, type SystemAlert, type SystemAlerts,
} from './waContract'
import './connected-wa.css'

// WA-4 (owner D17-5: "semua hal yg masuk ke reminder harus langsung forward wa"): the Pengingat sistem tab of the Reminder
// menu. One read facade (erp_cp7_get_alerts_v1) answers the system reminders of the kinds this account may read at their
// source screens; rows open and close by themselves from their sources, so nothing here writes. The owner also sees where
// each row stands on the way to WhatsApp.
type View = 'OPEN' | 'RESOLVED'

export default function SystemRemindersPanel({ owner, onOpenWa }: { owner: boolean; onOpenWa?: () => void }) {
  const { runtime } = useAuth()
  if (!isConnectedRuntime(runtime)) throw new Error('Sesi pengingat sistem belum siap.')
  const client = useMemo(() => getUatSupabaseClient(runtime), [runtime])
  const serial = useRef(0)
  const [data, setData] = useState<SystemAlerts | null>(null), [busy, setBusy] = useState(false), [error, setError] = useState('')
  const [view, setView] = useState<View>('OPEN')

  const load = useCallback(async () => {
    const n = ++serial.current
    setBusy(true); setError(''); setData(null)
    try {
      const reply = await client.rpc('erp_cp7_get_alerts_v1', { p: { resolved_days: ALERTS_RESOLVED_DAYS } })
      if (n !== serial.current) return
      if (reply.error) throw reply.error
      setData(parseSystemAlerts(reply.data, { owner }))
    } catch (e) {
      if (n === serial.current) { setData(null); setError(waErrorText(e)) }
    } finally { if (n === serial.current) setBusy(false) }
  }, [client, owner])
  useEffect(() => { void load() }, [load])
  useEffect(() => () => { ++serial.current }, [])

  const openCount = data?.rows.filter(r => r.state === 'OPEN').length ?? 0
  const resolvedCount = data ? data.rows.length - openCount : 0
  const groups = data ? alertKindOrder.flatMap(kind => {
    const source = data.kinds.find(k => k.kind === kind)
    return source ? [{ kind, source, rows: data.rows.filter(r => r.kind === kind && r.state === view) }] : []
  }) : []

  return <section className="panel csys" aria-label="Pengingat sistem">
    <header className="csys-head">
      <div>
        <span className="eyebrow">PENGINGAT SISTEM</span>
        <h2>Pengingat dari data ERP</h2>
        <p>Stok kain di bawah minimum, stok kain, aksesori dan barang jadi yang menipis (sampai titik pesan ulangnya), kain yang perlu dibeli,
          kekurangan produksi, tagihan supplier, dan piutang pelanggan yang jatuh tempo.
          Pengingat ini muncul dan tertutup sendiri mengikuti datanya, jadi tidak perlu ditandai selesai. Akun ini hanya melihat jenis yang boleh dibukanya.</p>
        {data ? <small>Dibaca {formatCp6WibDateTime(data.readAt)}.</small> : null}
      </div>
      <button type="button" aria-label="Muat ulang pengingat sistem" disabled={busy} onClick={() => { void load() }}>Muat ulang</button>
    </header>
    {error ? <p className="csys-alert" role="alert">{error}</p> : null}
    {busy && !data ? <p className="csys-loading" role="status">Memuat pengingat sistem…</p> : null}
    {data ? <>
      {!data.configured ? <div className="csys-note" role="note">
        <strong>Pengingat sistem belum berjalan.</strong>
        <p>Pengingat sistem mulai dikumpulkan sesudah Owner menyimpan pengaturan di tab Sambungan WhatsApp satu kali. WhatsApp boleh tetap mati;
          yang penting pengaturannya pernah disimpan.</p>
        {owner && onOpenWa ? <button type="button" aria-label="Buka tab Sambungan WhatsApp" onClick={onOpenWa}>Buka Sambungan WhatsApp</button> : null}
      </div> : null}
      <p className="csys-meta">{data.collector
        ? <>Pengumpul pengingat terakhir jalan {formatCp6WibDateTime(data.collector.at)}: {tickOutcomeLabel(data.collector.outcome)}.</>
        : <>Pengumpul pengingat belum pernah jalan.</>}</p>
      {data.analysis ? <AnalysisBlock analysis={data.analysis}/> : null}
      <div className="csys-filters" role="group" aria-label="Saring pengingat sistem">
        <button type="button" aria-label={`Tampilkan pengingat sistem yang terbuka (${formatWaNumber(openCount)})`} aria-pressed={view === 'OPEN'} className={view === 'OPEN' ? 'active' : ''}
          onClick={() => setView('OPEN')}>
          Terbuka ({formatWaNumber(openCount)})</button>
        <button type="button" aria-label={`Tampilkan pengingat sistem yang sudah beres ${ALERTS_RESOLVED_DAYS} hari terakhir (${formatWaNumber(resolvedCount)})`} aria-pressed={view === 'RESOLVED'}
          className={view === 'RESOLVED' ? 'active' : ''} onClick={() => setView('RESOLVED')}>
          Sudah beres ({ALERTS_RESOLVED_DAYS} hari) ({formatWaNumber(resolvedCount)})</button>
      </div>
      {groups.length === 0 ? <p className="csys-none">Akun ini belum punya hak membaca sumber pengingat sistem mana pun (stok kain, aksesori, barang jadi, keuangan, atau analisis).
        Minta Owner menambahkannya di Pengguna & Hak Akses bila perlu.</p> : null}
      {groups.map(g => <section key={g.kind} className="csys-group" aria-label={waKindLabel[g.kind]}>
        <header><strong>{waKindLabel[g.kind]}</strong><span>{formatWaNumber(data.rows.filter(r => r.kind === g.kind && r.state === 'OPEN').length)} terbuka</span></header>
        <SourceLine source={g.source}/>
        {g.rows.length ? <ul>{g.rows.map(r => <AlertRow key={r.id} alert={r} owner={owner}/>)}</ul>
          : <p className="csys-none">{view === 'OPEN' ? 'Tidak ada yang terbuka.' : `Tidak ada yang beres dalam ${ALERTS_RESOLVED_DAYS} hari terakhir.`}</p>}
      </section>)}
    </> : null}
  </section>
}

function SourceLine({ source }: { source: AlertSource }) {
  if (source.lastError) return <p className="csys-source bad">Sumber belum bisa dibaca{source.lastTryAt ? ` (dicoba ${formatCp6WibDateTime(source.lastTryAt)})` : ''}: {source.lastError}.
    Pengingat jenis ini mungkin belum yang terbaru.</p>
  // The analysis kinds are read by the analysis check (its status is above), not by the collector.
  if (isAnalysisKind(source.kind)) return null
  return <p className="csys-source">{source.lastOkAt ? `Sumber terakhir dibaca ${formatCp6WibDateTime(source.lastOkAt)}.` : 'Sumber belum pernah dibaca.'}</p>
}

function AlertRow({ alert: a, owner }: { alert: SystemAlert; owner: boolean }) {
  const analysis = alertAnalysisLine(a), chip = owner ? waChip(a.wa) : null, fg = a.detail.kind === 'FG_AT_REORDER_POINT' ? a.detail : null
  const material = a.detail.kind === 'FABRIC_AT_REORDER_POINT' || a.detail.kind === 'ACCESSORY_AT_REORDER_POINT' ? a.detail : null
  return <li className={`csys-row ${a.state.toLowerCase()}`} aria-label={`Pengingat sistem ${a.title}`}>
    <div className="csys-row-main">
      <strong>{a.title}</strong>
      <p>{alertSummary(a)}</p>
      {analysis ? <small className="csys-analysis-line">{analysis}</small> : null}
      {fg ? <small>SKU {fg.sku} · titik pesan ulang dari {fg.basis === 'MANUAL' ? 'angka manual' : 'rumus'} · rinciannya di Gudang › Ringkasan Barang Jadi</small> : null}
      {material ? <small>SKU {material.sku} · titik pesan ulang dari {material.basis === 'MANUAL' ? 'angka manual' : 'rumus'} · rinciannya di Gudang ›{' '}
        {material.materialType === 'FABRIC' ? 'Bahan & Roll' : 'Aksesori'}</small> : null}
      <small>Muncul {formatCp6WibDateTime(a.openedAt)}{a.episode > 1 ? ` (muncul lagi, ke-${a.episode})` : ''} · diperbarui {formatCp6WibDateTime(a.refreshedAt)}</small>
      {a.state === 'RESOLVED' ? <small className="csys-resolved">Beres {formatCp6WibDateTime(a.resolvedAt ?? '')} · {resolutionLabel(a.resolution)}</small> : null}
    </div>
    {chip ? <span className={`csys-wa ${chip.tone}`}>{chip.label}</span> : null}
  </li>
}

function AnalysisBlock({ analysis: { run, request, tick } }: { analysis: AnalysisStatus }) {
  const when = formatCp6WibDateTime
  const runText = !run ? 'Belum ada analisis Bos yang dicek ulang. Pengingat dari analisis muncul sesudah Bos menjalankan analisis di menu Analisis.'
    : run.phase === 'SET' ? `Analisis terbaru (data per ${when(run.dataAsOf)}) sedang disiapkan untuk dicek ulang.`
    : run.phase === 'CHECK' ? `Analisis terbaru (data per ${when(run.dataAsOf)}) sedang dicek ulang ke data ERP sekarang: ${formatWaNumber(run.checked)} kondisi sudah dicek.`
    : run.phase === 'DONE' ? `Analisis terbaru: data per ${when(run.dataAsOf)}, selesai dicek ulang ${when(run.finishedAt ?? '')}. ${formatWaNumber(run.stillOpen)} masih terbuka, `
      + `${formatWaNumber(run.closed)} sudah beres${run.ruleOff > 0 ? `, ${formatWaNumber(run.ruleOff)} tidak diteruskan karena aturan pengingatnya tidak aktif` : ''}.`
    : `Analisis terbaru (data per ${when(run.dataAsOf)}) tidak bisa dipakai, jadi pengingat darinya ditutup. Jalankan analisis baru di menu Analisis.`
      + `${run.error ? ` Catatan server: ${run.error}.` : ''}`
  const range = request?.query?.fromDate && request.query.throughDate ? ` untuk data ${formatWaDay(request.query.fromDate)} sampai ${formatWaDay(request.query.throughDate)}` : ''
  const requestText = !request ? 'Belum ada analisis otomatis yang diminta.'
    : request.state === 'PENDING' ? `Analisis otomatis akan diminta (dicatat ${when(request.createdAt)}${range}).`
    : request.state === 'REQUESTED' ? `Analisis otomatis terakhir diminta ${when(request.requestedAt ?? '')}${range}.`
    : request.state === 'FAILED' ? `Analisis otomatis terakhir gagal diminta ${when(request.requestedAt ?? '')}.${request.error ? ` Catatan server: ${request.error}.` : ''}`
    : `Analisis otomatis terakhir dilewati ${when(request.createdAt)}: data ERP tidak berubah sejak analisis sebelumnya.`
  return <section className="csys-analysis" aria-label="Status analisis">
    <strong>Analisis untuk kekurangan produksi dan kain</strong>
    <p>{runText}</p>
    <p>{requestText}</p>
    <small>{tick ? `Pemeriksa analisis terakhir jalan ${when(tick.at)}: ${tickOutcomeLabel(tick.outcome)}.` : 'Pemeriksa analisis belum pernah jalan.'}</small>
  </section>
}
