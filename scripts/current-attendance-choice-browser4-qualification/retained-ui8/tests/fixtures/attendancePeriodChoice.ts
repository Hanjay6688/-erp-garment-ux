/** UI contract/DOM doubles only: zero Native, Auth or browser case credit. */
import type {ProductionEnvelope} from '../../src/productionRecovery'
import type {AttendanceChoiceAction,AttendanceChoicePayload,AttendanceChoiceWorkspace,AttendanceChoicePreview,AttendanceChoiceOutcome,AttendanceChoiceHistory} from '../../src/attendancePeriodChoiceContract'
export const attendanceChoiceIds={decision:'00000000-0000-4000-8000-000000000001',allocation:'00000000-0000-4000-8000-000000000002',pool:'00000000-0000-4000-8000-000000000003',journal:'00000000-0000-4000-8000-000000000004',actor:'00000000-0000-4000-8000-000000000005',event:'00000000-0000-4000-8000-000000000006',account:'00000000-0000-4000-8000-000000000007',line:'00000000-0000-4000-8000-000000000008',request:'00000000-0000-4000-8000-000000000009'}
const id=attendanceChoiceIds
export const attendanceChoiceQuery={period_start:'2026-10-01',period_end:'2026-10-07',offset:0,limit:25}
export const attendanceChoiceBasePayload:AttendanceChoicePayload={period_start:attendanceChoiceQuery.period_start,period_end:attendanceChoiceQuery.period_end,choice:'CARRY',output_start:null,output_end:null,reason:'Biaya periode sudah diperiksa Owner'}
export function attendanceChoiceWorkspace(extra:Partial<AttendanceChoiceWorkspace>={}):AttendanceChoiceWorkspace{return {contract_version:'cp7.attendance-period-choice-workspace.v1',...attendanceChoiceQuery,amount_cents:'10000',source_binding:'a'.repeat(64),original_period_sewing_qty:'0',source_problem:null,closed_through:null,current_choice:null,current_allocation:null,history:[],history_total:'0',next_offset:null,can_manage:true,business_DML:false,...extra}}
export function attendanceChoiceHistory():AttendanceChoiceHistory[]{return [
 {event:'CANCEL_ALLOCATION',event_id:id.event,decision_id:id.decision,allocation_id:id.allocation,pool_id:id.pool,journal_id:id.journal,reason:'Alokasi dibatalkan dengan pemeriksaan',recorded_at:'2026-10-30T02:00:00.654321+00:00',actor:id.actor},
 {event:'ALLOCATE',event_id:id.allocation,decision_id:id.decision,allocation_id:id.allocation,pool_id:id.pool,output_start:'2026-10-08',output_end:'2026-10-14',reason:'Alokasi ke hasil jahit yang diperiksa',recorded_at:'2026-10-30T02:00:00.123456+00:00',actor:id.actor},
 {event:'CHOOSE',event_id:id.decision,decision_id:id.decision,choice:'CARRY',amount_cents:'10000',journal_id:null,correction_of:null,reason:'Biaya periode sudah diperiksa Owner',recorded_at:'2026-10-29T02:00:00+00:00',actor:id.actor},
]}
export function attendanceChoiceCurrent(choice:'CARRY'|'EXPENSE'='CARRY',allocated=false):AttendanceChoiceWorkspace{
 const h=attendanceChoiceHistory()[2];if(h.event!=='CHOOSE')throw Error('fixture')
 const events:AttendanceChoiceHistory[]=[{...h,choice,journal_id:choice==='EXPENSE'?id.journal:null}]
 if(allocated)events.unshift(attendanceChoiceHistory()[1])
 return attendanceChoiceWorkspace({current_choice:{decision_id:id.decision,choice,reason:h.reason,journal_id:choice==='EXPENSE'?id.journal:null},current_allocation:allocated?{allocation_id:id.allocation,pool_id:id.pool,output_start:'2026-10-08',output_end:'2026-10-14'}:null,history:events,history_total:String(events.length)})
}
export function attendanceChoicePayloadFixture(action:AttendanceChoiceAction):AttendanceChoicePayload{return {...attendanceChoiceBasePayload,choice:action==='CHOOSE'||action==='CORRECT'?'CARRY':null,output_start:action==='ALLOCATE'?'2026-10-08':null,output_end:action==='ALLOCATE'?'2026-10-14':null}}
export function attendanceChoicePreviewFixture(w:AttendanceChoiceWorkspace,p:AttendanceChoicePayload,action:AttendanceChoiceAction):AttendanceChoicePreview{
 const expense=(action==='CHOOSE'||action==='CORRECT')&&p.choice==='EXPENSE',allocate=action==='ALLOCATE',inverse=action==='CANCEL_ALLOCATION'||(action==='REVERSE'||action==='CORRECT')&&w.current_choice?.choice==='EXPENSE'
 return {contract_version:'cp7.attendance-period-choice.v1',action,payload:structuredClone(p),amount:'100.00',amount_cents:'10000',source_count:'2',denominator_qty:allocate?'10':null,economic_date:expense?p.period_end:allocate?p.output_end:null,book_date:expense?p.period_end:allocate?p.output_end:null,inverse_economic_date:inverse?'2026-10-30':null,inverse_book_date:inverse?'2026-10-30':null,decision_id:w.current_choice?.decision_id??null,allocation_id:w.current_allocation?.allocation_id??null,pool_id:w.current_allocation?.pool_id??null,source_binding:w.source_binding!,review_token:'b'.repeat(64),expense_account:expense?{id:id.account,code:'6200',name:'Beban periode absensi'}:null,can_apply:true,business_DML:false}
}
export function attendanceChoiceEnvelope(action:AttendanceChoiceAction='CHOOSE',p=attendanceChoicePayloadFixture(action)):ProductionEnvelope{
 const payload={...p,review_token:'b'.repeat(64)};return {action,payload,expectedVersion:null,id:id.request,createdAt:'2026-10-30T03:00:00Z',fingerprint:JSON.stringify({action,payload,expectedVersion:null})}
}
export function attendanceChoiceOutcomeFixture(e:ProductionEnvelope):AttendanceChoiceOutcome{
 const p=e.payload as unknown as AttendanceChoicePayload,a=e.action as AttendanceChoiceAction,allocate=a==='ALLOCATE',cancel=a==='CANCEL_ALLOCATION'
 return {contract_version:'cp7.attendance-period-choice-command.v1',action:a,request_id:e.id,period_start:p.period_start,period_end:p.period_end,decision_id:id.decision,event_id:a==='CHOOSE'||a==='CORRECT'?id.decision:id.event,amount_cents:'10000',pool_id:allocate||cancel?id.pool:null,native_result:allocate?{pool_id:id.pool,status:'ACTIVE',row_version:1,journal_entry_id:id.journal,validation:'PASS'}:cancel?{pool_id:id.pool,status:'CANCELLED',row_version:2,reversal_journal_entry_id:id.journal,residue_expected:0}:null,inverse_journal_id:null,dated_WIP:{all_original_debits_nonnegative_on_every_economic_and_book_cutoff:true,dated_available_WIP:[{line_id:id.line,axis:'ECONOMIC',date:p.period_end,available_cents:'10000'},{line_id:id.line,axis:'BOOK',date:p.period_end,available_cents:'10000'}]},status:'COMMITTED'}
}
