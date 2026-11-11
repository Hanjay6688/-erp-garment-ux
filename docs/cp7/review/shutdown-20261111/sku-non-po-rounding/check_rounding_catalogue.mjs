import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';

const hash = text => createHash('sha256').update(text).digest('hex');

async function catalogueRow(db, signature) {
  const { rows: [row] } = await db.query(`
    select pg_get_functiondef(p.oid) as body,
      to_jsonb(p) - 'prosrc' - 'prosqlbody' as metadata
    from pg_proc p where p.oid = $1::regprocedure`, [signature]);
  return row;
}

async function checkArithmetic(db, creditDefinition) {
  const marker = 'round(fg,2)::numeric fg,';
  assert.equal(creditDefinition.split(marker).length, 2);
  const expression = creditDefinition.split(marker)[1].split('::numeric cogs from raw_values')[0];
  assert.match(expression, /^\(case when p_po is null then /);
  const cases = [
    ['non-PO odd cent', null, '73.01', '36.505', '36.505', ['36.51', '36.50', '0.00']],
    ['non-PO even cents', null, '73.02', '36.510', '36.510', ['36.51', '36.51', '0.00']],
    ['non-PO genuine residual', null, '75.01', '36.505', '36.505', ['36.51', '36.50', '2.00']],
    ['non-PO negative raw COGS', null, '36.51', '36.505', '-0.005', ['36.51', '0.00', '0.00']],
    ['non-PO no FG', null, '73.01', '0', '73.010', ['0.00', '73.01', '0.00']],
    ['non-PO large numeric', null, '100000000000000.01', '99999999999999.995', '0.015',
      ['100000000000000.00', '0.01', '0.00']],
    ['PO original cent rule', '00000000-0000-0000-0000-000000000001', '73.01', '36.505', '36.505',
      ['36.51', '36.51', '-0.01']],
  ];
  const result = [];
  for (const [id, po, hpp, fg, cogs, expected] of cases) {
    const { rows: [row] } = await db.query(`
      with raw as (select $1::uuid p_po, $2::numeric hpp, $3::numeric fg, $4::numeric cogs),
      cents as (select hpp, round(fg,2) fg, ${expression} cogs from raw)
      select fg::text, cogs::text, (hpp - fg - cogs)::text as other from cents`, [po, hpp, fg, cogs]);
    const actual = [row.fg, row.cogs, row.other];
    assert.deepEqual(actual, expected, id);
    result.push({ id, status: 'PASS', expected, actual });
  }
  return result;
}

export async function checkRoundingCatalogue(db, input) {
  const checked = {};
  const replacements = input.probe_variant.source.source.replacements;
  for (const [signature, pins] of Object.entries(replacements)) {
    await db.exec(input.rounding_originals[signature]);
    const before = await catalogueRow(db, signature);
    assert.equal(hash(before.body), pins.before_sha256);
    await db.exec(input.candidate_money_definitions[signature]);
    const after = await catalogueRow(db, signature);
    assert.equal(hash(after.body), pins.after_sha256);
    assert.deepEqual(after.metadata, before.metadata, signature + ' authority and catalogue attributes');
    checked[signature] = { before_sha256: hash(before.body), after_sha256: hash(after.body), metadata_equal: true };
  }
  db.report.rounding_catalogue = checked;
  db.report.rounding_arithmetic = await checkArithmetic(
    db, input.candidate_money_definitions['cp7_credit.initial_hpp_targets_v1(uuid,uuid,jsonb,boolean)']);
}
