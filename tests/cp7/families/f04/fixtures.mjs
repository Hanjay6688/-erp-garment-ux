// Synthetic frozen business inputs. These quantities are oracles, not defaults.
export const refs = id => [{ kind: 'SYNTHETIC_FIXTURE', id, revision: '1' }];
export const clone = value => structuredClone(value);
export const at = (day, hour = '10') => `2026-01-${String(day).padStart(2, '0')}T${hour}:00:00Z`;
export const date = day => at(day).slice(0, 10);
export const envelope = contract_version => ({ contract_version, snapshot_id: 'frozen-fixture-1', scope_id: 'complete-scope-1' });
export const history = () => ({
  ...envelope('cp7.demand-input.v1'), known_as_of: at(30), effective_as_of: at(30),
  from_date: date(1), through_date: date(28), history_complete: true, group_mode: 'AS_SOLD',
  targets: [{ key: 'SKU-M', size_id: 'M', current_group_key: 'new-group', refs: refs('SKU-M') }], events: [], availability: [],
});
export const sale = (day, qty, overrides = {}) => ({
  lineage_key: `sale-${day}`, revision: '1', known_at: at(day), effective_at: at(day), posted_at: at(day),
  status: 'POSTED', target_key: 'SKU-M', size_id: 'M', sold_group_key: 'old-group', qty_pcs: String(qty), returned_pcs: '0', refs: refs(`sale-${day}`), ...overrides,
});
export const availabilityDay = (day, state) => ({ target_key: 'SKU-M', date: date(day), revision: '1', known_at: at(day, '16'), state, refs: refs(`av-${day}`) });
export const available = () => ({
  ...envelope('cp7.available-input.v1'), target_key: 'SKU-M', size_id: 'M', fg_basis: 'ON_HAND_AFTER_POSTED', fg_pcs: '100',
  open_drafts: [{ lineage_key: 'sale-open', qty_pcs: '24', refs: refs('sale-open') }], residual_future_pcs: '20', refs: refs('fg-ledger'),
});
export const target = () => ({ ...envelope('cp7.target-input.v1'), mode: 'DAYS', daily_mean: '4', lead_days: '7', review_days: '3', buffer_days: '2', quantile: null, horizon_samples: [], refs: refs('policy') });
export const estimate = () => ({ ...envelope('cp7.demand-estimate-input.v1'), target_key: 'SKU-M', size_id: 'M', minimum_own_available_days: '3',
  own: { available_total_pcs: '12', available_days: '3', capture_complete: true, refs: refs('own-history') },
  analog: null, manual: null, refs: refs('estimate-policy'),
});
export const capacity = () => ({ ...envelope('cp7.capacity-input.v1'), work_centre_id: 'sewing-crew', from_at: at(1, '00'), through_at: at(10, '23'),
  unit_minutes: '6', unit_time_basis: 'SELECTED_ASSUMPTION', windows: [{ key: 'shift-1', starts_at: at(1, '01'), ends_at: at(1, '09'), existing_load_minutes: '120', refs: refs('shift-1') }], refs: refs('calendar-v1'),
});
export const supply = (physical_key, kind, qty, day) => ({ physical_key, snapshot_id: 'frozen-fixture-1', target_key: 'SKU-M', size_id: 'M', kind, qty_pcs: String(qty), eta: at(day), eligible: true, refs: refs(physical_key) });
export const net = () => ({ ...envelope('cp7.net-input.v1'), scenario_id: 'scenario-A', target_key: 'SKU-M', size_id: 'M', deadline: at(10), target_pcs: '48', available_fg_pcs: '18', supplies: [supply('wip-directed', 'DIRECTED', 12, 3), supply('candidate', 'ALLOCATED_CANDIDATE', 10, 6)], refs: refs('need') });
export const event = (key, day, kind, qty, hour = '10', sequence = '1') => ({ key, at: at(day, hour), sequence, kind, qty_pcs: qty === null ? null : String(qty), refs: refs(key) });
export const timeline = (directedDay = 3) => ({
  ...envelope('cp7.timeline-input.v1'), target_key: 'SKU-M', size_id: 'M', mode: 'BACKLOG', initial_fg_pcs: '18', from_at: at(1, '00'), through_at: at(10, '23'),
  events: [...Array.from({ length: 10 }, (_, i) => event(`d${i + 1}`, i + 1, 'DEMAND', 4, '16')), event('directed', directedDay, 'SUPPLY', 12, '08'), event('candidate', 6, 'SUPPLY', 10, '08'), event('new', 7, 'SUPPLY', 8, '08')], refs: refs('dated-scenario'),
});
export const feasible = () => ({ ...envelope('cp7.feasibility-input.v1'), target_key: 'SKU-M', size_id: 'M', production_status: 'ACTIVE', need_pcs: '100', multiple_pcs: '1', capacity_pcs: '60', material_cap_pcs: '100', refs: refs('capacity-calendar') });
export const material = () => ({ ...envelope('cp7.material-need-input.v1'), material_id: 'zipper', unit: 'PCS', gross_need: '100', proven_installed: '60', deadline: at(10), supplies: [{ physical_key: 'unused-1', kind: 'UNUSED', quantity: '20', verified_eligible_allocated: true, eta: null, refs: refs('unused-1') }], refs: refs('installation-facts') });
export const allocation = (source = '60', capacity = '72', a = '42', b = '30') => ({
  ...envelope('cp7.allocation-input.v1'), scenario_id: 'candidate-scenario', complete_scope: true, capacity_pcs: capacity, refs: refs('capacity-calendar'),
  positions: { contract_version: 'cp7.wip-position.v1', snapshot_id: 'frozen-fixture-1', status: 'COMPLETE', allocation_review_required: false,
    positions: [{ key: 'source-M', size_id: 'M', pool_key: 'pool-1', remaining_pcs: source, eligible_company_wip: true, refs: refs('source-M'), projection: { quality: 'SCENARIO', numerator: '1', denominator: '1', eligible_input_pcs: source, projected_good_pcs: source } }],
    totals: [{ pool_key: 'pool-1', wip_pcs: source }],
  },
  matching: { snapshot_id: 'frozen-fixture-1', sources: [{ key: 'source-M', quality: 'COMPLETE', size_id: 'M', confirmed_target: null, constraints: [], refs: refs('source-M') }], targets: ['A', 'B'].map(key => ({ key, size_id: 'M', constraints: [], refs: refs(key) })) },
  etas: [{ position_key: 'source-M', at: at(7), refs: refs('eta-source-M') }],
  targets: [['A', a, 3], ['B', b, 4]].map(([key, need_pcs, risk]) => ({ key, size_id: 'M', need_pcs, deadline: at(10), risk_at: at(risk), helps_at: at(7), production_status: 'ACTIVE', refs: refs(key) })),
});
export const policy = () => ({ minimum_complete_folds: '3', minimum_mae_improvement: '0', maximum_bias_worsening: '0', maximum_tail_worsening: '0', season_lag: '1' });
export const metric = (mae, bias, tail, count = '3') => ({ fold_count: count, requested_folds: '3', mae, signed_bias: bias, tail_abs_error: tail });
export const model = (id, method, params = {}) => ({ id, method, params, registered_at: '2025-12-31T00:00:00Z' });
export const evaluation = () => ({
  ...envelope('cp7.model-evaluation-input.v1'), target_key: 'SKU-M', size_id: 'M', known_as_of: at(30), series_start: date(1), series_end: date(12),
  series: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12].map(day => ({ date: date(day), known_at: at(day), revision: '1', state: 'OBSERVED', value: String(day), refs: refs(`observation-${day}`) })),
  baseline: model('mean-v1', 'MEAN'), challengers: [model('naive-v1', 'NAIVE')],
  folds: [3, 5, 7].map(day => ({ id: `origin-${day}`, origin: date(day), horizon: '1' })), holdout: { origin: date(10), horizon: '1' }, policy: policy(), refs: refs('frozen-dataset'),
});
export const dependencies = () => {
  const vector = ['calendar', 'lead-time', 'yield', 'capacity'].map(domain => ({ domain, revision: 'v1', completeness: 'COMPLETE', fact_count: 4, source_hash: 'a'.repeat(64) }));
  return { ...envelope('cp7.dependency-check-input.v1'), captured_at: at(1), checked_at: at(10), required_domains: vector.map(x => x.domain), expected: vector, current: clone(vector), refs: refs('dependency-capture') };
};
export const outcome = (event_key, quantity, overrides = {}) => ({
  event_key, scope_id: 'complete-scope-1', plan_id: 'plan-1', plan_version: 1, target_key: 'SKU-M', size_id: 'M', metric_id: 'good-completed-pcs.v1',
  kind: 'POST', reverses_event_key: null, quantity_pcs: quantity === null ? null : String(quantity), effective_at: at(3), known_at: at(3), refs: refs(event_key), ...overrides,
});
export const comparison = () => ({
  ...envelope('cp7.plan-comparison-input.v1'), assessment_at: at(10), known_as_of: at(20), effective_through: at(10), knowledge_mode: 'AS_KNOWN', capture_complete: true, history_reconstructible: true,
  plan: { plan_id: 'plan-1', plan_version: 1, snapshot_id: 'original-plan-capture', scope_id: 'complete-scope-1', created_at: at(1), known_as_of: at(1), target_key: 'SKU-M', size_id: 'M', metric_id: 'good-completed-pcs.v1', period_start: at(2), period_end: at(10), planned: { state: 'KNOWN', value: '12', unit: 'PCS', refs: refs('frozen-planned-quantity') }, refs: refs('frozen-plan-1-v1') },
  events: [outcome('partial-a', 8), outcome('partial-b', 4, { effective_at: at(5), known_at: at(5) }), outcome('correction-a', 2, { kind: 'REVERSAL', reverses_event_key: 'partial-a', effective_at: at(3), known_at: at(7) })], refs: refs('actual-capture'),
});
