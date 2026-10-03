// @vitest-environment node
import { readFileSync } from 'node:fs'
import { afterAll, beforeAll, expect, test } from 'vitest'
import { openRuntime, jsonArg } from './f04/runtime.mjs'

// All observations/policies here are synthetic controls of a private kernel.
// They carry zero Native, factory coverage, source-adapter or acceptance credit.
let db: Awaited<ReturnType<typeof openRuntime>>
beforeAll(async () => {
  db = await openRuntime()
  await db.execute(readFileSync('scripts/cp7-src/cutting-yield/learning-kernel.sql', 'utf8'))
}, 120000)
afterAll(async () => { if (db) await db.close() })
const sizeA = '00000000-0000-4000-8000-000000000001'
const sizeB = '00000000-0000-4000-8000-000000000002'
const context = { family: { brand: 'BRAND', mill: 'MILL', variant: 'VARIANT', spec_revision: '1' }, pattern_id: 'PATTERN', pattern_revision: '1', marker_key: 'MARKER', unit: 'YARD', planned_mix: [{ size_id: sizeA, drawings: '2' }, { size_id: sizeB, drawings: '2' }] }
const stamp = (day: number) => `2026-01-${String(day).padStart(2, '0')}T12:00:00.000001Z`
const observation = (day: number, pcs = '2000', width: string | null = null) => ({ slice_key: `slice-${day}`, batch_key: `batch-${day}`, revision_key: '1', physical_at: stamp(day), known_at: stamp(day).replace('.000001', '.000002'), input_known_at: stamp(day).replace('12:00:00.000001', '11:00:00.000001'), native_valid: true, context, consumed: '100', actual_pcs: pcs, width_cm: width })
const records = () => [observation(2), observation(3), observation(4), observation(12, '1800'), observation(13), observation(14, '2200'), observation(15), observation(22, '1900'), observation(23, '2100'), observation(24)]
const query = () => ({ context, current_batch_key: 'current-batch', policy_known_at: stamp(1), train_through: stamp(10), calibration_through: stamp(20), evaluation_through: stamp(30), input_known_at: '2026-02-01T12:00:00.000001Z', coverage: '0.8', consumed: '100', width_cm: null as string | null, actual_pcs: null as string | null, source_complete: true })
const call = async (name: string, args: string[]) => (await db.query(`select cp7_cutting_learning.${name}(${args.join(',')}) result`))[0].result
const evaluate = (r = records(), q = query()) => call('evaluate', [jsonArg(r), jsonArg(q)])
const dataset = (r: unknown[], through = stamp(10), from: string | null = null) => call('dataset', [jsonArg(r), jsonArg(context), from === null ? 'null' : `'${from}'::timestamptz`, `'${through}'::timestamptz`, "'current-batch'"])
const isDecimal = (expected: string) => new RegExp(`^${expected}(\\.0+)?$`)

test('synthetic separated physical batches calibrate the baseline and flag both tails without guessing width or cause', async () => {
  const result = await evaluate()
  expect(result.status).toBe('PREDICTION_ONLY')
  expect(result.basis).toBe('WITHOUT_WIDTH')
  expect(result.interval.lower_pcs).toMatch(isDecimal('1800'))
  expect(result.interval.center_pcs).toMatch(isDecimal('2000'))
  expect(result.interval.upper_pcs).toMatch(isDecimal('2200'))
  expect(result.model.calibration_batches).toBe('4')
  expect(result.model.train_batches).toBe('3')
  expect(result.width_score).toBeNull()
  expect(result.automatic_activation).toBe(false)
  expect(result.business_write).toBe(false)
  expect(result.production_go).toBe(false)
  expect(result.causal_claim).toBe(false)
  expect((await evaluate(records(), { ...query(), actual_pcs: '0' })).status).toBe('LOW_REVIEW_REQUIRED')
  expect((await evaluate(records(), { ...query(), actual_pcs: '2300' })).status).toBe('HIGH_REVIEW_REQUIRED')
  expect((await evaluate(records(), { ...query(), actual_pcs: '2100' })).status).toBe('WITHIN_EMPIRICAL_INTERVAL')
  const canary = (await db.query('select amount::text amount from public.f04_ledger_canary'))[0]
  expect(canary.amount).toBe('12345.67')
})

