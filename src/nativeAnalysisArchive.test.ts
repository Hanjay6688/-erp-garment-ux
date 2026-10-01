import {describe,it,expect} from 'vitest'
import fixture from '../tests/fixtures/nativeAnalysisStandin.json'
import {parseNativeArchivePage} from './nativeAnalysisArchive'
const actor=fixture.analysis.scope.actor_scope_id
const pointer=(id=fixture.run_id,at=fixture.analysis.snapshot.generated_at)=>({runId:id,requestId:fixture.request_id,query:structuredClone(fixture.query),capturedAt:at,sourceHash:fixture.analysis.snapshot.source_hash,semanticHash:fixture.analysis.semantic_hash})
const page=(rows=[pointer()])=>({contract_version:'cp7.native-analysis-archives.v1',actor_scope_id:actor,rows,total_visible:String(rows.length),next_before_run:null as string|null,page_complete:true,read_at:'2026-10-01T07:01:02+07:00'})
describe('current actor-owned Native archive index',()=>{
 it('retains exact original pointers and decimal totals, with no report body',()=>{
  const v=page();v.total_visible='9007199254740993'
  const parsed=parseNativeArchivePage(v,actor,25)
  expect(parsed.totalVisible).toBe('9007199254740993');expect(parsed.rows).toEqual(v.rows)
  v.rows[0].query.group_mode='RESTATED';expect(parsed.rows[0].query.group_mode).toBe('AS_SOLD')
  expect(Object.keys(parsed.rows[0]).sort()).toEqual(['capturedAt','query','requestId','runId','semanticHash','sourceHash'])
 })
 it('orders PostgreSQL microseconds before UUID, then enforces UUID order for equal instants',()=>{
  const newer=pointer('00000000-0000-4000-8000-000000000001','2026-10-01T00:00:00.000002Z'),older=pointer('ffffffff-ffff-4fff-8fff-ffffffffffff','2026-10-01T00:00:00.000001Z')
  expect(parseNativeArchivePage(page([newer,older]),actor,2).rows).toEqual([newer,older])
  expect(()=>parseNativeArchivePage(page([older,newer]),actor,2)).toThrow()
  older.capturedAt=newer.capturedAt;expect(()=>parseNativeArchivePage(page([newer,older]),actor,2)).toThrow()
  expect(parseNativeArchivePage(page([older,newer]),actor,2).rows).toEqual([older,newer])
 })
 it('rejects foreign actors, extra cached facts and incomplete or oversized pages',()=>{
  for(const v of[{...page(),actor_scope_id:'00000000-0000-4000-8000-000000000001'},{...page(),financial_source:{}},{...page(),page_complete:false},page([pointer(),pointer('00000000-0000-4000-8000-000000000001')])])expect(()=>parseNativeArchivePage(v,actor,1)).toThrow()
  const v=page();Object.assign(v.rows[0],{report:{cash:'123'}});expect(()=>parseNativeArchivePage(v,actor,25)).toThrow()
 })
 it('requires a full page and its last original UUID for the next cursor',()=>{
  const v=page();v.total_visible='2';v.next_before_run=fixture.run_id
  expect(parseNativeArchivePage(v,actor,1).nextBeforeRun).toBe(fixture.run_id)
  expect(()=>parseNativeArchivePage(v,actor,2)).toThrow()
  v.next_before_run='00000000-0000-4000-8000-000000000001';expect(()=>parseNativeArchivePage(v,actor,1)).toThrow()
  v.next_before_run=fixture.run_id;v.total_visible='1';expect(()=>parseNativeArchivePage(v,actor,1)).toThrow()
  for(const total of['1e2','1.0','9223372036854775808','-1'])expect(()=>parseNativeArchivePage({...page(),total_visible:total},actor,25)).toThrow()
 })
 it('rejects normalized impossible dates, clock rollover, duplicate pointers and non-UTC capture clocks',()=>{
  for(const at of['2026-02-30T01:00:00Z','2026-10-01T24:00:00Z','2026-10-01T12:60:00Z','2026-10-01T00:00:00+00:00','2026-10-01T00:00:00.1234567Z'])expect(()=>parseNativeArchivePage(page([pointer(fixture.run_id,at)]),actor,25)).toThrow()
  expect(()=>parseNativeArchivePage({...page(),read_at:'2026-02-30T01:00:00Z'},actor,25)).toThrow()
  expect(()=>parseNativeArchivePage(page([pointer(),pointer()]),actor,25)).toThrow()
 })
})
