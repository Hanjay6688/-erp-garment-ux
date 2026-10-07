// @vitest-environment node
import { readFileSync } from 'node:fs'
import { expect, test } from 'vitest'
import { openRuntime, jsonArg } from './f04/runtime.mjs'
import * as f from './f04/fixtures.mjs'

// Self-check PL-3. A Native history capture can contain day D only from 00:00 WIB
// on D+1 (history_query and cp7_demand.history require through_date < capture WIB
// date). A fold trained through its origin day is therefore issued on origin+1;
// its training knowledge must close at the end of that day, or no fold on Native
// data can ever complete. Later knowledge and the configuration guard are unchanged.
const nextDay = (v, hour) => ({ ...v, series: v.series.map(x => ({ ...x, known_at: f.at(Number(x.date.slice(8)) + 1, hour) })) })
const block = (text, name) => { const a = text.indexOf(`create function ${name}(`); if (a < 0) throw new Error(name); return text.slice(a, text.indexOf('$$;', a) + 3) }

test('folds complete when each closed day becomes known on the next WIB day, and nothing later leaks in', async () => {
  const db = await openRuntime()
  try {
    const evaluate = v => db.call('cp7_models.evaluate', [jsonArg(v)])
    // Every day first known 08:00 WIB the next morning (01:00Z), the Native shape.
    const r = await evaluate(nextDay(f.evaluation(), '01'))
    expect([r.selected_model_id, r.selection_status, r.baseline.summary.fold_count, r.challengers[0].summary.fold_count]).toEqual(['naive-v1', 'CHALLENGER_RECOMMENDED', '3', '3'])
    expect(r.challengers[0].folds.map(x => Number(x.prediction.forecasts[0]))).toEqual([3, 5, 7])
    expect(r.baseline.folds.map(x => x.training_known_cutoff)).toEqual(['2026-01-04T16:59:59.999999Z', '2026-01-06T16:59:59.999999Z', '2026-01-08T16:59:59.999999Z'])
    expect(r.holdout.results.map(x => x.score === null)).toEqual([false, false])
    // The earliest instant a Native capture may hold day D: 00:00:00.000000 WIB on D+1.
    const midnight = f.evaluation(); midnight.series = midnight.series.map(x => ({ ...x, known_at: `${x.date}T17:00:00.000000Z` }))
    expect((await evaluate(midnight)).baseline.summary.fold_count).toBe('3')
    // Day 1 restated: known in the last microsecond of origin+1 enters fold 3; known at 00:00 WIB of origin+2 does not.
    const edge = nextDay(f.evaluation(), '01'); edge.series.push({ ...edge.series[0], revision: '2', known_at: '2026-01-04T16:59:59.999999Z', value: '999' })
    expect((await evaluate(edge)).baseline.folds.map(x => x.training.values[0])).toEqual(['999', '999', '999'])
    const late = nextDay(f.evaluation(), '01'); late.series.push({ ...late.series[0], revision: '2', known_at: '2026-01-04T17:00:00.000000Z', value: '999' })
    expect((await evaluate(late)).baseline.folds.map(x => x.training.values[0])).toEqual(['1', '999', '999'])
    // Configuration guard is NOT moved: a model first registered on origin+1 is still refused.
    const config = nextDay(f.evaluation(), '01'); config.challengers[0].registered_at = f.at(4, '01')
    await expect(evaluate(config)).rejects.toThrow(/CONFIG_AFTER_VALIDATION/)
  } finally { await db.close() }
}, 120_000)

