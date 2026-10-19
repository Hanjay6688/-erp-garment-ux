import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useAuth } from './auth/AuthProvider'
import { isConnectedRuntime } from './config/runtime'
import { getUatSupabaseClient } from './lib/supabase'
import { isUnansweredFailure } from './lib/clientError'
import { formatCp6WibDateTime } from './cp6BusinessTime'
import {
  WaResponseError, dispatchKindLabel, dispatchStatusLabel, formatWaNumber, outboxStateLabel, outboxStates, parseWaKeyResult, parseWaResolveResult,
  parseWaSaveResult, parseWaTestResult, parseWaWorkspace, sameWaDraft, tickOutcomeLabel, waDraftFromSettings, waDraftProblem, waEnableProblem, waErrorText,
  waKeyErrorText, waKeyPattern, waKindLabel, waKinds, waResolvePayload, waSettingsPayload, type DispatchOutcome, type WaDispatch, type WaDraft, type WaKind,
  type WaTickJob, type WaWorkspace,
} from './waContract'
import './connected-wa.css'

// WA-4 (owner D17-3..D17-6): the owner's Sambungan WhatsApp tab. Reads erp_cp7_get_wa_settings_v1 and writes through four
// owner-only RPCs. Nothing here is persisted in the browser: the settings, test and resolve requests keep their request id
// in memory only (a retry after a lost reply reuses it, so the server answers the first result), and the CallMeBot key is
// read from an uncontrolled password input at the moment it is sent with a fresh request id, then the input is emptied.
// The key is never React state, never in storage, a recovery envelope, a log line, an error text or any other request.
type Section = 'settings' | 'key' | 'test' | 'history'
type Note = { tone: 'ok' | 'bad'; text: string; reload?: boolean }
type Base = { draft: WaDraft; revision: number }
type Writing = 'SETTINGS' | 'KEY' | 'TEST' | 'RESOLVE' | null
const tickName: Record<WaTickJob, string> = { COLLECT: 'Pengumpul pengingat', SEND: 'Pengirim WhatsApp', ANALYSIS: 'Pemeriksa analisis' }
const lostReply = (what: string) => `Jawaban server tidak sampai, jadi belum pasti ${what}. Tekan tombolnya lagi tanpa mengubah apa pun: permintaan yang sama dikirim ulang, jadi tidak tercatat dua kali.`

export default function WaConnectionPanel() {
  const { runtime, identity } = useAuth()
  if (!isConnectedRuntime(runtime) || identity.status !== 'AUTHORIZED') throw new Error('Sesi Sambungan WhatsApp belum siap.')
  if (identity.profile.role !== 'OWNER') return <section className="panel cwa" role="alert">Sambungan WhatsApp hanya untuk akun Owner.</section>
  return <Connection/>
}

