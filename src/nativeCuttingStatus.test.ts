// @vitest-environment jsdom
import {beforeEach,it,expect} from 'vitest'
import {cuttingCoverageFromPercent,cuttingCoveragePercent,parseAutomaticCuttingStatus,validateCuttingStatusPolicyIntent,
  validateCuttingStatusPolicyResult,holdCuttingStatusPolicy,pendingCuttingStatusPolicies,releaseCuttingStatusPolicy,
  cuttingStatusPolicyPrefix} from './nativeCuttingStatus'
import {cuttingStatusFixture,statusGroup,statusActor,statusIntent,statusPolicyReply} from '../tests/fixtures/cuttingStatus'
beforeEach(()=>localStorage.clear())
it('accepts only factory data for the exact group with internally consistent total-PCS status',()=>{
  expect(parseAutomaticCuttingStatus(cuttingStatusFixture(),statusGroup).materials[0].total_pcs).toBe('100')
  const bad=cuttingStatusFixture();bad.materials[0].status='LOW'
  expect(()=>parseAutomaticCuttingStatus(bad,statusGroup)).toThrow()
  const insufficient=cuttingStatusFixture();insufficient.materials[0].history_groups='2'
  expect(()=>parseAutomaticCuttingStatus(insufficient,statusGroup)).toThrow()
  const wrong=cuttingStatusFixture();wrong.scope='ACCOUNT'
  expect(()=>parseAutomaticCuttingStatus(wrong,statusGroup)).toThrow()
  expect(()=>parseAutomaticCuttingStatus(cuttingStatusFixture(),statusActor)).toThrow()
  expect(()=>parseAutomaticCuttingStatus({...cuttingStatusFixture(),extra:true},statusGroup)).toThrow()
})
it('preserves integer PCS beyond JavaScript safe integers and refuses a contradictory range',()=>{
  const data=cuttingStatusFixture();Object.assign(data.materials[0],{total_pcs:'9007199254740993',lower_pcs:'9007199254740992',upper_pcs:'9007199254740994'})
  expect(parseAutomaticCuttingStatus(data,statusGroup).materials[0].total_pcs).toBe('9007199254740993')
  data.materials[0].upper_pcs='9007199254740992'
  expect(()=>parseAutomaticCuttingStatus(data,statusGroup)).toThrow()
})
it('does not admit an unposted result, missing policy, guessed zero or fractional pieces as judged',()=>{
  const unposted=cuttingStatusFixture();unposted.group.posted=false
  expect(()=>parseAutomaticCuttingStatus(unposted,statusGroup)).toThrow()
  expect(()=>parseAutomaticCuttingStatus({...cuttingStatusFixture(),policy:null},statusGroup)).toThrow()
  const zero=cuttingStatusFixture();Object.assign(zero.materials[0],{total_pcs:'0',lower_pcs:'0',upper_pcs:'0',consumed:'0'})
  expect(()=>parseAutomaticCuttingStatus(zero,statusGroup)).toThrow()
  for(const total of ['NaN','1.5','-1','01']){
    const data=cuttingStatusFixture();data.materials[0].total_pcs=total
    expect(()=>parseAutomaticCuttingStatus(data,statusGroup)).toThrow()
  }
})
it('converts human percentages exactly and has no activated fallback value',()=>{
  expect(cuttingCoverageFromPercent('95')).toBe('0.95')
  expect(cuttingCoverageFromPercent('99,125')).toBe('0.99125')
  expect(cuttingCoverageFromPercent('0.0000000001')).toBe('0.000000000001')
  expect(cuttingCoveragePercent('0.99125')).toBe('99.125')
  expect(cuttingCoveragePercent('0.1')).toBe('10')
  for(const bad of ['','0','100','100.1','-5','1e1','95%'])expect(()=>cuttingCoverageFromPercent(bad)).toThrow()
})
it('accepts only the exact actor, UUID, revision and submitted policy in a committed reply',()=>{
  const intent=statusIntent(),reply=statusPolicyReply(intent)
  expect(validateCuttingStatusPolicyResult(reply,intent,statusActor)).toBe('COMMITTED')
  for(const patch of [{actor:statusGroup},{revision:'3'},{coverage:'0.9'},{min_groups:'4'}])
    expect(()=>validateCuttingStatusPolicyResult({...reply,policy:{...reply.policy,...patch}},intent,statusActor)).toThrow()
  expect(()=>validateCuttingStatusPolicyResult({...reply,request_id:statusGroup},intent,statusActor)).toThrow()
  expect(validateCuttingStatusPolicyResult({...reply,status:'NOT_COMMITTED',policy:null},intent,statusActor)).toBe('NOT_COMMITTED')
  expect(()=>validateCuttingStatusPolicyResult({...reply,status:'NOT_COMMITTED'},intent,statusActor)).toThrow()
})
it('requires explicit review and rejects policy fields, quantities or precision not admitted by the server',()=>{
  for(const patch of [{min_groups:'0'},{min_groups:'1000001'},{coverage:'0.1234567890123'},
    {expected_revision:'9223372036854775807'},{explicit_review:false},{policy_clock:'2026-01-01'}])
    expect(()=>validateCuttingStatusPolicyIntent({...statusIntent(),payload:{...statusIntent().payload,...patch}})).toThrow()
})
it('keeps simultaneous-tab intents under separate UUIDs and removes only the matched intent',()=>{
  const scope='test:'+statusActor,a=statusIntent(),b=statusIntent(statusGroup)
  holdCuttingStatusPolicy(scope,a);holdCuttingStatusPolicy(scope,b)
  expect(pendingCuttingStatusPolicies(scope)).toHaveLength(2)
  expect(()=>holdCuttingStatusPolicy(scope,{...a,payload:{...a.payload,reason:'Changed bytes'}})).toThrow()
  releaseCuttingStatusPolicy(scope,a)
  expect(pendingCuttingStatusPolicies(scope)).toEqual([b])
  expect(pendingCuttingStatusPolicies('different-project:'+statusActor)).toEqual([])
})
it('fails closed on damaged recovery data without silently discarding it',()=>{
  const scope='test:'+statusActor,key=cuttingStatusPolicyPrefix(scope)+statusGroup
  localStorage.setItem(key,'{broken')
  expect(()=>pendingCuttingStatusPolicies(scope)).toThrow();expect(localStorage.getItem(key)).toBe('{broken')
})
