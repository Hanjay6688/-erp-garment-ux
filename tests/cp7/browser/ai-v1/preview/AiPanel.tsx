import { useEffect, useRef, useState } from 'react'
import { promptForQuestion, questions, type PreviewContext } from '../../planner/f05-preview/model'

export function AiPanel({ view }: PreviewContext) {
  const [question, setQuestion] = useState<string>(questions[0])
  const [status, setStatus] = useState('')
  const [busy, setBusy] = useState(false)
  const generation = useRef(0)
  const prompt = promptForQuestion(view, question)
  useEffect(() => { generation.current += 1; setStatus(''); setBusy(false); return () => { generation.current += 1 } }, [prompt.text])
  async function copy() {
    if (prompt.blocked || !prompt.text) return
    const id = ++generation.current; setBusy(true); setStatus('')
    try { await navigator.clipboard.writeText(prompt.text); if (id === generation.current) setStatus('Prompt berhasil disalin.') }
    catch { if (id === generation.current) setStatus('Salin otomatis gagal. Pilih teks prompt dan salin manual.') }
    finally { if (id === generation.current) setBusy(false) }
  }
  function open() {
    try {
      const popup = window.open('about:blank', '_blank')
      if (popup) { popup.opener = null; popup.location.href = 'https://chatgpt.com/'; setStatus('ChatGPT dibuka. Tempel prompt secara manual.') }
      else setStatus('Tab diblokir. Gunakan tautan ChatGPT dan tempel prompt secara manual.')
    } catch { setStatus('Tab gagal dibuka. Gunakan tautan ChatGPT dan tempel prompt secara manual.') }
  }
  return <><div className="f05-section-heading"><div><span className="f05-kicker">P17 · TANYA AI V1</span><h2>Pertanyaan bagus, sumber jelas.</h2><p>Siapkan prompt dari snapshot yang sama untuk ditinjau di ChatGPT.</p></div><span className="f05-badge">Salin & buka</span></div><div className="f05-grid"><article className="f05-card"><h3>Mulai dari pertanyaan</h3><div className="f05-question-list">{questions.map(item => <button key={item} aria-pressed={item === question} onClick={() => setQuestion(item)}>{item}</button>)}</div><label>Pertanyaanmu<textarea value={question} maxLength={2000} rows={4} onChange={event => setQuestion(event.target.value)} /></label><p className="f05-note">Belum ada API AI atau jawaban otomatis di ERP. Perhitungan tetap berasal dari mesin F04.</p></article><article className="f05-card"><h3>Sumber & batas jawaban</h3><dl className="f05-meta"><div><dt>Run</dt><dd>{view.analysis!.run_id}</dd></div><div><dt>Scope berizin contoh</dt><dd>{view.analysis!.scope.actor_scope_id}</dd></div><div><dt>Kesiapan keuangan</dt><dd>{view.analysis!.financial_readiness}</dd></div><div><dt>Payload</dt><dd>{prompt.truncation}</dd></div></dl><p>Asumsi, nilai unknown, alokasi sumber bersama, dan batas waktu ikut disalin. Data tidak ditempatkan pada URL.</p></article></div><article className="f05-card"><h3>Prompt yang bisa diperiksa</h3><textarea readOnly rows={18} aria-label="Prompt berizin" value={prompt.text} /><div className="f05-actions"><button disabled={prompt.blocked || busy || !question.trim()} onClick={() => void copy()}>{busy ? 'Menyalin…' : 'Salin prompt'}</button><button disabled={prompt.blocked} onClick={open}>Buka ChatGPT</button><a href="https://chatgpt.com/" target="_blank" rel="noopener noreferrer">Tautan manual ChatGPT ↗</a></div><p role="status">{status}</p></article></>
}
