import {useEffect,useMemo,useRef,useState} from 'react'
import {useAuth} from './auth/AuthProvider'
import {getUatSupabaseClient} from './lib/supabase'
import {normalizeClientError} from './lib/clientError'
import {formatCp6WibDateTime} from './cp6BusinessTime'
import type {StagedAnalysis} from './nativeAnalysisPages'
import type {Json} from './types/database.preconnect'
import {ruleEligibilityLabels} from './nativeRuleSource'
import type {ReminderRule} from './nativeReminderPolicy'
import {driveConditionSet,parseConditionsPage,parseWorkspace,parseObligations,parseRecheck,parseCommand,readReminderRequest,persistReminderRequest,clearReminderRequest,
 reminderV2RequestKey,verdictText,snapshotStateLabels,claimStatusLabels,conditionSetProgressText,conditionSetFailureText,ruleLabel,
 type ConditionSet,type ConditionsPage,type ConditionsQuery,type ReminderCondition,type ReminderWorkspace,type Recheck,type ReminderRequest,type Operation,type SnapshotState,
 type CommandResult,type ReminderClaim} from './nativeStagedReminders'

// Reminders v2 of the staged run on screen (snapshot contract v2 §5). The
// conditions are the snapshot "data per <time>"; before a local preview is
// made, and again when it is recorded, the server checks the condition with
// the ERP as it is now, and a condition resolved since the analysis is not
// billed. Receivables and payables are read now. Nothing leaves the ERP.
type Props={staged:StagedAnalysis;blocked:boolean}
const PAGE=25
const SNAPSHOT_RULES:ReminderRule[]=['PRODUCTION_GAP','FABRIC_NEED','ACCESSORY_NEED']
const serverAnswer=(e:unknown)=>e!==null&&typeof e==='object'&&typeof(e as {code?:unknown}).code==='string'&&/^[0-9A-Z]{5}$/.test((e as {code:string}).code)
export default function NativeStagedRemindersPanel(props:Props){
 const{runtime,identity}=useAuth();if(runtime.mode!=='DISPOSABLE_TEST'||identity.status!=='AUTHORIZED')return null
 return<Reminders {...props} key={`${runtime.projectRef}:${identity.profile.id}`} scope={`analysis:${runtime.projectRef}:${identity.profile.id}`} actor={identity.profile.authUserId}/>
}
function Reminders({staged,blocked:outer,scope,actor}:Props&{scope:string;actor:string}){
 const{runtime}=useAuth();if(runtime.mode!=='DISPOSABLE_TEST')throw Error('Sesi pengingat ERP belum siap.')
 const client=useMemo(()=>getUatSupabaseClient(runtime),[runtime]),run=staged.set,seq=useRef(0),mounted=useRef(true)
 const[set,setSet]=useState<ConditionSet|null>(null),[ws,setWs]=useState<ReminderWorkspace|null>(null),[page,setPage]=useState<ConditionsPage|null>(null)
 const[ruleFilter,setRuleFilter]=useState<ReminderRule|''>(''),[stateFilter,setStateFilter]=useState<SnapshotState|''>('ACTIVE'),[offset,setOffset]=useState(0)
 const[checks,setChecks]=useState<Record<string,Recheck>>({}),[last,setLast]=useState<CommandResult|null>(null),[live,setLive]=useState<{rows:ReminderCondition[];readAt:string}|null>(null)
 const[recovery,setRecovery]=useState(()=>readReminderRequest(scope)),[busy,setBusy]=useState(false),[error,setError]=useState(''),[message,setMessage]=useState('')
 const[bLabel,setBLabel]=useState('Pratinjau lokal'),[bRules,setBRules]=useState<ReminderRule[]>(['PRODUCTION_GAP']),[bEnabled,setBEnabled]=useState(true),[bReason,setBReason]=useState('')
 const[pRule,setPRule]=useState<ReminderRule>('PRODUCTION_GAP'),[pValue,setPValue]=useState(''),[pUnit,setPUnit]=useState('PCS'),[pCooldown,setPCooldown]=useState('0'),[pReason,setPReason]=useState('')
 const[resolveReason,setResolveReason]=useState('')
 useEffect(()=>{mounted.current=true;return()=>{mounted.current=false;++seq.current}},[])
 useEffect(()=>{const l=(e:StorageEvent)=>{if(e.key===null||e.key===reminderV2RequestKey(scope))setRecovery(readReminderRequest(scope))};addEventListener('storage',l);return()=>removeEventListener('storage',l)},[scope])
 const blocked=outer||busy
 const perform=async(op:(n:number)=>Promise<void>)=>{const n=++seq.current;setBusy(true);setError('');setMessage('');try{await op(n)}catch(e){if(n===seq.current&&mounted.current)setError(normalizeClientError(e).message)}finally{if(n===seq.current&&mounted.current){setBusy(false);setRecovery(readReminderRequest(scope))}}}
 const loadWs=async(n:number)=>{const r=await client.rpc('erp_cp7_get_reminder_workspace_v2',{p_run:run.runId});if(n!==seq.current)return;if(r.error)throw r.error;setWs(parseWorkspace(r.data,run.runId,run.identityHash,actor))}
 const loadPage=async(n:number,at:number)=>{const q:ConditionsQuery={run_id:run.runId,rule_id:ruleFilter||null,state:stateFilter||null,offset:at,limit:PAGE}
  const r=await client.rpc('erp_cp7_read_reminder_conditions_v2',{p_query:q});if(n!==seq.current)return;if(r.error)throw r.error;setPage(parseConditionsPage(r.data,q,actor,run.identityHash));setOffset(at)}
 const prepare=()=>void perform(async n=>{
  const s=await driveConditionSet({step:()=>client.rpc('erp_cp7_step_reminder_conditions_v2',{p_run:run.runId}),runId:run.runId,identityHash:run.identityHash,
   aborted:()=>n!==seq.current||!mounted.current,onStatus:x=>{if(n===seq.current)setSet(x)}})
  if(!s||n!==seq.current)return
  if(s.state==='FAILED'){setError(conditionSetFailureText(s.failure!));return}
  await loadWs(n);await loadPage(n,0)})
 const recheck=(c:ReminderCondition)=>void perform(async n=>{const r=await client.rpc('erp_cp7_recheck_reminder_v2',{p_run:run.runId,p_condition:c.key});if(n!==seq.current)return;if(r.error)throw r.error
  const v=parseRecheck(r.data,run.runId,actor,c.key);setChecks(x=>({...x,[c.key]:v}))})
 const readLive=()=>void perform(async n=>{const r=await client.rpc('erp_cp7_get_reminder_obligations_v2',{p_run:run.runId});if(n!==seq.current)return;if(r.error)throw r.error
  const o=parseObligations(r.data,run.runId,actor);setLive({rows:o.rows.filter(x=>x.state==='ACTIVE'),readAt:o.readAt})})
 const exec=(r:ReminderRequest,lookup:boolean)=>perform(async n=>{
  const payload=r.payload as Json
  const args={p_payload:payload,p_request:r.id}
  const res=lookup?await client.rpc('erp_cp7_get_reminder_request_v2',{...args,p_operation:r.operation})
   :r.operation==='BINDING'?await client.rpc('erp_cp7_save_reminder_binding_v2',args):r.operation==='POLICY'?await client.rpc('erp_cp7_save_reminder_policy_v2',args)
   :r.operation==='CLAIM'?await client.rpc('erp_cp7_claim_reminder_v2',args):r.operation==='OUTCOME'?await client.rpc('erp_cp7_finish_reminder_v2',args)
   :await client.rpc('erp_cp7_resolve_reminder_claim_v2',args)
  if(n!==seq.current)return
  if(res.error){if(serverAnswer(res.error))clearReminderRequest(scope,r);throw res.error}
  const out=parseCommand(res.data,r,actor);clearReminderRequest(scope,r);setLast(out)
  if(out.status==='NOT_COMMITTED')setMessage('Server memastikan permintaan lama belum tersimpan dan sudah ditutup. Buat permintaan baru bila masih diperlukan.')
  else if(out.outcome==='NOT_SENT'&&out.recheck)setMessage('Tidak dibuat pratinjau. '+verdictText(out.recheck))
  else if(out.operation==='BINDING')setMessage('Tujuan pratinjau lokal tersimpan. Tidak ada penerima atau pengiriman di luar ERP.')
  else if(out.operation==='POLICY')setMessage('Pengaturan pengingat tersimpan sebagai versi baru.')
  else if(out.operation==='OUTCOME'&&out.claim)setMessage(claimStatusLabels[out.claim.status]+(out.claim.status==='SUPPRESSED'&&out.recheck?'. '+verdictText(out.recheck):'.'))
  await loadWs(n)})
 const send=(operation:Operation,payload:Record<string,unknown>)=>{try{
  const held=readReminderRequest(scope);if(held.error||held.pending)throw Error(held.error??'Selesaikan permintaan pengingat yang tertunda terlebih dahulu.')
  const r:ReminderRequest={id:crypto.randomUUID(),operation,runId:run.runId,payload:{run_id:run.runId,identity_hash:run.identityHash,...payload}}
  persistReminderRequest(scope,r);setRecovery(readReminderRequest(scope));void exec(r,false)}catch(e){setError(normalizeClientError(e).message)}}
 const claim=(c:ReminderCondition)=>{if(!ws?.binding)return;send('CLAIM',{condition_key:c.key,condition_hash:c.conditionHash,binding_id:ws.binding.id})}
 const finish=(c:ReminderClaim,outcome:'LOCAL_CAPTURE'|'UNKNOWN')=>{try{const held=readReminderRequest(scope);if(held.error||held.pending)throw Error(held.error??'Selesaikan permintaan pengingat yang tertunda terlebih dahulu.')
  const r:ReminderRequest={id:crypto.randomUUID(),operation:'OUTCOME',runId:c.runId,payload:{run_id:c.runId,identity_hash:c.identityHash,claim_id:c.id,fence:c.fence,outcome}}
  persistReminderRequest(scope,r);setRecovery(readReminderRequest(scope));void exec(r,false)}catch(e){setError(normalizeClientError(e).message)}}
 const resolve=(c:ReminderClaim,outcome:'CAPTURE_CONFIRMED'|'NOT_CAPTURED_CONFIRMED')=>{try{if(!resolveReason.trim())throw Error('Isi alasan pemastian hasil pratinjau.')
  const held=readReminderRequest(scope);if(held.error||held.pending)throw Error(held.error??'Selesaikan permintaan pengingat yang tertunda terlebih dahulu.')
  const r:ReminderRequest={id:crypto.randomUUID(),operation:'RESOLUTION',runId:c.runId,payload:{run_id:c.runId,identity_hash:c.identityHash,claim_id:c.id,fence:c.fence,outcome,reason:resolveReason}}
  persistReminderRequest(scope,r);setRecovery(readReminderRequest(scope));void exec(r,false)}catch(e){setError(normalizeClientError(e).message)}}
 const saveBinding=()=>{if(!bReason.trim()||!bLabel.trim()||!bRules.length){setError('Isi nama tujuan, aturan, dan alasan.');return}
  send('BINDING',{expected_revision:ws?.binding?.revision??'0',enabled:bEnabled,label:bLabel,environment:'LOCAL_TEST_SINK',rules:bRules,reason:bReason})}
 const savePolicy=()=>{if(!pReason.trim()||!/^(0|[1-9][0-9]{0,11})(\.[0-9]{1,12})?$/.test(pValue)||!/^(0|[1-9][0-9]{0,5})$/.test(pCooldown)){setError('Isi batas, jeda (menit), dan alasan dengan benar.');return}
  const current=ws?.policies.find(p=>p.ruleId===pRule&&p.scopeKind==='GLOBAL')
  send('POLICY',{rule_id:pRule,scope_kind:'GLOBAL',scope_key:'*',expected_revision:current?.revision??'0',reason:pReason,
   config:{enabled:true,threshold_value:pValue,threshold_unit:pUnit,cooldown_minutes:pCooldown,quiet:{enabled:false,starts_at:null,ends_at:null,timezone:'Asia/Jakarta'}}})}
 const resume=(lookup:boolean)=>{const held=readReminderRequest(scope);setRecovery(held);if(!held.pending){setError(held.error??'Permintaan pengingat tersimpan tidak tersedia.');return}void exec(held.pending,lookup)}
 const pending=recovery.pending,manage=Boolean(ws?.manageAllowed),canClaim=manage&&Boolean(ws?.binding?.enabled)
 const row=(c:ReminderCondition)=>{const v=checks[c.key];return<li key={c.key} data-condition-key={c.key}>
  <p><strong>{c.label??c.key}</strong> · {ruleLabel(c.ruleId)} · {c.kind==='SNAPSHOT'?snapshotStateLabels[c.state as SnapshotState]:'masih terbuka sekarang'} · {c.value.value??'belum diketahui'} {c.value.unit}{c.remaining?` · sisa ${c.remaining} IDR`:''}</p>
  <p>Pengaturan: {ruleEligibilityLabels[c.eligibility]??c.eligibility}</p>
  <button disabled={blocked} aria-label={`Periksa ulang sekarang ${c.label??c.key}`} onClick={()=>recheck(c)}>Periksa ulang sekarang</button>
  {canClaim&&ws?.binding?.rules.includes(c.ruleId)?<button disabled={blocked||Boolean(pending)} aria-label={`Buat pratinjau lokal ${c.label??c.key}`} onClick={()=>claim(c)}>Buat pratinjau lokal</button>:null}
  {v?<p role="status" data-verdict={v.verdict}>Hasil periksa ulang {formatCp6WibDateTime(v.checkedAt)}: {verdictText(v)}</p>:null}</li>}
 return<section className="panel" role="region" aria-label="Pengingat dari analisis bertahap" data-set-state={set?.state??''}>
  <h3>Pengingat dari analisis bertahap</h3>
  <p>Daftar ini memakai data analisis per {formatCp6WibDateTime(run.reference.capturedAt)}: keadaan pada waktu itu, bukan angka saat ini. Sebelum pratinjau dibuat, dan lagi saat dicatat, server memeriksa ulang kondisinya dengan data ERP saat itu; yang sudah selesai sejak analisis tidak ditagih. Tidak ada pesan yang dikirim ke luar ERP: hasilnya hanya pratinjau lokal.</p>
  {set&&busy?<p role="status">{conditionSetProgressText(set)}</p>:busy?<p role="status">Memeriksa pengingat dan izin ERP…</p>:null}
  {error||recovery.error?<p role="alert">{error||recovery.error}</p>:null}{message?<p role="status">{message}</p>:null}
  {pending?<div role="status"><p>Ada permintaan pengingat yang belum pasti hasilnya. Permintaan yang sama dipertahankan.</p>
   <button disabled={blocked} onClick={()=>resume(false)}>Kirim ulang permintaan pengingat yang sama</button><button disabled={blocked} onClick={()=>resume(true)}>Periksa hasil permintaan pengingat</button></div>:null}
  <button disabled={blocked} onClick={prepare}>Siapkan daftar pengingat</button>
  {set&&!busy?<p>{conditionSetProgressText(set)}</p>:null}
  {set?.state==='DONE'&&set.totals?<p>Saat analisis: {Object.entries(set.totals.byRule).map(([r,m])=>`${ruleLabel(r as ReminderRule)} ${m.ACTIVE??0} perlu ditangani`).join(' · ')}.</p>:null}
  {set?.state==='DONE'?<div>
   <label>Jenis<select aria-label="Jenis pengingat" value={ruleFilter} disabled={blocked} onChange={e=>setRuleFilter(e.target.value as ReminderRule|'')}><option value="">Semua</option>{SNAPSHOT_RULES.map(r=><option key={r} value={r}>{ruleLabel(r)}</option>)}</select></label>
   <label>Keadaan saat analisis<select aria-label="Keadaan pengingat" value={stateFilter} disabled={blocked} onChange={e=>setStateFilter(e.target.value as SnapshotState|'')}><option value="">Semua</option>{(Object.keys(snapshotStateLabels) as SnapshotState[]).map(s=><option key={s} value={s}>{snapshotStateLabels[s]}</option>)}</select></label>
   <button disabled={blocked} onClick={()=>void perform(n=>loadPage(n,0))}>Tampilkan pengingat</button></div>:null}
  {page?<><p>{page.total} kondisi · menampilkan {page.total?offset+1:0}–{offset+page.rows.length}.</p><ul aria-label="Daftar pengingat dari analisis">{page.rows.map(row)}</ul>
   {offset>0?<button disabled={blocked} onClick={()=>void perform(n=>loadPage(n,Math.max(0,offset-PAGE)))}>Halaman pengingat sebelumnya</button>:null}
   {offset+page.rows.length<page.total?<button disabled={blocked} onClick={()=>void perform(n=>loadPage(n,offset+PAGE))}>Halaman pengingat berikutnya</button>:null}</>:null}
  {set?.state==='DONE'?<button disabled={blocked} onClick={readLive}>Baca piutang dan utang sekarang</button>:null}
  {live?<><p>Piutang dan utang dibaca {formatCp6WibDateTime(live.readAt)}, bukan dari analisis: {live.rows.length} masih terbuka.</p><ul aria-label="Piutang dan utang terbuka">{live.rows.map(row)}</ul></>:null}
  {last?.claim&&last.operation==='CLAIM'?<article aria-label="Pratinjau lokal pengingat" data-claim-status={last.claim.status}><pre>{last.claim.body}</pre></article>:null}
  {manage&&ws?<div aria-label="Pratinjau lokal tersimpan">{ws.claims.length?<h4>Pratinjau lokal</h4>:null}{ws.claims.map(c=><div key={c.id} data-claim-id={c.id} data-claim-status={c.status}>
   <p>{claimStatusLabels[c.status]} · {ruleLabel(c.ruleId)}{c.reason&&c.status==='SUPPRESSED'?` · ${c.reason}`:''}</p><pre>{c.body}</pre>
   {c.status==='CLAIMED'?<><button disabled={blocked||Boolean(pending)} onClick={()=>finish(c,'LOCAL_CAPTURE')}>Catat pratinjau lokal</button><button disabled={blocked||Boolean(pending)} onClick={()=>finish(c,'UNKNOWN')}>Tandai hasil belum pasti</button></>:null}
   {c.status==='UNKNOWN'&&!c.resolution?<><label>Alasan pemastian<input aria-label="Alasan pemastian pratinjau" value={resolveReason} maxLength={1000} disabled={blocked} onChange={e=>setResolveReason(e.target.value)}/></label>
    <button disabled={blocked||Boolean(pending)} onClick={()=>resolve(c,'CAPTURE_CONFIRMED')}>Pastikan tercatat</button><button disabled={blocked||Boolean(pending)} onClick={()=>resolve(c,'NOT_CAPTURED_CONFIRMED')}>Pastikan tidak tercatat</button></>:null}</div>)}</div>:null}
  {manage&&ws?<details><summary>Tujuan dan pengaturan pengingat</summary>
   <p>Tujuan sekarang: {ws.binding?`${ws.binding.label} (versi ${ws.binding.revision}, ${ws.binding.enabled?'aktif':'mati'}) untuk ${ws.binding.rules.map(ruleLabel).join(', ')}`:'belum ada'}. Hanya pratinjau lokal; bukan penerima WhatsApp.</p>
   <label>Nama tujuan<input aria-label="Nama tujuan pratinjau" value={bLabel} maxLength={120} disabled={blocked} onChange={e=>setBLabel(e.target.value)}/></label>
   <fieldset><legend>Aturan</legend>{ws.allowedRules.map(r=><label key={r}><input type="checkbox" aria-label={`Aturan tujuan ${ruleLabel(r)}`} checked={bRules.includes(r)} disabled={blocked} onChange={e=>setBRules(x=>e.target.checked?[...x,r]:x.filter(y=>y!==r))}/> {ruleLabel(r)}</label>)}</fieldset>
   <label><input type="checkbox" aria-label="Tujuan aktif" checked={bEnabled} disabled={blocked} onChange={e=>setBEnabled(e.target.checked)}/> Aktif</label>
   <label>Alasan<input aria-label="Alasan tujuan pratinjau" value={bReason} maxLength={1000} disabled={blocked} onChange={e=>setBReason(e.target.value)}/></label>
   <button disabled={blocked||Boolean(pending)} onClick={saveBinding}>Simpan tujuan pratinjau lokal</button>
   <label>Aturan pengingat<select aria-label="Aturan pengaturan pengingat" value={pRule} disabled={blocked} onChange={e=>{const r=e.target.value as ReminderRule;setPRule(r);setPUnit(r==='AR_DUE'||r==='AP_DUE'?'DAY':r==='PRODUCTION_GAP'?'PCS':'')}}>{ws.allowedRules.map(r=><option key={r} value={r}>{ruleLabel(r)}</option>)}</select></label>
   <label>Batas minimal<input aria-label="Batas pengingat" value={pValue} disabled={blocked} onChange={e=>setPValue(e.target.value.trim())}/></label>
   <label>Satuan<input aria-label="Satuan batas pengingat" value={pUnit} disabled={blocked||pRule==='PRODUCTION_GAP'||pRule==='AR_DUE'||pRule==='AP_DUE'} onChange={e=>setPUnit(e.target.value.trim())}/></label>
   <label>Jeda antar pengingat (menit)<input aria-label="Jeda pengingat" value={pCooldown} disabled={blocked} onChange={e=>setPCooldown(e.target.value.trim())}/></label>
   <label>Alasan<input aria-label="Alasan pengaturan pengingat" value={pReason} maxLength={1000} disabled={blocked} onChange={e=>setPReason(e.target.value)}/></label>
   <button disabled={blocked||Boolean(pending)} onClick={savePolicy}>Simpan pengaturan pengingat</button>
  </details>:null}
  {ws&&!manage?<p>Akun ini bisa melihat dan memeriksa ulang pengingat, tetapi tidak bisa membuat pratinjau atau mengubah pengaturan.</p>:null}
 </section>
}
