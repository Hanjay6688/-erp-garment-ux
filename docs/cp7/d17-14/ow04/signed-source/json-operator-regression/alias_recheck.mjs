import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import fs from 'node:fs/promises';
import path from 'node:path';

const root = path.resolve(process.argv[2] ?? '.');
const file = 'scripts/cp7_customer_credit/reconciliation/04_source_binding.sql';
const beforeCommit = '99695e103f6ec3c604f38419e65722e08013c02c';
const before = execFileSync('git', ['show', `${beforeCommit}:${file}`], { cwd: root, encoding: 'utf8' });
const after = await fs.readFile(path.join(root, file), 'utf8');
const { PGlite } = await import(process.env.PGLITE_MODULE ?? '@electric-sql/pglite');
const db = new PGlite();
const tests = [];

function statement(source) {
  const functionBody = source.split('create function cp7_credit.assert_source_materialization_v1(')[1]?.split('end $$;')[0];
  assert.ok(functionBody);
  const matches = [...functionBody.matchAll(/select coalesce\(sum\([\s\S]*?into before_i\s+from[\s\S]*?;/g)];
  assert.equal(matches.length, 1);
  return matches[0][0];
}
function definition(name, source) {
  // Preserve the real statement and colliding variable name. Only its input
  // container and financial-row type are synthetic; no authority is simulated.
  return `create function ${name}(p_input jsonb) returns numeric language plpgsql as $$
    declare m record; f record; before_i numeric;
    begin select p_input before_ordinal_input into m;
    ${statement(source)} return before_i; end $$;`;
}
try {
  await db.exec(definition('before_alias', before));
  await db.exec(definition('after_alias', after));
  const input = amounts => ({ families: amounts.map(values => ({ retained_recognition: values.map(amount => ({ amount })) })) });
  let oldError;
  try { await db.query('select before_alias($1::jsonb)', [JSON.stringify(input([['200.00']]))]); }
  catch (error) { oldError = { code: error.code, message: error.message }; }
  assert.equal(oldError?.code, '42702');
  tests.push({ id: 'BEFORE_REPRODUCES_ACTUAL_ALIAS_COLLISION', status: 'PASS', observed_error: oldError });
  for (const [id, amounts, expected] of [
    ['NO_FAMILIES', [], '0'],
    ['EMPTY_RECOGNITION', [[]], '0'],
    ['INITIAL200', [['200.00']], '200.00'],
    ['RETAINED_INITIAL200_ADJ_MINUS50', [['200.00', '-50.00']], '150.00'],
    ['RETAINED_FULL_CANCELLATION', [['200.00', '-200.00']], '0.00'],
    ['MULTIPLE_FAMILIES', [['200.00', '-50.00'], ['100.00'], []], '250.00'],
    ['EXACT_LARGE_CANCELLATION', [['999999999999999999999999.99', '-999999999999999999999999.98']], '0.01'],
  ]) {
    const observed = (await db.query('select after_alias($1::jsonb)::text result', [JSON.stringify(input(amounts))])).rows[0].result;
    assert.equal(observed, expected, id);
    tests.push({ id, status: 'PASS', expected, observed });
  }
  process.stdout.write(JSON.stringify({
    classification: 'LOCAL_ACTUAL_PRODUCT_STATEMENT_IN_SYNTHETIC_PLPGSQL_CONTEXT_NOT_NATIVE_PROOF',
    version: (await db.query('select version() version')).rows[0].version,
    source: file, before_candidate: beforeCommit,
    tests, passed: tests.length, database_network_calls: 0, production_go: false,
  }, null, 2) + '\n');
} finally { await db.close(); }
