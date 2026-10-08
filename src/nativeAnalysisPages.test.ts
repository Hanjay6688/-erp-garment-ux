// @vitest-environment jsdom
import {expect,it} from 'vitest'
import {parseAnalysisPageSet,parseAnalysisHeader,parseAnalysisPage,parseStagedSourceCheck,parseStagedFreshness,parseStagedCheck,stagedRangeLabel,stagedIdentityHash,ANALYSIS_STAGED_TARGETS,ANALYSIS_PAGE_UTF8_BYTES} from './nativeAnalysisPages'
import {stagedRun,rehash,stagedFreshnessFixture,stagedCheckFixture} from '../tests/fixtures/nativeAnalysisPages'
import {sha} from '../tests/fixtures/nativeAnalysisTransport'
const other='33333333-3333-4333-8333-333333333333',none={ownerReports:false,preflight:false}
type J=Record<string,any>
const clone=<T,>(v:T):T=>structuredClone(v)
// The fixtures' own digest (WebCrypto), apart from the parser's.
const nodeSha=(text:string)=>sha(text)
// Restates a tampered page set's identity from its listed hashes, so a
// structural refusal is proven apart from the identity check.
const reidentified=async(m:J)=>({...m,identity_hash:await nodeSha(m.header.sha256+'\n'+m.pages.map((p:J)=>p.sha256).join('\n'))})

it('reads a staged run as a verified page set, header and uneven pages; ranges, counts and offsets follow the page set',async()=>{
 const s=await stagedRun({targets:23,pageSizes:[5,9,4,5],unreviewed:4})
 const m=await parseAnalysisPageSet(s.pageSet,s.runId,s.pageSet.request_id)
 expect(m.pageCount).toBe(4);expect(m.pages.map(p=>[p.targetLo,p.targetHi])).toEqual([[1,5],[6,14],[15,18],[19,23]])
 expect(m.identityHash).toBe(await nodeSha([s.headerSha,...s.pageSet.pages.map(p=>p.sha256)].join('\n')));expect(m.reference).toEqual({capturedAt:s.reference.captured_at,sourceHash:s.reference.source_hash})
 expect(m.totals).toMatchObject({targets:23,policyUnreviewed:5});expect(m.totals.recommendations.ACTIVE+m.totals.recommendations.PAUSED+m.totals.recommendations.STOPPED).toBe(18)
 const h=await parseAnalysisHeader(m,s.query,s.actor,none)
 expect(h.analysisHeader.recommendations).toEqual([]);expect(h.analysisHeader.assumptions).toHaveLength(1);expect(h.labels).toHaveLength(23);expect('semantic_hash'in h.analysisHeader).toBe(false)
 let seen=0
 for(let i=0;i<m.pageCount;i++){const p=await parseAnalysisPage(s.page(i),m,h,i);expect([p.targetLo,p.targetHi]).toEqual([m.pages[i].targetLo,m.pages[i].targetHi]);seen+=p.items.actions.length
  expect(p.items.recommendations.length+p.summary.policyUnreviewed).toBe(p.targetHi-p.targetLo+1)}
 expect(seen).toBe(23)
 // The pages, in order, are the per-target items of the whole analysis.
 const whole=(s.original.analysis as J).timeline.slice(0),pages=[] as unknown[]
 for(let i=0;i<m.pageCount;i++)pages.push(...(await parseAnalysisPage(s.page(i),m,h,i)).items.timeline)
 expect(pages).toEqual(whole)
})

it('labels the visible range against the whole run and states the identity hash as §10 defines it',async()=>{
 expect(stagedRangeLabel(501,1000,5000)).toBe('Target 501–1.000 dari 5.000');expect(stagedRangeLabel(1,500,5000)).toBe('Target 1–500 dari 5.000');expect(stagedRangeLabel(4951,5000,5000)).toBe('Target 4.951–5.000 dari 5.000')
 const h='a'.repeat(64),p=['b'.repeat(64),'c'.repeat(64)]
 expect(await stagedIdentityHash(h,p)).toBe(await nodeSha(`${h}\n${p[0]}\n${p[1]}`));expect(await stagedIdentityHash(h,[])).toBe(await nodeSha(`${h}\n`))
})

