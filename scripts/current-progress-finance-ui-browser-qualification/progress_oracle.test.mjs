import test from 'node:test'
import assert from 'node:assert/strict'
import {expectedProgress} from './progress_oracle.mjs'

// These controlled responses exercise the test oracle, not product runtime.
const pending=()=>({contract_version:'cp7.frozen-analysis-progress.v1',policy_id:'D17-18-20261026',production_go:false,
  observed_at:'2026-10-26T00:01:00.000001+00:00',
  operational:{created_at:'2026-10-26T00:00:00.000002+00:00',finished_at:'2026-10-26T00:00:30+00:00'},
  finance:{capture_id:'capture-1',finished_at:null},
  status:{request_id:'request-1',state:'DONE',units_done:3600,unit_count:3600,plan_final:true,
    finance_capture:{state:'RUNNING',capture:{capture_id:'capture-1',units_done:0,units_total:null},result:null}}})
test('unknown financial denominator produces no financial bar; fractional timestamps preserve 59 seconds',()=>{
  const r=expectedProgress(pending(),'request-1','RUNNING')
  assert.equal(r.bars.length,1);assert.equal(r.bars[0].done,3600)
  assert.ok(r.texts.includes('0 langkah selesai; jumlah akhir belum diketahui.'))
  assert.ok(r.texts.includes('Waktu berjalan yang tercatat: 59 detik.'))
})
test('a finished production response cannot certify a complete financial report',()=>{
  assert.throws(()=>expectedProgress(pending(),'request-1','COMPLETED'))
})
test('an unrelated request or mismatched financial capture fails closed',()=>{
  assert.throws(()=>expectedProgress(pending(),'other','RUNNING'))
  const w=pending();w.finance.capture_id='other'
  assert.throws(()=>expectedProgress(w,'request-1','RUNNING'))
})
test('revoked financial access requires removal of capture, result, metadata and duration',()=>{
  const w=pending();w.status.finance_capture={state:'ACCESS_REVOKED',capture:null,result:null}
  assert.throws(()=>expectedProgress(w,'request-1','ACCESS_REVOKED'))
  w.finance=null
  const r=expectedProgress(w,'request-1','ACCESS_REVOKED')
  assert.equal(r.bars.length,1);assert.ok(r.texts.every(t=>!t.startsWith('Waktu ')))
})
test('BLOCKED finished financial work remains separate from complete analysis',()=>{
  const w=pending();w.status.finance_capture={state:'READY',capture:{capture_id:'capture-1',units_done:2,units_total:2},result:{readiness:'BLOCKED'}}
  w.finance.finished_at='2026-10-26T00:00:50.000002+00:00'
  const r=expectedProgress(w,'request-1','BLOCKED')
  assert.equal(r.bars.length,2)
  assert.ok(r.texts.includes('Waktu pemrosesan: 50 detik.'))
  assert.throws(()=>expectedProgress(w,'request-1','COMPLETED'))
})
