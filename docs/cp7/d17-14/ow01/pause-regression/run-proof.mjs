#!/usr/bin/env node
// Exact old-source causal control + actual candidate; synthetic module proof only.
import assert from 'node:assert/strict'
import { readFile, writeFile, mkdir } from 'node:fs/promises'
import { spawnSync, execFileSync } from 'node:child_process'
import { dirname, resolve, join } from 'node:path'
import { fileURLToPath } from 'node:url'
const args = process.argv.slice(2)
const option = (key, fallback) => args.includes(key) ? args[args.indexOf(key) + 1] : fallback
const repo = resolve(option('--repo', process.cwd()))
const base = option('--baseline', '6efdcd787e07355e7ae68d53244a88fb905ad7f8')
const here = dirname(fileURLToPath(import.meta.url))
const output = resolve(option('--out', join(here, `run-${new Date().toISOString().replace(/[:.]/g, '-')}`)))
await mkdir(output, { recursive: false }) // A prior result is never overwritten.
const baselinePath = join(output, 'source-baseline.sql')
const candidatePath = join(output, 'source-candidate.sql')
await writeFile(baselinePath, execFileSync('git', ['show', `${base}:scripts/cp7-src/alerts/alerts.sql`], { cwd: repo }))
await writeFile(candidatePath, await readFile(join(repo, 'scripts/cp7-src/alerts/alerts.sql')))
const run = async (name, source, extra = []) => {
  const jsonPath = join(output, `${name}.json`)
  const result = spawnSync(process.execPath, [join(here, 'pause-regression.mjs'), '--source', source, '--output', jsonPath, ...extra],
    { cwd: repo, env: process.env, encoding: 'utf8' })
  await writeFile(join(output, `${name}.stdout.log`), result.stdout ?? '')
  await writeFile(join(output, `${name}.stderr.log`), result.stderr ?? '')
  let report = null
  try { report = JSON.parse(await readFile(jsonPath, 'utf8')) } catch {}
  return { exit: result.status, report, json_path: jsonPath }
}
const old = await run('baseline-first-result', baselinePath, ['--first-retention-only'])
const candidate = await run('candidate-result', candidatePath)
let status = 'PASS', error
try {
  assert.equal(old.exit, 1)
  assert.equal(old.report?.status, 'FAIL')
  assert.equal(old.report?.first_failure?.case, 'FIRST_RETENTION_WA_OFF_THEN_EXPLICIT_ENABLE_SAME_ROUND_ZERO')
  assert.equal(old.report?.cases[0]?.observed?.paused?.state, 'DISABLED')
  assert.equal(candidate.exit, 0)
  assert.equal(candidate.report?.status, 'PASS')
  assert.equal(candidate.report?.cases?.length, 6)
  assert.ok(candidate.report.cases.every(c => c.status === 'PASS'))
} catch (failure) { status = 'FAIL';error = failure.message;process.exitCode = 1 }
const summary = { classification: 'SYNTHETIC_PGLITE_ACTUAL_SQL_MODULE_SELECTION_ONLY', status, error,
  baseline_commit: base, repo, output, baseline_expected_first_retention_failure: old,
  candidate, Native: false, real_Auth_or_ACL: false, concurrency: false, provider_delivery: false }
await writeFile(join(output, 'summary.json'), JSON.stringify(summary, null, 2) + '\n')
console.log(JSON.stringify({ status, baseline_expected_failure: old.report?.first_failure?.case,
  candidate_cases: candidate.report?.cases?.length, summary: join(output, 'summary.json'), Native: false }))
