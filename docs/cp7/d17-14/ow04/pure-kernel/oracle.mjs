#!/usr/bin/env node
// ISOLATED PGlite arithmetic evidence. No ERP schema, Native call, or admission.
import { readFile, writeFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import assert from 'node:assert/strict';

const directory = dirname(fileURLToPath(import.meta.url));
const pgliteModule = process.env.OW04_PGLITE_MODULE
  ?? '@electric-sql/pglite';
const { PGlite } = await import(pgliteModule);
const sql = await readFile(resolve(directory, 'kernel.sql'), 'utf8');
const expectedText = await readFile(resolve(directory, 'EXPECTED.json'), 'utf8');
const expected = JSON.parse(expectedText);
const expectedReceipt = JSON.parse(await readFile(resolve(directory, 'EXPECTED_RECEIPT.json'), 'utf8'));
const sha256 = value => createHash('sha256').update(value).digest('hex');
assert.equal(sha256(expectedText), expectedReceipt.sha256, 'Expected literals changed after their receipt');

const cents = value => {
  assert.equal(typeof value, 'string');
  assert.match(value, /^[+-]?(0|[1-9][0-9]*)(\.[0-9]{1,2})?$/);
  const negative = value[0] === '-';
  const clean = value.replace(/^[+-]/, '');
  const [whole, fraction = ''] = clean.split('.');
  const n = BigInt(whole) * 100n + BigInt(fraction.padEnd(2, '0'));
  return negative ? -n : n;
};
const money = n => `${n < 0n ? '-' : ''}${(n < 0n ? -n : n) / 100n}.${((n < 0n ? -n : n) % 100n).toString().padStart(2, '0')}`;
const uniqueSorted = values => [...new Set(values)].sort();
const sum = values => values.reduce((a, b) => a + b, 0n);
const sourcePrefix = (events, e, b, kind) => sum(events.filter(x => x.kind === kind && x.economic_date <= e && x.transaction_date <= b).map(x => cents(x.amount)));
const overflow = (events, e, b) => {
  const funding = sourcePrefix(events, e, b, 'FUNDING');
  const net = sourcePrefix(events, e, b, 'NET');
  assert(net >= 0n && funding >= 0n, 'Independent raw source prefix is invalid');
  return funding > net ? funding - net : 0n;
};
const partialComponent = x => ({ amount: x.amount, economic_date: x.economic_date, transaction_date: x.transaction_date });
const dateForAxis = axis => axis === 'economic' ? 'economic_date' : 'transaction_date';
const results = [];
let db;
let activeCase = 'load_kernel';

async function queryOne(query, parameters) {
  return (await db.query(query, parameters)).rows[0].value;
}

async function plan(before, added) {
  return queryOne('SELECT ow04_pure_kernel.recognition_plan_v1($1::jsonb, $2::jsonb) AS value', [JSON.stringify(before), JSON.stringify(added)]);
}

async function capacity(fixture) {
  return queryOne('SELECT ow04_pure_kernel.credit_capacity_v1($1::jsonb, $2::jsonb, $3::text, $4::text) AS value', [JSON.stringify(fixture.components), JSON.stringify(fixture.consumptions), fixture.economic_date, fixture.transaction_date]);
}

async function expectError(name, run, message) {
  let caught;
  try { await run(); } catch (error) { caught = error; }
  assert(caught, `${name} unexpectedly succeeded`);
  assert.equal(caught.message, message, `${name}: wrong refusal`);
  assert.equal(caught.code, '22023', `${name}: wrong SQLSTATE`);
  return { name, status: 'EXPECTED_REFUSAL', reason: caught.message, sqlstate: caught.code };
}

async function checkHash(vector, observed) {
  const canonical = await queryOne('SELECT $1::jsonb::text AS value', [JSON.stringify(vector)]);
  assert.equal(observed, sha256(canonical), 'Canonical normalized vector digest mismatch');
}

function checkFullGrid(fixture, observed) {
  const before = fixture.before;
  const after = [...before, ...fixture.added];
  const economics = uniqueSorted(after.map(x => x.economic_date));
  const books = uniqueSorted(after.map(x => x.transaction_date));
  const d = (e, b) => e === null || b === null ? 0n : overflow(after, e, b) - overflow(before, e, b);
  const reconstructed = (e, b) => sum(observed.components.filter(x => x.economic_date <= e && x.transaction_date <= b).map(x => cents(x.amount)));
  for (const e of economics) {
    for (const b of books) assert.equal(reconstructed(e, b), d(e, b), `Signed components do not reconstruct D(${e},${b})`);
  }
  for (const component of observed.components) {
    assert(component.transaction_date >= component.economic_date);
    assert.match(component.amount, /^-?(0|[1-9][0-9]*)\.[0-9]{2}$/);
    assert.notEqual(cents(component.amount), 0n);
    const ei = economics.indexOf(component.economic_date);
    const bi = books.indexOf(component.transaction_date);
    assert(ei >= 0 && bi >= 0);
    const previousE = ei === 0 ? null : economics[ei - 1];
    const previousB = bi === 0 ? null : books[bi - 1];
    assert.equal(component.previous_economic_date, previousE);
    assert.equal(component.previous_transaction_date, previousB);
    assert.deepEqual(component.corners, {
      d_here: money(d(component.economic_date, component.transaction_date)),
      d_prev_economic: money(d(previousE, component.transaction_date)),
      d_prev_transaction: money(d(component.economic_date, previousB)),
      d_prev_both: money(d(previousE, previousB)),
    });
    const c = component.corners;
    assert.equal(cents(component.amount), cents(c.d_here) - cents(c.d_prev_economic) - cents(c.d_prev_transaction) + cents(c.d_prev_both));
  }
  const current = economics.length ? d(economics.at(-1), books.at(-1)) : 0n;
  assert.equal(cents(observed.net_current_k), current);
  assert.equal(sum(observed.components.map(x => cents(x.amount))), current);
  assert.equal(observed.has_recognition_effect, observed.components.length > 0);
  // Independent economic/book margins, with the other axis fully visible.
  for (const axis of ['economic_date', 'transaction_date']) {
    const dates = axis === 'economic_date' ? economics : books;
    for (const day of dates) {
      const margin = sum(observed.components.filter(x => x[axis] <= day).map(x => cents(x.amount)));
      const e = axis === 'economic_date' ? day : economics.at(-1);
      const b = axis === 'transaction_date' ? day : books.at(-1);
      assert.equal(margin, d(e, b));
    }
  }
  for (const axis of ['economic', 'book']) {
    const field = dateForAxis(axis);
    for (const [day, want] of Object.entries(fixture.profiles?.[axis] ?? {})) {
      const raw = sum(after.filter(x => x[field] <= day).map(x => cents(x.amount) * (x.kind === 'NET' ? 1n : -1n)));
      const issue = sum(observed.components.filter(x => x[field] <= day).map(x => cents(x.amount)));
      assert.deepEqual({ AR: money(raw + issue), issued_credit: money(issue) }, want);
    }
  }
}

function checkCapacityGrid(fixture, observed) {
  const movements = [...fixture.components.map(x => ({ ...x, signed: cents(x.amount) })), ...fixture.consumptions.map(x => ({ ...x, signed: -cents(x.amount) }))];
  const economics = uniqueSorted([...movements.map(x => x.economic_date), fixture.economic_date]);
  const books = uniqueSorted([...movements.map(x => x.transaction_date), fixture.transaction_date]);
  const balance = (e, b) => sum(movements.filter(x => x.economic_date <= e && x.transaction_date <= b).map(x => x.signed));
  const later = economics.flatMap(e => books.map(b => ({ e, b, balance: balance(e, b) }))).filter(x => x.e >= fixture.economic_date && x.b >= fixture.transaction_date);
  const minimum = later.reduce((m, x) => x.balance < m ? x.balance : m, later[0].balance);
  assert.equal(cents(observed.minimum_available), minimum);
  assert.equal(cents(observed.current_balance), sum(movements.map(x => x.signed)));
  assert.equal(cents(observed.requested_pair_balance), balance(fixture.economic_date, fixture.transaction_date));
  assert.equal(observed.source_prefixes_nonnegative, economics.every(e => books.every(b => balance(e, b) >= 0n)));
  assert.deepEqual(observed.limiting_pairs, later.filter(x => x.balance === minimum).map(x => ({ economic_date: x.e, transaction_date: x.b })));
}

try {
  db = new PGlite();
  await db.exec(sql);
  for (const fixture of expected.planning_fixtures) {
    activeCase = `plan:${fixture.name}`;
    if (fixture.expected_error) {
      results.push(await expectError(fixture.name, () => plan(fixture.before, fixture.added), fixture.expected_error));
      continue;
    }
    const observed = await plan(fixture.before, fixture.added);
    assert.equal(observed.contract_version, 'ow04.pure-recognition-plan.v1');
    assert.equal(observed.kernel_version, 'ow04-2d-difference-v1');
    assert.deepEqual(observed.components.map(partialComponent), fixture.expected_components);
    assert.equal(observed.net_current_k, fixture.expected_net_current_k);
    assert.equal(observed.has_recognition_effect, fixture.expected_has_recognition_effect);
    checkFullGrid(fixture, observed);
    assert.deepEqual(observed.support, [...fixture.before, ...fixture.added].sort((a, b) => a.id < b.id ? -1 : a.id > b.id ? 1 : 0).map(x => ({ id: x.id, source_sha256: x.source_sha256 })));
    assert.deepEqual(observed.before_events, fixture.before.map(x => ({ ...x, amount: money(cents(x.amount)) })).sort((a, b) => a.id < b.id ? -1 : a.id > b.id ? 1 : 0));
    assert.deepEqual(observed.added_events, fixture.added.map(x => ({ ...x, amount: money(cents(x.amount)) })).sort((a, b) => a.id < b.id ? -1 : a.id > b.id ? 1 : 0));
    await checkHash(observed.before_events, observed.before_source_sha256);
    await checkHash([...observed.before_events, ...observed.added_events].sort((a, b) => a.id < b.id ? -1 : a.id > b.id ? 1 : 0), observed.after_source_sha256);
    assert.deepEqual(await plan([...fixture.before].reverse(), [...fixture.added].reverse()), observed, 'Source input order changed canonical plan');
    results.push({ name: fixture.name, status: 'MATCHES_LITERAL_EXPECTED_AND_RAW_PREFIX_ORACLE', components: observed.components, net_current_k: observed.net_current_k, has_recognition_effect: observed.has_recognition_effect });
  }
  for (const fixture of expected.capacity_fixtures) {
    activeCase = `capacity:${fixture.name}`;
    const observed = await capacity(fixture);
    assert.equal(observed.contract_version, 'ow04.pure-credit-capacity.v1');
    assert.equal(observed.kernel_version, 'ow04-2d-difference-v1');
    assert.deepEqual(Object.fromEntries(Object.keys(fixture.expected).map(k => [k, observed[k]])), fixture.expected);
    checkCapacityGrid(fixture, observed);
    results.push({ name: fixture.name, status: 'MATCHES_LITERAL_EXPECTED_AND_ORTHANT_ORACLE', observed });
  }
  const baseEvent = { id: 'sale', kind: 'NET', amount: '1000', economic_date: '2026-10-18', transaction_date: '2026-10-18', source_sha256: 'a'.repeat(64) };
  for (const fixture of expected.invalid_input_fixtures) {
    activeCase = `invalid:${fixture.name}`;
    let before = [{ ...baseEvent }];
    let added = [];
    if (fixture.mutate) before[0][fixture.mutate.field] = fixture.mutate.value;
    if (fixture.operation === 'duplicate_before') before.push({ ...baseEvent });
    if (fixture.operation === 'duplicate_added') added.push({ ...baseEvent });
    if (fixture.operation === 'before_object') before = {};
    if (fixture.operation === 'added_null') added = null;
    results.push(await expectError(fixture.name, () => plan(before, added), fixture.expected_error));
  }
  activeCase = 'normalization_hash_dependency_and_immutability_controls';
  const canonical = await plan([baseEvent], []);
  assert.equal(canonical.before_events[0].amount, '1000.00');
  const plus = await plan([{ ...baseEvent, amount: '+1000.0' }], []);
  assert.deepEqual(plus, canonical, 'Equivalent exact-cent spelling was not canonicalized');
  const changedHash = await plan([{ ...baseEvent, source_sha256: 'b'.repeat(64) }], []);
  assert.deepEqual(changedHash.components, canonical.components);
  assert.notEqual(changedHash.before_source_sha256, canonical.before_source_sha256, 'Full support source digest did not affect vector hash');
  const changedReturn = await plan([{ ...baseEvent }, { ...baseEvent, id: 'oldReturn', amount: '-100' }], []);
  assert.notEqual(changedReturn.before_source_sha256, canonical.before_source_sha256, 'Earlier return dependency omitted from full source hash');
  const zero = await plan([{ ...baseEvent, amount: '-0.00' }], []);
  assert.equal(zero.before_events[0].amount, '0.00');
  const huge = '1000000000000000000000000.01';
  const exactHuge = await plan([{ ...baseEvent, amount: huge }, { ...baseEvent, id: 'funding', kind: 'FUNDING', amount: huge }], [{ ...baseEvent, id: 'ret', amount: '-0.01', economic_date: '2026-10-19', transaction_date: '2026-10-19' }]);
  assert.equal(exactHuge.net_current_k, '0.01', 'Money passed through floating point');
  await db.exec("SET DateStyle = 'SQL, DMY'; SET TimeZone = 'Pacific/Honolulu';");
  assert.deepEqual(await plan([baseEvent], []), canonical, 'Session date/zone changed immutable result');
  await db.exec("SET DateStyle = 'ISO, MDY'; SET TimeZone = 'UTC';");
  const audit = (await db.query("SELECT p.proname, p.provolatile, p.prosecdef FROM pg_catalog.pg_proc p JOIN pg_catalog.pg_namespace n ON n.oid = p.pronamespace WHERE n.nspname = 'ow04_pure_kernel' ORDER BY p.proname")).rows;
  assert.equal(audit.length, 6);
  assert(audit.every(x => x.provolatile === 'i' && x.prosecdef === false), 'Kernel helper is not immutable invoker');
  results.push({ name: activeCase, status: 'PASS', audited_functions: audit, arbitrary_precision_cent_control: exactHuge.net_current_k });
  activeCase = 'capacity_input_controls';
  const capBase = { ...baseEvent };
  delete capBase.kind;
  results.push(await expectError('duplicate_movement_across_roles', () => capacity({ components: [capBase], consumptions: [capBase], economic_date: '2026-10-19', transaction_date: '2026-10-19' }), 'DUPLICATE_EVENT_ID'));
  results.push(await expectError('capacity_fractional_cent', () => capacity({ components: [{ ...capBase, amount: '1.001' }], consumptions: [], economic_date: '2026-10-19', transaction_date: '2026-10-19' }), 'EXACT_CENTS_REQUIRED'));
  results.push(await expectError('capacity_pair_book_before_economic', () => capacity({ components: [], consumptions: [], economic_date: '2026-10-20', transaction_date: '2026-10-19' }), 'BOOK_BEFORE_ECONOMIC'));
  results.push(await expectError('capacity_invalid_requested_date', () => capacity({ components: [], consumptions: [], economic_date: '2026-02-30', transaction_date: '2026-10-19' }), 'CANONICAL_DATE_REQUIRED'));
  const report = {
    classification: 'ISOLATED_PGLITE_PURE_ARITHMETIC_PROPOSAL',
    source_candidate: expected.source_candidate,
    native_executed: false, authoritative_source_collector_implemented: false,
    product_schema_modified: false, product_installer_provided: false,
    pglite_module: pgliteModule,
    postgresql_version: await queryOne('SELECT version() AS value'),
    expected_sha256: sha256(expectedText), sql_sha256: sha256(sql), driver_sha256: sha256(await readFile(fileURLToPath(import.meta.url))),
    counts: { planning: expected.planning_fixtures.length, capacity: expected.capacity_fixtures.length, invalid_inputs: expected.invalid_input_fixtures.length, total: results.length },
    results,
  };
  await writeFile(resolve(directory, 'RESULT.json'), `${JSON.stringify(report, null, 2)}\n`);
  console.log(JSON.stringify({ status: 'PASS', ...report.counts, sql_sha256: report.sql_sha256, expected_sha256: report.expected_sha256, native_executed: false }));
} catch (error) {
  const failure = { classification: 'ISOLATED_PGLITE_FIRST_FAILURE', case: activeCase, message: error.message, code: error.code, stack: error.stack, sql_sha256: sha256(sql), expected_sha256: sha256(expectedText) };
  try { await writeFile(resolve(directory, 'FIRST_FAILURE.json'), `${JSON.stringify(failure, null, 2)}\n`, { flag: 'wx' }); } catch (writeError) { if (writeError.code !== 'EEXIST') throw writeError; }
  console.error(JSON.stringify(failure, null, 2));
  process.exitCode = 1;
} finally {
  if (db) await db.close();
}
