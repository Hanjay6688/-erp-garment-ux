import { useState } from 'react'
import { changeAttention, enqueueSimulation, type Attention, type Episode, type PreviewContext, type QueueItem } from '../../../browser/planner/f05-preview/model'
import { reasonLabel } from '../../../../../src/cp7/workspace'

type Manual = { id: string; title: string; due: string; attention: Attention }
export function ReminderPanel(context: PreviewContext) {
  const [attention, setAttention] = useState<Record<string, Attention>>({})
  const [queue, setQueue] = useState<readonly QueueItem[]>([])
  const [manual, setManual] = useState<Manual[]>([])
  const [title, setTitle] = useState('')
  const [due, setDue] = useState('')
  const [schedule, setSchedule] = useState('08:00')
  const [status, setStatus] = useState('')
  const episodes: Episode[] = [
    ...context.view.actions.map(action => ({ id: action.key, title: reasonLabel(action.primary_reason), condition: 'REVIEW_REQUIRED' as const, source: action.source_keys.join(', '), attention: attention[action.key] ?? 'NEW' })),
    ...['Aksesori', 'Utang', 'Piutang'].map(domain => ({ id: `unknown-${domain}`, title: `${domain}: data belum lengkap`, condition: 'UNKNOWN' as const, source: domain === 'Aksesori' ? 'BOM / konsumsi / alokasi belum terbukti' : 'Outstanding dan jatuh tempo belum dibaca', attention: attention[`unknown-${domain}`] ?? 'NEW' })),
  ]
  function update(episode: Episode, next: Attention) {
    const changed = changeAttention(episode, next); setAttention(items => ({ ...items, [changed.id]: changed.attention }))
  }
  return <><div className="f05-section-heading"><div><span className="f05-kicker">P16 · REMINDER</span><h2>Perhatian bukan penyelesaian.</h2><p>Kondisi sumber, perhatian operator, dan pengiriman punya status terpisah.</p></div><span className="f05-badge">Simulasi lokal</span></div>
    <div className="f05-grid">{episodes.map(episode => <article className="f05-card" key={episode.id}><span className="f05-kicker">EPISODE CONTOH</span><h3>{episode.title}</h3><dl className="f05-meta"><div><dt>Kondisi sumber</dt><dd data-condition={episode.id}>{episode.condition}</dd></div><div><dt>Perhatian</dt><dd data-attention={episode.id}>{episode.attention}</dd></div><div><dt>Dasar</dt><dd>{episode.source}</dd></div></dl><div className="f05-actions"><button onClick={() => update(episode, 'ACK')}>Tandai dibaca</button><button onClick={() => update(episode, 'SNOOZED')}>Tunda perhatian</button><button onClick={() => update(episode, 'DONE')}>Selesai ditinjau</button><button disabled={context.stale} onClick={() => { try { setQueue(items => enqueueSimulation(context, episode, items)); setStatus('Masuk antrean simulasi. Tidak ada pesan yang dikirim.') } catch (error) { setStatus(error instanceof Error ? error.message : 'Antrean belum siap.') } }}>Antrekan simulasi</button></div><p className="f05-note">ACK, tunda, dan selesai ditinjau tidak mengubah kondisi sumber.</p></article>)}</div>
    <article className="f05-card"><h3>Reminder manual contoh</h3><form onSubmit={event => { event.preventDefault(); if (!title.trim() || !due) { setStatus('Isi judul dan tanggal reminder.'); return }; setManual(items => [...items, { id: `manual-${items.length + 1}`, title: title.trim(), due, attention: 'NEW' }]); setTitle(''); setStatus('Reminder tersimpan dalam sesi pratinjau saja.') }}><div className="f05-grid"><label>Judul reminder<input value={title} maxLength={240} onChange={event => setTitle(event.target.value)} required /></label><label>Jadwal manual · Asia/Jakarta<input type="datetime-local" value={due} onChange={event => setDue(event.target.value)} required /></label></div><button>Simpan reminder contoh</button></form>{manual.map(item => <div className="f05-source" key={item.id}><strong>{item.title}</strong><p>{item.due} · Asia/Jakarta · {item.attention}</p><div className="f05-actions"><button onClick={() => setManual(items => items.map(row => row.id === item.id ? { ...row, attention: 'DONE' } : row))}>Selesai manual</button><button onClick={() => setManual(items => items.map(row => row.id === item.id ? { ...row, attention: 'CANCELLED' } : row))}>Batalkan manual</button></div></div>)}</article>
    <article className="f05-card"><h3>Jadwal & koneksi WA</h3><label>Jam pengingat contoh · Asia/Jakarta<input type="time" value={schedule} onChange={event => setSchedule(event.target.value)} /></label><dl className="f05-meta"><div><dt>Scheduler</dt><dd>Tidak aktif</dd></div><div><dt>Provider / penerima</dt><dd>Belum dipilih</dd></div><div><dt>Transport / bukti terkirim</dt><dd>Belum tersambung / tidak ada</dd></div></dl><button disabled>Aktifkan pengiriman WA</button><p role="status">{status}</p><h4>Antrean simulasi ({queue.length})</h4>{queue.map(item => <details className="f05-source" key={item.key}><summary>{item.episodeId} · {item.status}</summary><textarea readOnly rows={8} aria-label={`Pesan simulasi ${item.episodeId}`} value={item.text} /></details>)}<p className="f05-note">Antrean dideduplikasi per episode / run / versi skenario. Jadwal, reminder dan antrean hilang saat reload atau ganti hak akses.</p></article>
  </>
}
