import { createHash, randomUUID } from 'node:crypto'
import { existsSync, mkdirSync, readFileSync, readdirSync, rmSync, writeFileSync, copyFileSync } from 'node:fs'
import { dirname, relative, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { spawnSync } from 'node:child_process'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '../../../../..')
const preview = 'tests/cp7/browser/planner/f05-preview'
const owned = [preview, 'tests/cp7/browser/ai-v1/preview', 'tests/cp7/families/reports/preview', 'tests/cp7/families/reminder/preview']
const analyzer = ['scripts/cp7-src/models', 'tests/cp7/families/models/yield']
const args = process.argv.slice(2)
if (args.includes('--help')) {
  console.log('Usage: node tests/cp7/browser/planner/f05-preview/verify-f05.mjs [--browser]\nFast: TypeScript, F05 unit tests, preview build and secret scan. --browser adds desktop/mobile stories. No install, deployment, hosted data or external delivery.')
  process.exit(0)
}
if (args.some(arg => arg !== '--browser')) throw new Error('Unknown option; use --help.')
const browser = args.includes('--browser')
const output = resolve(root, 'test-results/f05-continuation')
mkdirSync(output, { recursive: true })
const hash = path => createHash('sha256').update(readFileSync(path)).digest('hex')
const filesUnder = path => readdirSync(path, { withFileTypes: true }).flatMap(entry => entry.isDirectory() ? filesUnder(resolve(path, entry.name)) : entry.isFile() && /\.(?:tsx?|mjs|css|html|json|sql)$/.test(entry.name) ? [resolve(path, entry.name)] : [])
const dependencies = ['package.json', 'package-lock.json', 'tsconfig.app.json', 'tsconfig.json', 'src/vite-env.d.ts', 'src/config/runtime.ts', 'src/cp7/workspace.ts', 'src/cp7/contract.ts', 'src/cp7/fixture.ts', 'src/cp7/reasons.json', 'docs/cp7/contracts/analysis.example.json', 'scripts/build-preflight.mjs', 'scripts/scan-client-artifacts.mjs']
const sourcePaths = [...new Set([...owned.concat(analyzer).flatMap(path => filesUnder(resolve(root, path))), ...dependencies.concat('tests/cp7/families/models/yield.test.ts').map(path => resolve(root, path))])].sort()
const sourceHashes = () => Object.fromEntries(sourcePaths.map(path => [relative(root, path).replaceAll('\\', '/'), hash(path)]))
const before = sourceHashes()
const git = (...args) => spawnSync('git', args, { cwd: root, encoding: 'utf8' })
const head = git('rev-parse', 'HEAD')
const dirty = git('status', '--porcelain', '--untracked-files=no')
const receipt = { version: 'f05.continuation-checks.v1', run_id: randomUUID(), started_at: new Date().toISOString(), git_head: head.status === 0 ? head.stdout.trim() : null, tracked_changes: dirty.status === 0 ? dirty.stdout.trim() !== '' : null, source_sha256: before, browser_requested: browser, status: 'RUNNING', stages: [] }
const unitFile = resolve(output, 'unit-results.json')
const browserFile = resolve(root, 'test-results/f05-browser/results.json')
rmSync(unitFile, { force: true })
rmSync(resolve(output, 'browser-results.json'), { force: true })
if (browser) rmSync(browserFile, { force: true })
const steps = [
  ['f04_yield_kernel', ['tests/cp7/families/models/yield/run.mjs']],
  ['typescript', ['node_modules/typescript/bin/tsc', '-p', `${preview}/tsconfig.json`]],
  ['unit', ['node_modules/vitest/vitest.mjs', 'run', ...owned, '--reporter=default', '--reporter=json', `--outputFile=${unitFile}`]],
  ['preview_build', ['node_modules/vite/bin/vite.js', 'build', '--config', `${preview}/vite.config.mjs`]],
  ['preview_secret_scan', ['scripts/scan-client-artifacts.mjs', 'f05-preview-build']],
  ...(browser ? [['browser', ['node_modules/@playwright/test/cli.js', 'test', '--config', `${preview}/playwright.config.mjs`]]] : []),
]
let failed = false
try {
  for (const [name, command] of steps) {
    if (failed) { receipt.stages.push({ name, status: 'NOT_RUN' }); continue }
    console.log(`\nF05: ${name}`)
    const startedAt = new Date().toISOString()
    const environment={...process.env,CI:'1'}
    // Local WASM proof is labelled explicitly; native CI can never use it.
    if(name==='f04_yield_kernel' && process.env.F04_YIELD_PGLITE_MODULE && !process.env.CI)delete environment.CI
    if(name==='f04_yield_kernel')environment.F04_YIELD_RECEIPT_PATH=resolve(output,'yield-kernel.json')
    const result = spawnSync(process.execPath, command, { cwd: root, stdio: 'inherit', env: environment })
    failed = result.status !== 0 || Boolean(result.error)
    receipt.stages.push({ name, status: failed ? 'FAIL' : 'PASS', exit_code: result.status, signal: result.signal, started_at: startedAt, completed_at: new Date().toISOString(), ...(result.error ? { error: result.error.message } : {}) })
    if(name==='f04_yield_kernel' && !failed) {
      const kernel=JSON.parse(readFileSync(resolve(output,'yield-kernel.json'),'utf8'))
      receipt.yield_kernel={passed:kernel.passed,failures:kernel.failures,runtime:kernel.runtime,version:kernel.version}
      if(kernel.failures.length || kernel.passed<40)throw new Error('Yield kernel proof failed or incomplete.')
    }
    if (name === 'unit' && !failed) {
      const unit = JSON.parse(readFileSync(unitFile, 'utf8'))
      receipt.unit = Object.fromEntries(['numTotalTests', 'numPassedTests', 'numFailedTests', 'success'].map(key => [key, unit[key]]))
      if (!unit.success || unit.numFailedTests || unit.numTotalTests === 0) throw new Error('Unit receipt is incomplete or failed.')
    }
    if (name === 'browser' && !failed) {
      if (!existsSync(browserFile)) throw new Error('Fresh browser receipt missing.')
      const result = JSON.parse(readFileSync(browserFile, 'utf8'))
      receipt.browser = result.stats
      if (!result.stats.expected || result.stats.unexpected || result.stats.flaky || result.stats.skipped) throw new Error('Browser receipt is incomplete or failed.')
      copyFileSync(browserFile, resolve(output, 'browser-results.json'))
    }
  }
  if (JSON.stringify(before) !== JSON.stringify(sourceHashes())) throw new Error('Source changed during verification; rerun on a stable tree.')
} catch (error) {
  failed = true; receipt.error = error.message
} finally {
  for (const [name] of steps) if (!receipt.stages.some(stage => stage.name === name)) receipt.stages.push({ name, status: 'NOT_RUN' })
  receipt.status = failed ? 'FAIL' : 'PASS'; receipt.completed_at = new Date().toISOString()
  writeFileSync(resolve(output, 'checks.json'), `${JSON.stringify(receipt, null, 2)}\n`)
  console.log(`\nF05 ${receipt.status}: test-results/f05-continuation/checks.json`)
}
process.exitCode = failed ? 1 : 0