it('refuses page sets that misstate the run, identity, reference, header, ranges, counts, totals or bounds',async()=>{
 const s=await stagedRun({targets:12,pageSizes:[5,3,4],unreviewed:3}),ok=s.pageSet as J
 await expect(parseAnalysisPageSet(ok,s.runId,other)).rejects.toThrow();await expect(parseAnalysisPageSet(ok,other,null)).rejects.toThrow()
 expect((await parseAnalysisPageSet(ok,s.runId,null)).requestId).toBe(ok.request_id)
 const edit=(f:(m:J)=>void)=>{const m=clone(ok);f(m);return m}
 // Identity: a stated hash that is not the one over the listed hashes; a
 // listed page or header hash that is not the body's.
 await expect(parseAnalysisPageSet(edit(m=>{m.identity_hash='0'.repeat(64)}),s.runId,null)).rejects.toThrow('belum sesuai');await expect(parseAnalysisPageSet(edit(m=>{m.identity_hash='A'.repeat(64)}),s.runId,null)).rejects.toThrow()
 await expect(parseAnalysisPageSet(edit(m=>{m.pages[1].sha256='1'.repeat(64)}),s.runId,null)).rejects.toThrow()
 await expect(parseAnalysisPageSet(edit(m=>{m.header.sha256='2'.repeat(64)}),s.runId,null)).rejects.toThrow()
 await expect(parseAnalysisPageSet(await reidentified(edit(m=>{m.header.sha256='2'.repeat(64)})),s.runId,null)).rejects.toThrow()
 await expect(parseAnalysisPageSet(edit(m=>{m.header.body=m.header.body.replace('"TEST"','"TESX"')}),s.runId,null)).rejects.toThrow()
 await expect(parseAnalysisPageSet(edit(m=>{m.header.utf8_bytes+=1}),s.runId,null)).rejects.toThrow()
 // Structure, each also with a consistent identity over its tampered hashes.
 const bad=[
  edit(m=>{m.contract_version='cp7.native-analysis-manifest.v1'}),edit(m=>{m.apply_enabled=true}),edit(m=>{m.production_go=true}),edit(m=>{m.extra=1}),
  edit(m=>{m.document={utf8_bytes:1,characters:1,sha256:'a'.repeat(64),segment_count:1,segment_characters:2000000}}),edit(m=>{m.semantic_hash='a'.repeat(64)}),edit(m=>{m.source_state='UNCHANGED'}),
  edit(m=>{delete m.reference}),edit(m=>{m.reference={captured_at:'kemarin',source_hash:m.reference.source_hash}}),edit(m=>{m.reference.source_hash='zz'}),edit(m=>{m.reference.extra=1}),
  edit(m=>{m.pages[1].target_lo=7}),edit(m=>{m.pages[1].target_lo=5}),edit(m=>{m.pages[2].target_hi=11}),edit(m=>{m.pages[2].target_hi=13}),edit(m=>{m.pages[1].index=2}),edit(m=>{m.pages.pop();m.page_count=2}),edit(m=>{m.pages.pop()}),
  edit(m=>{m.pages[0].counts.timeline+=1}),edit(m=>{delete m.pages[0].counts.timeline}),edit(m=>{m.pages[0].utf8_bytes=ANALYSIS_PAGE_UTF8_BYTES+1}),edit(m=>{m.pages[0].sha256='x'}),
  edit(m=>{m.totals.targets=13}),edit(m=>{m.totals.recommendations.ACTIVE+=1}),edit(m=>{m.totals.policy_unreviewed+=1}),edit(m=>{m.totals.items.actions+=1}),
  edit(m=>{m.paged.timeline.items+=1}),edit(m=>{m.paged.unknown_field={prefix:0,items:1}}),edit(m=>{m.targets_total=13}),edit(m=>{m.page_count=2}),
  edit(m=>{m.targets_total=ANALYSIS_STAGED_TARGETS+1}),edit(m=>{m.header.utf8_bytes=8000001}),edit(m=>{m.access_epoch='a'})]
 for(const m of bad){await expect(parseAnalysisPageSet(m,s.runId,ok.request_id)).rejects.toThrow();await expect(parseAnalysisPageSet(await reidentified(m),s.runId,ok.request_id)).rejects.toThrow()}
})

