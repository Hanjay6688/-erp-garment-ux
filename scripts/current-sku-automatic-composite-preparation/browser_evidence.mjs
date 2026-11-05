// Pure evidence checks for the retained real fixture under current valuation.
// These checks alone grant no browser, Auth, Native or owning-run credit.
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';

const originalURL = new URL('../current-sku-pair-browser-qualification/evidence.mjs', import.meta.url);
const original = readFileSync(originalURL);
assert.equal(original.length, 7049, 'CURRENT_SKU_EXACT_RETAINED_BROWSER_EVIDENCE_SIZE');
assert.equal(createHash('sha256').update(original).digest('hex'),
  '790083c4f578de04d54e943f58746ae73d269362e8337773a0847a293333213f',
  'CURRENT_SKU_EXACT_RETAINED_BROWSER_EVIDENCE_SOURCE');
const before = 'assert.equal(cents(value.cost.source_value),6006n)';
const after = 'assert.equal(cents(value.cost.native_physical_value),6006n)';
const text = original.toString('utf8');
assert.equal(text.split(before).length - 1, 1);
assert(!text.includes(after));
const derived = text.replace(before, after);
assert.equal(derived.replace(after, before), text, 'CURRENT_SKU_COMPLETE_BROWSER_EVIDENCE_NOT_RECOVERED');
// Compile the whole retained ES module, preserving every other function.
const physical = await import('data:text/javascript;base64,' + Buffer.from(derived).toString('base64'));

export const IDS = [
  'SKU_CURRENT_MOVAVG_DESKTOP_REAL_AUTH_PAIR_VALUE_RECOVERY_INVERSE',
  'SKU_CURRENT_MOVAVG_MOBILE390_REAL_AUTH_PAIR_VALUE_GUARDS_INVERSE',
];
export const cents = physical.cents;
export const equalCensus = physical.equalCensus;
export const pairOnly = physical.pairOnly;
export const observeConsole = physical.observeConsole;
export const requireConsoleEvidence = physical.requireConsoleEvidence;
export const readable = physical.readable;
export const physicalPostedOracle = physical.postedOracle;
export const derivation = Object.freeze({
  retained_bytes: original.length,
  retained_sha256: createHash('sha256').update(original).digest('hex'),
  derived_sha256: createHash('sha256').update(derived).digest('hex'),
  complete_original_recovered: true,
  expression_routes: 1,
  physical_FIFO_quantities_allocations_HPP_and_full_boundary_assertions_preserved: true,
  historical_FIFO_case_ids_not_reused_as_current_credit: true,
  actual_browser_cases: 0,
});

const BASIS = 'SKU_LOCATION_GRADE_MOVING_AVERAGE_V2';
// Independent fixture facts from the exact retained Native constructor:
// source 3 @10.01 + 7 @20.02, target 4 @30.03, 1 source piece reserved,
// 4 pieces moved. Reservations stay in the economic pool.
const SOURCE_QTY = 10n, TARGET_QTY = 4n, MOVE_QTY = 4n;
const SOURCE_CENTS = 3n * 1001n + 7n * 2002n;
const TARGET_CENTS = 4n * 3003n;