test('latest known revision wins before cancellation filtering; recaptures and future facts cannot multiply observations', async () => {
  const r = observation(2)
  expect(await dataset([r, r])).toHaveLength(1)
  const corrected = { ...r, revision_key: '2', actual_pcs: '2100', known_at: stamp(3) }
  const future = { ...r, revision_key: '3', actual_pcs: '9000', known_at: stamp(15) }
  const row = (await dataset([r, corrected, future]))[0]
  expect(row.revision_key).toBe('2')
  expect(row.rate).toMatch(isDecimal('21'))
  expect(await dataset([r, corrected, { ...corrected, revision_key: '3', native_valid: false, known_at: stamp(4) }])).toEqual([])
  expect(await dataset([{ ...r, input_known_at: r.physical_at }])).toEqual([])
  expect(await dataset([{ ...r, input_known_at: null }])).toEqual([])
  expect(await dataset([{ ...r, context: null }])).toEqual([])
  expect(await dataset([{ ...r, batch_key: 'current-batch' }])).toEqual([])
  expect((await dataset([{ ...r, actual_pcs: '0' }]))[0].rate).toMatch(isDecimal('0'))
  await expect(dataset([r, { ...r, actual_pcs: '2100' }])).rejects.toThrow('CP7_CUTTING_KNOWLEDGE_CONFLICT')
  await expect(dataset([r, { ...r, batch_key: 'other-batch', known_at: stamp(3) }])).rejects.toThrow('CP7_CUTTING_SLICE_IDENTITY_CHANGED')
  await expect(dataset([r, { ...r, slice_key: 'other-slice', physical_at: stamp(3), known_at: stamp(4) }])).rejects.toThrow('CP7_CUTTING_BATCH_SPLIT')
})

test('matching preserves family, pattern, marker, mix and exact Native units; empty/late policy/unsupported folds withhold', async () => {
  const ratio = [{ size_id: sizeB, drawings: '2' }, { size_id: sizeA, drawings: '1' }, { size_id: sizeA.toUpperCase(), drawings: '1' }]
  expect(await call('mix', [jsonArg(ratio)])).toEqual([{ size_id: sizeA, drawings: '1' }, { size_id: sizeB, drawings: '1' }])
  const r = observation(2)
  for (const changed of [{ ...context, unit: 'M' }, { ...context, marker_key: 'OTHER' }, { ...context, pattern_revision: '2' }, { ...context, family: { ...context.family, variant: 'OTHER' } }, { ...context, planned_mix: [{ size_id: sizeA, drawings: '3' }, { size_id: sizeB, drawings: '2' }] }]) {
    expect(await dataset([{ ...r, context: changed }])).toEqual([])
  }
  expect((await evaluate([])).interval).toBeNull()
  expect((await evaluate(records(), { ...query(), source_complete: false })).reason).toBe('INCOMPLETE_NATIVE_SCOPE')
  expect((await evaluate(records(), { ...query(), policy_known_at: stamp(11) })).reason).toBe('PREKNOWN_POLICY_AND_CHRONOLOGICAL_FOLDS_REQUIRED')
  expect((await evaluate(records(), { ...query(), calibration_through: stamp(10) })).interval).toBeNull()
  expect((await evaluate(records(), { ...query(), consumed: '101' })).reason).toBe('CONSUMPTION_OUTSIDE_TRAINING_SUPPORT')
  expect((await evaluate(records(), { ...query(), coverage: '0.9' })).reason).toBe('INSUFFICIENT_SEPARATE_BATCH_CALIBRATION_OR_HOLDOUT')
  const failed = records().map(r => r.physical_at > stamp(20) ? { ...r, actual_pcs: '4000' } : r)
  expect((await evaluate(failed)).reason).toBe('BASELINE_HOLDOUT_COVERAGE_FAILED')
})

