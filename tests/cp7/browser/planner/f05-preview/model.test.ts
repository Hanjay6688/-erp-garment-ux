import { describe, expect, it } from 'vitest'
import { createAnalysisReadPort, projectShell } from '../../../../../src/cp7/workspace'
import { archiveReport, changeAttention, enqueueSimulation, periodAvailability, promptForQuestion, type Episode, type Period } from './model'

const period: Period = { kind: 'daily', start: '2026-09-30', end: '2026-09-30' }
const episode: Episode = { id: 'review', title: 'Periksa kandidat', source: 'fixture', condition: 'REVIEW_REQUIRED', attention: 'NEW' }
async function context() { return { view: projectShell(await createAnalysisReadPort('DEMO_SIMULATION').read('FRAMEWORK'), 'OWNER'), stale: false } }
describe('F05 shell invariants', () => {
  it('keeps a dated snapshot distinct from unavailable periods', () => {
    expect(periodAvailability(period)).toBeNull()
    expect(periodAvailability({ ...period, kind: 'weekly' })).toContain('belum tersedia')
    expect(periodAvailability({ ...period, end: '2026-10-10' })).toContain('belum tersedia')
    expect(periodAvailability({ ...period, start: '2026-10-10' })).toContain('tidak melewati')
  })
  it('freezes archive content and creates explicitly linked revisions', async () => {
    const ctx = await context(); const first = archiveReport(ctx, period, [], null)
    const second = archiveReport(ctx, period, [first], first.id)
    expect(second.revisionOf).toBe(first.id); expect(second.id).not.toBe(first.id)
    expect(Object.isFrozen(first)).toBe(true); expect(Object.isFrozen(first.period)).toBe(true)
    expect(first.text).toBe(ctx.view.report)
    expect(() => archiveReport({ ...ctx, stale: true }, period, [first], first.id)).toThrow('belum siap')
    expect(() => archiveReport(ctx, period, [first], 'missing')).toThrow('tidak ditemukan')
  })
  it.each(['ACK', 'SNOOZED', 'DONE', 'CANCELLED'] as const)('does not resolve source conditions through %s', attention => {
    expect(changeAttention(episode, attention)).toEqual({ ...episode, attention })
    expect(changeAttention({ ...episode, condition: 'UNKNOWN' }, attention).condition).toBe('UNKNOWN')
    expect(episode.attention).toBe('NEW')
  })
  it('deduplicates local queue records without claiming transport success', async () => {
    const ctx = await context(); const queue = enqueueSimulation(ctx, episode, [])
    expect(enqueueSimulation(ctx, episode, queue)).toBe(queue)
    expect(queue[0].status).toBe('LOCAL_SIMULATION_ONLY'); expect(queue[0].text).toContain(ctx.view.report)
    expect(() => enqueueSimulation({ ...ctx, stale: true }, episode, queue)).toThrow('belum siap')
    expect(queue[0].text).toContain('tidak dikirim')
  })
  it('uses the authorized projection for reports, queue, and prompt', async () => {
    const state = await createAnalysisReadPort('DEMO_SIMULATION').read('FRAMEWORK')
    const operations = projectShell(state, 'OPERATIONS'); const denied = projectShell(state, 'DENIED')
    expect(operations.analysis!.metrics).toEqual([])
    expect(promptForQuestion(operations, 'Kenapa?').text).not.toContain('GROSS_MARGIN')
    expect(promptForQuestion(denied, 'Kenapa?')).toMatchObject({ text: '', blocked: true })
    expect(enqueueSimulation({ view: operations, stale: false }, episode, [])[0].text).not.toContain('GROSS_MARGIN')
  })
  it('does not trim capacity caveats or shared source edges to fit a prompt', async () => {
    const ctx = await context(); const payload = promptForQuestion(ctx.view, 'Kenapa?')
    expect(payload.blocked).toBe(false); expect(payload.text).toContain('Sumber bersama tidak boleh dipakai berulang')
    expect(payload.text).toContain('fixture-batch-candidate:size30'); expect(payload.text).toContain('asumsi')
    const huge = promptForQuestion(ctx.view, 'x'.repeat(64001))
    expect(huge.blocked).toBe(true); expect(huge.text.length).toBeGreaterThan(64001)
  })
})
