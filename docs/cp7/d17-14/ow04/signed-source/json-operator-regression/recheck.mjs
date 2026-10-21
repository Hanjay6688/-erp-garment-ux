import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import fs from 'node:fs/promises';
import path from 'node:path';

// Execute the actual source expressions; a PL/pgSQL CREATE alone does not
// prepare these expressions. This is local PostgreSQL 18, not Native 17 proof.
const root = path.resolve(process.argv[2] ?? '.');
const file = 'scripts/cp7_customer_credit/reconciliation/03_native_inverse_proof.sql';
const beforeCommit = '8ed949bb4c0ebaacae5cf83653174799936374f4';
const before = execFileSync('git', ['show', `${beforeCommit}:${file}`], { cwd: root, encoding: 'utf8' });
const after = await fs.readFile(path.join(root, file), 'utf8');
const { PGlite } = await import(process.env.PGLITE_MODULE ?? '@electric-sql/pglite');
const db = new PGlite();
const results = [];
const sale = { id: 'sale-fixture', customer_id: 'customer-A', status: 'PAID', row_version: 7, updated_at: '2026-10-21T00:00:00Z' };

function expression(source, left, right) {
  const operand = name => `\\(?${name}->'sale'\\)?-array\\['status','row_version','updated_at'\\]`;
  const matches = [...source.matchAll(new RegExp(`${operand(left)}is distinct from\\s*${operand(right)}`, 'g'))];
  assert.equal(matches.length, 1, `exactly one product predicate for ${left}/${right}`);
  return matches[0][0];
}

try {
  const version = (await db.query('select version() version')).rows[0].version;
  for (const [left, right] of [['p_before', 'p_actual'], ['p_native', 'p_final']]) {
    const query = expr => `with snapshots as (select $1::jsonb ${left}, $2::jsonb ${right}) select ${expr} changed from snapshots`;
    const a = { sale };
    let oldError;
    try { await db.query(query(expression(before, left, right)), [JSON.stringify(a), JSON.stringify(a)]); }
    catch (error) { oldError = { code: error.code, message: error.message }; }
    assert.equal(oldError?.code, '22P02', 'original candidate must reproduce the actual failure');
    results.push({ id: `${left}_BEFORE_REPRODUCES_22P02`, status: 'PASS', observed_error: oldError });

    const missingCustomer = { ...sale }; delete missingCustomer.customer_id;
    const vectors = [
      ['IDENTICAL', { ...sale }, false],
      ['ONLY_NATIVE_HEADER_FIELDS_CHANGED', { ...sale, status: 'PARTIAL', row_version: 8, updated_at: '2026-10-21T00:01:00Z' }, false],
      ['IMMUTABLE_CUSTOMER_CHANGED', { ...sale, customer_id: 'customer-B' }, true],
      ['IMMUTABLE_CUSTOMER_REMOVED', missingCustomer, true],
      ['UNEXPECTED_IMMUTABLE_FIELD_ADDED', { ...sale, unexpected_field: 'extra' }, true],
    ];
    for (const [id, actual, expected] of vectors) {
      const observed = (await db.query(query(expression(after, left, right)), [JSON.stringify(a), JSON.stringify({ sale: actual })])).rows[0].changed;
      assert.equal(observed, expected, id);
      results.push({ id: `${left}_${id}`, status: 'PASS', expected_changed: expected, observed_changed: observed });
    }
  }
  process.stdout.write(JSON.stringify({
    classification: 'LOCAL_ACTUAL_PRODUCT_SQL_EXPRESSION_EXECUTION_NOT_NATIVE_LIFECYCLE_PROOF',
    version, source: file, before_candidate: beforeCommit,
    tests: results, passed: results.length, database_network_calls: 0, production_go: false,
  }, null, 2) + '\n');
} finally { await db.close(); }
