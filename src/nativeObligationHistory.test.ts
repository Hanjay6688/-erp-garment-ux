import{it,expect}from'vitest'
import{parseNativeObligationHistory as parse,type ObligationHistoryQuery}from'./nativeObligationEpisodes'
import{nativeEpisodeFixture}from'../tests/fixtures/nativeObligationEpisodes'
import original from'../tests/fixtures/nativeAnalysisStandin.json'
import type{NativeDemandQuery}from'./nativeDemandHistory'
const q=original.query as NativeDemandQuery,actor=original.analysis.scope.actor_scope_id,finance={ownerReports:false,preflight:false}
const p:ObligationHistoryQuery={run_id:original.run_id,domain:'AR',source_id:nativeEpisodeFixture().result.rows[0].source_id,before_episode:null,through_episode:null,limit:25}
const id=(n:number)=>'00000000-0000-4000-8000-'+String(n).padStart(12,'0')
function fixture(count=1){
 const a=nativeEpisodeFixture(),r=a.result.rows[0],rows=Array.from({length:Math.min(count,25)},(_,j)=>{
  const n=count-j,active=n===count,ep={...structuredClone(r.episode),id:id(900+n),number:String(n),previous_episode_id:n===1?null:id(900+n-1),state:active?'ACTIVE':'RESOLVED',closed_at:active?null:a.read_at}
  return{source_label:r.source_label,condition_state:active?'OVERDUE':'ZERO_BALANCE',reason:active?'NATIVE_CONDITION_REQUIRES_REVIEW':'NATIVE_ZERO_AND_REQUIRED_INVOICE_COVERAGE',source_revision:r.source_revision,native_source_hash:r.native_source_hash,episode:ep}
 })
 return{contract_version:'cp7.native-obligation-history.v1',actor_scope_id:actor,analysis:structuredClone(original),read_kind:'SAVED_EPISODE_HISTORY',domain:'AR',source_id:p.source_id,source_label:r.source_label,source_scope_hash:'c'.repeat(64),source_scope_read_at:a.read_at,through_episode:String(count),before_episode:null as string|null,limit:25,total:String(count),rows,next_before_episode:count>25?rows.at(-1)!.episode.number:null as string|null,page_complete:true,read_at:a.read_at}
}
const read=(e=fixture(),query=p)=>parse(e,q,actor,finance,query,true)
it('keeps deep-owned saved history, Native revisions and the exact immutable Original without a live balance projection',()=>{
 const e=fixture(),r=read(e);expect(r.analysis.analysis).toEqual(original.analysis);expect(r.rows[0].source_revision).toBe('9007199254740993');e.rows[0].source_label='changed outside receiver';expect(r.rows[0].source_label).toBe('AR-SUMBER-1');expect(JSON.stringify(r.rows)).not.toContain('remaining')
})
it('accepts complete anchored25 plus1 pages and refuses a missing cursor, duplicate/reordered row or wrong page anchor',()=>{
 const e=fixture(26);expect(read(e).nextBefore).toBe('2');const last=fixture(1);Object.assign(last,{through_episode:'26',before_episode:'2',total:'26'});Object.assign(last.rows[0],{condition_state:'ZERO_BALANCE',reason:'NATIVE_ZERO_AND_REQUIRED_INVOICE_COVERAGE'});Object.assign(last.rows[0].episode,{state:'RESOLVED',closed_at:last.read_at});expect(read(last,{...p,before_episode:'2',through_episode:'26'}).rows[0].episode.number).toBe('1')
 const noCursor=fixture(26);noCursor.next_before_episode=null;expect(()=>read(noCursor)).toThrow();const duplicate=fixture(26);duplicate.rows[1]=structuredClone(duplicate.rows[0]);expect(()=>read(duplicate)).toThrow();const reordered=fixture(26);reordered.rows.reverse();expect(()=>read(reordered)).toThrow();expect(()=>read(last,{...p,before_episode:'2',through_episode:'25'})).toThrow()
})
it('preserves archived Original and closed resolution; UNKNOWN can never be a resolved historical episode',()=>{
 const e=fixture(2);e.analysis.source_state='ARCHIVED_STALE';expect(read(e).analysis.state).toBe('ARCHIVED_STALE');e.rows[1].episode.freshness='UNKNOWN';expect(()=>read(e)).toThrow();const a=fixture();Object.assign(a.rows[0],{condition_state:'SOURCE_UNKNOWN',reason:'SOURCE_INCOMPLETE'});a.rows[0].episode.freshness='UNKNOWN';expect(read(a).rows[0].episode.freshness).toBe('UNKNOWN')
})
it('requires current actor/domain/source/Original and declared source-scope integrity before exposing saved history',()=>{
 for(const change of[(e:ReturnType<typeof fixture>)=>{e.actor_scope_id='foreign'},(e:ReturnType<typeof fixture>)=>{e.domain='MATERIAL_AP'},(e:ReturnType<typeof fixture>)=>{e.source_id=id(303)},(e:ReturnType<typeof fixture>)=>{e.source_scope_hash='bad'},(e:ReturnType<typeof fixture>)=>{e.limit=50},(e:ReturnType<typeof fixture>)=>{e.page_complete=false},(e:ReturnType<typeof fixture>)=>{e.source_scope_read_at='2026-10-01T01:00:00+00:00'}]){
  const e=fixture();change(e);expect(()=>read(e)).toThrow()
 }
 expect(()=>parse(fixture(),q,actor,finance,p,false)).toThrow();expect(()=>read(fixture(),{...p,run_id:id(444)})).toThrow()
})
it('rejects undocumented money/actor fields, fabricated empty completion, future clocks and out-of-range Native integer transport',()=>{
 const extra=fixture();Object.assign(extra.rows[0],{remaining:'0'});expect(()=>read(extra)).toThrow();const empty=fixture();empty.rows=[];expect(()=>read(empty)).toThrow();const future=fixture();future.rows[0].episode.last_observed_at='2026-10-02T00:00:00+00:00';expect(()=>read(future)).toThrow();const unsafe=fixture();unsafe.rows[0].source_revision='9223372036854775808';expect(()=>read(unsafe)).toThrow();const number=fixture();Object.assign(number,{total:1});expect(()=>read(number)).toThrow()
})
it('accepts a truly empty metadata history only with a complete zero origin; it does not mean the Native bill is healthy',()=>{
 const e=fixture(0);expect(read(e).rows).toEqual([]);expect(read(e).through).toBe('0');e.through_episode='1';expect(()=>read(e)).toThrow()
})

it('refuses impossible history reason/condition pairs and an exclusive cursor beyond its frozen anchor',()=>{const e=fixture();e.rows[0].reason='NATIVE_BALANCE_UNKNOWN';expect(()=>read(e)).toThrow();const page=fixture(2);page.before_episode='4';expect(()=>read(page,{...p,before_episode:'4',through_episode:'2'})).toThrow()})

it('accepts the actual Native UNKNOWN observation shape without turning its saved last-known overdue condition into current knowledge',()=>{const e=fixture();e.rows[0].episode.freshness='UNKNOWN';e.rows[0].reason='SOURCE_INCOMPLETE';const got=read(e);expect(got.rows[0].condition_state).toBe('OVERDUE');expect(got.rows[0].episode.freshness).toBe('UNKNOWN');e.rows[0].episode.freshness='KNOWN';expect(()=>read(e)).toThrow()})
