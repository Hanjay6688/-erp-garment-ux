import { expect, it } from 'vitest'
import { guardYieldReview, sizeMixKey, sizeMixLabel, yieldInputKey, type YieldReview } from './cuttingYieldContract'
import { readYieldFixture, yieldFixtureInput, type YieldExample } from './cuttingYieldFixtures'

const context = { runId: 'test-run', actorScope: 'test-scope', accessEpoch: 'test-epoch' }
it('retains multiplicity rather than reducing a mix to size range 28–30', () => {
  const a = ['28', '28', '29', '29', '30', '30']; const b = ['28', '29', '29', '29', '30', '30']
  expect(sizeMixKey(a)).not.toBe(sizeMixKey(b)); expect(sizeMixKey(a)).toBe(sizeMixKey([...a].reverse()))
  expect(sizeMixLabel(b)).toBe('28×1 · 29×3 · 30×2')
})
it('allows a complete comparison without width or physical proof and declares its basis', async () => {
  const input = { ...yieldFixtureInput('small', 'NORMAL'), markerRevision: null,
    measurements: { ...yieldFixtureInput('small', 'NORMAL').measurements, evidence: 'UNVERIFIED' as const, issuedMeasuredM: null, remainingMeasuredM: null, refs: [] } }
  const result = await readYieldFixture(input, context, 'small', 'NORMAL')
  expect(result.status).toBe('READY'); if (result.status !== 'READY') return
  expect(result.interval).toMatchObject({ basis: 'WITHOUT_WIDTH', lower: '80', upper: '120' })
  expect(result.findings.join(' ')).toContain('Lebar belum tercatat')
})
it('adding width changes the supplied comparison and prevents reuse of the old result', async () => {
  const noWidth = yieldFixtureInput('small', 'NORMAL'); const known = yieldFixtureInput('small', 'NORMAL', '150')
  const original = await readYieldFixture(noWidth, context, 'small', 'NORMAL'); const next = await readYieldFixture(known, context, 'small', 'NORMAL')
  expect(() => guardYieldReview(original, known, context)).toThrow('Konteks')
  if (next.status === 'READY') expect(next.interval).toMatchObject({ basis: 'WITH_RECORDED_WIDTH', lower: '90', upper: '110' })
})
it.each(['NORMAL', 'LOW', 'HIGH', 'SHORT_ROLL', 'NARROW_BATCH'] as const)('validates the explicitly supplied %s case without inferring theft', async mode => {
  const input = yieldFixtureInput('small', mode); const review = await readYieldFixture(input, context, 'small', mode)
  expect(review.status).toBe('READY'); expect(guardYieldReview(review, input, context)).toBe(review)
})
it.each(['INSUFFICIENT', 'INCOMPLETE', 'UNSEEN_COMBINATION', 'ERROR'] as const)('does not emit ranges in %s', async mode => {
  const review = await readYieldFixture(yieldFixtureInput('small', mode), context, 'small', mode)
  expect(review.status).toBe(mode); expect('interval' in review).toBe(false)
})
it('all-30 and unsupported widths are not silently assigned a mixed-size interval', async () => {
  expect((await readYieldFixture(yieldFixtureInput('all30', 'NORMAL'), context, 'all30', 'NORMAL')).status).toBe('UNSEEN_COMBINATION')
  expect((await readYieldFixture(yieldFixtureInput('small', 'NORMAL', '147'), context, 'small', 'NORMAL')).status).toBe('UNSEEN_COMBINATION')
})
it('binds roll revision, material family, size mix, input quantity and actor scope', async () => {
  const input = yieldFixtureInput('small', 'LOW'); const review = await readYieldFixture(input, context, 'small', 'LOW')
  for (const other of [{ ...input, rollRevision: 'r2' }, { ...input, sizeSlots: ['30'] }, { ...input, consumed: { value: '90', unit: 'M' as const } }, { ...input, materialFamily: { ...input.materialFamily, millId: 'different' } }]) {
    expect(yieldInputKey(other)).not.toBe(yieldInputKey(input)); expect(() => guardYieldReview(review, other, context)).toThrow('Konteks')
  }
  expect(() => guardYieldReview(review, input, { ...context, actorScope: 'different' })).toThrow('Konteks')
})
it('rejects impossible ranges, contradictory classifications and wrong optional-width basis', async () => {
  const input = yieldFixtureInput('small', 'LOW'); const review = await readYieldFixture(input, context, 'small', 'LOW')
  if (review.status !== 'READY') throw new Error('ready expected')
  const bad: YieldReview[] = [
    { ...review, interval: { ...review.interval, lower: '999' } },
    { ...review, assessment: 'NORMAL' },
    { ...review, interval: { ...review.interval, basis: 'WITH_RECORDED_WIDTH' } },
    { ...review, peers: [review.peers[0], review.peers[0]] },
  ]
  for (const result of bad) expect(() => guardYieldReview(result, input, context)).toThrow()
})
it('records length discrepancies as measured differences and keeps cause unknown', async () => {
  const mode: YieldExample = 'SHORT_ROLL'; const review = await readYieldFixture(yieldFixtureInput('small', mode), context, 'small', mode)
  if (review.status !== 'READY') throw new Error('ready expected')
  expect(review.findings.join(' ')).toContain('100 M, tersedia fisik 80 M')
  expect(review.findings.join(' ')).toContain('Penyebab selisih panjang belum diketahui')
})