test('width must beat its fixed baseline on separate batches; missing width and out-of-support inputs cannot force promotion', async () => {
  const r = [observation(2, '2000', '100'), observation(3, '3000', '150'), observation(4, '4000', '200'),
    observation(12, '2000', '100'), observation(13, '3000', '150'), observation(14, '4000', '200'), observation(15, '3000', '150'),
    observation(22, '2000', '100'), observation(23, '3000', '150'), observation(24, '4000', '200')]
  const q = { ...query(), width_cm: '175' }
  const learned = await evaluate(r, q)
  expect(learned.basis).toBe('WITH_RECORDED_WIDTH')
  expect(learned.interval.center_pcs).toMatch(isDecimal('3500'))
  expect(learned.width_score.mae).toMatch(isDecimal('0'))
  expect(learned.model.train_batches).toBe('3')
  expect((await evaluate(r, { ...q, width_cm: null })).basis).toBe('WITHOUT_WIDTH')
  expect((await evaluate(r.map(x => x.slice_key === 'slice-24' ? { ...x, width_cm: null } : x), q)).basis).toBe('WITHOUT_WIDTH')
  expect((await evaluate(r, { ...q, width_cm: '250' })).reason).toBe('WIDTH_OUTSIDE_TRAINING_SUPPORT')
  const flat = r.map(x => ({ ...x, actual_pcs: '3000' }))
  expect((await evaluate(flat, q)).basis).toBe('WITHOUT_WIDTH')
  const lateWidth = r.map(x => x.slice_key === 'slice-24' ? { ...x, width_cm: '250', actual_pcs: '3000' } : x)
  expect((await evaluate(lateWidth, q)).basis).toBe('WITHOUT_WIDTH')
})

test('subdividing one physical batch does not multiply its training weight', async () => {
  const rows = [
    { slice_key: 'a', batch_key: 'one', consumed: '100', rate: '20', width_cm: '100' },
    { slice_key: 'b', batch_key: 'two', consumed: '100', rate: '40', width_cm: '200' }]
  const split = [
    { ...rows[0], slice_key: 'a1', consumed: '25' },
    { ...rows[0], slice_key: 'a2', consumed: '75' }, rows[1]]
  for (const width of ['false', 'true']) {
    const one = await call('fit', [jsonArg(rows), width])
    const many = await call('fit', [jsonArg(split), width])
    expect(many.intercept).toBe(one.intercept)
    expect(many.slope).toBe(one.slope)
    expect(many.train_batches).toBe('2')
  }
})

test('finite decimal strings and explicit timezone clocks are mandatory; private functions cannot be executed by application roles', async () => {
  for (const value of ['NaN', 'Infinity', '-1', '1e2', '1,000', 100, '9'.repeat(201)]) {
    await expect(evaluate(records(), { ...query(), consumed: value } as ReturnType<typeof query>)).rejects.toThrow('CP7_CUTTING_DECIMAL_REQUIRED')
  }
  for (const value of ['infinity', '2026-02-01 12:00:00', null]) {
    await expect(evaluate(records(), { ...query(), input_known_at: value } as ReturnType<typeof query>)).rejects.toThrow('CP7_CUTTING_CLOCK_REQUIRED')
  }
  await expect(evaluate(records(), { ...query(), actual_pcs: '1.5' })).rejects.toThrow('CP7_CUTTING_DECIMAL_REQUIRED')
  await expect(dataset([{ ...observation(2), width_cm: 'NaN' }])).rejects.toThrow('CP7_CUTTING_DECIMAL_REQUIRED')
  const privs = await db.query(`select pg_get_userbyid(proowner) owner,prosecdef definer,provolatile volatility,
    has_function_privilege('anon',oid,'EXECUTE') anon,has_function_privilege('authenticated',oid,'EXECUTE') authenticated,
    has_function_privilege('service_role',oid,'EXECUTE') service_role from pg_proc where pronamespace='cp7_cutting_learning'::regnamespace`)
  expect(privs).toHaveLength(9)
  for (const r of privs) expect(r).toEqual({ owner: 'cp7_capture', definer: false, volatility: 'i', anon: false, authenticated: false, service_role: false })
  // Native runtime queries have separate psql sessions. Exercise the denied
  // call in the same SQL invocation as SET ROLE in both supported runtimes.
  await expect(db.execute(`set role authenticated;select cp7_cutting_learning.evaluate(${jsonArg(records())},${jsonArg(query())})`)).rejects.toThrow(/permission denied/)
  await db.execute('reset role')
})
