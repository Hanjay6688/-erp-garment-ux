import assert from 'node:assert/strict';
import { readFileSync, writeFileSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { performance } from 'node:perf_hooks';
import { openRuntime, jsonArg, textArg, sourceHashes, digest } from './runtime.mjs';
import * as f from './fixtures.mjs';
import { continuation } from './continuation.mjs';

const db = await openRuntime();
const cases = [], failures = [];
const sql = (name, value) => db.call(name, [jsonArg(value)]);
const predict = (method, values, params = {}, horizon = 1) => db.call('cp7_models.predict', [textArg(method), jsonArg(values), jsonArg(params), String(horizon)]);
const score = (actual, forecast, training = ['1', '2'], season = 1) => db.call('cp7_models.score', [jsonArg(actual), jsonArg(forecast), jsonArg(training), String(season)]);
const promotion = (base, challenger, policy = f.policy()) => db.call('cp7_models.promotion', [jsonArg(base), jsonArg(challenger), jsonArg(policy)]);
const equal = (actual, expected) => { assert.deepEqual(actual, expected); return { expected, actual }; };
const near = (actual, expected) => { assert.ok(Math.abs(Number(actual) - expected) <= 1e-9, `${actual} != ${expected}`); return { expected, actual, tolerance: 1e-9 }; };
async function run(id, fn) {
  const start = performance.now();
  try { const evidence = await fn(); cases.push({ id, status: 'PASS', evidence, elapsed_ms: Math.round(performance.now() - start) }); }
  catch (error) { failures.push({ id, error: error.message }); cases.push({ id, status: 'FAIL', error: error.message }); }
}
async function rejected(id, fn, reason) {
  await run(id, async () => {
    await assert.rejects(fn, new RegExp(reason));
    return { expected: reason, actual: 'REJECTED_AS_EXPECTED' };
  });
}
let cleanup;
try {
  await run('O06.draft-once', async () => { const v = f.available();v.open_drafts.push(f.clone(v.open_drafts[0]));const r = await sql('cp7_demand.availability', v);return equal([r.physical_fg_pcs, r.reserved_pcs, r.available_fg_pcs, r.projected_residual_pcs], ['100', '24', '76', '56']); });
  await run('O06.posted-ledger-not-double-subtracted', async () => { const v = f.available();v.fg_pcs = '76';v.open_drafts = [];return equal((await sql('cp7_demand.availability', v)).projected_residual_pcs, '56'); });
  await run('O06.cancelled-draft-released', async () => { const v = f.available();v.open_drafts = [];return equal((await sql('cp7_demand.availability', v)).projected_residual_pcs, '80'); });
  await rejected('O06.conflicting-draft-rejected', () => { const v = f.available();v.open_drafts.push({ ...v.open_drafts[0], qty_pcs: '25' });return sql('cp7_demand.availability', v); }, 'DRAFT_CONFLICT');
  await run('O11.stockout-is-not-zero-demand', async () => {
    const v = f.history();v.events = Array.from({ length: 14 }, (_, i) => f.sale(i + 1, 10));v.availability = Array.from({ length: 28 }, (_, i) => f.availabilityDay(i + 1, i < 14 ? 'AVAILABLE' : 'STOCKOUT'));
    const r = (await sql('cp7_demand.history', v)).rows[0];equal([Number(r.calendar_sales_mean), Number(r.available_sales_mean), r.lost_sales_pcs, r.available_days, r.stockout_days], [5, 10, null, 14, 14]);return equal(r.demand_estimate_basis, 'ASSUMED_AVAILABLE_DAYS_REPRESENTATIVE');
  });
  await run('O12.valid-zero-and-missing-distinct', async () => {
    const v = f.history();v.through_date = f.date(5);v.events = [f.sale(2, 10)];v.availability = [1, 2, 3].map(d => f.availabilityDay(d, 'AVAILABLE'));
    const r = (await sql('cp7_demand.history', v)).rows[0];equal(r.days.map(d => d.training_pcs), ['0', '10', '0', null, null]);equal([r.available_days, r.unknown_days], [3, 2]);return near(r.available_sales_mean, 10 / 3);
  });
  await run('P05.lifecycle-return-preserves-gross', async () => {
    const v = f.history();v.events = [f.sale(1, 24, { status: 'DRAFT', posted_at: null }), f.sale(2, 24, { lineage_key: 'sale-1', revision: '2' }), f.sale(3, 24, { lineage_key: 'sale-1', revision: '3', posted_at: f.at(2), returned_pcs: '5' })];
    const r = (await sql('cp7_demand.history', v)).rows[0];return equal([r.gross_observed_pcs, r.draft_reserved_pcs, r.days[1].returned_pcs], ['24', '0', '5']);
  });
  await run('M03.later-known-backdate-excluded', async () => {
    const v = f.history();v.events = [f.sale(1, 6), f.sale(1, 100, { revision: '2', known_at: f.at(31) })];const r = (await sql('cp7_demand.history', v)).rows[0];return equal(r.gross_observed_pcs, '6');
  });
  await run('X02.as-sold-restated-conserve-size', async () => {
    const v = f.history();v.events = [f.sale(1, 6)];const a = await sql('cp7_demand.history', v);v.group_mode = 'RESTATED';const b = await sql('cp7_demand.history', v);
    return equal([a.group_events[0].group_key, b.group_events[0].group_key, a.group_events[0].size_id, b.group_events[0].qty_pcs], ['old-group', 'new-group', 'M', '6']);
  });
  await run('P05.unknown-history-no-invented-zero-mean', async () => { const v = f.history();v.history_complete = false;const r = (await sql('cp7_demand.history', v)).rows[0];return equal([r.calendar_sales_mean, r.available_sales_mean, r.unknown_days], [null, null, 28]); });
  await rejected('P05.conflicting-revision', () => { const v = f.history();v.events = [f.sale(1, 6), f.sale(1, 7)];return sql('cp7_demand.history', v); }, 'REVISION_CONFLICT');
  await rejected('P05.physical-size-mismatch', () => { const v = f.history();v.events = [f.sale(1, 6, { size_id: 'L' })];return sql('cp7_demand.history', v); }, 'TARGET_SIZE');
  await rejected('P05.partial-day-denominator-refused', () => { const v = f.history();v.through_date = f.date(30);return sql('cp7_demand.history', v); }, 'COMPLETE_DAYS');
  await run('E01.own-history-explicit-assumption', async () => { const r = await sql('cp7_demand.estimate', f.estimate());equal(r.basis, 'OWN_AVAILABLE_HISTORY_ASSUMED_REPRESENTATIVE');return near(r.daily_pcs, 4); });
  await run('E01.no-history-no-default-batch', async () => { const v = f.estimate();v.own = null;const r = await sql('cp7_demand.estimate', v);return equal([r.status, r.daily_pcs], ['UNKNOWN', null]); });
  await run('E01.reviewed-same-size-analog', async () => { const v = f.estimate();v.own = null;v.analog = { source_key: 'analog-M', source_size_id: 'M', available_total_pcs: '30', available_days: '10', scale_factor: '0.5', reason: 'Explicit fixture assumption', reviewed: true, refs: f.refs('analogy') };const r = await sql('cp7_demand.estimate', v);return near(r.daily_pcs, 1.5); });
  await run('E01.unreviewed-analog-not-promoted', async () => { const v = f.estimate();v.own = null;v.analog = { source_key: 'analog-M', source_size_id: 'M', available_total_pcs: '30', available_days: '10', scale_factor: '1', reason: 'Not reviewed', reviewed: false, refs: f.refs('analogy') };return equal((await sql('cp7_demand.estimate', v)).status, 'UNKNOWN'); });
  await run('E01.manual-must-be-selected', async () => { const v = f.estimate();v.own = null;v.manual = { daily_pcs: '2', assumption_id: 'assumption-1', selected: false, refs: f.refs('manual') };equal((await sql('cp7_demand.estimate', v)).status, 'UNKNOWN');v.manual.selected = true;const r = await sql('cp7_demand.estimate', v);return equal([r.basis, r.daily_pcs], ['SELECTED_MANUAL_ASSUMPTION', '2']); });
  await run('O01.base-and-conditional-gap', async () => { const r = await sql('cp7_baseline.net', f.net());return equal([r.q_base_pcs, r.q_conditional_pcs, r.inputs.available_fg_pcs], ['18', '8', '18']); });
  await run('O02.days-target-buffer-separated', async () => { const r = await sql('cp7_baseline.target', f.target());return equal([r.horizon_days, r.horizon_demand_pcs, r.buffer_pcs, r.target_pcs], ['10', '40', '8', '48']); });
  await run('O02.dated-balances', async () => { const r = await sql('cp7_baseline.timeline', f.timeline());return equal(r.events.filter(e => e.event.kind === 'DEMAND').map(e => Number(e.balance_pcs)), [14, 10, 18, 14, 10, 16, 20, 16, 12, 8]); });
  await run('O03.late-arrival-retains-early-gap', async () => { const r = await sql('cp7_baseline.timeline', f.timeline(8));equal(r.events.filter(e => e.event.kind === 'DEMAND').map(e => Number(e.balance_pcs)), [14, 10, 6, 2, -2, 4, 8, 16, 12, 8]);return equal([r.first_known_gap.at, r.first_known_gap.gap_pcs], [f.at(5, '16'), '2']); });
  await run('O05.candidate-is-conditional-scenario', async () => { const v = f.net();v.target_pcs = '100';v.available_fg_pcs = '10';v.supplies[0].qty_pcs = '60';v.supplies[1].qty_pcs = '40';const r = await sql('cp7_baseline.net', v);return equal([r.q_base_pcs, r.q_conditional_pcs], ['30', '0']); });
  await run('O07.size-gap-not-hidden-by-group-surplus', async () => { const s = f.net();s.supplies = [];s.target_pcs = '10';s.available_fg_pcs = '25';const l = f.clone(s);l.target_key = 'SKU-L';l.size_id = 'L';l.target_pcs = '20';l.available_fg_pcs = '5';return equal([(await sql('cp7_baseline.net', s)).q_base_pcs, (await sql('cp7_baseline.net', l)).q_base_pcs], ['0', '15']); });
  await run('O08.batch-rounding-extra-visible', async () => { const v = f.feasible();v.need_pcs = '8';v.multiple_pcs = '12';const r = await sql('cp7_baseline.feasibility', v);return equal([r.rounded_need_pcs, r.rounding_extra_pcs, r.start_new_pcs], ['12', '4', '12']); });
  await run('O09.remaining-material', async () => { const r = await sql('cp7_baseline.material', f.material());return equal([r.remaining_need, r.external_need], ['40', '20']); });
  await run('O09.issue-does-not-prove-installed', async () => { const v = f.material();v.proven_installed = null;v.supplies = [{ ...v.supplies[0], kind: 'ISSUED', quantity: '80' }];const r = await sql('cp7_baseline.material', v);return equal([r.status, r.remaining_need, r.external_need], ['UNKNOWN', null, null]); });
  await run('O10.need-vs-feasible', async () => { const r = await sql('cp7_baseline.feasibility', f.feasible());return equal([r.need_pcs, r.start_new_pcs, r.unresolved_pcs], ['100', '60', '40']); });
  await run('O17.stop-keeps-gap', async () => { const v = f.feasible();v.need_pcs = '70';v.production_status = 'STOP';const r = await sql('cp7_baseline.feasibility', v);return equal([r.need_pcs, r.start_new_pcs, r.unresolved_pcs], ['70', '0', '70']); });
  await run('O19.unknown-fg-not-zero', async () => { const v = f.net();v.available_fg_pcs = null;const r = await sql('cp7_baseline.net', v);return equal([r.status, r.q_base_pcs], ['UNKNOWN', null]); });
  await run('P06.unknown-capacity-does-not-create-throughput', async () => { const v = f.feasible();v.capacity_pcs = null;const r = await sql('cp7_baseline.feasibility', v);return equal([r.status, r.need_pcs, r.start_new_pcs], ['UNKNOWN', '100', null]); });
  await run('P06.calendar-capacity-minus-existing-load', async () => { const r = await sql('cp7_baseline.capacity', f.capacity());return equal([Number(r.available_minutes), r.capacity_pcs], [360, '60']); });
  await run('P06.unknown-unit-time-not-invented', async () => { const v = f.capacity();v.unit_minutes = null;return equal((await sql('cp7_baseline.capacity', v)).capacity_pcs, null); });
  await run('P06.overbooked-window-no-negative-capacity', async () => { const v = f.capacity();v.windows[0].existing_load_minutes = '500';const r = await sql('cp7_baseline.capacity', v);return equal([r.capacity_pcs, Number(r.overbooked_minutes)], ['0', 20]); });
  await rejected('P06.overlapping-shifts-not-double-counted', () => { const v = f.capacity();v.windows.push({ ...v.windows[0], key: 'shift-2' });return sql('cp7_baseline.capacity', v); }, 'WINDOW_OVERLAP');
  await run('P06.fractional-instants-ordered-by-time', async () => { const v = f.capacity();v.unit_minutes = '0.005';v.windows = [{ ...v.windows[0], starts_at: '2026-01-01T01:00:00Z', ends_at: '2026-01-01T01:00:00.500Z', existing_load_minutes: '0' }, { ...v.windows[0], key: 'shift-2', starts_at: '2026-01-01T01:00:00.500Z', ends_at: '2026-01-01T01:00:01Z', existing_load_minutes: '0' }];return equal((await sql('cp7_baseline.capacity', v)).capacity_pcs, '3'); });
  await run('P06.batch-does-not-fit-capacity', async () => { const v = f.feasible();v.need_pcs = '8';v.multiple_pcs = '12';v.capacity_pcs = '10';return equal((await sql('cp7_baseline.feasibility', v)).start_new_pcs, '0'); });
  await run('M06.aggregate-horizon-quantile', async () => { const v = f.target();Object.assign(v, { mode: 'STATISTICAL', daily_mean: null, buffer_days: null, quantile: '0.75', horizon_samples: ['0', '20', '30', '100'] });return equal((await sql('cp7_baseline.target', v)).target_pcs, '30'); });
  await rejected('M06.double-buffer-refused', () => { const v = f.target();v.quantile = '0.95';return sql('cp7_baseline.target', v); }, 'DOUBLE_BUFFER');
  await run('P06.source-duplicate-not-counted-twice', async () => { const v = f.net();v.supplies.push(f.clone(v.supplies[0]));return equal((await sql('cp7_baseline.net', v)).q_base_pcs, '18'); });
  await rejected('P06.same-physical-source-in-two-kinds', () => { const v = f.net();v.supplies.push({ ...v.supplies[0], kind: 'INCOMING' });return sql('cp7_baseline.net', v); }, 'PHYSICAL_SOURCE_CONFLICT');
  await run('P06.late-supply-excluded-from-deadline', async () => { const v = f.net();v.supplies[0].eta = f.at(11);return equal((await sql('cp7_baseline.net', v)).q_base_pcs, '30'); });
  await run('P06.unknown-eta-review', async () => { const v = f.net();v.supplies[0].eta = null;return equal((await sql('cp7_baseline.net', v)).status, 'UNKNOWN'); });
  await run('X10.backlog-and-lost-sales', async () => { const v = f.timeline();v.initial_fg_pcs = '0';v.events = [f.event('morning-demand', 1, 'DEMAND', 5, '01'), f.event('evening-arrival', 1, 'SUPPLY', 5, '12')];const a = await sql('cp7_baseline.timeline', v);v.mode = 'LOST_SALES';const b = await sql('cp7_baseline.timeline', v);return equal([a.end_balance_pcs, a.first_known_gap.gap_pcs, b.end_balance_pcs, b.unmet_pcs], ['0', '5', '5', '5']); });
  await run('X11.unknown-event-preserved', async () => { const v = f.timeline();v.events[3].qty_pcs = null;const r = await sql('cp7_baseline.timeline', v);return equal([r.status, r.end_balance_pcs, r.events.at(-1).balance_pcs], ['UNKNOWN', null, null]); });
  await run('X12.same-day-order-changes-gap', async () => { const v = f.timeline();v.initial_fg_pcs = '0';v.events = [f.event('arrival', 1, 'SUPPLY', 5, '01'), f.event('demand', 1, 'DEMAND', 5, '12')];return equal((await sql('cp7_baseline.timeline', v)).first_known_gap, null); });
  await rejected('X12.ambiguous-timestamp-order-refused', () => { const v = f.timeline();v.events = [f.event('a', 1, 'SUPPLY', 5), f.event('b', 1, 'DEMAND', 5)];return sql('cp7_baseline.timeline', v); }, 'INTRADAY_ORDER');
  await run('O04.global-source-cap-60', async () => { const r = await sql('cp7_baseline.allocate', f.allocation());return equal(r.rows.map(x => [x.allocated_good_pcs, x.unresolved_pcs]), [['42', '0'], ['18', '12']]); });
  await run('O16.shared-capacity-cap-36', async () => { const r = await sql('cp7_baseline.allocate', f.allocation('40', '36', '30', '30'));equal(r.allocation.edges.map(e => e.input_pcs), ['30', '6']);return equal(r.rows.map(x => [x.allocated_good_pcs, x.unresolved_pcs]), [['30', '0'], ['6', '24']]); });
  await run('P06.filter-is-not-new-allocation-scope', async () => { const v = f.allocation();v.complete_scope = false;return equal((await sql('cp7_baseline.allocate', v)).status, 'UNKNOWN'); });
  await run('P06.match-recomputed-from-physical-facts', async () => { const v = f.allocation();v.matching.sources[0].confirmed_target = 'A';const r = await sql('cp7_baseline.allocate', v);return equal(r.rows.map(x => x.allocated_good_pcs), ['42', '0']); });
  await run('P06.required-material-mismatch', async () => { const v = f.allocation();v.matching.sources[0].constraints = [{ field: 'material', value: 'cotton', required: true, basis: 'FACT' }];v.matching.targets.forEach(t => { t.constraints = [{ field: 'material', value: 'denim', required: true, basis: 'FACT' }]; });return equal((await sql('cp7_baseline.allocate', v)).allocation.edges, []); });
  await run('P06.unknown-time-target-review-queue', async () => { const v = f.allocation();v.targets[0].risk_at = null;const r = await sql('cp7_baseline.allocate', v);equal(r.review_queue[0].reason, 'TIME_UNKNOWN');return equal(r.rows[0].target_key, 'B'); });
  await run('P06.yield-exact-rational-rounding', async () => { const v = f.allocation('10', '20', '7', '1');Object.assign(v.positions.positions[0].projection, { numerator: '3', denominator: '4', projected_good_pcs: '7' });return equal((await sql('cp7_baseline.allocate', v)).allocation.edges.map(e => [e.input_pcs, e.projected_good_pcs]), [['10', '7']]); });
  await rejected('P06.snapshot-mismatch', () => { const v = f.allocation();v.matching.snapshot_id = 'other';return sql('cp7_baseline.allocate', v); }, 'MATCH_SNAPSHOT');
  await run('X13.mean-oracle', async () => near((await predict('MEAN', ['2', '4', '6'])).forecasts[0], 4));
  await run('X13.naive-oracle', async () => near((await predict('NAIVE', ['2', '4', '6'])).forecasts[0], 6));
  await run('X13.moving-mean-oracle', async () => near((await predict('MOVING_MEAN', ['2', '4', '6'], { window: '2' })).forecasts[0], 5));
  await run('X13.ses-oracle', async () => near((await predict('SES', ['20', '30'], { alpha: '0.5', initial_level: '10' })).forecasts[0], 22.5));
  await run('X13.damped-holt-oracle', async () => { const r = await predict('DAMPED_HOLT', ['12'], { alpha: '0.5', beta: '0.5', phi: '0.8', initial_level: '10', initial_trend: '2' }, 2);near(r.forecasts[0], 13.16);return near(r.forecasts[1], 14.248); });
  await run('X13.seasonal-naive-oracle', async () => equal((await predict('SEASONAL_NAIVE', ['1', '2', '3', '4'], { season: '2' }, 3)).forecasts.map(Number), [3, 4, 3]));
  await run('X13.sba-oracle', async () => near((await predict('SBA', ['0', '0', '4', '0', '0', '8'], { alpha: '0.5', beta: '0.5' })).forecasts[0], 1.5));
  await run('X13.tsb-real-zero-decay', async () => near((await predict('TSB', ['4', '0', '0'], { alpha: '0.5', beta: '0.5' })).forecasts[0], 1));
  await run('M01.censored-period-not-zero', async () => equal((await predict('TSB', ['4', null, '0'], { alpha: '0.5', beta: '0.5' })).status, 'INELIGIBLE'));
  await run('M01.short-history-fallback-reason', async () => equal((await predict('MOVING_MEAN', ['1'], { window: '3' })).reason, 'WINDOW_HISTORY_SHORT'));
  await run('M05.insufficient-season-cycles', async () => equal((await predict('SEASONAL_NAIVE', ['1', '2', '3'], { season: '2' })).reason, 'FEWER_THAN_TWO_COMPLETE_SEASONS'));
  await rejected('M02.invalid-smoothing-parameter', () => predict('SES', ['1'], { alpha: '1.1', initial_level: null }), 'MODEL_ALPHA');
  await rejected('M02.non-finite-value', () => predict('MEAN', ['NaN']), 'F04_DECIMAL');
  await rejected('M02.negative-demand', () => predict('MEAN', ['-1']), 'F04_DECIMAL');
  await run('M02.nonnegative-damped-output', async () => equal((await predict('DAMPED_HOLT', ['0'], { alpha: '0.5', beta: '0.5', phi: '0.8', initial_level: '0', initial_trend: '-10' })).forecasts.map(Number), [0]));
  await run('O20.zero-scaled-denominator-is-NA', async () => { const r = await score(['0', '0'], ['0', '0'], ['0', '0', '0']);return equal([Number(r.mae), r.mase, r.rmsse, r.scaled_score_status], [0, null, null, 'NA_ZERO_DENOMINATOR']); });
  await run('P07.metric-sign-and-horizon-total', async () => { const r = await score(['10', '10'], ['9', '9']);return equal([Number(r.mae), Number(r.signed_bias), Number(r.horizon_total_abs_error)], [1, -1, 2]); });
  await run('X14.three-fold-challenger-wins', async () => { const b = await score(['10'], ['5']);const c = await score(['10'], ['9']);return equal((await promotion(f.metric(b.mae, b.signed_bias, b.horizon_total_abs_error), f.metric(c.mae, c.signed_bias, c.horizon_total_abs_error))).promote, true); });
  await run('M05.tie-keeps-baseline', async () => equal((await promotion(f.metric('1', '0', '2'), f.metric('1', '0', '2'))).promote, false));
  await run('P07.insufficient-folds-refuses-promotion', async () => equal((await promotion(f.metric('5', '-5', '5', '2'), f.metric('1', '-1', '1', '2'))).promote, false));
  await run('P07.bias-guard', async () => equal((await promotion(f.metric('5', '0', '5'), f.metric('1', '1', '1'))).reasons, ['BIAS_GUARD_FAILED']));
  await run('P07.tail-guard', async () => equal((await promotion(f.metric('5', '-5', '5'), f.metric('1', '-1', '6'))).reasons, ['TAIL_GUARD_FAILED']));
  await rejected('P07.null-bias-cannot-bypass-promotion-guard', () => promotion(f.metric('5', '-5', '5'), f.metric('1', null, '1')), 'MODEL_METRIC');
  await run('P07.rolling-evaluation-real-kernels', async () => { const r = await sql('cp7_models.evaluate', f.evaluation());equal(r.challengers[0].folds.map(x => Number(x.prediction.forecasts[0])), [3, 5, 7]);return equal([r.selected_model_id, r.holdout.used_for_selection], ['naive-v1', false]); });
  await run('M05.winning-challenger-tie-prefers-simpler', async () => { const v = f.evaluation();v.challengers = [f.model('ses-v1', 'SES', { alpha: '1', initial_level: null }), f.model('naive-v1', 'NAIVE')];const a = await sql('cp7_models.evaluate', v);v.challengers.reverse();const b = await sql('cp7_models.evaluate', v);return equal([a.selected_model_id, b.selected_model_id], ['naive-v1', 'naive-v1']); });
  await run('X15.holdout-perturbation-does-not-select', async () => { const v = f.evaluation();const a = await sql('cp7_models.evaluate', v);v.series[10].value = '0';const b = await sql('cp7_models.evaluate', v);equal(a.challengers, b.challengers);equal(a.selected_model_id, b.selected_model_id);return equal(b.holdout.results.map(x => Number(x.score.mae)), [5.5, 10]); });
  await run('M03.training-respects-knowledge-cutoff', async () => { const v = f.evaluation();v.series.push({ ...v.series[0], revision: '2', known_at: f.at(20), value: '999' });const r = await sql('cp7_models.evaluate', v);return equal(r.baseline.folds.map(x => x.training.values[0]), ['1', '1', '1']); });
  await run('M01.unknown-training-retains-baseline-honestly', async () => { const v = f.evaluation();v.series[0].state = 'UNKNOWN';v.series[0].value = null;const r = await sql('cp7_models.evaluate', v);return equal([r.selected_model_id, r.baseline.summary.fold_count, r.baseline.summary.mae, r.holdout.results[0].score], ['mean-v1', '0', null, null]); });
  await rejected('X15.validation-cannot-overlap-holdout', () => { const v = f.evaluation();v.folds[2].origin = f.date(10);return sql('cp7_models.evaluate', v); }, 'FOLD_LEAKAGE');
  await rejected('M03.future-registered-config-rejected', () => { const v = f.evaluation();v.challengers[0].registered_at = f.at(4);return sql('cp7_models.evaluate', v); }, 'CONFIG_AFTER_VALIDATION');
  await rejected('M02.conflicting-observation-revision', () => { const v = f.evaluation();v.series.push({ ...v.series[0], value: '999' });return sql('cp7_models.evaluate', v); }, 'REVISION_CONFLICT');
  await continuation({ run, rejected, equal, sql });
  await run('SEC.no-definer-or-operational-execute', async () => {
    const r = await db.query("select count(*)::int as functions, count(*) filter(where p.prosecdef)::int as definers, count(*) filter(where has_function_privilege('anon',p.oid,'EXECUTE') or has_function_privilege('authenticated',p.oid,'EXECUTE') or has_function_privilege('service_role',p.oid,'EXECUTE'))::int as exposed from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname in ('cp7_demand','cp7_baseline','cp7_models')");
    return equal(r[0], { functions: 22, definers: 0, exposed: 0 });
  });
  for (const role of ['anon', 'authenticated', 'service_role']) {
    await run(`SEC.${role}-direct-call-denied`, async () => {
      try { await assert.rejects(() => db.execute(`set role ${role};select cp7_baseline.target(${jsonArg(f.target())});`), /permission denied/); }
      finally { await db.execute('reset role;'); }
      return { expected: 'PERMISSION_DENIED', actual: 'PERMISSION_DENIED' };
    });
  }
  await run('SEC.capture-owner-can-compute-without-ledger-write', async () => {
    try { await db.execute(`set role cp7_capture;select cp7_baseline.target(${jsonArg(f.target())});select cp7_baseline.dependencies(${jsonArg(f.dependencies())});select cp7_models.compare_plan(${jsonArg(f.comparison())});`); }
    finally { await db.execute('reset role;'); }
    return equal((await db.query("select amount::text as amount from public.f04_ledger_canary where id=1"))[0].amount, '12345.67');
  });
} finally { await db.close();cleanup = 'CLOSED_DISPOSABLE_RUNTIME'; }
const receipt = {
  schema: 'cp7.f04.writer-kernel-receipt.v1', source_head: execFileSync('git', ['rev-parse', 'HEAD'], { encoding: 'utf8' }).trim(),
  runtime: db.flavor, version: db.version, source_hashes: sourceHashes,
  fixture_hash: digest(readFileSync('tests/cp7/families/f04/fixtures.mjs')), case_hash: digest(readFileSync('tests/cp7/families/f04/run.mjs')),
  additional_case_hashes: { 'tests/cp7/families/f04/continuation.mjs': digest(readFileSync('tests/cp7/families/f04/continuation.mjs')) },
  oracle_hash: digest(readFileSync('docs/cp7/framework-v2/04_BUKTI_DAN_ORACLE.md')), passed: cases.filter(c => c.status === 'PASS').length,
  failures, cases, cleanup, qualification: 'WRITER_PRIVATE_KERNEL_PROOF_ONLY',
  not_proven: ['CP6/F03 authoritative capture', 'real Supabase Auth/RLS composition', 'browser flows', 'X06 stale/race boundary', 'P08 apply', 'independent F04 acceptance', 'real-business predictive accuracy'],
};
if (process.env.F04_RECEIPT_PATH) writeFileSync(process.env.F04_RECEIPT_PATH, `${JSON.stringify(receipt, null, 2)}\n`);
process.stdout.write(`${JSON.stringify(receipt)}\n`);
if (failures.length) process.exitCode = 1;