function decimal(value) {
  assert.equal(typeof value, 'string', 'EXACT_DECIMAL_STRING_REQUIRED');
  const match = /^(-?)(\d+)(?:\.(\d+))?$/.exec(value);
  assert(match, 'FINITE_EXACT_DECIMAL_REQUIRED');
  const [, sign, whole, fraction = ''] = match;
  return {n: BigInt(whole + fraction) * (sign ? -1n : 1n), d: 10n ** BigInt(fraction.length)};
}
function exactDecimal(observed, n, d, label) {
  const value = decimal(observed);
  assert.equal(value.n * d, n * value.d, label);
}
function rounded(n, d) {
  assert(n >= 0n && d > 0n);
  return (2n * n + d) / (2n * d);
}
function pool(value, qty, n, d) {
  assert.equal(value.state, 'KNOWN');
  assert.equal(value.basis, BASIS);
  assert.equal(value.reserved_included, true);
  exactDecimal(value.qty, qty, 1n, 'EXACT_PHYSICAL_POOL_QUANTITY');
  exactDecimal(value.value, n, d, 'EXACT_RAW_ECONOMIC_POOL_VALUE');
  exactDecimal(value.base_value, n, d, 'EXACT_COMPONENT_BASE_VALUE');
  exactDecimal(value.adjustment, 0n, 1n, 'COMPONENT_POOL_ADJUSTMENT_NOT_A_SECOND_VALUE');
  exactDecimal(value.average, n, d * qty, 'EXACT_CURRENT_MOVING_AVERAGE');
  assert.match(value.revision, /^[a-f0-9]{32}$/);
}
function productBooks(state, fixture, sourceCents, targetCents) {
  // Native function columns are hpp_total_cost, fg_value, cogs_value,
  // other_out_value. No sale has posted in this conversion fixture.
  for (const [product, value] of [[fixture.source, sourceCents], [fixture.target, targetCents]]) {
    assert.deepEqual(state.Native_nonPO_books[product].map(cents), [value, value, 0n, 0n],
      'EXACT_CURRENT_PRODUCT_HPP_AND_FG_BOOKS');
  }
}

export function previewOracle(value, fixture) {
  physical.previewOracle(value, fixture);
  assert.equal(value.cost.basis, BASIS);
  assert.equal(cents(value.cost.source_value), rounded(SOURCE_CENTS * MOVE_QTY, SOURCE_QTY),
    'EXACT_ROUNDED_MOVING_AVERAGE_TRANSFER_68_07');
  pool(value.source_value_pool, SOURCE_QTY, SOURCE_CENTS, 100n);
  pool(value.target_value_pool, TARGET_QTY, TARGET_CENTS, 100n);
  assert.equal(value.source_value_revision, value.source_value_pool.revision);
  assert.equal(value.target_value_revision, value.target_value_pool.revision);
}

export function postedOracle(state, fixture, result) {
  physical.postedOracle(state, fixture, result);
  const sourceRaw = SOURCE_CENTS * (SOURCE_QTY - MOVE_QTY);
  const targetRaw = TARGET_CENTS * SOURCE_QTY + SOURCE_CENTS * MOVE_QTY;
  const denominator = 100n * SOURCE_QTY;
  pool(state.current_economic_pools[fixture.source], SOURCE_QTY - MOVE_QTY, sourceRaw, denominator);
  pool(state.current_economic_pools[fixture.target], TARGET_QTY + MOVE_QTY, targetRaw, denominator);
  productBooks(state, fixture, rounded(sourceRaw, SOURCE_QTY), rounded(targetRaw, SOURCE_QTY));
  // Six-decimal component values conserve 290.290000. The journal conserves
  // the independent cent amount 102.10 +188.19, without rounding each root.
  assert.equal(sourceRaw + targetRaw, (SOURCE_CENTS + TARGET_CENTS) * SOURCE_QTY);
}

export function inverseOracle(state, fixture) {
  assert.deepEqual(state.source, {physical: 10, reserved: 1, available: 9});
  assert.deepEqual(state.target, {physical: 4, reserved: 0, available: 4});
  assert.deepEqual(state.accounts, fixture.baseline_accounts);
  assert.equal(state.groups.length, 1);
  assert.equal(state.members.length, 2);
  assert(state.members.every(row => row.status === 'REVERSED'));
  pool(state.current_economic_pools[fixture.source], SOURCE_QTY, SOURCE_CENTS, 100n);
  pool(state.current_economic_pools[fixture.target], TARGET_QTY, TARGET_CENTS, 100n);
  productBooks(state, fixture, SOURCE_CENTS, TARGET_CENTS);
}

export function hiddenValueOracle(value) {
  assert.deepEqual(value.cost, {}, 'NO_FINANCIAL_COST_WITHOUT_CURRENT_PERMISSION');
  assert(value.allocations.every(row => row.source_value === null), 'NO_PHYSICAL_HPP_WITHOUT_CURRENT_PERMISSION');
  for (const name of ['source_value_pool', 'target_value_pool']) {
    assert.deepEqual(value[name], {state: 'HIDDEN', reserved_included: true, basis: BASIS},
      'NO_POOL_NUMBERS_WITHOUT_CURRENT_HPP_PERMISSION');
  }
}