it('refuses a tampered, foreign, financial or whole-Original header',async()=>{
 const s=await stagedRun({targets:12,pageSizes:[7,5]}),m=await parseAnalysisPageSet(s.pageSet,s.runId,null)
 const withBody=async(h:J)=>{const body=JSON.stringify(h);return{...m,header:{utf8Bytes:new TextEncoder().encode(body).byteLength,sha256:await sha(body),body}}}
 await expect(parseAnalysisHeader({...m,header:{...m.header,body:m.header.body.replace('TEST','TESX')}},s.query,s.actor,none)).rejects.toThrow('belum sesuai')
 const h=clone(s.headerDoc) as J
 for(const change of [(x:J)=>{x.run_id=other},(x:J)=>{x.request_id=other},(x:J)=>{x.contract_version='cp7.native-analysis-run.v1'},(x:J)=>{x.analysis=x.analysis_header},(x:J)=>{x.semantic_hash='b'.repeat(64)},
  (x:J)=>{x.document_sha256='c'.repeat(64)},(x:J)=>{x.analysis_header.semantic_hash='d'.repeat(64)},(x:J)=>{x.financial_source={contract_version:'cp7.native-analysis-finance.v1'}},(x:J)=>{x.paged.timeline.prefix=1},
  (x:J)=>{x.query.group_mode='RESTATED'},(x:J)=>{x.analysis_header.scope.actor_scope_id=other},(x:J)=>{x.product_labels.push({...x.product_labels[0]})},(x:J)=>{x.analysis_header.sources[0].allocated.value='999999'},
  (x:J)=>{x.targets_total=13},(x:J)=>{x.page_count=3},(x:J)=>{x.apply_enabled=true},(x:J)=>{x.production_go=true}]){
  const y=clone(h);change(y);await expect(parseAnalysisHeader(await withBody(y),s.query,s.actor,none)).rejects.toThrow()
 }
 await expect(parseAnalysisHeader(m,{...s.query,from_date:'2026-01-01'},s.actor,none)).rejects.toThrow();await expect(parseAnalysisHeader(m,s.query,other,none)).rejects.toThrow()
})

it('refuses tampered, reordered, foreign, shifted and internally inconsistent pages',async()=>{
 const s=await stagedRun({targets:12,pageSizes:[5,3,4],unreviewed:3}),m=await parseAnalysisPageSet(s.pageSet,s.runId,null),h=await parseAnalysisHeader(m,s.query,s.actor,none)
 const refuse=async(v:unknown,i=1)=>expect(parseAnalysisPage(v,m,h,i)).rejects.toThrow('belum sesuai')
 const p1=s.page(1) as J,body=JSON.parse(p1.body) as J
 // Envelope: changed body under the listed hash, another page for this index,
 // another run, another header or identity, a size or hash not listed.
 await refuse({...p1,body:p1.body.replace('SOURCE_INPUT_NOT_PROVEN','SOURCE_INPUT_NOT_PROVEX')})
 await refuse(s.page(2));await refuse(s.page(1),0);await refuse({...p1,run_id:other});await refuse({...p1,header_sha256:'d'.repeat(64)});await refuse({...p1,identity_hash:'d'.repeat(64)});await refuse({...p1,document_sha256:'d'.repeat(64)})
 await refuse({...p1,extra:1});await refuse({...p1,target_lo:7});await refuse(await rehash(p1,p1.body+' '))
 // A consistent envelope around a changed body, with the page set restated
 // over the new page hash: only the page's own content can catch it.
 const forged=async(change:(b:J)=>void)=>{const b=clone(body);change(b);const env=await rehash(p1,JSON.stringify(b)),pages=m.pages.map((p,i)=>i===1?{...p,utf8Bytes:env.utf8_bytes,sha256:env.sha256}:p),identityHash=await stagedIdentityHash(m.header.sha256,pages.map(p=>p.sha256));return parseAnalysisPage({...env,identity_hash:identityHash},{...m,pages,identityHash},h,1)}
 await expect(forged(()=>{})).resolves.toMatchObject({targetLo:6,targetHi:8})
 for(const change of [(b:J)=>{b.run_id=other},(b:J)=>{b.request_id=other},(b:J)=>{b.index=2},(b:J)=>{b.target_lo=5},(b:J)=>{b.targets_total=13},(b:J)=>{b.header_sha256='e'.repeat(64)},(b:J)=>{b.semantic_hash='e'.repeat(64)},(b:J)=>{b.document_sha256='e'.repeat(64)},
  (b:J)=>{b.counts.timeline-=1},(b:J)=>{b.offsets.timeline+=1},(b:J)=>{b.totals.timeline+=1},(b:J)=>{b.items.timeline.pop()},(b:J)=>{b.items.recommendations.pop();b.counts.recommendations-=1},
  (b:J)=>{b.summary.recommendations.ACTIVE+=1},(b:J)=>{b.summary.policy_unreviewed+=1},(b:J)=>{b.items.timeline[0].target_key=JSON.parse(s.page(0).body).items.recommendations[0].target.key},
  (b:J)=>{b.items.material_needs[0].target_key='nowhere'},(b:J)=>{b.items.metrics[0].scope_key='nowhere'},(b:J)=>{b.items.actions[0].source_keys=['nowhere']},
  (b:J)=>{b.items.recommendations[0].target_qty.assumption_ids=['missing']},(b:J)=>{b.items.recommendations[1]=b.items.recommendations[0]},(b:J)=>{b.items.timeline[0].extra=1},
  (b:J)=>{b.apply_enabled=true},(b:J)=>{b.production_go=true},(b:J)=>{b.items.analysis=[]}])
  await expect(forged(change)).rejects.toThrow()
})

