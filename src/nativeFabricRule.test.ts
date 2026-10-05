// @vitest-environment jsdom
import {it,expect} from 'vitest'
import original from '../tests/fixtures/nativeAnalysisStandin.json'
import {ruleSourceFixture,ruleFixtureActor} from '../tests/fixtures/nativeRuleSource'
import {fabricAnalysisFixture,fabricRecipeId,fabricMaterialId} from '../tests/fixtures/nativeFabricRecipe'
import {parseRuleSource} from './nativeRuleSource'
import {reminderRuleIds,reminderRuleLabels} from './nativeReminderPolicy'
import type {NativeDemandQuery} from './nativeDemandHistory'
// Receiver stand-ins only: the fabric numbers are the P08 fixture choice, not
// an owner policy or Native evidence.
const q=original.query as NativeDemandQuery,finance={ownerReports:false,preflight:false},rights={ar:true,ap:true}
function fabricSource(external:'176'|'0'|null){
 const base=ruleSourceFixture(),analysis=fabricAnalysisFixture(),m=analysis.analysis.material_needs.at(-1)!,refs=m.gross.refs,ids=[fabricRecipeId]
 if(external!==null){
  m.installed_proven={state:'ASSUMED',value:'0',unit:'M',refs,assumption_ids:ids}
  m.unused_allocated_proven={state:'ASSUMED',value:'10',unit:'M',refs:[...refs,{kind:'CP7_FABRIC_FREE_STOCK',id:fabricMaterialId,revision:'e'.repeat(64)}],assumption_ids:ids}
  m.additional_external={state:'ASSUMED',value:external,unit:'M',refs,assumption_ids:ids}
 }
 const state=external===null?'DATA_REVIEW':external==='0'?'NO_CURRENT_GAP':'ACTIVE'
 const fabric={...base.rows[1],domain:'FABRIC',key:`FABRIC_NEED:${m.target_key}:${m.material_key}`,rule_id:'FABRIC_NEED',material_key:m.material_key,state,
  reason:external===null?'SOURCE_INPUT_NOT_PROVEN':external==='0'?'SELECTED_FABRIC_RECIPE_SCENARIO_NOT_PHYSICAL_RESOLUTION':'SOURCE_BOUND_ADDITIONAL_EXTERNAL_FABRIC_NEED',
  value:structuredClone(m.additional_external),scope:'CURRENT_NATIVE_FABRIC_RECIPE_AND_PHYSICAL_ALLOCATION',
  policy_binding:{rule_id:'FABRIC_NEED',target_key:m.target_key,basis:'MISSING',policy:null},
  eligibility:state==='DATA_REVIEW'?'SOURCE_REVIEW_REQUIRED':state==='ACTIVE'?'UNCONFIGURED':'NO_CURRENT_ALERT'}
 return{...base,analysis,rows:[...base.rows,fabric],total:String(base.rows.length+1)}
}
it('lists the fabric rule as a target rule with its own label',()=>{
 expect(reminderRuleIds).toContain('FABRIC_NEED');expect(reminderRuleLabels.FABRIC_NEED).toBe('Kebutuhan kain')
})
it('copies an ASSUMED external fabric need exactly: positive is ACTIVE, assumed zero is never business resolution',()=>{
 const active=parseRuleSource(fabricSource('176'),q,ruleFixtureActor,finance,rights).rows.find(r=>r.rule_id==='FABRIC_NEED')!
 expect(active).toMatchObject({domain:'FABRIC',state:'ACTIVE',business_resolved:false,material_key:'FABRIC_MATERIAL:'+fabricMaterialId,eligibility:'UNCONFIGURED'})
 expect('value'in active.value?active.value.value:null).toBe('176')
 const zero=parseRuleSource(fabricSource('0'),q,ruleFixtureActor,finance,rights).rows.find(r=>r.rule_id==='FABRIC_NEED')!
 expect(zero).toMatchObject({state:'NO_CURRENT_GAP',business_resolved:false,eligibility:'NO_CURRENT_ALERT'})
})
it('keeps an unknown fabric physical fact as DATA_REVIEW with the shared fact reason, not zero',()=>{
 const row=parseRuleSource(fabricSource(null),q,ruleFixtureActor,finance,rights).rows.find(r=>r.rule_id==='FABRIC_NEED')!
 expect(row).toMatchObject({state:'DATA_REVIEW',reason:'SOURCE_INPUT_NOT_PROVEN',eligibility:'SOURCE_REVIEW_REQUIRED'});expect('value'in row.value).toBe(false)
})
it('refuses an edited value, a different reason, a resolved assumed zero, a wrong key or domain and a missing or extra fabric row',()=>{
 type Wire=ReturnType<typeof fabricSource>
 const last=(v:Wire)=>v.rows.at(-1) as Record<string,unknown>
 for(const[external,change]of[
  ['176',(v:Wire)=>{(last(v).value as Record<string,unknown>).value='170'}],
  ['176',(v:Wire)=>{last(v).reason='FABRIC_RECIPE_NOT_REVIEWED'}],
  [null,(v:Wire)=>{last(v).reason='FABRIC_PHYSICAL_NOT_PROVEN'}],
  ['0',(v:Wire)=>{Object.assign(last(v),{state:'RESOLVED',business_resolved:true,reason:'KNOWN_CURRENT_ZERO_FABRIC_NEED'})}],
  ['176',(v:Wire)=>{last(v).key='FABRIC_NEED:'+String(last(v).target_key)+':UNKNOWN_BOM'}],
  ['176',(v:Wire)=>{Object.assign(last(v),{domain:'ACCESSORY',rule_id:'ACCESSORY_NEED',scope:'CURRENT_NATIVE_ACCESSORY_BOM_INSTALLATION_AND_ALLOCATION'})}],
  ['176',(v:Wire)=>{v.rows.pop();v.total=String(v.rows.length)}],
  ['176',(v:Wire)=>{v.coverage={...v.coverage,fabric:'COMPLETE_AUTHORIZED_ORIGINAL'}}],
 ]as const){const wire=fabricSource(external);change(wire);expect(()=>parseRuleSource(wire,q,ruleFixtureActor,finance,rights)).toThrow()}
})
