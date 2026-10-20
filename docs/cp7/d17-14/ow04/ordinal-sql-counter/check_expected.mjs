#!/usr/bin/env node
// Existing pure kernel only; no new SQL function/protocol or Native admission.
import { readFile, writeFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import assert from 'node:assert/strict';
const here = dirname(fileURLToPath(import.meta.url));
const modulePath = process.env.OW04_PGLITE_MODULE ?? '@electric-sql/pglite';
const { PGlite } = await import(modulePath);
const expectedText = await readFile(resolve(here, 'EXPECTED.json'), 'utf8');
const expected = JSON.parse(expectedText);
const receipt = JSON.parse(await readFile(resolve(here, 'EXPECTED_RECEIPT.json'), 'utf8'));
const sql = await readFile(resolve(here, '../pure-kernel/kernel.sql'), 'utf8');
const hash = x => createHash('sha256').update(x).digest('hex');
assert.equal(hash(expectedText), receipt.sha256);
const cents = text => {
  const negative = text.startsWith('-');
  const [a, b = ''] = text.replace(/^[+-]/, '').split('.');
  const v = BigInt(a) * 100n + BigInt(b.padEnd(2, '0'));
  return negative ? -v : v;
};
const money = x => `${x < 0n ? '-' : ''}${(x < 0n ? -x : x) / 100n}.${((x < 0n ? -x : x) % 100n).toString().padStart(2, '0')}`;
const sum = xs => xs.reduce((a, b) => a + b, 0n);
const component = x => ({ amount: x.amount, economic_date: x.economic_date, transaction_date: x.transaction_date });
const prefix = (xs, e, b) => sum(xs.filter(x => x.economic_date <= e && x.transaction_date <= b).map(x => cents(x.amount)));
function difference(target, actual) {
  const pairs = new Map();
  for (const [events, sign] of [[target, 1n], [actual, -1n]]) for (const x of events) {
    const key = `${x.economic_date}|${x.transaction_date}`;
    pairs.set(key, (pairs.get(key) ?? 0n) + sign * cents(x.amount));
  }
  return [...pairs].sort(([a], [b]) => a < b ? -1 : a > b ? 1 : 0).filter(([, a]) => a !== 0n).map(([key, a]) => {
    const [economic_date, transaction_date] = key.split('|');
    return { amount: money(a), economic_date, transaction_date };
  });
}
function movements(events, role, family) {
  return events.map((x, i) => ({ ...component(x), id: `${family}:${role}:${i}`, source_sha256: hash(JSON.stringify(component(x))) }));
}
const results = [];
let db;
let active = 'load_kernel';
try {
  db = new PGlite();
  await db.exec(sql);
  async function plan(before, added) {
    return (await db.query('SELECT ow04_pure_kernel.recognition_plan_v1($1::jsonb,$2::jsonb) AS value', [JSON.stringify(before), JSON.stringify(added)])).rows[0].value;
  }
  async function capacity(components, consumptions, e, b, family) {
    return (await db.query('SELECT ow04_pure_kernel.credit_capacity_v1($1::jsonb,$2::jsonb,$3,$4) AS value', [JSON.stringify(movements(components, 'recognition', family)), JSON.stringify(movements(consumptions, 'consumption', family)), e, b])).rows[0].value;
  }
  for (const fixture of expected.fixtures) {
    active = fixture.name;
    if (fixture.source_pairs) {
      // Source-expression counter only. It does not call a product date resolver.
      const candidate = [fixture.current_resolver_result, fixture.source_pairs.sale_active_leaf[1]].sort().at(-1);
      const withRoots = [candidate, fixture.source_pairs.sale_root[1], fixture.source_pairs.return_family_root[1]].sort().at(-1);
      assert.equal(candidate, fixture.candidate_current_leaf_only_date);
      assert.equal(withRoots, fixture.expected_return_transaction_date);
      assert.equal(candidate === withRoots, fixture.expected_current_leaf_only_supported);
      results.push({ name: active, classification: 'STATIC_DATE_EXPRESSION_COUNTER_MATCHES_LITERAL', candidate_book_date: candidate, expected_root_bound_book_date: withRoots });
      continue;
    }
    const families = [...fixture.families_before].sort((a, b) => a.ordinal - b.ordinal);
    assert.equal(new Set(families.map(x => x.ordinal)).size, families.length);
    const baseAfter = [...fixture.base_before, ...fixture.source_added];
    const baseline = await plan([], baseAfter);
    assert.deepEqual(baseline.components, [], 'F(noReturns) is not zero');
    let prior = baseAfter;
    const targets = {};
    const adjustments = {};
    const currentFaces = {};
    const currentAvailable = {};
    const prefixFlags = {};
    let familyPositive;
    for (const family of families) {
      const eDates = [...new Set(family.events.map(x => x.economic_date))].sort();
      const bDates = [...new Set(family.events.map(x => x.transaction_date))].sort();
      for (const e of eDates) for (const b of bDates) if (prefix(family.events, e, b) > 0n) familyPositive ??= { family: family.root_return_id, economic_date: e, transaction_date: b, net: money(prefix(family.events, e, b)) };
      const target = await plan(prior, family.events);
      targets[family.root_return_id] = target.components.map(component);
      currentFaces[family.root_return_id] = target.net_current_k;
      if (fixture.retained_components) adjustments[family.root_return_id] = difference(targets[family.root_return_id], fixture.retained_components[family.root_return_id]);
      if (fixture.expected_has_recognition_effect?.[family.root_return_id] !== undefined) assert.equal(target.has_recognition_effect, fixture.expected_has_recognition_effect[family.root_return_id]);
      const consume = fixture.consumptions?.[family.root_return_id] ?? [];
      const minimumDate = [...target.components.map(x => x.economic_date), ...consume.map(x => x.economic_date), ...baseAfter.map(x => x.economic_date)].sort()[0];
      const state = await capacity(targets[family.root_return_id], consume, minimumDate, minimumDate, family.root_return_id);
      currentAvailable[family.root_return_id] = state.current_balance;
      prefixFlags[family.root_return_id] = state.source_prefixes_nonnegative;
      prior = [...prior, ...family.events];
    }
    if (fixture.expected_source_admission === 'REFUSE') {
      assert(familyPositive, 'Noncausal family did not expose its positive NET prefix');
      const bad = fixture.expected_disallowed_target_prefix;
      assert.equal(money(prefix(targets[bad.cohort], bad.economic_date, bad.transaction_date)), bad.amount);
      assert.equal(prefixFlags[bad.cohort], false);
      results.push({ name: active, classification: 'EXPECTED_SOURCE_ADMISSION_REFUSAL', positive_family_prefix: familyPositive, disallowed_target_prefix: bad, raw_kernel_targets: targets });
      continue;
    }
    assert.equal(familyPositive, undefined, 'Family cumulative NET became positive');
    assert.deepEqual(targets, fixture.expected_targets);
    if (fixture.expected_adjustments) assert.deepEqual(adjustments, fixture.expected_adjustments);
    assert.deepEqual(currentFaces, fixture.expected_current_faces);
    if (fixture.expected_current_available) assert.deepEqual(currentAvailable, fixture.expected_current_available);
    if (fixture.expected_global_current_available) assert.equal(money(sum(Object.values(currentAvailable).map(cents))), fixture.expected_global_current_available);
    const capacityResults = [];
    for (const control of fixture.capacity_controls ?? []) {
      const state = await capacity(targets[control.cohort], fixture.consumptions?.[control.cohort] ?? [], ...control.proposed_pair, control.cohort);
      for (const field of ['minimum_available', 'requested_pair_balance', 'current_balance', 'source_prefixes_nonnegative']) if (control[field] !== undefined) assert.equal(state[field], control[field]);
      if (control.economic_margin !== undefined) assert.equal(money(sum(targets[control.cohort].filter(x => x.economic_date <= control.proposed_pair[0]).map(x => cents(x.amount)))), control.economic_margin);
      if (control.book_margin !== undefined) assert.equal(money(sum(targets[control.cohort].filter(x => x.transaction_date <= control.proposed_pair[1]).map(x => cents(x.amount)))), control.book_margin);
      for (const n of ['1', '150']) if (control[`positive_consumption_${n}_supported`] !== undefined) assert.equal(state.source_prefixes_nonnegative && cents(state.minimum_available) >= BigInt(n) * 100n, control[`positive_consumption_${n}_supported`]);
      capacityResults.push(state);
    }
    if (fixture.expected_mutation_supported !== undefined) assert.equal(Object.values(prefixFlags).every(Boolean), fixture.expected_mutation_supported);
    // Original face, registration, mode and account are immutable owning facts;
    // this arithmetic test cannot create them or authorize a settlement choice.
    results.push({ name: active, classification: 'PURE_TARGET_ADJUSTMENT_AND_CAPACITY_MATCH_LITERAL', targets, adjustments, current_faces: currentFaces, current_available: currentAvailable, cohort_prefixes_nonnegative: prefixFlags, capacity_results: capacityResults, source_admission_and_account_authority_implemented: false });
  }
  const report = { classification: 'ISOLATED_ORDINAL_EXPECTATION_RECHECK_EXISTING_KERNEL', native_executed: false, product_modified: false, new_sql_api_added: false, expected_sha256: hash(expectedText), kernel_sql_sha256: hash(sql), results };
  await writeFile(resolve(here, 'RESULT.json'), `${JSON.stringify(report, null, 2)}\n`);
  console.log(JSON.stringify({ status: 'PASS', fixtures: results.length, expected_sha256: report.expected_sha256, native_executed: false, new_sql_api_added: false }));
} catch (error) {
  const failure = { case: active, message: error.message, stack: error.stack, expected_sha256: hash(expectedText), kernel_sql_sha256: hash(sql) };
  try { await writeFile(resolve(here, 'FIRST_FAILURE.json'), `${JSON.stringify(failure, null, 2)}\n`, { flag: 'wx' }); } catch (writeError) { if (writeError.code !== 'EEXIST') throw writeError; }
  console.error(JSON.stringify(failure, null, 2));
  process.exitCode = 1;
} finally { if (db) await db.close(); }
