// Independent expected values for M07/M08 private boundaries, not generated
// from SQL formulas. The original runner owns runtime lifecycle and receipt.
import * as f from './fixtures.mjs';

export async function continuation({ run, rejected, equal, sql }) {
  await run('M07.same-vector-later-clock-is-current', async () => {
    const r = await sql('cp7_baseline.dependencies', f.dependencies());
    return equal([r.status, r.dependencies_match, r.recompute_required, r.authorization_checked], ['CURRENT', true, false, false]);
  });
  for (const domain of ['calendar', 'lead-time', 'yield', 'capacity']) {
    await run(`M07.${domain}-revision-invalidates`, async () => {
      const v = f.dependencies();v.current.find(x => x.domain === domain).revision = 'v2';
      const r = await sql('cp7_baseline.dependencies', v);
      return equal([r.status, r.recompute_required, r.checks.find(x => x.domain === domain).reasons], ['STALE', true, ['REVISION_CHANGED']]);
    });
  }
  await run('M07.same-count-backdate-hash-invalidates', async () => {
    const v = f.dependencies();v.current[0].source_hash = 'b'.repeat(64);
    const r = await sql('cp7_baseline.dependencies', v);
    return equal([r.status, r.checks[0].reasons], ['STALE', ['SOURCE_HASH_CHANGED']]);
  });
  await run('M07.deletion-retains-authoritative-vector', async () => {
    const v = f.dependencies();Object.assign(v.current[0], { revision: 'v2-tombstone', fact_count: 0, source_hash: 'c'.repeat(64) });
    const r = await sql('cp7_baseline.dependencies', v);
    return equal([r.status, r.checks[0].reasons], ['STALE', ['REVISION_CHANGED', 'SOURCE_HASH_CHANGED', 'FACT_COUNT_CHANGED']]);
  });
  await run('M07.missing-current-is-not-proof-of-deletion', async () => {
    const v = f.dependencies();v.current.shift();const r = await sql('cp7_baseline.dependencies', v);
    return equal([r.status, r.dependencies_match, r.evidence_complete], ['UNKNOWN', null, false]);
  });
  await run('M07.required-domain-missing-from-both', async () => {
    const v = f.dependencies();v.required_domains.push('material');return equal((await sql('cp7_baseline.dependencies', v)).status, 'UNKNOWN');
  });
  await run('M07.same-partial-vector-not-current', async () => {
    const v = f.dependencies();v.expected[0].completeness = 'PARTIAL';v.current[0].completeness = 'PARTIAL';
    return equal((await sql('cp7_baseline.dependencies', v)).status, 'UNKNOWN');
  });
  await run('M07.changed-plus-incomplete-retains-both-findings', async () => {
    const v = f.dependencies();v.current[0].revision = 'v2';v.current[1].completeness = 'UNKNOWN';
    const r = await sql('cp7_baseline.dependencies', v);return equal([r.status, r.evidence_complete, r.dependencies_match], ['STALE', false, false]);
  });
  await run('M07.additional-dependency-invalidates', async () => {
    const v = f.dependencies();v.current.push({ ...v.current[0], domain: 'new-material' });return equal((await sql('cp7_baseline.dependencies', v)).status, 'STALE');
  });
  await run('M07.vector-order-does-not-change-checks', async () => {
    const v = f.dependencies();const a = await sql('cp7_baseline.dependencies', v);v.current.reverse();v.expected.reverse();
    return equal((await sql('cp7_baseline.dependencies', v)).checks, a.checks);
  });
  await rejected('M07.duplicate-domain-refused', () => { const v = f.dependencies();v.current.push(f.clone(v.current[0]));return sql('cp7_baseline.dependencies', v); }, 'DUPLICATE_DOMAIN');
  await rejected('M07.empty-required-manifest-refused', () => { const v = f.dependencies();v.required_domains = [];return sql('cp7_baseline.dependencies', v); }, 'REQUIRED_DOMAINS');
  await rejected('M07.timestamp-cannot-substitute-for-hash', () => { const v = f.dependencies();v.current[0].source_hash = f.at(10);return sql('cp7_baseline.dependencies', v); }, 'DEPENDENCY_HASH');
  await run('M08.partial-completion-minus-linked-correction', async () => {
    const r = await sql('cp7_models.compare_plan', f.comparison());
    return equal([r.comparison.plan_version, r.comparison.planned.value, r.comparison.actual.value, r.variance_pcs, r.remaining_to_plan_pcs, r.selected_event_count], [1, '12', '10', '-2', '2', 3]);
  });
  await run('M08.progress-is-not-final-plan-miss', async () => {
    const v = f.comparison();v.effective_through = f.at(4);v.assessment_at = f.at(4);const r = await sql('cp7_models.compare_plan', v);
    return equal([r.comparison.actual.value, r.coverage, r.variance_pcs, r.remaining_to_plan_pcs, r.decision_verdict], ['8', 'PERIOD_IN_PROGRESS', null, '4', 'NOT_INFERRED_FROM_OUTCOME']);
  });
  await run('M08.late-entry-does-not-rewrite-as-known', async () => {
    const v = f.comparison();const a = await sql('cp7_models.compare_plan', v);
    v.events.push(f.outcome('late-post', 3, { effective_at: f.at(6), known_at: f.at(15) }));
    const b = await sql('cp7_models.compare_plan', v);
    equal(b.comparison, a.comparison);return equal([b.original_plan, b.later_known_event_count], [v.plan, 0]);
  });
  await run('M08.restated-late-entry-preserves-original-plan', async () => {
    const v = f.comparison();v.knowledge_mode = 'RESTATED';v.events.push(f.outcome('late-post', 3, { effective_at: f.at(6), known_at: f.at(15) }));
    const r = await sql('cp7_models.compare_plan', v);equal(r.original_plan, v.plan);
    return equal([r.comparison.actual.value, r.variance_pcs, r.later_known_event_count, r.knowledge_cutoff, r.decision_verdict], ['13', '1', 1, f.at(20), 'NOT_INFERRED_FROM_OUTCOME']);
  });
  await run('M08.late-reversal-only-in-restated-view', async () => {
    const v = f.comparison();v.events[2].known_at = f.at(15);const a = await sql('cp7_models.compare_plan', v);v.knowledge_mode = 'RESTATED';const b = await sql('cp7_models.compare_plan', v);
    return equal([a.comparison.actual.value, b.comparison.actual.value, b.later_known_event_count], ['12', '10', 1]);
  });
  await run('M08.complete-reversal-can-prove-zero', async () => {
    const v = f.comparison();v.events = [v.events[0], { ...v.events[2], quantity_pcs: '8' }];
    const r = await sql('cp7_models.compare_plan', v);return equal([r.comparison.actual.state, r.comparison.actual.value, r.variance_pcs], ['KNOWN', '0', '-12']);
  });
  await run('M08.multiple-partial-reversals-net-once', async () => {
    const v = f.comparison();v.events.push(f.outcome('correction-b', 3, { kind: 'REVERSAL', reverses_event_key: 'partial-a', effective_at: f.at(3), known_at: f.at(8) }));
    const r = await sql('cp7_models.compare_plan', v);return equal(r.comparison.actual.value, '7');
  });
  await run('M08.exact-duplicate-effect-counted-once', async () => {
    const v = f.comparison();v.events.push(f.clone(v.events[0]), f.clone(v.events[2]));const r = await sql('cp7_models.compare_plan', v);
    return equal([r.comparison.actual.value, r.selected_event_count], ['10', 3]);
  });
  await run('M08.incomplete-capture-is-not-known-zero', async () => {
    const v = f.comparison();v.capture_complete = false;v.events = [];const r = await sql('cp7_models.compare_plan', v);
    return equal([r.comparison.actual.state, r.comparison.actual.reason, r.variance_pcs], ['UNKNOWN', 'CAPTURE_INCOMPLETE', null]);
  });
  await run('M08.complete-empty-capture-is-observed-zero', async () => {
    const v = f.comparison();v.events = [];const r = await sql('cp7_models.compare_plan', v);
    return equal([r.comparison.actual.state, r.comparison.actual.value, r.variance_pcs], ['KNOWN', '0', '-12']);
  });
  await run('M08.historical-capture-must-be-reconstructible', async () => {
    const v = f.comparison();v.history_reconstructible = false;const r = await sql('cp7_models.compare_plan', v);
    equal([r.comparison.actual.state, r.variance_pcs], ['UNKNOWN', null]);v.knowledge_mode = 'RESTATED';
    return equal((await sql('cp7_models.compare_plan', v)).comparison.actual.value, '10');
  });
  await run('M08.unknown-effect-quantity-is-not-zero', async () => {
    const v = f.comparison();v.events[2].quantity_pcs = null;const r = await sql('cp7_models.compare_plan', v);
    return equal([r.comparison.actual.state, r.known_signed_subtotal_pcs, r.variance_pcs], ['UNKNOWN', '12', null]);
  });
  await run('M08.assumption-remains-visible-in-comparison', async () => {
    const v = f.comparison();v.plan.planned.state = 'ASSUMED';v.plan.planned.assumption_ids = ['owner-scenario-1'];
    const r = await sql('cp7_models.compare_plan', v);return equal(r.comparison.planned, v.plan.planned);
  });
  await run('M08.unknown-plan-is-not-retrofitted-from-actual', async () => {
    const v = f.comparison();v.plan.planned = { state: 'UNKNOWN', unit: 'PCS', reason: 'No forecast', refs: f.refs('unknown-plan') };
    const r = await sql('cp7_models.compare_plan', v);return equal([r.status, r.comparison.actual.value, r.variance_pcs, r.remaining_to_plan_pcs], ['UNKNOWN', '10', null, null]);
  });
  await run('M08.period-end-exclusive-and-future-knowledge-excluded', async () => {
    const v = f.comparison();v.events.push(f.outcome('end-boundary', 100, { effective_at: f.at(10), known_at: f.at(10) }), f.outcome('not-yet-known', 100, { known_at: f.at(21) }));v.knowledge_mode = 'RESTATED';
    return equal((await sql('cp7_models.compare_plan', v)).comparison.actual.value, '10');
  });
  await run('M08.event-order-does-not-change-result', async () => {
    const v = f.comparison();const a = await sql('cp7_models.compare_plan', v);v.events.reverse();const b = await sql('cp7_models.compare_plan', v);
    return equal([b.comparison, b.events], [a.comparison, a.events]);
  });
  await rejected('M08.over-reversal-refused', () => { const v = f.comparison();v.events[2].quantity_pcs = '9';return sql('cp7_models.compare_plan', v); }, 'OVER_REVERSAL');
  await rejected('M08.sum-of-reversals-cannot-exceed-original', () => { const v = f.comparison();v.events.push({ ...v.events[2], event_key: 'another-correction', quantity_pcs: '7' });return sql('cp7_models.compare_plan', v); }, 'OVER_REVERSAL');
  await rejected('M08.orphan-reversal-refused-for-complete-capture', () => { const v = f.comparison();v.events.shift();return sql('cp7_models.compare_plan', v); }, 'ORPHAN_REVERSAL');
  await run('M08.orphan-in-incomplete-capture-remains-unknown', async () => { const v = f.comparison();v.capture_complete = false;v.events.shift();return equal((await sql('cp7_models.compare_plan', v)).comparison.actual.state, 'UNKNOWN'); });
  await rejected('M08.reversal-cannot-correct-another-reversal', () => { const v = f.comparison();v.events.push({ ...v.events[2], event_key: 'nested-correction', reverses_event_key: 'correction-a', known_at: f.at(8) });return sql('cp7_models.compare_plan', v); }, 'REVERSAL_LINK');
  await rejected('M08.correction-cannot-change-effective-period', () => { const v = f.comparison();v.events[2].effective_at = f.at(4);return sql('cp7_models.compare_plan', v); }, 'REVERSAL_LINK');
  await rejected('M08.conflicting-event-identity-refused', () => { const v = f.comparison();v.events.push({ ...v.events[0], quantity_pcs: '9' });return sql('cp7_models.compare_plan', v); }, 'EVENT_CONFLICT');
  for (const [field, value] of [['plan_version', 2], ['plan_id', 'other-plan'], ['size_id', 'L'], ['target_key', 'SKU-L'], ['scope_id', 'other-scope'], ['metric_id', 'sales-gross-pcs.v1']]) {
    await rejected(`M08.wrong-${field}-refused`, () => { const v = f.comparison();v.events[0][field] = value;return sql('cp7_models.compare_plan', v); }, 'ATTRIBUTION');
  }
  await rejected('M08.future-fact-in-original-plan-refused', () => { const v = f.comparison();v.plan.known_as_of = f.at(2);return sql('cp7_models.compare_plan', v); }, 'PERIOD_OR_ORIGIN');
  await rejected('M08.capture-cannot-predate-assessment', () => { const v = f.comparison();v.known_as_of = f.at(9);return sql('cp7_models.compare_plan', v); }, 'CUTOFF_ORDER');
}