function Connection() {
  const { runtime } = useAuth()
  if (!isConnectedRuntime(runtime)) throw new Error('Sesi Sambungan WhatsApp belum siap.')
  const client = useMemo(() => getUatSupabaseClient(runtime), [runtime])
  const serial = useRef(0)
  const [data, setData] = useState<WaWorkspace | null>(null), [busy, setBusy] = useState(false), [error, setError] = useState('')
  const [draft, setDraftState] = useState<WaDraft | null>(null), [base, setBaseState] = useState<Base | null>(null)
  const draftRef = useRef<WaDraft | null>(null), baseRef = useRef<Base | null>(null)
  const [writing, setWriting] = useState<Writing>(null), [notes, setNotes] = useState<Partial<Record<Section, Note>>>({})
  const keyInput = useRef<HTMLInputElement>(null), [keyCheck, setKeyCheck] = useState<'EMPTY' | 'BAD' | 'OK'>('EMPTY')
  const pendingSave = useRef<{ id: string; fingerprint: string } | null>(null), pendingTest = useRef<string | null>(null)
  const pendingResolve = useRef(new Map<string, string>())

  const note = (section: Section, value: Note | null) => setNotes(current => {
    const next = { ...current }
    if (value) next[section] = value; else delete next[section]
    return next
  })
  const setDraft = (next: WaDraft) => { draftRef.current = next; setDraftState(next) }
  // reset: put the form back to what the server holds. Otherwise only an untouched form follows the server, so a reload
  // after saving the key or sending a test never drops what the owner is typing.
  const load = useCallback(async (reset: boolean) => {
    const n = ++serial.current
    setBusy(true); setError('')
    try {
      const reply = await client.rpc('erp_cp7_get_wa_settings_v1')
      if (n !== serial.current) return
      if (reply.error) throw reply.error
      const parsed = parseWaWorkspace(reply.data), fresh = waDraftFromSettings(parsed.settings)
      const current = draftRef.current, held = baseRef.current
      if (reset || !current || !held || sameWaDraft(current, held.draft)) {
        draftRef.current = fresh; setDraftState(fresh)
        baseRef.current = { draft: fresh, revision: parsed.settings.revision }; setBaseState(baseRef.current)
      }
      setData(parsed)
    } catch (e) {
      if (n === serial.current) { setData(null); setError(waErrorText(e)) }
    } finally { if (n === serial.current) setBusy(false) }
  }, [client])
  useEffect(() => { void load(true) }, [load])
  useEffect(() => () => { ++serial.current }, [])

  const locked = busy || writing !== null || !data || !draft || !base
  const problem = draft && data ? waDraftProblem(draft) || waEnableProblem(draft, data.keyPresent) : ''
  const changed = draft !== null && base !== null && !sameWaDraft(draft, base.draft)
  // The first save (revision 0) starts the collector even when nothing differs from the defaults.
  const firstSave = base?.revision === 0
  const canSave = !locked && problem === '' && (changed || firstSave)
  const behind = data !== null && base !== null && data.settings.revision !== base.revision
  const testBlocked = !data?.settings.phone ? 'Simpan nomor WA Bos di Pengaturan dulu.' : !data.keyPresent ? 'Simpan kunci CallMeBot dulu.' : ''
  const reload = () => { setNotes({}); void load(true) }

  const saveSettings = async () => {
    if (!canSave || !draft || !base) return
    const payload = waSettingsPayload(draft, base.revision), fingerprint = JSON.stringify(payload), held = pendingSave.current
    const request = held && held.fingerprint === fingerprint ? held.id : crypto.randomUUID()
    pendingSave.current = { id: request, fingerprint }
    setWriting('SETTINGS'); note('settings', null)
    try {
      const reply = await client.rpc('erp_cp7_save_wa_settings_v1', { p: payload, p_request: request })
      if (reply.error) throw reply.error
      const r = parseWaSaveResult(reply.data, payload)
      pendingSave.current = null
      note('settings', { tone: 'ok', text: `Tersimpan (revisi ${formatWaNumber(r.settings.revision)}).${r.replay ? ' Permintaan ini ternyata sudah tersimpan sebelumnya.' : ''}` })
      setWriting(null); await load(true)
    } catch (e) {
      if (isUnansweredFailure(e)) note('settings', { tone: 'bad', text: lostReply('pengaturan tersimpan') })
      else {
        pendingSave.current = null
        const stale = /\bCP7_WA_SETTINGS_STALE\b/.test(String((e as { message?: unknown })?.message ?? ''))
        note('settings', { tone: 'bad', text: waErrorText(e), reload: stale || e instanceof WaResponseError })
      }
    } finally { setWriting(null) }
  }

  const saveKey = async () => {
    const input = keyInput.current
    if (!input || locked || keyCheck !== 'OK' || !waKeyPattern.test(input.value)) return
    setWriting('KEY'); note('key', null)
    try {
      const sent = client.rpc('erp_cp7_set_wa_key_v1', { p_key: input.value, p_request: crypto.randomUUID() })
      input.value = ''; setKeyCheck('EMPTY')
      const reply = await sent
      if (reply.error) throw reply.error
      const r = parseWaKeyResult(reply.data)
      note('key', { tone: 'ok', text: `Kunci tersimpan (${formatCp6WibDateTime(r.keySetAt)}). Kunci tidak pernah ditampilkan lagi; untuk menggantinya, ketik kunci baru.` })
      setWriting(null); await load(false)
    } catch (e) {
      note('key', { tone: 'bad', text: waKeyErrorText(e) })
    } finally { input.value = ''; setKeyCheck('EMPTY'); setWriting(null) }
  }

  const sendTest = async () => {
    if (locked || testBlocked) return
    const request = pendingTest.current ?? crypto.randomUUID()
    pendingTest.current = request
    setWriting('TEST'); note('test', null)
    try {
      const reply = await client.rpc('erp_cp7_send_wa_test_v1', { p_request: request })
      if (reply.error) throw reply.error
      const r = parseWaTestResult(reply.data)
      pendingTest.current = null
      note('test', { tone: 'ok', text: `Pesan uji masuk antrean kirim (pesan nomor ${r.dispatchId}). Sekitar satu menit lagi statusnya muncul di Riwayat pesan; `
        + 'tekan "Muat ulang sambungan" untuk melihatnya, lalu cek WhatsApp Bos.' })
      setWriting(null); await load(false)
    } catch (e) {
      if (isUnansweredFailure(e)) note('test', { tone: 'bad', text: lostReply('pesan uji terkirim') })
      else { pendingTest.current = null; note('test', { tone: 'bad', text: waErrorText(e) }) }
    } finally { setWriting(null) }
  }

  const resolve = async (d: WaDispatch, outcome: DispatchOutcome) => {
    if (locked) return
    const payload = waResolvePayload(d.id, outcome), slot = `${d.id}:${outcome}`
    const request = pendingResolve.current.get(slot) ?? crypto.randomUUID()
    pendingResolve.current.set(slot, request)
    setWriting('RESOLVE'); note('history', null)
    try {
      const reply = await client.rpc('erp_cp7_resolve_wa_dispatch_v1', { p: payload, p_request: request })
      if (reply.error) throw reply.error
      const r = parseWaResolveResult(reply.data, payload)
      pendingResolve.current.delete(slot)
      note('history', { tone: 'ok', text: r.outcome === 'DELIVERED' ? `Pesan nomor ${r.dispatchId} ditandai masuk.`
        : `Pesan nomor ${r.dispatchId} ditandai tidak masuk; pengingat di dalamnya akan dikirim lagi.` })
      setWriting(null); await load(false)
    } catch (e) {
      if (isUnansweredFailure(e)) note('history', { tone: 'bad', text: lostReply('tanda pesan tersimpan') })
      else { pendingResolve.current.delete(slot); note('history', { tone: 'bad', text: waErrorText(e) }) }
    } finally { setWriting(null) }
  }

  const set = <K extends keyof WaDraft>(key: K, value: WaDraft[K]) => {
    if (!draftRef.current) return
    setDraft({ ...draftRef.current, [key]: value }); note('settings', null)
  }
  const setSlot = (i: number, value: string) => draft && set('digestTimes', draft.digestTimes.map((t, j) => j === i ? value : t))
  const toggleKind = (k: WaKind, on: boolean) => draft && set('kinds', waKinds.filter(x => x === k ? on : draft.kinds.includes(x)))
  const noteView = (n: Note | undefined) => n ? <p className={`cwa-note ${n.tone}`} role={n.tone === 'bad' ? 'alert' : 'status'}>{n.text}
    {n.reload ? <button type="button" aria-label="Muat ulang sambungan sekarang" disabled={busy || writing !== null} onClick={reload}>Muat ulang sambungan</button> : null}</p> : null

  return <section className="panel cwa" aria-label="Sambungan WhatsApp">
    <header className="cwa-head">
      <div>
        <span className="eyebrow">SAMBUNGAN WHATSAPP · KHUSUS OWNER</span>
        <h2>Teruskan pengingat ke WhatsApp Bos</h2>
        <p>Setiap pengingat sistem yang baru muncul, dan pengingat pribadi Bos yang waktunya sudah tiba, diteruskan ke WhatsApp Bos lewat CallMeBot.
          Ditambah ringkasan pada jam ringkasan. Hanya ke nomor Bos sendiri; pengingat pribadi staf tidak pernah diteruskan.</p>
        {data ? <small>Dibaca {formatCp6WibDateTime(data.readAt)}.</small> : null}
      </div>
      <button type="button" aria-label="Muat ulang sambungan WhatsApp" disabled={busy || writing !== null} onClick={reload}>Muat ulang sambungan</button>
    </header>
    {error ? <p className="cwa-note bad" role="alert">{error}</p> : null}
    {busy && !data ? <p className="cwa-loading" role="status">Memuat sambungan WhatsApp…</p> : null}
    {data && draft && base ? <>
      <section className="cwa-block" aria-label="Status sambungan">
        <h3>Status sekarang</h3>
        <dl className="cwa-status">
          <div><dt>WhatsApp</dt><dd className={data.settings.enabled ? 'on' : 'off'}>{data.settings.enabled ? 'Menyala' : 'Mati'}</dd></div>
          <div><dt>Nomor WA</dt><dd>{data.settings.phone ?? 'Belum diisi'}</dd></div>
          <div><dt>Kunci CallMeBot</dt><dd>{data.keyPresent ? data.keySetAt ? `Kunci tersimpan sejak ${formatCp6WibDateTime(data.keySetAt)}` : 'Kunci tersimpan' : 'Belum ada kunci'}</dd></div>
          <div><dt>Isi pesan</dt><dd>{data.settings.detail === 'SUMMARY' ? 'Ringkas' : 'Rinci'}</dd></div>
          <div><dt>Pengaturan</dt><dd>{data.settings.revision === 0 ? 'Belum pernah disimpan'
            : `Revisi ${formatWaNumber(data.settings.revision)}, disimpan ${formatCp6WibDateTime(data.settings.savedAt ?? '')}`}</dd></div>
          <div><dt>Jam tenang</dt><dd>{data.settings.quietEnabled ? `${data.settings.quietStart}–${data.settings.quietEnd} WIB` : 'Tidak dipakai'}
            {data.quietNow ? ' · sekarang jam tenang, pesan ditahan sampai jam tenang selesai' : ''}</dd></div>
        </dl>
        {!data.transportIsCallmebot ? <p className="cwa-warn" role="note">Alamat uji (bukan CallMeBot): pesan dikirim ke server uji, tidak sampai ke WhatsApp sungguhan.</p> : null}
        <ul className="cwa-ticks">{(['COLLECT', 'SEND', 'ANALYSIS'] as const).map(job => {
          const t = data.ticks[job]
          return <li key={job}><strong>{tickName[job]}:</strong> {t ? `terakhir jalan ${formatCp6WibDateTime(t.at)}, ${tickOutcomeLabel(t.outcome)}` : 'belum pernah jalan'}</li>
        })}</ul>
        <p className="cwa-meta">Antrean pesan: {outboxStates.some(s => data.outbox[s]) ? outboxStates.filter(s => data.outbox[s])
          .map(s => `${formatWaNumber(data.outbox[s] ?? 0)} ${outboxStateLabel[s]}`).join(' · ') : 'belum ada pengingat yang masuk antrean WhatsApp'}.</p>
      </section>

      <section className="cwa-block" aria-label="Cara memasang">
        <h3>Cara memasang</h3>
        <ol className="cwa-steps">
          <li>Dari WhatsApp Bos sendiri, kirim kalimat persetujuan ke nomor CallMeBot (nomor dan kalimatnya dilihat di situs CallMeBot saat itu). Tunggu balasan berisi kunci (apikey).</li>
          <li>Di layar ini, isi nomor WA Bos di Pengaturan lalu tekan <b>Simpan pengaturan</b>. Ketik kuncinya di kotak Kunci CallMeBot lalu tekan <b>Simpan kunci</b>.
            Kunci cukup diketik di sini; jangan dikirim lewat chat ke siapa pun.</li>
          <li>Tekan <b>Kirim pesan uji</b>. Kalau pesannya masuk ke WA Bos, centang <b>Nyalakan WhatsApp</b> lalu tekan <b>Simpan pengaturan</b>.</li>
        </ol>
      </section>

      <section className="cwa-block" aria-label="Bagian kunci CallMeBot">
        <h3>Kunci CallMeBot</h3>
        <p className="cwa-meta">{data.keyPresent ? data.keySetAt ? `Kunci tersimpan sejak ${formatCp6WibDateTime(data.keySetAt)}.` : 'Kunci tersimpan.' : 'Belum ada kunci.'} Kunci
          yang tersimpan tidak pernah ditampilkan lagi. Untuk mengganti, ketik kunci baru.</p>
        <label className="cwa-field"><span>KUNCI DARI BALASAN CALLMEBOT</span>
          <input ref={keyInput} type="password" aria-label="Kunci CallMeBot" autoComplete="off" autoCapitalize="none" spellCheck={false} maxLength={64}
            disabled={locked} onChange={e => setKeyCheck(e.target.value === '' ? 'EMPTY' : waKeyPattern.test(e.target.value) ? 'OK' : 'BAD')}/></label>
        {keyCheck === 'BAD' ? <p className="cwa-problem">Kunci berisi 4 sampai 64 huruf, angka, tanda minus (-) atau garis bawah (_), tanpa spasi.</p> : null}
        <div className="cwa-actions"><button type="button" className="primary-btn" aria-label="Simpan kunci CallMeBot" disabled={locked || keyCheck !== 'OK'} onClick={() => { void saveKey() }}>Simpan kunci</button></div>
        {noteView(notes.key)}
      </section>

      <section className="cwa-block" aria-label="Pengaturan WhatsApp">
        <h3>Pengaturan</h3>
        {behind ? <p className="cwa-warn" role="note">Pengaturan di server sudah berubah (revisi {formatWaNumber(data.settings.revision)}). Tekan "Muat ulang sambungan" untuk
          melihatnya; isian di bawah yang belum disimpan akan diganti.</p> : null}
        <label className="cwa-check"><input type="checkbox" aria-label="Nyalakan WhatsApp" checked={draft.enabled} disabled={locked}
          onChange={e => set('enabled', e.target.checked)}/><span>Nyalakan WhatsApp: teruskan pengingat ke WA Bos</span></label>
        <div className="cwa-grid">
          <label className="cwa-field"><span>NOMOR WA BOS (DENGAN KODE NEGARA)</span>
            <input type="tel" inputMode="tel" aria-label="Nomor WA Bos" autoComplete="off" placeholder="+62…" maxLength={16} value={draft.phone} disabled={locked}
              onChange={e => set('phone', e.target.value)}/></label>
          <label className="cwa-field"><span>ISI PESAN</span>
            <select aria-label="Isi pesan WhatsApp" value={draft.detail} disabled={locked} onChange={e => set('detail', e.target.value === 'DETAILED' ? 'DETAILED' : 'SUMMARY')}>
              <option value="SUMMARY">Ringkas: nama supplier dan pelanggan tidak ditulis</option>
              <option value="DETAILED">Rinci: nama supplier dan pelanggan ditulis</option>
            </select></label>
        </div>
        <fieldset className="cwa-fieldset"><legend>Jam ringkasan (WIB, paling banyak 4)</legend>
          <p className="cwa-hint">Ringkasan berisi semua yang masih belum beres. Kosongkan jam yang tidak dipakai.</p>
          <div className="cwa-times">{draft.digestTimes.map((t, i) => <div className="cwa-time" key={i}>
            <input type="time" aria-label={`Jam ringkasan ${i + 1}`} value={t} disabled={locked} onChange={e => setSlot(i, e.target.value)}/>
            <button type="button" aria-label={`Kosongkan jam ringkasan ${i + 1}`} disabled={locked || t === ''} onClick={() => setSlot(i, '')}>Kosongkan</button>
          </div>)}</div>
        </fieldset>
        <fieldset className="cwa-fieldset"><legend>Yang diteruskan ke WA</legend>
          <div className="cwa-kinds">{waKinds.map(k => <label className="cwa-check" key={k}>
            <input type="checkbox" aria-label={`Teruskan ${waKindLabel[k]}`} checked={draft.kinds.includes(k)} disabled={locked} onChange={e => toggleKind(k, e.target.checked)}/>
            <span>{waKindLabel[k]}</span></label>)}</div>
        </fieldset>
        <fieldset className="cwa-fieldset"><legend>Supaya tidak kebanjiran pesan</legend>
          <div className="cwa-grid">
            <NumberField label="ULANGI YANG BELUM BERES TIAP (MENIT)" name="Ulangi pesan tiap (menit)" hint="0 = tidak diulang; 60 sampai 10.080. 1.440 menit = 24 jam."
              value={draft.repeatMinutes} min={0} max={10080} disabled={locked} onChange={v => set('repeatMinutes', v)}/>
            <NumberField label="MULAI DIGABUNG SESUDAH (PESAN SEHARI)" name="Batas pesan sehari" hint="1 sampai 200."
              value={draft.burstAfterPerDay} min={1} max={200} disabled={locked} onChange={v => set('burstAfterPerDay', v)}/>
            <NumberField label="LALU KIRIM GABUNGAN TIAP (MENIT)" name="Jeda pesan gabungan (menit)" hint="5 sampai 240."
              value={draft.burstMergeMinutes} min={5} max={240} disabled={locked} onChange={v => set('burstMergeMinutes', v)}/>
            <NumberField label="PALING BANYAK BARIS PER JENIS" name="Baris per jenis dalam satu pesan" hint={'1 sampai 20; sisanya ditulis "dan N lainnya".'}
              value={draft.maxItems} min={1} max={20} disabled={locked} onChange={v => set('maxItems', v)}/>
          </div>
        </fieldset>
        <fieldset className="cwa-fieldset"><legend>Jam tenang</legend>
          <label className="cwa-check"><input type="checkbox" aria-label="Pakai jam tenang" checked={draft.quietEnabled} disabled={locked}
            onChange={e => set('quietEnabled', e.target.checked)}/><span>Pakai jam tenang: pesan yang muncul di jam ini ditahan sampai jam tenang selesai</span></label>
          <div className="cwa-grid">
            <label className="cwa-field"><span>MULAI</span><input type="time" aria-label="Jam tenang mulai" value={draft.quietStart} disabled={locked} onChange={e => set('quietStart', e.target.value)}/></label>
            <label className="cwa-field"><span>SELESAI</span><input type="time" aria-label="Jam tenang selesai" value={draft.quietEnd} disabled={locked} onChange={e => set('quietEnd', e.target.value)}/></label>
          </div>
        </fieldset>
        <fieldset className="cwa-fieldset"><legend>Analisis otomatis (untuk kekurangan produksi dan kain)</legend>
          <div className="cwa-grid">
            <NumberField label="JALANKAN TIAP (MENIT)" name="Analisis otomatis tiap (menit)" hint="0 = mati; 15 sampai 1.440."
              value={draft.analysisEveryMinutes} min={0} max={1440} disabled={locked} onChange={v => set('analysisEveryMinutes', v)}/>
            <label className="cwa-field"><span>JAM MULAI</span><input type="time" aria-label="Jam analisis mulai" value={draft.analysisStart} disabled={locked} onChange={e => set('analysisStart', e.target.value)}/></label>
            <label className="cwa-field"><span>JAM SELESAI</span><input type="time" aria-label="Jam analisis selesai" value={draft.analysisEnd} disabled={locked} onChange={e => set('analysisEnd', e.target.value)}/></label>
          </div>
        </fieldset>
        {problem ? <p className="cwa-problem">{problem}</p>
          : firstSave ? <p className="cwa-hint">Pengaturan belum pernah disimpan. Simpan sekali supaya Pengingat sistem mulai berjalan; WhatsApp boleh tetap mati.</p>
          : !changed ? <p className="cwa-hint">Belum ada yang diubah.</p> : null}
        <div className="cwa-actions">
          <button type="button" className="soft-btn" aria-label="Kembalikan isian pengaturan ke yang tersimpan" disabled={locked || !changed}
            onClick={() => { setDraft(base.draft); note('settings', null) }}>Kembalikan isian</button>
          <button type="button" className="primary-btn" aria-label="Simpan pengaturan WhatsApp" disabled={!canSave} onClick={() => { void saveSettings() }}>Simpan pengaturan</button>
        </div>
        {noteView(notes.settings)}
      </section>

      <section className="cwa-block" aria-label="Pesan uji">
        <h3>Pesan uji</h3>
        <p className="cwa-meta">Mengirim satu pesan uji ke nomor WA yang tersimpan. Paling banyak 3 kali dalam satu jam.</p>
        {testBlocked ? <p className="cwa-problem">{testBlocked}</p> : null}
        <div className="cwa-actions"><button type="button" className="primary-btn" aria-label="Kirim pesan uji ke WhatsApp Bos" disabled={locked || testBlocked !== ''} onClick={() => { void sendTest() }}>Kirim pesan uji</button></div>
        {noteView(notes.test)}
      </section>

      <section className="cwa-block" aria-label="Riwayat pesan WhatsApp">
        <h3>Riwayat pesan</h3>
        <p className="cwa-meta">30 pesan terakhir, yang terbaru di atas.</p>
        {noteView(notes.history)}
        {data.dispatches.length === 0 ? <p className="cwa-hint">Belum ada pesan.</p> : <ol className="cwa-history">{data.dispatches.map(d =>
          <Dispatch key={d.id} d={d} disabled={locked} onResolve={outcome => { void resolve(d, outcome) }}/>)}</ol>}
      </section>
    </> : null}
  </section>
}

