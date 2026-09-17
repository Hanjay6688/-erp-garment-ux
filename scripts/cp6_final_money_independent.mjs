// Independent arithmetic expectations; imports the admitted product unchanged.
import assert from 'node:assert/strict'
import fs from 'node:fs'
import crypto from 'node:crypto'
import { parseBsMoney } from '../src/bsResolutionModel.ts'

const cases = [
  ['zero', '0', 0], ['cent-comma', '0,01', .01], ['cent-dot', '0.01', .01],
  ['quarter', '0,25', .25], ['claim-comma', '14,25', 14.25],
  ['claim-dot', '14.25', 14.25], ['single-decimal', '14,2', 14.2],
  ['spaces', ' 14,25 ', 14.25], ['leading-zero', '00014.25', 14.25],
  ['ceiling', '999999999', 999999999], ['below-ceiling', '999999998,99', 999999998.99],
  ...['', ' ', '-1', '+1', '1e2', 'Infinity', 'NaN', '14,250', '14.251',
    '14,25.00', '14.25,00', 'Rp14,25', '1.000,25', '1,000.25', '1 000',
    '999999999.01', '14.', ',25', '1\n2'].map((s, i) => ['reject-' + i, s, null]),
]
const results = cases.map(([id, input, expected]) => {
  const actual = parseBsMoney(input)
  assert.equal(actual, expected, id)
  return { id, input, expected, actual, status: 'PASS' }
})
for (const [id, input, cap, expected] of [
  ['exact-cent-cap', '0,25', .25, .25], ['over-cent-cap', '0.26', .25, null],
  ['exact-claim-cap', '14,25', 14.25, 14.25], ['over-claim-cap', '14,26', 14.25, null],
]) {
  const actual = parseBsMoney(input, cap)
  assert.equal(actual, expected, id)
  results.push({ id, input, cap, expected, actual, status: 'PASS' })
}
const report = {
  status: 'PASS_REVIEWED_SCOPE', scope: 'PARSE_ONLY_NOT_HTTP_OR_UI',
  product_sha256: crypto.createHash('sha256').update(fs.readFileSync('src/bsResolutionModel.ts')).digest('hex'),
  planned: results.length, completed: results.length, cases: results, production_go: false,
}
if (process.argv[2]) fs.writeFileSync(process.argv[2], JSON.stringify(report, null, 2) + '\n')
console.log(JSON.stringify({ status: report.status, scope: report.scope, completed: results.length }))