test('daily Native captures complete three paired folds through the real dataset/build adapter', async () => {
  const db = await openRuntime()
  try {
    const src = p => readFileSync(`scripts/cp7-src/${p}`, 'utf8')
    const config = JSON.parse(src('model-native/bootstrap.sql').match(/clock_timestamp\(\),\n '(\{.*\})'::jsonb/)[1])
    await db.execute(`create schema extensions;create extension pgcrypto schema extensions;create schema cp7_planning;create schema cp7_model_native;
      create table cp7_planning.history_runs(id uuid primary key,actor uuid not null,query jsonb not null,captured_at timestamptz not null,result jsonb not null,dependency_hash text not null);
      create table cp7_model_native.registry(id text primary key,registered_at timestamptz not null,configuration jsonb not null);
      insert into cp7_model_native.registry values('cp7.native-model-policy.v1','2026-08-31T00:00:00Z',${jsonArg(config)});
      ${block(src('planning/bootstrap.sql'), 'cp7_planning.utc')}
      ${block(src('model-native/source.sql'), 'cp7_model_native.dataset')}
      ${block(src('model-native/evaluation.sql'), 'cp7_model_native.build')}`)
    const actor = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa', root = '11111111-1111-4111-8111-111111111111', size = '22222222-2222-4222-8222-222222222222', target = `${root}:${size}`
    const day = n => new Date(Date.UTC(2026, 8, 1 + n)).toISOString().slice(0, 10)
    // One capture every morning 08:00 WIB on day c, holding 2026-09-01..c-1 (value 10+i, all AVAILABLE).
    const rows = Array.from({ length: 30 }, (_, k) => {
      const c = k + 1, days = Array.from({ length: c }, (_, i) => ({ date: day(i), state: 'AVAILABLE', training_pcs: String(10 + i) }))
      const result = { history: { rows: [{ target_key: target, size_id: size, available_sales_mean: '1', refs: [{ kind: 'PRODUCT', id: root, revision: '1' }], days }] },
        current_stock: [{ target_key: target, sku: 'PL3', product_name: 'Native-shaped daily captures' }] }
      return `('00000000-0000-4000-8000-${String(c).padStart(12, '0')}','${actor}',${jsonArg({ from_date: day(0), through_date: day(c - 1), group_mode: 'AS_SOLD' })},'${day(c)}T01:00:00Z',${jsonArg(result)},'h${c}')`
    })
    await db.execute(`insert into cp7_planning.history_runs values ${rows.join(',')};`)
    const q = { history_run_id: '00000000-0000-4000-8000-000000000030', target_key: target, horizon_days: '1' }
    const r = (await db.query(`select cp7_model_native.build(cp7_model_native.dataset(${jsonArg(q)},'${actor}')) as r`))[0].r
    expect([r.known_as_of, r.through_date, r.reason, r.selection_status]).toEqual(['2026-10-01T01:00:00.000000Z', '2026-09-30', 'COMPLETE_VALIDATION_RECOMMENDATION_REQUIRES_REVIEW', 'CHALLENGER_RECOMMENDED'])
    expect([r.evaluation.baseline, ...r.evaluation.challengers].map(m => m.summary.fold_count)).toEqual(Array(8).fill('3'))
    expect(r.evaluation.baseline.folds.map(x => [x.fold.origin, x.training.sources.at(-1).known_at, x.training_known_cutoff])).toEqual([
      ['2026-09-26', '2026-09-27T01:00:00.000000Z', '2026-09-27T16:59:59.999999Z'],
      ['2026-09-27', '2026-09-28T01:00:00.000000Z', '2026-09-28T16:59:59.999999Z'],
      ['2026-09-28', '2026-09-29T01:00:00.000000Z', '2026-09-29T16:59:59.999999Z']])
    // Independent oracles: mean of 10..35/36/37 against 36/37/38 -> errors 13.5/14/14.5; naive misses each day by 1.
    const s = id => [r.evaluation.baseline, ...r.evaluation.challengers].find(m => m.model.id === id).summary
    expect([Number(s('mean-1').mae), Number(s('mean-1').signed_bias), Number(s('mean-1').tail_abs_error)]).toEqual([14, -14, 14.5])
    expect([Number(s('naive-1').mae), Number(s('naive-1').signed_bias), Number(s('naive-1').tail_abs_error)]).toEqual([1, -1, 1])
    expect([r.forecast.status, r.evaluation.holdout.used_for_selection]).toEqual(['ELIGIBLE', false])
  } finally { await db.close() }
}, 120_000)
