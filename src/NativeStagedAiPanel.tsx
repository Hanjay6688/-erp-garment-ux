import {useEffect,useMemo,useRef,useState} from 'react'
import {useAuth} from './auth/AuthProvider'
import {getUatSupabaseClient} from './lib/supabase'
import {normalizeClientError} from './lib/clientError'
import {formatCp6WibDateTime} from './cp6BusinessTime'
import {parseFinanceReport,type FinanceReport} from './financeReportContract'
import type {AnalysisFinanceAccess} from './nativeAnalysis'
import type {StagedAnalysis} from './nativeAnalysisPages'
import {parseStagedAiBrief,stagedAiPrompt,stagedAiFinanceDates,STAGED_AI_SELECTED} from './nativeStagedAi'

// "Tanya AI" for a staged run (snapshot contract v2 §6): the question with a
// bounded brief of the run (server) and, only when chosen and permitted, the
// owner finance report read now. The text is checked and copied; the app
// sends nothing to an AI. The analysis is always the state "per <time>".
type Props={staged:StagedAnalysis;selected:string[];labels:Map<string,string>;onClear:()=>void;blocked:boolean;financeAccess:AnalysisFinanceAccess}
export default function NativeStagedAiPanel(props:Props){
 const{runtime,identity}=useAuth();if(runtime.mode!=='DISPOSABLE_TEST'||identity.status!=='AUTHORIZED')return null
 return<Ai {...props} actor={identity.profile.authUserId}/>
}
function Ai({staged,selected,labels,onClear,blocked:outer,financeAccess,actor}:Props&{actor:string}){
 const{runtime}=useAuth();if(runtime.mode!=='DISPOSABLE_TEST')throw Error('Sesi AI ERP belum siap.')
 const client=useMemo(()=>getUatSupabaseClient(runtime),[runtime]),seq=useRef(0),mounted=useRef(true)
 const[question,setQuestion]=useState('Apa yang perlu diperiksa lebih dulu dari analisis ini?'),[withFinance,setWithFinance]=useState(false)
 const[text,setText]=useState(''),[busy,setBusy]=useState(false),[error,setError]=useState(''),[message,setMessage]=useState('')
 useEffect(()=>{mounted.current=true;return()=>{mounted.current=false;++seq.current}},[])
 useEffect(()=>{setText('');setMessage('')},[staged.set.runId,selected.join('|'),question,withFinance])
 const blocked=outer||busy
 const prepare=async()=>{const n=++seq.current;setBusy(true);setError('');setMessage('');setText('');try{
  const keys=[...selected];if(keys.length>STAGED_AI_SELECTED)throw Error(`Pilih paling banyak ${STAGED_AI_SELECTED} target untuk AI.`)
  const r=await client.rpc('erp_cp7_get_staged_ai_brief_v1',{p_run:staged.set.runId,p_targets:keys});if(n!==seq.current)return;if(r.error)throw r.error
  const brief=parseStagedAiBrief(r.data,actor,staged.set,staged.header.query,keys)
  let finance:FinanceReport|null=null
  if(withFinance&&financeAccess.ownerReports){const dates=stagedAiFinanceDates(staged.header.query)
   const f=await client.rpc('erp_cp7_get_finance_report_v1',{p_query:{...dates,filing_id:null,offset:0,limit:25}});if(n!==seq.current)return;if(f.error)throw f.error
   finance=parseFinanceReport(f.data,dates,null,0,financeAccess.preflight)}
  const prompt=stagedAiPrompt(brief,question,finance);setText(prompt)
  try{await navigator.clipboard.writeText(prompt);if(n===seq.current)setMessage('Pertanyaan dan ringkasan analisis disalin; siap ditinjau di AI pilihanmu.')}
  catch{if(n===seq.current)setMessage('Salin otomatis gagal. Pilih teks di bawah dan salin manual.')}
 }catch(e){if(n===seq.current&&mounted.current)setError(normalizeClientError(e).message)}finally{if(n===seq.current&&mounted.current)setBusy(false)}}
 return<section className="panel" role="region" aria-label="Tanya AI dari analisis bertahap">
  <h3>Tanya AI dari analisis bertahap</h3>
  <p>Pertanyaan disalin bersama ringkasan analisis per {formatCp6WibDateTime(staged.set.reference.capturedAt)}: total seluruh target, 25 target dengan kekurangan terbesar, target yang kamu pilih (paling banyak {STAGED_AI_SELECTED}), dan perubahan sejak data diambil. Angka analisis adalah keadaan pada waktu itu, bukan angka saat ini.</p>
  {selected.length?<div aria-label="Target pilihan untuk AI"><p>{selected.length} target dipilih: {selected.map(k=>labels.get(k)??k).join(', ')}.</p><button disabled={blocked} onClick={onClear}>Kosongkan pilihan AI</button></div>
   :<p>Belum ada target yang dipilih. Pilih target di tabel di atas bila ingin rinciannya ikut.</p>}
  <label>Pertanyaanmu<textarea aria-label="Pertanyaan untuk AI dari analisis bertahap" value={question} maxLength={10000} disabled={blocked} onChange={e=>setQuestion(e.target.value)}/></label>
  {financeAccess.ownerReports?<label><input type="checkbox" aria-label="Sertakan keuangan dan HPP untuk AI" checked={withFinance} disabled={blocked} onChange={e=>setWithFinance(e.target.checked)}/> Sertakan keuangan dan HPP dari laporan keuangan ERP hari ini (menunggu buku besar)</label>:<p>Keuangan dan HPP tidak ikut; akun ini tidak membuka laporan keuangan.</p>}
  <button disabled={blocked||!question.trim()} onClick={()=>void prepare()}>Periksa & salin pertanyaan untuk AI</button>
  {busy?<p role="status">Menyiapkan ringkasan analisis dari server…</p>:null}{error?<p role="alert">{error}</p>:null}{message?<p role="status">{message}</p>:null}
  {text?<><label>Teks yang sudah diperiksa<textarea readOnly rows={14} aria-label="Salinan pertanyaan dan ringkasan analisis bertahap" value={text} onFocus={e=>e.currentTarget.select()}/></label>
   <a href="https://chatgpt.com/" target="_blank" rel="noopener noreferrer">Buka ChatGPT (tempel manual)</a><p>Pertanyaan dan data tidak dimasukkan ke tautan. Jawaban AI tetap perlu ditinjau.</p></>:null}
 </section>
}