function NumberField({ label, name, hint, value, min, max, disabled, onChange }: {
  label: string; name: string; hint: string; value: string; min: number; max: number; disabled: boolean; onChange: (value: string) => void
}) {
  return <label className="cwa-field"><span>{label}</span>
    <input type="number" inputMode="numeric" aria-label={name} min={min} max={max} step={1} value={value} disabled={disabled} onChange={e => onChange(e.target.value)}/>
    <small>{hint}</small></label>
}

function Dispatch({ d, disabled, onResolve }: { d: WaDispatch; disabled: boolean; onResolve: (outcome: DispatchOutcome) => void }) {
  const tone = d.status === 'PROVIDER_ACCEPTED' ? 'ok' : d.status === 'QUEUED' || d.status === 'NOTHING_DUE' ? 'wait' : 'bad'
  const facts = [`Dibuat ${formatCp6WibDateTime(d.queuedAt)}`]
  if (d.answeredAt) facts.push(`dijawab ${formatCp6WibDateTime(d.answeredAt)}`)
  if (d.digestSlot) facts.push(`ringkasan jam ${formatCp6WibDateTime(d.digestSlot)}`)
  if (d.kind !== 'TEST') facts.push(`${formatWaNumber(d.items)} pengingat`)
  return <li className="cwa-dispatch" aria-label={`Pesan ${d.id}`}>
    <div className="cwa-dispatch-head"><strong>{dispatchKindLabel[d.kind]} · nomor {d.id}</strong><span className={`cwa-chip ${tone}`}>{dispatchStatusLabel(d)}</span></div>
    <small>{facts.join(' · ')}</small>
    {d.body ? <pre className="cwa-body" tabIndex={0} aria-label={`Isi pesan ${d.id}`}>{d.body}</pre> : null}
    {d.providerText ? <small>Jawaban CallMeBot: {d.providerText}</small> : null}
    {d.status === 'UNKNOWN' && d.resolvedOutcome === null ? <div className="cwa-resolve" role="group" aria-label={`Tandai pesan ${d.id}`}>
      <p>Belum pasti pesan ini sampai. Cek WhatsApp Bos, lalu tandai:</p>
      <button type="button" aria-label={`Tandai pesan ${d.id} masuk`} disabled={disabled} onClick={() => onResolve('DELIVERED')}>Masuk</button>
      <button type="button" aria-label={`Tandai pesan ${d.id} tidak masuk`} disabled={disabled} onClick={() => onResolve('NOT_DELIVERED')}>Tidak masuk</button>
    </div> : null}
    {d.resolvedOutcome ? <small>Bos menandai pesan ini {d.resolvedOutcome === 'DELIVERED' ? 'masuk' : 'tidak masuk (isinya dikirim lagi)'} {formatCp6WibDateTime(d.resolvedAt ?? '')}.</small> : null}
  </li>
}
