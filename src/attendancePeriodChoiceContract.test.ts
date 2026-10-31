import {describe,expect,it,vi} from 'vitest'
import {ATTENDANCE_CHOICE_ACTIONS,attendanceChoiceActions,attendanceChoiceDecimal,attendanceChoicePayload,attendanceChoiceRpc,attendanceChoiceRupiah,attendanceChoiceSavePayload,parseAttendanceChoiceOutcome,parseAttendanceChoicePreview,parseAttendanceChoiceWorkspace} from './attendancePeriodChoiceContract'
import {attendanceChoiceBasePayload as base,attendanceChoiceCurrent as current,attendanceChoiceEnvelope as envelope,attendanceChoiceHistory as history,attendanceChoiceOutcomeFixture as outcome,attendanceChoicePayloadFixture as payload,attendanceChoicePreviewFixture as preview,attendanceChoiceQuery as query,attendanceChoiceWorkspace as workspace} from '../tests/fixtures/attendancePeriodChoice'
describe('S03 closed client contract; declared UI doubles, no Native execution',()=>{
 it('keeps bigint cents and decimal/display amounts exact',()=>{
  expect(attendanceChoiceDecimal('900719925474099301')).toBe('9007199254740993.01');expect(attendanceChoiceRupiah('900719925474099301')).toBe('Rp9.007.199.254.740.993,01');expect(attendanceChoiceDecimal('9223372036854775807')).toBe('92233720368547758.07')
  for(const bad of ['01','-1','1.2','9223372036854775808',null,100])expect(()=>attendanceChoiceDecimal(bad as string)).toThrow()
 })
 it.each(ATTENDANCE_CHOICE_ACTIONS)('accepts all six explicit fields for %s and adds only review_token for save',a=>{
  const p=payload(a);expect(attendanceChoicePayload(a,p)).toEqual(p);expect(attendanceChoiceSavePayload(a,envelope(a).payload)).toEqual({...p,review_token:'b'.repeat(64)})
  const {choice:_,...missing}=p;expect(()=>attendanceChoicePayload(a,missing)).toThrow();expect(()=>attendanceChoicePayload(a,{...p,context:{}})).toThrow()
 })
 it('rejects wrong action casing, unused values and invalid or overlapping civil periods',()=>{
  expect(()=>attendanceChoicePayload('choose' as 'CHOOSE',base)).toThrow();expect(()=>attendanceChoicePayload('REVERSE',{...base,choice:'CARRY'})).toThrow();expect(()=>attendanceChoicePayload('CHOOSE',{...base,output_start:'2026-10-08'})).toThrow()
  for(const dates of [{period_start:'2026-02-30'},{period_end:'2026-09-30'},{period_end:'2027-10-03'},{period_start:'2026-10-01T00:00:00Z'},{reason:' x '}])expect(()=>attendanceChoicePayload('CHOOSE',{...base,...dates})).toThrow()
  expect(()=>attendanceChoicePayload('ALLOCATE',{...payload('ALLOCATE'),output_start:base.period_end})).toThrow()
 })
 it('distinguishes unknown source from zero and blocks retained source facts when source_problem is set',()=>{
  const unknown=workspace({amount_cents:null,source_binding:null,original_period_sewing_qty:null,source_problem:'CP7_S03_NO_ELIGIBLE_COST'});expect(parseAttendanceChoiceWorkspace(unknown,query).amount_cents).toBeNull();expect(attendanceChoiceActions(unknown)).toEqual([])
  expect(()=>parseAttendanceChoiceWorkspace({...unknown,source_problem:null},query)).toThrow();expect(attendanceChoiceActions(workspace({source_problem:'Changed'}))).toEqual([]);expect(attendanceChoiceActions(workspace({amount_cents:'0'}))).toEqual([])
 })
 it('offers only the owning lifecycle state and respects closed target/source periods',()=>{
  expect(attendanceChoiceActions(workspace())).toEqual(['CHOOSE']);expect(attendanceChoiceActions(current())).toEqual(['CORRECT','REVERSE','ALLOCATE']);expect(attendanceChoiceActions(current('EXPENSE'))).toEqual(['CORRECT','REVERSE']);expect(attendanceChoiceActions(current('CARRY',true))).toEqual(['CANCEL_ALLOCATION'])
  expect(attendanceChoiceActions({...current(),closed_through:'2026-10-07'})).toEqual(['ALLOCATE']);expect(attendanceChoiceActions({...current('CARRY',true),closed_through:'2026-10-14'})).toEqual([])
 })
 it('validates paginated immutable event-specific history and refuses injected or duplicate facts',()=>{
  const h=history(),w=workspace({history:h.slice(0,2),history_total:'3',limit:2,next_offset:2});expect(parseAttendanceChoiceWorkspace(w,{...query,limit:2}).history).toEqual(h.slice(0,2))
  for(const bad of [{history_total:'1'},{next_offset:null},{history:[h[0],h[0]]},{history:[{...h[0],private_source:{}}]},{current_allocation:current('CARRY',true).current_allocation}])expect(()=>parseAttendanceChoiceWorkspace({...w,...bad},{...query,limit:2})).toThrow()
  expect(()=>parseAttendanceChoiceWorkspace({...workspace(),amount_cents:10000},query)).toThrow();expect(()=>parseAttendanceChoiceWorkspace({...workspace(),private_context:{}},query)).toThrow()
 })
 it.each(ATTENDANCE_CHOICE_ACTIONS)('binds %s preview to exact payload/current source/decision/account/dates',a=>{
  const w=a==='CHOOSE'?workspace():current(a==='REVERSE'?'EXPENSE':'CARRY',a==='CANCEL_ALLOCATION'),p=payload(a),q=preview(w,p,a)
  expect(parseAttendanceChoicePreview(q,a,p,w)).toEqual(q)
  for(const bad of [{source_binding:'c'.repeat(64)},{amount:'100.001'},{amount_cents:'10001'},{payload:{...p,reason:'Changed reason'}},{can_apply:false},{context:{}}])expect(()=>parseAttendanceChoicePreview({...q,...bad},a,p,w)).toThrow()
 })
 it('rejects reversed microsecond audit order, old dates posing as valid timestamps and changed choice identity',()=>{
  const h=history();expect(()=>parseAttendanceChoiceWorkspace(workspace({history:[h[1],h[0]],history_total:'2'}),query)).toThrow();expect(()=>parseAttendanceChoiceWorkspace(workspace({history:[{...h[0],recorded_at:'2026-02-30T01:00:00+00:00'}],history_total:'1'}),query)).toThrow();const e=envelope(),r=outcome(e);expect(()=>parseAttendanceChoiceOutcome({...r,event_id:'00000000-0000-4000-8000-000000000099'},e)).toThrow()
 })
 it('requires the exact expense account and both date axes, preserving later lawful book dates',()=>{
  const w=workspace(),p={...base,choice:'EXPENSE' as const},q=preview(w,p,'CHOOSE');q.book_date='2026-10-30';expect(parseAttendanceChoicePreview(q,'CHOOSE',p,w).book_date).toBe('2026-10-30')
  for(const bad of [{expense_account:null},{expense_account:{...q.expense_account,extra:'private'}},{economic_date:'2026-10-06'},{book_date:'2026-10-06'}])expect(()=>parseAttendanceChoicePreview({...q,...bad},'CHOOSE',p,w)).toThrow()
 })
 it.each(ATTENDANCE_CHOICE_ACTIONS)('validates %s historical committed receipt against exact request/action/period',a=>{
  const e=envelope(a),r=outcome(e);expect(parseAttendanceChoiceOutcome(r,e)).toEqual(r)
  for(const bad of [{request_id:'00000000-0000-4000-8000-000000000099'},{period_end:'2026-10-08'},{status:'READY'},{amount_cents:10000},{dated_WIP:{all_original_debits_nonnegative_on_every_economic_and_book_cutoff:false,dated_available_WIP:[]}}])expect(()=>parseAttendanceChoiceOutcome({...r,...bad},e)).toThrow()
 })
 it('requires exact Native pool identity/status/dated proof and refuses unsafe numeric versions',()=>{
  const e=envelope('ALLOCATE'),r=outcome(e)
  for(const native of [{...r.native_result,validation:'BLOCKED'},{...r.native_result,pool_id:'00000000-0000-4000-8000-000000000099'},{...r.native_result,row_version:9007199254740992},{...r.native_result,private_context:{}}])expect(()=>parseAttendanceChoiceOutcome({...r,native_result:native},e)).toThrow()
  expect(()=>parseAttendanceChoiceOutcome({...r,dated_WIP:{...r.dated_WIP,dated_available_WIP:[{...r.dated_WIP.dated_available_WIP[0],available_cents:'-1'}]}},e)).toThrow()
 })
 it('counts reason characters like PostgreSQL rather than accepting four surrogate-pair characters as five',()=>{
  expect(()=>attendanceChoicePayload('CHOOSE',{...base,reason:'😀'.repeat(4)})).toThrow();expect(attendanceChoicePayload('CHOOSE',{...base,reason:'😀'.repeat(5)}).reason).toBe('😀'.repeat(5));expect(attendanceChoicePayload('CHOOSE',{...base,reason:'😀'.repeat(1000)}).reason).toBe('😀'.repeat(1000));expect(()=>attendanceChoicePayload('CHOOSE',{...base,reason:'😀'.repeat(1001)})).toThrow();expect(attendanceChoicePayload('CHOOSE',{...base,reason:'\tAlasan tersimpan\t'}).reason).toBe('\tAlasan tersimpan\t')
 })
 it('refuses invalid periods, invented versions, altered envelopes and request IDs before any RPC',()=>{
  const rpc=vi.fn(async(_name:string,_args:Record<string,unknown>)=>({data:null,error:null})),client=attendanceChoiceRpc({rpc}),e=envelope();expect(()=>client.workspace({...query,period_end:'2027-10-03'})).toThrow();expect(()=>client.workspace({...query,offset:100001})).toThrow();expect(()=>client.save({...e,expectedVersion:1})).toThrow();expect(()=>client.save({...e,id:'invented'})).toThrow();expect(()=>client.save({...e,payload:{...base,reason:'A changed intent',review_token:'b'.repeat(64)}})).toThrow();expect(rpc).not.toHaveBeenCalled()
 })
 it('accepts exact PostgreSQL UUID bits produced by the owning deterministic md5 derivation',()=>{
  const pg='f3b101d0-158b-cc5c-fd15-058776bab27e',e=envelope(),r=outcome(e);expect(parseAttendanceChoiceOutcome({...r,decision_id:pg,event_id:pg},e).decision_id).toBe(pg)
  const w=current(),h=w.history[0];if(h.event!=='CHOOSE')throw Error('fixture');const changed={...w,current_choice:{...w.current_choice!,decision_id:pg},history:[{...h,event_id:pg,decision_id:pg}]};expect(parseAttendanceChoiceWorkspace(changed,query).current_choice?.decision_id).toBe(pg)
  // Exact frozen backend seed, independently computed with Python hashlib.md5.
  const derived='8d8b571a-674e-87f4-3f04-a119c09eeae9';expect(parseAttendanceChoiceOutcome({...r,decision_id:derived,event_id:derived},e).event_id).toBe(derived)
  for(const bad of ['f3b101d0158bcc5cfd15058776bab27e','f3b101d0-158b-cc5c-fd15-058776bab27x','f3b101d0-158b-cc5c-fd15-058776bab27e extra'])expect(()=>parseAttendanceChoiceOutcome({...r,decision_id:bad,event_id:bad},e)).toThrow()
 })
 it('offers only reverse when source-period output arrives after a waiting or expense choice',()=>{
  for(const c of ['CARRY','EXPENSE']as const){expect(attendanceChoiceActions({...current(c),original_period_sewing_qty:'1'})).toEqual(['REVERSE']);expect(attendanceChoiceActions({...current(c),original_period_sewing_qty:'1',closed_through:query.period_end})).toEqual([])}
  expect(attendanceChoiceActions({...current('CARRY',true),original_period_sewing_qty:'1'})).toEqual(['CANCEL_ALLOCATION'])
 })
 it('uses only the three named RPCs and exact argument/payload keys',async()=>{
  const rpc=vi.fn(async(_name:string,_args:Record<string,unknown>)=>({data:null,error:null})),client=attendanceChoiceRpc({rpc});await client.workspace(query);await client.preview('CHOOSE',base);await client.save(envelope())
  expect(rpc.mock.calls.map(c=>c[0])).toEqual(['erp_cp7_get_attendance_choice_v1','erp_cp7_preview_attendance_choice_v1','erp_cp7_save_attendance_choice_v1']);expect(rpc.mock.calls[0][1]).toEqual({p_period_start:query.period_start,p_period_end:query.period_end,p_offset:0,p_limit:25});expect(rpc.mock.calls[2][1]).toEqual({p_action:'CHOOSE',p_payload:envelope().payload,p_request:envelope().id})
 })
})
