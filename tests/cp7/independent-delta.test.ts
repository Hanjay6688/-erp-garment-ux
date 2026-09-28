import { describe, it, expect } from 'vitest'
import { frameworkExample } from '../../src/cp7/fixture'
import { assertFixtureCoherence, createAnalysisReadPort, projectShell } from '../../src/cp7/workspace'
import { previewWhatsApp } from '../../src/cp7/notification'
import { previewAutomation } from '../../docs/cp7/prototypes/automation'
import type { AnalysisResult } from '../../src/cp7/contract'

const fixture = (): AnalysisResult => structuredClone(frameworkExample)
const context = { allocationScopeId: 'warehouse-a', policyVersion: 'vendor-v2', activeModelVersion: 'baseline-v1', trainingEvidence: 'UNKNOWN' as const }

describe('Independent CP6 policy to CP7 contract deltas; synthetic only', () => {
  it('retains physical target identity when commercial group changes', () => {
    const old = fixture(), next = fixture()
    if (next.recommendations[0].target.kind !== 'PRODUCT') throw Error('fixture requires physical target')
    next.recommendations[0].target.commercial_identity.sku_id = 'new-commercial-group'
    next.recommendations[0].target.commercial_identity.membership_version_id = 'member-v2'
    const a=projectShell({kind:'READY',analysis:old,message:'old'},'OWNER')
    const b=projectShell({kind:'READY',analysis:next,message:'new'},'OWNER')
    expect(b.rows[0].target.key).toBe(a.rows[0].target.key)
    expect(b.rows[0].target.size_id).toBe(a.rows[0].target.size_id)
    expect(b.rows[0].actual_fg).toEqual(a.rows[0].actual_fg)
    expect(b.analysis!.allocation_edges).toEqual(a.analysis!.allocation_edges)
    expect(a.rows[0].target).not.toEqual(b.rows[0].target)
    expect(old).toEqual(frameworkExample)
  })
  it('export never converts pending cost to free when a current snapshot has physical stock', () => {
    const f=fixture()
    f.metrics[0].value={state:'UNKNOWN',unit:'IDR',reason:'WAITING_FOR_KONTRA_BON',refs:[]}
    const v=projectShell({kind:'READY',analysis:f,message:'example'},'OWNER')
    for(const output of [v.report,v.prompt,previewWhatsApp(v)]) {
      expect(output).toContain('GROSS_MARGIN: Belum diketahui')
      expect(output).not.toContain('GROSS_MARGIN: Rp0')
      expect(output).toContain('Utang/piutang dan jatuh tempo belum dibaca')
    }
  })
  it('access denied clears all downstream consumers after a previous owner projection', () => {
    const f=fixture(), state={kind:'READY' as const,analysis:f,message:'example'}
    const a=projectShell(state,'OWNER'), b=projectShell(state,'DENIED')
    expect(a.prompt.length).toBeGreaterThan(0)
    expect(b.analysis).toBeNull()
    expect(b.rows).toEqual([]); expect(b.actions).toEqual([])
    expect(b.report).toBe('');expect(b.prompt).toBe('');expect(previewWhatsApp(b)).toBe('')
  })
  it('financial plan comparisons do not survive an operations projection', () => {
    const f=fixture()
    const value={state:'KNOWN' as const,unit:'IDR',value:'987654321.09',refs:[{kind:'COST',id:'confidential-plan',revision:'1'}]}
    f.plan_comparisons=[{plan_id:'owner-plan',plan_version:1,metric_id:'COST',planned:value,actual:value,knowledge_mode:'RESTATED',interpretation:'Actual contra bon cost'}]
    assertFixtureCoherence(f)
    const v=projectShell({kind:'READY',analysis:f,message:'example'},'OPERATIONS')
    expect(JSON.stringify(v)).not.toContain('987654321.09')
  })
  it('a source correction and policy correction request fresh analysis without training', () => {
    const signal={kind:'SOURCE_CHANGE' as const,committed:true,source:{kind:'SUPPLIER_CREDIT',id:'return-1',revision:'1'}}
    const original=previewAutomation(signal,context)
    const corrected=previewAutomation({...signal,source:{...signal.source,revision:'2'}},context)
    const newPolicy=previewAutomation(signal,{...context,policyVersion:'vendor-v3'})
    expect(new Set([original.proposedRequestKey,corrected.proposedRequestKey,newPolicy.proposedRequestKey]).size).toBe(3)
    for(const p of [original,corrected,newPolicy]) {
      expect(p.operational).toBe(false)
      expect(p.proposedWork).not.toContain('EVALUATE_MODEL_CANDIDATE')
      expect(p.proposedWork).toEqual(['CAPTURE_COHERENT_SNAPSHOT','COMPUTE_SHARED_ANALYSIS','OBSERVE_CONDITIONS'])
    }
  })
  it('malformed physical allocation is refused before any formatted recommendation', () => {
    const f=fixture()
    f.allocation_edges[0].projected_output_qty={state:'KNOWN',unit:'PCS',value:'999',refs:[{kind:'TEST',id:'over-project',revision:'1'}]}
    expect(()=>assertFixtureCoherence(f)).toThrow()
  })
  it('each consumer can be cleared after a successful read without reusing the last example', async () => {
    const port=createAnalysisReadPort('DEMO_SIMULATION')
    await port.read('FRAMEWORK')
    for(const state of ['EMPTY','PARTIAL','ERROR'] as const) {
      const v=projectShell(await port.read(state),'OWNER')
      expect(v.analysis).toBeNull();expect(v.actions).toEqual([])
      expect(v.report).toBe('');expect(v.prompt).toBe('')
    }
  })
})
