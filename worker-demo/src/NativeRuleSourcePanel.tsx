import {ReturnTaskList} from './AccessoryReturnTasks'
import {useEffect,useMemo,useRef,useState} from 'react'
import {useAuth} from './auth/AuthProvider'
import {getUatSupabaseClient} from './lib/supabase'
import {normalizeClientError} from './lib/clientError'
import {formatCp6WibDateTime} from './cp6BusinessTime'
import {assertSameAnalysis,type NativeAnalysis,type AnalysisFinanceAccess} from './nativeAnalysis'
import {productionLockManager,productionLockName,readProductionRecovery,hasProductionPending} from './productionRecovery'
import {formatFact} from './cp7/workspace'
import {reminderRuleIds,reminderRuleLabels,type ReminderRule} from './nativeReminderPolicy'
import {formatReceiptDecimal} from './procurementContract'
import {laundryServices,parseRuleSource,parseRuleObservations,parseLocalWorkspace,parseLocalCommand,readRuleRequest,persistRuleRequest,clearRuleRequest,ruleRequestKey,ruleConditionLabels,ruleEligibilityLabels,localClaimLabels,type RuleSource,type RuleObservationResult,type RuleRequest,type LocalWorkspace,type LocalClaim} from './nativeRuleSource'

type Props={context:NativeAnalysis|null;generation:number;blocked:boolean;access:AnalysisFinanceAccess;onReadStart:()=>number;isReadCurrent:(n:number)=>boolean;onReadEnd:(n:number)=>void;onAnalysis:(a:NativeAnalysis,n:number)=>void;requireClear:()=>void}
type Facts={authority:string;generation:number;source:RuleSource|null;observations:RuleObservationResult|null;local:LocalWorkspace|null}
type LastRead={authority:string;key:string;source:RuleSource}
function originalKey(a:NativeAnalysis) {
 const {actor_scope_id,allocation_scope_id,display_filter}=a.analysis.scope
 return JSON.stringify([a.runId,actor_scope_id,allocation_scope_id,display_filter,a.analysis.versions.access_epoch,
  a.analysis.snapshot.source_hash,a.query.from_date,a.query.through_date,a.query.group_mode])
}
function accessLost(e:unknown){
 const normalized=normalizeClientError(e)
 if(['AUTH_FAILED','AUTH_REQUIRED','FORBIDDEN','NOT_FOUND'].includes(normalized.code))return true
 const raw=e as {code?:string;message?:string;status?:number}
 return ['401','403','42501','PGRST301','PGRST302'].includes(String(raw?.code??raw?.status))||
  /(?:FORBIDDEN|ACCESS_DENIED|SCOPE_CHANGED|ACCESS_CHANGED|ACCESS_EPOCH|RUN_NOT_FOUND)/i.test(raw?.message??'')
}
const emptyFacts:Facts={authority:'',generation:-1,source:null,observations:null,local:null}
// Fabric condition reasons in plain words; the number itself stays the shared analysis fact.
const fabricReasonText:Record<string,string>={SOURCE_BOUND_ADDITIONAL_EXTERNAL_FABRIC_NEED:'Perlu tambahan kain dari luar menurut asumsi resep; ini bukan perintah beli.',
 SELECTED_FABRIC_RECIPE_SCENARIO_NOT_PHYSICAL_RESOLUTION:'Tidak perlu tambahan kain pada skenario ini; belum terbukti secara fisik.',
 FABRIC_RECIPE_NOT_REVIEWED:'Resep kain produk ini belum direview; kebutuhan kain belum diketahui.',
 FABRIC_WIP_IDENTITY_UNRESOLVED:'WIP sejenis belum pasti milik produk ini; lihat batas atas pada analisis.',
 FABRIC_SHARED_SUPPLY_SPLIT_UNDECIDED:'Stok bebas dibutuhkan beberapa produk; pembagian belum diputuskan.',
 FABRIC_SHARED_NEED_UNKNOWN:'Kebutuhan kain produk lain belum diketahui.',FABRIC_OTHER_NEEDS_UNREVIEWED:'Kebutuhan kain produk lain belum direview.',
 FABRIC_UNLINKED_NATIVE_DRAFT:'Ada draf potong yang belum terhubung ke rencana.',FABRIC_LINKED_DRAFT_NOT_ELIGIBLE:'Draf potong yang terhubung belum layak dihitung.',
 FABRIC_STOCK_INCONSISTENT:'Stok roll bahan ini tidak konsisten.',FABRIC_INCOMING_LOCATION_NOT_ELIGIBLE:'Ada PO ke lokasi yang bukan gudang bahan aktif.',
 FABRIC_DEADLINE_UNKNOWN:'Batas waktu kebutuhan belum diketahui.',FABRIC_INCOMING_OVERDUE:'Ada PO yang lewat tanggal datang dan belum diterima.',
 FABRIC_INCOMING_ETA_UNKNOWN:'Ada PO tanpa tanggal datang.',FABRIC_PRODUCTION_DISABLED:'Produksi baru produk ini dihentikan.',
 IMMUTABLE_ORIGINAL_REQUIRES_NEW_CAPTURE:'Analisis lama; ambil analisis baru.'}
