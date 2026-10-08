// PL-5 B (owner decision 8 Oct 2026): the history yield policy (versioned, signed by
// an owner or admin) and the history yield the plan preview states. The client never
// computes a yield; it checks what the server returned, including the Wilson bound.
export type YieldPolicyState='ACTIVE'|'PAUSED'
export type YieldPolicyRow={id:string;revision:string;state:YieldPolicyState;windowDays:string;minGroups:string;minCutPcs:string;confidence:'0.90';reason:string;actor:string;actorRole:'OWNER'|'ADMIN';recordedAt:string}
export type YieldPolicyValues={windowDays:string;minGroups:string;minCutPcs:string}
export type YieldPolicyWorkspace={state:'PENDING_POLICY_VALUE'|YieldPolicyState;current:YieldPolicyRow|null;revisions:YieldPolicyRow[];decided:YieldPolicyValues;manageAllowed:boolean}
export type YieldPolicyPayload={expected_revision:string;state:YieldPolicyState;window_days:string;min_groups:string;min_cut_pcs:string;confidence:'0.90';reason:string}
export type YieldPolicyRequest={id:string;payload:YieldPolicyPayload}
export type HistoryLevel={level:'PRODUCT_SIZE'|'MODEL';status:string;groups:string|null;cutPcs:string|null;fgPcs:string|null}
export type HistoryYield={status:'PENDING_POLICY_VALUE'|'POLICY_PAUSED'|'AVAILABLE'|'INSUFFICIENT_SAMPLE'|'UNKNOWN';reason:string|null;level:'PRODUCT_SIZE'|'MODEL'|null;
 groups:string|null;cutPcs:string|null;fgPcs:string|null;permille:string|null;policyRevision:string|null;minGroups:string|null;minCutPcs:string|null;levels:HistoryLevel[]}

const fail=():never=>{throw Error('Kebijakan atau hasil yield histori dari server berubah atau belum lengkap. Muat ulang.')}
const obj=(v:unknown):Record<string,unknown>=>v&&typeof v==='object'&&!Array.isArray(v)?v as Record<string,unknown>:fail()
const str=(v:unknown)=>typeof v==='string'&&v.length>0?v:fail()
const id=(v:unknown)=>typeof v==='string'&&/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(v)?v:fail()
const count=(v:unknown)=>typeof v==='string'&&/^(0|[1-9][0-9]{0,18})$/.test(v)?v:fail()
const exact=(v:Record<string,unknown>,keys:string[])=>{if(Object.keys(v).sort().join('|')!==[...keys].sort().join('|'))fail()}
const between=(v:string,lo:bigint,hi:bigint)=>{const n=BigInt(v);if(n<lo||n>hi)fail();return v}
const DECIDED={decision:'OWNER_DECISION_2026_10_08',window_days:'180',min_groups:'5',min_cut_pcs:'200',confidence:'0.90',method:'WILSON_SCORE_ONE_SIDED_LOWER_BOUND',rounding:'FLOOR_PERMILLE'}

