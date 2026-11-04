// Explicit protocol models only. No browser, Auth or ERP operation is run.
import assert from 'node:assert/strict';
import test from 'node:test';
import * as evidence from './browser_evidence.mjs';

const basis = 'SKU_LOCATION_GRADE_MOVING_AVERAGE_V2';
const fixture = {source: 'SOURCE', target: 'TARGET', location: 'LOCATION', lots: ['LOT1', 'LOT2'],
  baseline_accounts: {FG_INVENTORY: '290.29', COGS: '0'}, physical_iso: '2026-11-05T01:00:00+07:00'};
const result = {conversion_id: 'GROUP', conversion_ids: ['PART1', 'PART2']};
function pool(qty, value, average, revision = '1'.repeat(32)) {
  return {state: 'KNOWN', qty, value, average, base_value: value, adjustment: '0',
    basis, reserved_included: true, revision};
}
function preview() {
  return {source_product_id: fixture.source, target_product_id: fixture.target, location_id: fixture.location,
    qty_pcs: 4, physical_at: fixture.physical_iso,
    source_stock: {physical: 10, reserved: 1, available: 9}, source_after: {physical: 6, reserved: 1, available: 5},
    target_stock: {physical: 4, reserved: 0, available: 4}, target_after: {physical: 8, reserved: 0, available: 8},
    allocations: [{source_lot_id: 'LOT1', qty_pcs: 2, source_value: '20.02'},
      {source_lot_id: 'LOT2', qty_pcs: 2, source_value: '40.04'}],
    cost: {source_value: '68.07', native_physical_value: '60.06', basis},
    source_value_pool: pool('10', '170.170000', '17.0170000000000000'),
    target_value_pool: pool('4', '120.120000', '30.0300000000000000', '2'.repeat(32)),
    source_value_revision: '1'.repeat(32), target_value_revision: '2'.repeat(32)};
}
function posted() {
  return {source: {physical: 6, reserved: 1, available: 5}, target: {physical: 8, reserved: 0, available: 8},
    accounts: structuredClone(fixture.baseline_accounts), groups: [{id: 'GROUP'}],
    members: [{source_lot_id: 'LOT1', qty_pcs: 2, unit_hpp: '10.01', destination_value: '20.02',
      conversion_id: 'PART1', group_id: 'GROUP', status: 'POSTED'},
    {source_lot_id: 'LOT2', qty_pcs: 2, unit_hpp: '20.02', destination_value: '40.04',
      conversion_id: 'PART2', group_id: 'GROUP', status: 'POSTED'}],
    current_economic_pools: {SOURCE: pool('6', '102.102000', '17.0170000000000000'),
      TARGET: pool('8', '188.188000', '23.5235000000000000', '2'.repeat(32))},
    Native_nonPO_books: {SOURCE: ['102.10', '102.10', '0.00', '0.00'],
      TARGET: ['188.19', '188.19', '0.00', '0.00']}};
}

test('current preview retains physical 60.06 and independently requires average 68.07', () => {
  evidence.previewOracle(preview(), fixture);
  evidence.postedOracle(posted(), fixture, result);
  assert.equal(evidence.derivation.expression_routes, 1);
  assert.equal(evidence.derivation.complete_original_recovered, true);
  assert.equal(evidence.derivation.actual_browser_cases, 0);
  assert(!evidence.IDS.some(id => id.includes('FIFO')));
});

test('old FIFO accounting and wrong cent are both refused before a real journey', () => {
  for (const value of ['60.06', '68.06', '68.08']) {
    const changed = preview();changed.cost.source_value = value;
    assert.throws(() => evidence.previewOracle(changed, fixture));
  }
  const changed = preview();delete changed.cost.native_physical_value;
  assert.throws(() => evidence.previewOracle(changed, fixture));
});

test('physical allocations, Native HPP and current product books all remain strict', () => {
  const changed = preview();changed.allocations[0].qty_pcs = 1;changed.allocations[1].qty_pcs = 3;
  assert.throws(() => evidence.previewOracle(changed, fixture));
  const native = posted();native.members[0].unit_hpp = '17.017';
  assert.throws(() => evidence.postedOracle(native, fixture, result));
  const books = posted();books.Native_nonPO_books.SOURCE = ['102.11', '102.11', '0', '0'];
  assert.throws(() => evidence.postedOracle(books, fixture, result));
});

test('raw component values cannot be prematurely replaced by journal cents', () => {
  const changed = posted();changed.current_economic_pools.SOURCE.value = '102.10';
  changed.current_economic_pools.TARGET.value = '188.19';
  assert.throws(() => evidence.postedOracle(changed, fixture, result));
  const reserved = preview();reserved.source_value_pool.qty = '9';
  assert.throws(() => evidence.previewOracle(reserved, fixture));
  const stale = preview();stale.source_value_revision = '3'.repeat(32);
  assert.throws(() => evidence.previewOracle(stale, fixture));
});

test('withdrawn financial access may expose no accounting or physical HPP numbers', () => {
  const value = preview();value.cost = {};
  value.allocations.forEach(row => {row.source_value = null;});
  value.source_value_pool = {state: 'HIDDEN', reserved_included: true, basis};
  value.target_value_pool = structuredClone(value.source_value_pool);
  evidence.hiddenValueOracle(value);
  const leaked = structuredClone(value);leaked.target_value_pool.average = '30.03';
  assert.throws(() => evidence.hiddenValueOracle(leaked));
  const nativeLeak = structuredClone(value);nativeLeak.allocations[0].source_value = '20.02';
  assert.throws(() => evidence.hiddenValueOracle(nativeLeak));
});

test('whole group inverse restores original pools and exact economic product books', () => {
  const state = posted();state.source = {physical: 10, reserved: 1, available: 9};
  state.target = {physical: 4, reserved: 0, available: 4};state.members.forEach(row => {row.status = 'REVERSED';});
  state.current_economic_pools.SOURCE = pool('10', '170.170000', '17.0170000000000000');
  state.current_economic_pools.TARGET = pool('4', '120.120000', '30.0300000000000000', '2'.repeat(32));
  state.Native_nonPO_books = {SOURCE: ['170.17', '170.17', '0', '0'], TARGET: ['120.12', '120.12', '0', '0']};
  evidence.inverseOracle(state, fixture);
  state.current_economic_pools.SOURCE.value = '170.18';
  assert.throws(() => evidence.inverseOracle(state, fixture));
});