function LaundryServiceList({document}:{document:Record<string,unknown>}){
 const rows=laundryServices(document)
 if(!rows.length)return null
 return <details><summary>Harga per layanan laundry</summary><ul>{rows.map(row=><li key={row.id}>
  {row.service} · {row.covered_qty} pcs · {{UNKNOWN:'Tarif belum diketahui',FREE:'Gratis',WAIVED:'Dibebaskan',KNOWN:'Tarif diketahui'}[row.rate_status]}
  {row.amount!==null&&<> · nilai layanan Rp{formatReceiptDecimal(row.amount)}</>}{row.reason&&<> · {row.reason}</>}
 </li>)}</ul></details>
}
export default function NativeRuleSourcePanel(props:Props){
 const{runtime,identity}=useAuth()
 if(runtime.mode!=='DISPOSABLE_TEST'||identity.status!=='AUTHORIZED'||!['OWNER','ADMIN','STAFF'].includes(identity.profile.role)||!['master.product.view','production.wip.view','warehouse.stock.view','sales.invoice.view'].every(p=>identity.permissions.includes(p)))return null
 const identityKey=JSON.stringify([runtime.projectRef,identity.profile.id,identity.profile.authUserId,identity.profile.role,
  identity.profile.rowVersion,identity.profile.roleRowVersion,[...identity.permissions].sort(),props.access])
 return <Conditions key={identityKey} {...props} projectRef={runtime.projectRef} profileId={identity.profile.id} actor={identity.profile.authUserId} manage={['OWNER','ADMIN'].includes(identity.profile.role)&&identity.permissions.includes('master.product.manage')} ar={identity.permissions.includes('finance.ar.view')} ap={identity.permissions.includes('finance.ap.view')} hpp={identity.permissions.includes('finance.hpp.view')} payroll={identity.permissions.includes('finance.payroll.view')} accessoryPayables={identity.permissions.includes('warehouse.accessory.view')&&(identity.permissions.includes('finance.hpp.view')||identity.permissions.includes('finance.hpp.manage'))} laundry={identity.permissions.includes('production.laundry.view')&&(identity.permissions.includes('finance.hpp.view')||identity.permissions.includes('finance.hpp.manage'))}/>
}
function Conditions(props:Props&{projectRef:string;profileId:string;actor:string;manage:boolean;ar:boolean;ap:boolean;hpp:boolean;payroll:boolean;accessoryPayables:boolean;laundry:boolean}){
 const{runtime}=useAuth();if(runtime.mode!=='DISPOSABLE_TEST')throw Error('Sesi pemeriksaan kondisi belum siap.')
 const client=useMemo(()=>getUatSupabaseClient(runtime),[runtime]),scope='analysis:'+props.projectRef+':'+props.profileId,productionScope='erp:'+props.projectRef+':'+props.profileId,rights={hpp:props.hpp,ar:props.ar,ap:props.ap,payroll:props.payroll,accessoryPayables:props.accessoryPayables,laundry:props.laundry}
 const authority=JSON.stringify([scope,props.actor,props.manage,rights,props.access]),authorityRef=useRef(authority);authorityRef.current=authority
 const mounted=useRef(true),active=useRef<number|null>(null),[busy,setBusy]=useState(false),[error,setError]=useState(''),[message,setMessage]=useState(''),[facts,setFacts]=useState<Facts>(emptyFacts),[recovery,setRecovery]=useState(()=>readRuleRequest(scope))
 const [last,setLast]=useState<LastRead|null>(null),[staleGeneration,setStaleGeneration]=useState<number|null>(null)
 const contextKey=props.context?originalKey(props.context):null
 const prior=last?.authority===authority&&(!contextKey||contextKey===last.key)?last:null
 const historical=staleGeneration===props.generation&&props.isReadCurrent(props.generation)?prior:null
 const readableOriginal=props.context??historical?.source.analysis
 useEffect(()=>{if(contextKey&&last&&contextKey!==last.key){setLast(null);setStaleGeneration(null)}},[contextKey,last])
 const[label,setLabel]=useState(''),[enabled,setEnabled]=useState(''),[selectedRules,setSelectedRules]=useState<ReminderRule[]>([]),[bindingReason,setBindingReason]=useState(''),[reviewed,setReviewed]=useState(false),[selectedKey,setSelectedKey]=useState(''),[resolutionReason,setResolutionReason]=useState(''),[resolutionOutcome,setResolutionOutcome]=useState(''),[resolutionReviewed,setResolutionReviewed]=useState(false),[page,setPage]=useState(0)
 useEffect(()=>{mounted.current=true;return()=>{mounted.current=false}},[])
 useEffect(()=>{const listener=(e:StorageEvent)=>{if(e.key===null||e.key===ruleRequestKey(scope)){setRecovery(readRuleRequest(scope));setFacts(emptyFacts);setLast(null);setStaleGeneration(null);setReviewed(false);setResolutionReviewed(false)}};addEventListener('storage',listener);return()=>removeEventListener('storage',listener)},[scope])
 const current=(n:number)=>mounted.current&&props.isReadCurrent(n)&&authorityRef.current===authority
 const data=facts.generation===props.generation&&facts.authority===authority&&(!contextKey||!facts.source||originalKey(facts.source.analysis)===contextKey)?facts:null
 const source=data?.source??historical?.source,blocked=props.blocked||busy||Boolean(recovery.error||recovery.pending)
 const eligible=data?.source?.rows.filter(r=>r.eligibility==='LOCAL_PREVIEW_ELIGIBLE')??[],binding=data?.local?.binding
 const perform=async(fn:(n:number)=>Promise<void>)=>{
  if(active.current!==null)return
  const n=props.onReadStart();active.current=n;setBusy(true);setFacts(emptyFacts);setStaleGeneration(null);setReviewed(false);setResolutionReviewed(false);setError('');setMessage('')
  try{await fn(n)}catch(e){if(current(n))setError(normalizeClientError(e).message)}
  finally{if(mounted.current){setBusy(false);setRecovery(readRuleRequest(scope))}if(active.current===n)active.current=null;props.onReadEnd(n)}
 }
 const load=(local=false)=>{
  const original=readableOriginal
  void perform(async n=>{
   props.requireClear()
   if(!original)throw Error('Muat analisis ERP terlebih dahulu.')
   let changedAuthority=false
   try{
    const r=local?await client.rpc('erp_cp7_get_local_reminders_v1',{p_run:original.runId}):await client.rpc('erp_cp7_get_rule_conditions_v1',{p_run:original.runId})
    if(!current(n))return
    if(r.error)throw r.error
    const raw=r.data as unknown as {source?:unknown;actor_scope_id?:string}|null
    const envelope=(local?raw?.source:raw) as {actor_scope_id?:string;analysis?:{run_id?:string;analysis?:NativeAnalysis['analysis']}}|null
    const body=envelope?.analysis?.analysis
    changedAuthority=Boolean(envelope?.actor_scope_id&&envelope.actor_scope_id!==props.actor ||
      envelope?.analysis?.run_id&&envelope.analysis.run_id!==original.runId ||
      body?.versions?.access_epoch&&body.versions.access_epoch!==original.analysis.versions.access_epoch ||
      body?.scope?.actor_scope_id!=null&&body.scope.actor_scope_id!==original.analysis.scope.actor_scope_id||
      body?.scope?.allocation_scope_id!=null&&body.scope.allocation_scope_id!==original.analysis.scope.allocation_scope_id||
      body?.scope?.display_filter!=null&&body.scope.display_filter!==original.analysis.scope.display_filter)
    if(changedAuthority)throw Error('Akses atau cakupan observasi berubah. Muat kembali analisis.')
    const workspace=local?await parseLocalWorkspace(r.data,original.query,props.actor,props.access,rights):null
    const next=workspace?.source??parseRuleSource(r.data,original.query,props.actor,props.access,rights)
    if(!current(n))return
    assertSameAnalysis(original,next.analysis)
    setLast({authority,key:originalKey(next.analysis),source:next});setFacts({authority,generation:n,source:next,observations:null,local:workspace})
    setPage(0);props.onAnalysis(next.analysis,n)
   }catch(e){
    if(current(n)){
     if(changedAuthority||accessLost(e))setLast(null)
     else if(prior?.key===originalKey(original))setStaleGeneration(n)
    }
    throw e
   }
  })
 }
 const send=(request:RuleRequest,lookup=false)=>void perform(async n=>{
  props.requireClear();const manager=productionLockManager();if(!manager)throw Error('Pencatatan pemeriksaan membutuhkan pengunci tab. Sumber masih dapat dibaca.')
  await manager.request(productionLockName(productionScope),{mode:'exclusive',ifAvailable:true},async lock=>{
   if(!lock)throw Error('Ada transaksi ERP di tab lain. Tunggu selesai.');if(!current(n))return;const shared=readProductionRecovery(productionScope);if(shared.corrupted||!lookup&&hasProductionPending(shared))throw Error('Pastikan hasil transaksi ERP yang tertunda terlebih dahulu.')
   persistRuleRequest(scope,request);setRecovery(readRuleRequest(scope));const args={p_payload:request.payload,p_request:request.id}
   const r=request.operation==='EPISODES'?(lookup?await client.rpc('erp_cp7_get_rule_episode_request_v1',args):await client.rpc('erp_cp7_evaluate_rule_episodes_v1',args)):lookup?await client.rpc('erp_cp7_get_local_reminder_request_v1',{...args,p_operation:request.operation}):request.operation==='BINDING'?await client.rpc('erp_cp7_save_local_binding_v1',args):request.operation==='PREVIEW'?await client.rpc('erp_cp7_claim_local_preview_v1',args):request.operation==='OUTCOME'?await client.rpc('erp_cp7_finish_local_preview_v1',args):await client.rpc('erp_cp7_resolve_local_preview_v1',args)
   if(!current(n))return;if(r.error)throw r.error
   const observations=request.operation==='EPISODES'?parseRuleObservations(r.data,request,props.actor,props.access,rights):null,command=observations?null:await parseLocalCommand(r.data,request,props.actor,props.access,rights),source=observations?.source??command!.workspace.source
   if(!current(n))return;clearRuleRequest(scope,request.id);setRecovery(readRuleRequest(scope));setFacts({authority,generation:n,source,observations,local:command?.workspace??null});props.onAnalysis(source.analysis,n);setMessage((observations?.status??command?.status)==='COMMITTED'?'Catatan tersimpan. Status bisnis tetap mengikuti sumber ERP.':'Permintaan lama belum tersimpan dan sudah ditutup. Periksa sumber sebelum mencoba lagi.')
  })
 })
 const action=(operation:RuleRequest['operation'],payload:RuleRequest['payload'])=>{try{props.requireClear();const held=readRuleRequest(scope);if(held.error||held.pending)throw Error(held.error??'Pastikan hasil permintaan lokal yang tertunda.');if(!props.context||!data?.source||historical)throw Error('Periksa sumber terlebih dahulu.');send({id:crypto.randomUUID(),query:props.context.query,operation,payload:{run_id:props.context.runId,...payload}})}catch(e){setError(normalizeClientError(e).message)}}
 const retry=(lookup:boolean)=>{try{const held=readRuleRequest(scope);setRecovery(held);if(!held.pending)throw Error(held.error??'Permintaan lokal tidak tersedia.');send(held.pending,lookup)}catch(e){setError(normalizeClientError(e).message)}}
 const saveBinding=()=>{if(!reviewed||!['true','false'].includes(enabled)||!label.trim()||!bindingReason.trim()||!selectedRules.length)return;action('BINDING',{expected_revision:binding?.revision??'0',enabled:enabled==='true',label,environment:'LOCAL_TEST_SINK',rules:selectedRules,reason:bindingReason})}
 const finish=(claim:LocalClaim,outcome:'LOCAL_CAPTURE'|'UNKNOWN')=>action('OUTCOME',{claim_id:claim.id,fence:claim.fence,outcome})
 const resolve=(claim:LocalClaim)=>{if(!resolutionReviewed||!resolutionReason.trim()||!['CAPTURE_CONFIRMED','NOT_CAPTURED_CONFIRMED'].includes(resolutionOutcome))return;action('RESOLUTION',{claim_id:claim.id,fence:claim.fence,outcome:resolutionOutcome,reason:resolutionReason})}
 return <section aria-label="Kondisi masalah dan pratinjau lokal"><h3>Kondisi yang perlu ditangani</h3><p>Sudah dibaca, selesai ditinjau, dan hasil pesan adalah catatan terpisah. Masalah selesai hanya ketika sumber ERP membuktikannya.</p>
  <button disabled={blocked||!readableOriginal}onClick={()=>load()}>Periksa kondisi masalah ERP</button>{props.manage?<button disabled={blocked||!readableOriginal}onClick={()=>load(true)}>Muat pratinjau lokal tersimpan</button>:null}
  {error?<p role="alert">{error}</p>:null}{recovery.error?<p role="alert">{recovery.error}</p>:null}{message?<p role="status">{message}</p>:null}
  {recovery.pending?<aside><p>Hasil pencatatan belum diketahui. Permintaan yang sama dipertahankan.</p><button disabled={props.blocked||busy}onClick={()=>retry(false)}>Ulangi permintaan kondisi yang sama</button><button disabled={props.blocked||busy}onClick={()=>retry(true)}>Pastikan hasil kondisi di server</button></aside>:null}
  {historical&&<p role="status">Pembacaan gagal. Kondisi berikut memakai observasi terakhir yang berhasil pada {formatCp6WibDateTime(historical.source.readAt)} · {Math.max(0,Math.floor((Date.now()-Date.parse(historical.source.readAt))/60000))} menit lalu. Baca ulang untuk memperbarui.</p>}
  {source?<>{Boolean(source.recostTasks?.length)&&<section aria-label="Hitung ulang HPP"><h4>HPP menunggu hitung ulang</h4><ul>{source.recostTasks!.map(t=><li key={t.queue_id}>{t.po_number??t.entity_id} · {t.status} · antrean {t.queue_id}</li>)}</ul></section>}{Boolean(source.returnTasks?.length)&&<ReturnTaskList rows={source.returnTasks!}/>}<p>Kondisi diperiksa {formatCp6WibDateTime(source.readAt)} · {source.rows.length} kondisi.</p><p>Saldo awal, gaji, aksesori, dan laundry mengikuti hak akses saat ini. Sisa tagihan disalin dari sumber ERP; tanggal yang belum dicatat tetap belum diketahui. Alokasi ke gaji dan perkiraan laundry belum membuktikan pembayaran.</p><button disabled={blocked||Boolean(historical)}onClick={()=>action('EPISODES',{source_hash:source.hash})}>Catat pemeriksaan kondisi ERP</button>
   {source.rows.slice(page*25,(page+1)*25).map(r=><article key={r.key}aria-label={`Kondisi ${r.key}`}><h4>{reminderRuleLabels[r.rule_id]} · {r.label}</h4><p>{r.reason==='PRICE_KNOWN_AWAITING_INVOICE'?'Menunggu tagihan laundry':ruleConditionLabels[r.state]}. {r.value.unit==='DAY'?'Umur jatuh tempo: ':''}{formatFact(r.value)}</p>{r.rule_id==='FABRIC_NEED'?<p>{fabricReasonText[r.reason]??'Lihat penjelasan kebutuhan kain pada analisis bersama.'}</p>:null}{r.financial_source?<>{r.domain==='LAUNDRY_RECEIPT'&&<LaundryServiceList document={r.financial_source.document}/>}<p>Sisa tagihan: {formatFact(r.financial_source.remaining)}.</p><p>{r.financial_source.recorded_due_date?'Jatuh tempo '+r.financial_source.recorded_due_date:'Tanggal jatuh tempo belum dicatat'}.</p>{r.economic_state==='OPEN'?<p>Saldo kewajiban masih terbuka, termasuk ketika umur jatuh tempo belum diketahui.</p>:null}{r.reason==='ALLOCATION_NOT_SETTLEMENT'?<p>Nilai yang dialokasikan ke gaji belum membuktikan bahwa aksesori sudah dibayar.</p>:null}{r.reason==='PRICE_KNOWN_AWAITING_INVOICE'?<p>Tarif layanan sudah diketahui. Penerimaan menunggu tagihan untuk sisa yang belum ditagih.</p>:null}{r.reason==='LAUNDRY_FREE'?<p>Seluruh layanan tercatat gratis.</p>:null}{r.reason==='LAUNDRY_WAIVED'?<p>Seluruh layanan tercakup dalam tarif nol dan pembebasan yang tercatat.</p>:null}{['VALUE_PENDING','INVOICE_PENDING'].includes(r.reason)?<p>Nota belum lengkap. Perkiraan biaya belum menjadi saldo tagihan final.</p>:null}</>:null}<p>{ruleEligibilityLabels[r.eligibility]}. {r.policy_timing.next_at?'Dapat diperiksa lagi '+formatCp6WibDateTime(r.policy_timing.next_at)+'.':''}</p><p>{r.business_resolved?'Sumber membuktikan selesai.':'Belum ada bukti sumber bahwa masalah ini selesai.'}</p>{r.production_state==='PAUSED'||r.production_state==='STOPPED'?<p>Produksi ditunda atau dihentikan; kebutuhan tercatat tetap dipertahankan.</p>:null}<details><summary>Dasar pemeriksaan kondisi</summary><p>{r.reason} · {r.source_hash}</p><p>{r.policy_binding.policy?'Mengikuti versi aturan '+r.policy_binding.policy.revision+'.':'Aturan belum diatur.'}</p></details></article>)}
   <nav aria-label="Halaman kondisi masalah"><button disabled={blocked||page===0}onClick={()=>setPage(p=>p-1)}>Kondisi sebelumnya</button><span>Halaman {page+1} dari {Math.max(1,Math.ceil(source.rows.length/25))}</span><button disabled={blocked||(page+1)*25>=source.rows.length}onClick={()=>setPage(p=>p+1)}>Kondisi berikutnya</button></nav>
   {data?.observations?<section aria-label="Catatan pemeriksaan kondisi"><h4>Catatan pemeriksaan kondisi</h4>{data.observations.freshness==='HISTORICAL_SOURCE_CHANGED'?<p>Catatan ini memakai sumber sebelumnya. Sumber terkini ditampilkan pada daftar kondisi.</p>:null}{data.observations.rows.filter(r=>r.episode).map(r=><p key={r.condition.key}>{r.condition.label} · kejadian {r.episode!.number} · {r.episode!.state==='ARCHIVED'?'diarsipkan karena transaksi asal tidak aktif; bukan pembayaran':r.episode!.state==='RESOLVED'?'sumber membuktikan selesai':'masih terbuka'} · pertama dicatat {formatCp6WibDateTime(r.episode!.first_observed_at)}. {r.episode!.freshness==='UNKNOWN'?'Data kini belum pasti; umur masalah tetap dipertahankan.':''}</p>)}</section>:null}
  </>:null}
  {props.manage?<><h4>Pratinjau lokal</h4><p>Pratinjau ini dicatat di aplikasi uji. Belum ada penerima, pengiriman keluar, atau penjadwalan otomatis.</p>
   {data?.local?<><p>{binding?'Tujuan lokal: '+binding.label+' · versi '+binding.revision+' · '+(binding.enabled?'aktif':'dimatikan')+'.':'Belum ada tujuan pratinjau lokal.'}</p><fieldset disabled={blocked}><legend>Tujuan pratinjau yang ditinjau</legend><label>Nama tujuan lokal<input aria-label="Nama tujuan lokal"maxLength={120}value={label}onChange={e=>{setLabel(e.target.value);setReviewed(false)}}/></label><label>Status tujuan lokal<select aria-label="Status tujuan lokal"value={enabled}onChange={e=>{setEnabled(e.target.value);setReviewed(false)}}><option value="">Pilih status</option><option value="true">Aktif</option><option value="false">Dimatikan</option></select></label>
    {reminderRuleIds.filter(r=>r==='AR_DUE'?props.ar:r==='AP_DUE'?props.ap:true).map(r=><label key={r}><input aria-label={`Tujuan lokal ${reminderRuleLabels[r]}`}type="checkbox"checked={selectedRules.includes(r)}onChange={e=>{setSelectedRules(s=>e.target.checked?[...s,r]:s.filter(x=>x!==r));setReviewed(false)}}/>{reminderRuleLabels[r]}</label>)}
    <label>Alasan tujuan lokal<textarea aria-label="Alasan tujuan lokal"maxLength={1000}value={bindingReason}onChange={e=>{setBindingReason(e.target.value);setReviewed(false)}}/></label><label><input aria-label="Tujuan lokal sudah ditinjau"type="checkbox"checked={reviewed}onChange={e=>setReviewed(e.target.checked)}/>Tujuan dan aturan sudah saya tinjau.</label><button disabled={!reviewed||!enabled||!label.trim()||!bindingReason.trim()||!selectedRules.length}onClick={saveBinding}>Simpan versi tujuan lokal</button></fieldset>
    <label>Kondisi untuk pratinjau<select aria-label="Kondisi untuk pratinjau"value={selectedKey}disabled={blocked}onChange={e=>setSelectedKey(e.target.value)}><option value="">Pilih kondisi yang sudah diperiksa</option>{eligible.map(r=><option key={r.key}value={r.key}>{reminderRuleLabels[r.rule_id]} · {r.label}</option>)}</select></label><button disabled={blocked||!binding?.enabled||!eligible.some(r=>r.key===selectedKey&&binding.rules.includes(r.rule_id))}onClick={()=>action('PREVIEW',{condition_key:selectedKey,source_hash:source!.hash,binding_id:binding!.id})}>Buat pratinjau lokal</button>
    {data.local.claims.map(c=><article key={c.id}aria-label={`Pratinjau lokal ${c.id}`}><h5>{source!.rows.find(r=>r.key===c.condition_key)?.label}</h5><p>{localClaimLabels[c.status]}. Pesan belum dikirim keluar.</p>{c.body?<pre aria-label="Isi pratinjau lokal">{c.body}</pre>:<p>Isi sumber lama tidak ditampilkan sebagai pratinjau terkini.</p>}{c.status==='CLAIMED'?<><button disabled={blocked}onClick={()=>finish(c,'LOCAL_CAPTURE')}>Catat hasil pratinjau lokal</button><button disabled={blocked}onClick={()=>finish(c,'UNKNOWN')}>Hasil pratinjau belum pasti</button></>:null}{c.status==='UNKNOWN'&&!c.resolution?<fieldset disabled={blocked}><legend>Pastikan hasil lokal secara manual</legend><p>Permintaan baru ditahan sampai hasil ini dipastikan. Catatan lama tetap utuh.</p><label>Hasil pemeriksaan manual<select aria-label="Hasil pemeriksaan manual"value={resolutionOutcome}onChange={e=>{setResolutionOutcome(e.target.value);setResolutionReviewed(false)}}><option value="">Pilih hasil yang sudah diperiksa</option><option value="CAPTURE_CONFIRMED">Pratinjau sudah tercatat</option><option value="NOT_CAPTURED_CONFIRMED">Pratinjau belum tercatat</option></select></label><label>Alasan pemeriksaan manual<textarea aria-label="Alasan pemeriksaan manual"maxLength={1000}value={resolutionReason}onChange={e=>{setResolutionReason(e.target.value);setResolutionReviewed(false)}}/></label><label><input aria-label="Hasil lokal sudah diperiksa"type="checkbox"checked={resolutionReviewed}onChange={e=>setResolutionReviewed(e.target.checked)}/>Saya sudah memeriksa hasil lokal dan alasannya.</label><button disabled={!resolutionReviewed||!resolutionOutcome||!resolutionReason.trim()}onClick={()=>resolve(c)}>Simpan kepastian hasil lokal</button></fieldset>:null}{c.resolution?<p>Hasil dipastikan secara manual: {c.resolution.outcome==='CAPTURE_CONFIRMED'?'sudah tercatat':'belum tercatat'}. Alasan: {c.resolution.reason}. Kejadian lama tetap {localClaimLabels[c.status].toLowerCase()}.</p>:null}</article>)}
   </>:null}
  </>:null}
 </section>
}