function row(raw:unknown):YieldPolicyRow{
 const r=obj(raw);exact(r,['id','revision','state','window_days','min_groups','min_cut_pcs','confidence','method','rounding','levels','reason','actor','actor_role','recorded_at'])
 if(r.state!=='ACTIVE'&&r.state!=='PAUSED'||r.confidence!=='0.90'||r.method!==DECIDED.method||r.rounding!==DECIDED.rounding||JSON.stringify(r.levels)!=='["PRODUCT_SIZE","MODEL"]'||(r.actor_role!=='OWNER'&&r.actor_role!=='ADMIN'))fail()
 const reason=str(r.reason);if(reason.length>1000)fail()
 return{id:id(r.id),revision:between(count(r.revision),1n,10n**18n),state:r.state as YieldPolicyState,windowDays:between(count(r.window_days),1n,3660n),minGroups:between(count(r.min_groups),1n,1000n),
  minCutPcs:between(count(r.min_cut_pcs),1n,1000000n),confidence:'0.90',reason,actor:id(r.actor),actorRole:r.actor_role as YieldPolicyRow['actorRole'],recordedAt:str(r.recorded_at)}
}
export function parseYieldPolicyWorkspace(raw:unknown):YieldPolicyWorkspace{
 const w=obj(raw);exact(w,['contract_version','state','current','revisions','decided_package','manage_allowed'])
 if(w.contract_version!=='cp7.history-yield-policy.v1'||typeof w.manage_allowed!=='boolean'||!Array.isArray(w.revisions)||w.revisions.length>50)fail()
 const d=obj(w.decided_package);exact(d,['decision','window_days','min_groups','min_cut_pcs','confidence','method','rounding','levels'])
 for(const[k,v]of Object.entries(DECIDED))if(d[k]!==v)fail()
 if(JSON.stringify(d.levels)!=='["PRODUCT_SIZE","MODEL"]')fail()
 const revisions=(w.revisions as unknown[]).map(row),current=w.current===null?null:row(w.current)
 if(revisions.some((r,i)=>i>0&&BigInt(r.revision)>=BigInt(revisions[i-1].revision)))fail()
 if(current===null?(w.state!=='PENDING_POLICY_VALUE'||revisions.length!==0):(w.state!==current.state||revisions[0]?.id!==current.id))fail()
 return{state:w.state as YieldPolicyWorkspace['state'],current,revisions,decided:{windowDays:DECIDED.window_days,minGroups:DECIDED.min_groups,minCutPcs:DECIDED.min_cut_pcs},manageAllowed:w.manage_allowed as boolean}
}
export function yieldPolicyPayload(ws:YieldPolicyWorkspace,state:YieldPolicyState,values:YieldPolicyValues,reason:string):YieldPolicyPayload{
 const clean=reason.trim();if(!clean||clean.length>1000)throw Error('Isi alasan kebijakan, maksimal 1000 karakter.')
 const whole=(v:string,hi:bigint,label:string)=>{if(!/^[1-9][0-9]*$/.test(v)||BigInt(v)>hi)throw Error(label+' harus bilangan bulat 1 sampai '+hi.toString()+'.');return v}
 return{expected_revision:ws.current?.revision??'0',state,window_days:whole(values.windowDays.trim(),3660n,'Jendela histori (hari)'),min_groups:whole(values.minGroups.trim(),1000n,'Minimal grup selesai'),
  min_cut_pcs:whole(values.minCutPcs.trim(),1000000n,'Minimal PCS potong'),confidence:'0.90',reason:clean}
}
export function checkYieldPolicyOutcome(raw:unknown,r:YieldPolicyRequest):YieldPolicyRow{
 const o=obj(raw);exact(o,['contract_version','request_id','policy']);if(o.contract_version!=='cp7.history-yield-policy-outcome.v1'||o.request_id!==r.id)fail()
 const p=row(o.policy),q=r.payload
 if(BigInt(p.revision)!==BigInt(q.expected_revision)+1n||p.state!==q.state||p.windowDays!==q.window_days||p.minGroups!==q.min_groups||p.minCutPcs!==q.min_cut_pcs||p.reason!==q.reason)fail()
 return p
}
export const yieldPolicyRequestKey=(scope:string)=>'erp.cp7.history-yield-policy-request.v1:'+scope
export function readYieldPolicyRequest(scope:string):{pending:YieldPolicyRequest|null;error:string}{
 try{const raw=localStorage.getItem(yieldPolicyRequestKey(scope));if(raw===null)return{pending:null,error:''}
  const r=obj(JSON.parse(raw)),p=obj(r.payload);exact(r,['id','payload']);exact(p,['expected_revision','state','window_days','min_groups','min_cut_pcs','confidence','reason'])
  if(p.state!=='ACTIVE'&&p.state!=='PAUSED'||p.confidence!=='0.90')fail();const reason=str(p.reason);if(reason.trim()!==reason||reason.length>1000)fail()
  return{pending:{id:id(r.id),payload:{expected_revision:count(p.expected_revision),state:p.state as YieldPolicyState,window_days:between(count(p.window_days),1n,3660n),min_groups:between(count(p.min_groups),1n,1000n),
   min_cut_pcs:between(count(p.min_cut_pcs),1n,1000000n),confidence:'0.90',reason}},error:''}}
 catch{return{pending:null,error:'Permintaan simpan kebijakan belum bisa dibaca. Pulihkan catatan sebelum menyimpan lagi.'}}
}
export function persistYieldPolicyRequest(scope:string,r:YieldPolicyRequest){
 const old=readYieldPolicyRequest(scope);if(old.error||old.pending)throw Error('Pastikan permintaan tersimpan yang sama terlebih dahulu.')
 const raw=JSON.stringify(r);localStorage.setItem(yieldPolicyRequestKey(scope),raw);if(localStorage.getItem(yieldPolicyRequestKey(scope))!==raw||readYieldPolicyRequest(scope).pending?.id!==r.id)throw Error('Permintaan simpan belum tersimpan. Periksa penyimpanan.')
}
export function clearYieldPolicyRequest(scope:string,requestId:string){
 const old=readYieldPolicyRequest(scope);if(old.error||old.pending?.id!==requestId)throw Error('Catatan simpan kebijakan berubah. Periksa permintaan yang sama.')
 localStorage.removeItem(yieldPolicyRequestKey(scope));if(localStorage.getItem(yieldPolicyRequestKey(scope))!==null)throw Error('Catatan simpan kebijakan belum dapat diselesaikan.')
}

// The one-sided 90% Wilson bound, floored to 0.1%, checked exactly in integers:
// z=Z/D, A'=1000(2x·D²+Z²)−2k(n·D²+Z²); 1000L≥k ⇔ A'≥0 and A'²·n≥10⁶·Z²·(Z²·n+4x(n−x)·D²).
const Z=12815515655446004n,D=10n**16n
const bound=(x:bigint,n:bigint,k:bigint)=>{const a=1000n*(2n*x*D*D+Z*Z)-2n*k*(n*D*D+Z*Z);return a>=0n&&a*a*n>=1000000n*Z*Z*(Z*Z*n+4n*x*(n-x)*D*D)}
export const wilsonPermilleHolds=(fg:string,cut:string,permille:string)=>{const x=BigInt(fg),n=BigInt(cut),k=BigInt(permille);return n>0n&&x>=0n&&x<=n&&bound(x,n,k)&&!bound(x,n,k+1n)}

