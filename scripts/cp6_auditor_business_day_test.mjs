// The browser host's business-day guard (scripts/cp6_auditor_business_day.mjs) gives the same rows as the Python rule.
import assert from 'node:assert/strict'
import { execFileSync } from 'node:child_process'
import { dirname } from 'node:path'
import { fileURLToPath } from 'node:url'
import { WIB_DAY, guard } from './cp6_auditor_business_day.mjs'

const here = dirname(fileURLToPath(import.meta.url))
const vectors = [
  [{ status: 'PASS' }, '2026-10-09', '2026-10-09', '2026-10-09'],
  [{ status: 'PASS' }, '2026-10-09', '2026-10-10', '2026-10-10'],
  [{ status: 'PASS' }, '2026-10-09', '2026-10-09', '2026-10-10'],
  [{ status: 'PASS', error: null }, '2026-10-09', '2026-10-10', '2026-10-10'],
  [{ status: 'FAIL', error: 'ORIGINAL' }, '2026-10-09', '2026-10-10', '2026-10-10'],
  [{ status: 'COUNTEREXAMPLE' }, '2026-10-09', '2026-10-10', '2026-10-10'],
  [{ status: 'INCOMPLETE', error: "AssertionError [ERR_ASSERTION]: '2' !== '1'" }, '2026-10-09', '2026-10-10', '2026-10-10'],
]
const js = vectors.map(([row, ...days]) => { const r = { ...row }; const rolled = guard(r, ...days); return [rolled, r] })
const py = JSON.parse(execFileSync('python3', ['-c', `
import json,sys
import cp6_auditor_business_day as bd
out=[]
for row,*days in json.load(sys.stdin):
    r=dict(row);out.append([bd.guard(r,*days),r])
print(json.dumps(dict(rows=out,day=bd.WIB_DAY)))`], { cwd: here, input: JSON.stringify(vectors), encoding: 'utf8' }))
assert.deepEqual(js, py.rows)
assert.equal(WIB_DAY, py.day)
assert.deepEqual(js.map(([rolled, r]) => [rolled, r.status]), [[false, 'PASS'], [true, 'INCOMPLETE'], [true, 'INCOMPLETE'], [true, 'INCOMPLETE'],
  [true, 'FAIL'], [true, 'COUNTEREXAMPLE'], [true, 'INCOMPLETE']])
assert.equal(js[4][1].error, 'ORIGINAL')
const host = (await import('node:fs')).readFileSync(here + '/cp6_auditor_browser_host.mjs', 'utf8')
assert.match(host, /const dayBefore = sql\(WIB_DAY\)/)
assert.match(host, /businessDayGuard\(row, today, dayBefore, sql\(WIB_DAY\)\)\n    report\.cases\[id\] = /)
console.log(JSON.stringify({ business_day_guard_vectors: vectors.length, python_parity: true }))