it('refuses pages whose items belong to targets outside the range they claim, even when every hash and total agrees',async()=>{
 const s=await stagedRun({targets:12,perPage:5,unreviewed:3,itemRanges:[[1,5],[6,9],[10,12]]}),m=await parseAnalysisPageSet(s.pageSet,s.runId,null),h=await parseAnalysisHeader(m,s.query,s.actor,none)
 await expect(parseAnalysisPage(s.page(0),m,h,0)).resolves.toMatchObject({targetLo:1,targetHi:5})
 await expect(parseAnalysisPage(s.page(1),m,h,1)).rejects.toThrow('belum sesuai');await expect(parseAnalysisPage(s.page(2),m,h,2)).rejects.toThrow('belum sesuai')
})

it('a run without per-target items has a header and no page; its identity includes the empty page list separator; any page index is refused',async()=>{
 const s=await stagedRun({targets:0})
 const m=await parseAnalysisPageSet(s.pageSet,s.runId,null);expect(m.pages).toEqual([]);expect(m.identityHash).toBe(await nodeSha(s.headerSha+'\n'))
 await expect(parseAnalysisPageSet({...s.pageSet,identity_hash:await nodeSha(s.headerSha)},s.runId,null)).rejects.toThrow()
 await expect(parseAnalysisPage({},m,{} as never,0)).rejects.toThrow('belum sesuai')
 await expect(parseAnalysisPageSet(await reidentified({...s.pageSet,paged:{actions:{prefix:0,items:1}}}),s.runId,null)).rejects.toThrow()
})

it('reads the source check and refuses other runs, states or shapes',()=>{
 const run='f0165dc7-18c0-41f3-9ed5-ff0f28154197'
 expect(parseStagedSourceCheck({source_state:'UNCHANGED',checked_at:'2026-10-07T10:00:00.000000Z'},run)).toEqual({sourceState:'UNCHANGED',checkedAt:'2026-10-07T10:00:00.000000Z'})
 expect(parseStagedSourceCheck({contract_version:'cp7.native-analysis-staged-source.v1',run_id:run,source_state:'ARCHIVED_STALE',checked_at:'2026-10-07T10:00:00+00:00'},run).sourceState).toBe('ARCHIVED_STALE')
 for(const v of [{source_state:'LIVE',checked_at:'2026-10-07T10:00:00Z'},{source_state:'UNCHANGED'},{source_state:'UNCHANGED',checked_at:'besok'},{source_state:'UNCHANGED',checked_at:'2026-10-07T10:00:00Z',run_id:other},
  {source_state:'UNCHANGED',checked_at:'2026-10-07T10:00:00Z',extra:1},{source_state:'UNCHANGED',checked_at:'2026-10-07T10:00:00Z',contract_version:7},null,[],'UNCHANGED'])expect(()=>parseStagedSourceCheck(v,run)).toThrow()
})