const PENDING=['status','reason','window_days','minimum_sample','lower_bound','numerator','denominator','target_key']
export function parseHistoryYield(raw:unknown,targetKey:string):HistoryYield{
 const h=obj(raw)
 if(h.status==='PENDING_POLICY_VALUE'){
  exact(h,PENDING);if(h.reason!=='OWNER_HISTORY_YIELD_POLICY_NOT_APPROVED'||h.target_key!==targetKey||PENDING.slice(2,7).some(k=>h[k]!==null))fail()
  return{status:'PENDING_POLICY_VALUE',reason:null,level:null,groups:null,cutPcs:null,fgPcs:null,permille:null,policyRevision:null,minGroups:null,minCutPcs:null,levels:[]}
 }
 if(h.contract_version!=='cp7.history-yield.v2'||h.target_key!==targetKey||!['POLICY_PAUSED','AVAILABLE','INSUFFICIENT_SAMPLE','UNKNOWN'].includes(h.status as string))fail()
 const policy=obj(h.policy),ms=obj(h.minimum_sample),levels=Array.isArray(h.levels)?h.levels.map(x=>{const l=obj(x);if(l.level!=='PRODUCT_SIZE'&&l.level!=='MODEL')fail()
  return{level:l.level as HistoryLevel['level'],status:str(l.status),groups:l.groups==null?null:count(l.groups),cutPcs:l.cut_pcs==null?null:count(l.cut_pcs),fgPcs:l.fg_pcs==null?null:count(l.fg_pcs)}}):fail()
 const out:HistoryYield={status:h.status as HistoryYield['status'],reason:typeof h.reason==='string'?h.reason:null,level:null,groups:null,cutPcs:null,fgPcs:null,permille:null,
  policyRevision:count(policy.revision),minGroups:count(ms.groups),minCutPcs:count(ms.cut_pcs),levels}
 if(h.status==='AVAILABLE'){
  if(h.level!=='PRODUCT_SIZE'&&h.level!=='MODEL'||h.denominator!=='1000'||h.numerator!==h.lower_bound_permille||h.basis!=='PL8_STORED_PROOF_MATCHING_CURRENT_FACTS')fail()
  const g=count(h.groups),c=count(h.cut_pcs),f=count(h.fg_pcs),k=count(h.numerator)
  if(BigInt(k)<1n||BigInt(k)>999n||BigInt(g)<BigInt(out.minGroups!)||BigInt(c)<BigInt(out.minCutPcs!)||!wilsonPermilleHolds(f,c,k))fail()
  Object.assign(out,{level:h.level,groups:g,cutPcs:c,fgPcs:f,permille:k})
 }else if(h.numerator!==null||h.denominator!==null)fail()
 return out
}
const pct=(permille:string)=>{const n=Number(permille);return `${Math.floor(n/10)},${n%10}%`}
const levelText=(l:string|null)=>l==='PRODUCT_SIZE'?'produk dan ukuran ini':'model yang sama'
const reasonText:Record<string,string>={HISTORY_GROUP_LIMIT:'lebih dari 200 grup pada satu tingkat',TARGET_MODEL_CHANGED:'model produk berubah',PROOF_KERNEL_UNAVAILABLE:'bukti grup habis belum dapat diperiksa',
 HISTORY_SOURCE_INCOMPLETE:'sumber produksi belum lengkap',HISTORY_NORMALIZATION_REFUSED:'sumber produksi belum konsisten',LOWER_BOUND_BELOW_ONE_PERMILLE:'batas bawah di bawah 0,1%'}
export function historyYieldText(h:HistoryYield):string{
 if(h.status==='AVAILABLE')return `batas bawah ${pct(h.permille!)} dari ${h.groups} grup selesai (${h.fgPcs} PCS bagus dari ${h.cutPcs} PCS potong), tingkat ${levelText(h.level)}; kebijakan versi ${h.policyRevision}`
 if(h.status==='PENDING_POLICY_VALUE')return 'kebijakan yield histori belum disimpan'
 if(h.status==='POLICY_PAUSED')return 'kebijakan yield histori sedang dijeda'
 if(h.status==='INSUFFICIENT_SAMPLE')return `data histori belum cukup (${h.levels.map(l=>`${l.level==='PRODUCT_SIZE'?'produk+ukuran':'model'} ${l.groups??'0'} grup/${l.cutPcs??'0'} PCS`).join('; ')}; perlu minimal ${h.minGroups} grup dan ${h.minCutPcs} PCS potong)`
 return `histori belum dapat dipastikan: ${reasonText[h.reason??'']??'sumber belum lengkap'}`
}
