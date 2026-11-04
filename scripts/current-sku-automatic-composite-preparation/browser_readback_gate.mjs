// Recheck complete saved observations using the same retained physical oracle
// and independent current economic oracle. This never opens a browser or DB.
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {IDS, equalCensus, pairOnly, previewOracle, postedOracle, inverseOracle} from './browser_evidence.mjs';

export function check(actual) {
  assert.deepEqual(actual.planned_case_ids, IDS);
  assert.deepEqual(Object.keys(actual.cases).sort(), [...IDS].sort());
  for (const [index, name] of IDS.entries()) {
    const row = actual.cases[name], f = row.current_fixture;
    const steps = ['BEFORE_PAIR', 'PAIR_FIRST', 'PAIR_REVERSE_DUPLICATE', 'PAIR_DELETE_REVERSE_SIDE',
      'BEFORE_PREVIEW', 'AFTER_PREVIEW', ...(!index ? ['LOST_COMMITTED_REPLY', 'RECONCILED_SAME_UUID'] : []),
      'POSTED', 'ACTIVE_DRAFT_BEFORE_REFUSAL', 'ACTIVE_DRAFT_AFTER_REFUSAL', 'WHOLE_GROUP_REVERSED'];
    assert.deepEqual(row.current_observations.map(item => item.step), steps);
    const states = Object.fromEntries(row.current_observations.map(item => [item.step, item.state]));
    for (const state of Object.values(states)) {
      assert.deepEqual(state.current_session_leaks, {advisory_locks: 0, advisory_lock_keys: [], other_sessions: []});
    }
    const source = f.groups[0].id, target = f.groups[1].id;
    pairOnly(states.BEFORE_PAIR, states.PAIR_FIRST, source, target, 1);
    pairOnly(states.PAIR_FIRST, states.PAIR_REVERSE_DUPLICATE, source, target, 1);
    pairOnly(states.PAIR_REVERSE_DUPLICATE, states.PAIR_DELETE_REVERSE_SIDE, target, null, 1);
    equalCensus(states.BEFORE_PREVIEW.census, states.AFTER_PREVIEW.census);
    equalCensus(states.ACTIVE_DRAFT_BEFORE_REFUSAL.census, states.ACTIVE_DRAFT_AFTER_REFUSAL.census);
    previewOracle(row.actual_preview, f);
    postedOracle(states.POSTED, f, row.actual_post_result);
    if (!index) {
      postedOracle(states.LOST_COMMITTED_REPLY, f, row.actual_post_result);
      postedOracle(states.RECONCILED_SAME_UUID, f, row.actual_post_result);
      equalCensus(states.LOST_COMMITTED_REPLY.census, states.RECONCILED_SAME_UUID.census);
    }
    assert.deepEqual(states.ACTIVE_DRAFT_AFTER_REFUSAL.ledgers, states.ACTIVE_DRAFT_BEFORE_REFUSAL.ledgers);
    assert(states.ACTIVE_DRAFT_AFTER_REFUSAL.members.every(member => member.status === 'POSTED'));
    assert.equal(row.actual_refusal.status, 400);
    assert.equal(row.actual_refusal.body.code, 'P0001');
    assert.match(row.actual_refusal.body.message, /downstream/i);
    assert.deepEqual(new Set(row.actual_inverse_result.conversion_ids), new Set(row.actual_post_result.conversion_ids));
    inverseOracle(states.WHOLE_GROUP_REVERSED, f);
    assert.deepEqual(states.WHOLE_GROUP_REVERSED.pairs, []);
    assert.equal(states.WHOLE_GROUP_REVERSED.census.catalog_sha256, states.BEFORE_PAIR.census.catalog_sha256);
    assert.deepEqual(row.visible_text_contrast.map(item => item.state),
      ['PAIR_TWO_SIDES', 'FIFO_PREVIEW', 'ACTIVE_DRAFT_REFUSAL', 'WHOLE_GROUP_REVERSED']);
    for (const contrast of row.visible_text_contrast) {
      assert(contrast.rows.length > 0);
      assert(contrast.rows.every(item => Number.isFinite(item.ratio) && item.ratio >= 4.5));
    }
    const writes = row.write_requests;
    assert.equal(writes.filter(item => item.rpc === 'erp_save_sku_action_v1').length, 3);
    const posts = writes.filter(item => item.rpc === 'erp_save_product_conversion_action_v1' && item.args.p_action === 'POST');
    assert.equal(posts.length, index ? 1 : 2);
    if (!index) assert.deepEqual(posts[0].args, posts[1].args);
    assert.equal(writes.filter(item => item.rpc === 'erp_save_product_conversion_action_v1' && item.args.p_action === 'REVERSE').length, 2);
  }
  return {status: 'CURRENT_BROWSER2_COMPLETE_RECORDED_ORACLES_RECHECKED', cases: 2,
    actual_Auth_HTTP_case_credit: 0, actual_two_session_case_credit: 0};
}

if (process.argv[1] && import.meta.url === new URL('file://' + process.argv[1]).href) {
  console.log(JSON.stringify(check(JSON.parse(readFileSync(process.argv[2], 'utf8')))));
}