it('reads snapshot freshness bound to its run: every state as the server derives it, never a sameness without a check',async()=>{
 const s=await stagedRun({targets:12,perPage:5}),m=await parseAnalysisPageSet(s.pageSet,s.runId,null),T='2026-10-07T10:30:00.000000+00:00'
 const none=parseStagedFreshness(stagedFreshnessFixture(s),m);expect(none).toMatchObject({state:'NO_RECORDED_CHANGE',changesTotal:0,lastCheck:null,sameAsOf:null,dataAsOf:s.reference.captured_at})
 const changed=parseStagedFreshness(stagedFreshnessFixture(s,{rows:{SALES:[3,1],MASTER_DATA:[2,0]}}),m)
 expect(changed.state).toBe('CHANGES_RECORDED');expect(changed.changesTotal).toBe(5);expect(changed.changes.find(c=>c.category==='SALES')).toMatchObject({rows:3,deleted:1,rowsAfterCheck:null})
 const same=parseStagedFreshness(stagedFreshnessFixture(s,{rows:{SALES:[3,0,0]},check:{source_state:'UNCHANGED',checked_at:T}}),m)
 expect(same).toMatchObject({state:'VERIFIED_SAME',sameAsOf:T,lastCheck:{sourceState:'UNCHANGED',checkedAt:T,changesAfterCheck:0}})
 const after=parseStagedFreshness(stagedFreshnessFixture(s,{rows:{SALES:[3,0,1]},check:{source_state:'UNCHANGED',checked_at:T}}),m)
 expect(after).toMatchObject({state:'CHANGES_RECORDED',sameAsOf:null,lastCheck:{changesAfterCheck:1}})
 expect(parseStagedFreshness(stagedFreshnessFixture(s,{check:{source_state:'ARCHIVED_STALE',checked_at:T}}),m).state).toBe('STALE_VERIFIED')
 const ok=stagedFreshnessFixture(s,{rows:{SALES:[3,1,1]},check:{source_state:'UNCHANGED',checked_at:T}})
 const bad:Record<string,unknown>[]=[{...ok,run_id:other},{...ok,identity_hash:'b'.repeat(64)},{...ok,data_as_of:'2026-10-07T09:00:01.000000Z'},{...ok,freshness_state:'VERIFIED_SAME'},
  {...ok,same_as_of:T},{...ok,changes_total:4},{...ok,apply_enabled:true},{...ok,production_go:true},{...ok,extra:1},{...ok,contract_version:'cp7.native-analysis-snapshot-freshness.v2'},
  {...ok,changes_since:ok.changes_since.slice(1)},{...ok,changes_since:[...ok.changes_since].reverse()},{...ok,capture_boundary:'CLOCK'},
  {...ok,changes_since:ok.changes_since.map(c=>c.category==='SALES'?{...c,deleted:4}:c)},{...ok,changes_since:ok.changes_since.map(c=>c.category==='SALES'?{...c,rows_after_check:null}:c)},
  {...ok,changes_since:ok.changes_since.map(c=>c.category==='FG_STOCK'?{...c,last_recorded_at:T}:c)},{...ok,last_full_check:{...ok.last_full_check!,changes_after_check:0}},
  {...stagedFreshnessFixture(s),freshness_state:'VERIFIED_SAME'},{...stagedFreshnessFixture(s,{check:{source_state:'UNCHANGED',checked_at:T}}),same_as_of:null}]
 for(const v of bad)expect(()=>parseStagedFreshness(v,m),JSON.stringify(v).slice(0,200)).toThrow('belum sesuai')
})

it('reads one recorded check and refuses another run, contract or shape',()=>{
 const run='f0165dc7-18c0-41f3-9ed5-ff0f28154197',T='2026-10-07T10:30:00.000000+00:00',ok=stagedCheckFixture(run,{source_state:'UNCHANGED',checked_at:T})
 expect(parseStagedCheck(ok,run)).toEqual({sourceState:'UNCHANGED',checkedAt:T,boundary:'SNAPSHOT'})
 for(const v of [{...ok,run_id:other},{...ok,contract_version:'cp7.native-analysis-staged-source.v1'},{...ok,source_state:'LIVE'},{...ok,boundary:'NONE'},{...ok,extra:1},{...ok,checked_at:'besok'}])expect(()=>parseStagedCheck(v,run)).toThrow()
})
