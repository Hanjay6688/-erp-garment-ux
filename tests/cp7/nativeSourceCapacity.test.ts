import {Buffer} from 'node:buffer'
import {expect,it} from 'vitest'
import original from '../fixtures/nativeAnalysisStandin.json'
import {ruleSourceFixture,ruleFixtureActor,ruleFixtureId,ruleFixtureClock} from '../fixtures/nativeRuleSource'
import {parseNativeAnalysis} from '../../src/nativeAnalysis'
import {parseRuleSource,parseRuleObservations,type RuleRequest,type NativeObligationFinancial} from '../../src/nativeRuleSource'
import type {NativeDemandQuery} from '../../src/nativeDemandHistory'

// Adversarial receiver fixtures, not Native Auth or factory-volume credit.
// Node's byte oracle is independent of the browser receiver's encoder.
const q=original.query as NativeDemandQuery,finance={ownerReports:false,preflight:false},rights={ar:true,ap:true}
const bytes=(v:unknown)=>Buffer.byteLength(JSON.stringify(v),'utf8')
function sizedAnalysis(size:number,multibyte=true){
 const wire=structuredClone(original);wire.analysis.generation_warnings=['']
 const gap=size-bytes(wire.analysis);expect(gap).toBeGreaterThan(0)
 wire.analysis.generation_warnings[0]=multibyte?'漢'.repeat(Math.floor(gap/3))+'x'.repeat(gap%3):'x'.repeat(gap)
 expect(bytes(wire.analysis)).toBe(size)
 return wire
}
const parseAnalysis=(v:unknown)=>parseNativeAnalysis(v,q,ruleFixtureActor)
const parseRules=(v:unknown)=>parseRuleSource(v,q,ruleFixtureActor,finance,rights)
const copiedDocument=(row:{financial_source:unknown})=>(row.financial_source as NativeObligationFinancial).document

it('rejects an over-8MB UTF8 analysis even when its UTF16 count fits the old cap',()=>{
 const wire=sizedAnalysis(8_000_001)
 expect(JSON.stringify(wire.analysis).length).toBeLessThan(8_000_000)
 expect(()=>parseAnalysis(wire)).toThrow()
})
it.each([false,true])('preserves a complete analysis at exactly 8MB; multibyte=%s',multibyte=>{
 const wire=sizedAnalysis(8_000_000,multibyte),parsed=parseAnalysis(wire)
 expect(parsed.analysis).toEqual(wire.analysis)
 expect(parsed.labels[0].sku).toBe(original.product_labels[0].sku)
 expect(parsed.analysis.recommendations[0].q_base).toEqual(original.analysis.recommendations[0].q_base)
})
it('rejects oversized complete condition rows without enabling a partial source',()=>{
 const wire=ruleSourceFixture();wire.rows[2].label='漢'.repeat(3_000_000)
 expect(bytes(wire.rows)).toBeGreaterThan(8_000_000)
 expect(JSON.stringify(wire.rows).length).toBeLessThan(8_000_000)
 expect(()=>parseRules(wire)).toThrow()
})
it('rejects an oversized copied Native financial document measured in UTF8 bytes',()=>{
 const wire=ruleSourceFixture(),document=copiedDocument(wire.rows[2])
 document.notes='漢'.repeat(3_000_000)
 expect(bytes(document)).toBeGreaterThan(8_000_000)
 expect(JSON.stringify(document).length).toBeLessThan(8_000_000)
 expect(()=>parseRules(wire)).toThrow()
})
it('checks historical financial-document bytes even when the current source fits its cap',()=>{
 const source=ruleSourceFixture(),condition=structuredClone(source.rows[2])
 const request:RuleRequest={id:ruleFixtureId(74),query:q,operation:'EPISODES',payload:{run_id:original.run_id,source_hash:source.source_hash}}
 source.source_hash='5'.repeat(64)
 const receipt={contract_version:'cp7.native-rule-observations.v1',actor_scope_id:ruleFixtureActor,source,
  result:{request_id:request.id,status:'COMMITTED',source_hash:request.payload.source_hash,rows:[{condition,
   episode:{id:ruleFixtureId(76),number:'1',previous_id:null,state:'ACTIVE',freshness:'KNOWN',first_observed_at:ruleFixtureClock,last_observed_at:ruleFixtureClock,resolved_at:null},transition:'OPENED'}]},
  result_freshness:'HISTORICAL_SOURCE_CHANGED',external_delivery_enabled:false,business_DML:false}
 expect(parseRuleObservations(receipt,request,ruleFixtureActor,finance,rights).freshness).toBe('HISTORICAL_SOURCE_CHANGED')
 copiedDocument(condition).notes='漢'.repeat(3_000_000)
 expect(bytes(source.rows)).toBeLessThan(8_000_000)
 expect(bytes(copiedDocument(condition))).toBeGreaterThan(8_000_000)
 expect(()=>parseRuleObservations(receipt,request,ruleFixtureActor,finance,rights)).toThrow()
})
it('retains complete under-budget Unicode conditions, financial values and rights checks',()=>{
 const wire=ruleSourceFixture();wire.rows[2].label='漢'.repeat(100_000)
 const parsed=parseRules(wire)
 expect(parsed.rows).toEqual(wire.rows)
 expect(parsed.rows[2].financial_source).toEqual(wire.rows[2].financial_source)
 expect(()=>parseRuleSource(wire,q,ruleFixtureActor,finance,{ar:false,ap:true})).toThrow()
})
