// @vitest-environment jsdom
import{describe,expect,it,beforeEach}from'vitest'
import{parseYieldPolicyWorkspace,yieldPolicyPayload,checkYieldPolicyOutcome,parseHistoryYield,historyYieldText,wilsonPermilleHolds,readYieldPolicyRequest,persistYieldPolicyRequest,clearYieldPolicyRequest,yieldPolicyRequestKey}from'./nativeHistoryYieldPolicy'
import{policyRow,policyWorkspace,historyAvailable,historyInsufficient,historyPending,yieldTarget}from'../tests/fixtures/nativeHistoryYield'

beforeEach(()=>localStorage.clear())
describe('history yield policy',()=>{
 it('reads the pending workspace with the owner-approved package and the versioned rows',()=>{
  const w=parseYieldPolicyWorkspace(policyWorkspace());expect(w.state).toBe('PENDING_POLICY_VALUE');expect(w.decided).toEqual({windowDays:'180',minGroups:'5',minCutPcs:'200'});expect(w.current).toBeNull()
  const saved=parseYieldPolicyWorkspace(policyWorkspace([policyRow('2','PAUSED'),policyRow('1','ACTIVE')]));expect(saved.state).toBe('PAUSED');expect(saved.current?.revision).toBe('2')
 })
 it('refuses a changed package, a changed confidence, out-of-order revisions or a mismatched state',()=>{
  const bad=[{...policyWorkspace(),decided_package:{...policyWorkspace().decided_package,window_days:'90'}},policyWorkspace([{...policyRow('1','ACTIVE'),confidence:'0.95'}]),
   policyWorkspace([policyRow('1','ACTIVE'),policyRow('2','ACTIVE')]),{...policyWorkspace([policyRow('1','ACTIVE')]),state:'PAUSED'},{...policyWorkspace(),extra:true}]
  for(const raw of bad)expect(()=>parseYieldPolicyWorkspace(raw)).toThrow()
 })
 it('builds the payload on the latest revision with whole numbers only and the fixed confidence',()=>{
  const w=parseYieldPolicyWorkspace(policyWorkspace([policyRow('1','ACTIVE')]))
  expect(yieldPolicyPayload(w,'PAUSED',{windowDays:' 90 ',minGroups:'5',minCutPcs:'200'},' alasan ')).toEqual({expected_revision:'1',state:'PAUSED',window_days:'90',min_groups:'5',min_cut_pcs:'200',confidence:'0.90',reason:'alasan'})
  for(const v of[{windowDays:'0',minGroups:'5',minCutPcs:'200'},{windowDays:'3661',minGroups:'5',minCutPcs:'200'},{windowDays:'1.5',minGroups:'5',minCutPcs:'200'},{windowDays:'180',minGroups:'1001',minCutPcs:'200'}])expect(()=>yieldPolicyPayload(w,'ACTIVE',v,'x')).toThrow()
  expect(()=>yieldPolicyPayload(w,'ACTIVE',{windowDays:'180',minGroups:'5',minCutPcs:'200'},'  ')).toThrow()
 })
 it('checks the outcome against the request and keeps the request through a lost reply',()=>{
  const w=parseYieldPolicyWorkspace(policyWorkspace()),payload=yieldPolicyPayload(w,'ACTIVE',w.decided,'Keputusan owner'),request={id:'11111111-1111-4111-8111-111111111111',payload}
  persistYieldPolicyRequest('s',request);expect(readYieldPolicyRequest('s').pending).toEqual(request);expect(()=>persistYieldPolicyRequest('s',request)).toThrow()
  const ok={contract_version:'cp7.history-yield-policy-outcome.v1',request_id:request.id,policy:{...policyRow('1','ACTIVE'),reason:'Keputusan owner'}}
  expect(checkYieldPolicyOutcome(ok,request).revision).toBe('1');expect(()=>checkYieldPolicyOutcome({...ok,policy:{...ok.policy,revision:'2'}},request)).toThrow()
  clearYieldPolicyRequest('s',request.id);expect(readYieldPolicyRequest('s').pending).toBeNull()
  localStorage.setItem(yieldPolicyRequestKey('s'),'broken');expect(readYieldPolicyRequest('s').error).toContain('belum bisa dibaca')
 })
})
describe('history yield of a plan',()=>{
 it('checks the Wilson bound exactly: 180/200 is 86.9%, all good never 100%',()=>{
  expect(wilsonPermilleHolds('180','200','869')).toBe(true);expect(wilsonPermilleHolds('180','200','870')).toBe(false);expect(wilsonPermilleHolds('180','200','868')).toBe(false)
  expect(wilsonPermilleHolds('185','200','897')).toBe(true);expect(wilsonPermilleHolds('200','200','991')).toBe(true);expect(wilsonPermilleHolds('200','200','1000')).toBe(false)
 })
 it('accepts the pending answer byte for byte and an available bound only when it holds',()=>{
  expect(parseHistoryYield(historyPending(),yieldTarget).status).toBe('PENDING_POLICY_VALUE')
  expect(()=>parseHistoryYield({...historyPending(),numerator:'1'},yieldTarget)).toThrow()
  const a=parseHistoryYield(historyAvailable(),yieldTarget);expect([a.level,a.groups,a.cutPcs,a.fgPcs,a.permille]).toEqual(['PRODUCT_SIZE','5','200','185','897'])
  expect(()=>parseHistoryYield({...historyAvailable(),numerator:'898',lower_bound_permille:'898'},yieldTarget)).toThrow()
  expect(()=>parseHistoryYield({...historyAvailable(),groups:'4'},yieldTarget)).toThrow()
  expect(()=>parseHistoryYield({...historyAvailable(),denominator:'100'},yieldTarget)).toThrow()
 })
 it('says what the planner sees in plain words',()=>{
  expect(historyYieldText(parseHistoryYield(historyAvailable(),yieldTarget))).toBe('batas bawah 89,7% dari 5 grup selesai (185 PCS bagus dari 200 PCS potong), tingkat produk dan ukuran ini; kebijakan versi 1')
  expect(historyYieldText(parseHistoryYield(historyPending(),yieldTarget))).toBe('kebijakan yield histori belum disimpan')
  expect(historyYieldText(parseHistoryYield(historyInsufficient(),yieldTarget))).toBe('data histori belum cukup (produk+ukuran 2 grup/80 PCS; model 2 grup/80 PCS; perlu minimal 5 grup dan 200 PCS potong)')
 })
})
