// Offline controls for the new browser driver, not real browser/ERP evidence.
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import {createRequire} from 'node:module'
import {dirname, resolve} from 'node:path'
import {fileURLToPath} from 'node:url'
import vm from 'node:vm'
import {IDS, displayed, cleanupSteps} from './browser.mjs'

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '../..')
const require = createRequire(resolve(process.env.S05_NODE_ROOT || ROOT, 'package.json'))
const React = require('react'), {renderToStaticMarkup} = require('react-dom/server')
const {transformSync} = require('esbuild'), {JSDOM, VirtualConsole} = require('jsdom')
function ts(path) {
  const code = transformSync(readFileSync(resolve(ROOT, path), 'utf8'), {loader: 'ts', format: 'cjs', target: 'es2022'}).code
  const module = {exports: {}}
  new Function('module', 'exports', code)(module, module.exports)
  return module.exports
}
const product = ts('src/accessoryStandardReport.ts'), dates = ts('src/cp6BusinessTime.ts')
const fixtures = ts('tests/fixtures/accessoryStandardReport.ts')
const values = [null, '0', '0.000000', '-0.000000', '7.500000', '-2.500000', '22.750000', '9007199254740993.000001']
for (const value of values) for (const money of [false, true]) assert.equal(displayed(value, money), product.accessoryReportNumber(value, money))
for (const value of ['NaN', '1e6', '1,000', '', 1, undefined]) assert.throws(() => displayed(value))

// The installed Playwright engine resolves the actual rendered product JSX.
const engineRoot = dirname(require.resolve('playwright-core/package.json'))
assert.equal(JSON.parse(readFileSync(resolve(engineRoot, 'package.json'))).version, '1.62.1')
const literal = readFileSync(resolve(engineRoot, 'lib/coreBundle.js'), 'utf8').match(/source4 = ('(?:\\.|[^'\\])*');/s)
assert.ok(literal)
const engine = vm.runInNewContext(literal[1])
const raw = readFileSync(resolve(ROOT, 'src/ConnectedAccessoryStandardReportPage.tsx'), 'utf8')
const qtyStart = raw.indexOf('const qty = '), reportStart = raw.indexOf('function Report({ report:')
assert.ok(qtyStart >= 0 && reportStart > qtyStart)
const code = transformSync(raw.slice(qtyStart, raw.indexOf('\n', qtyStart))+'\n'+raw.slice(reportStart), {loader: 'tsx', jsx: 'transform', target: 'es2022'}).code
const Report = new Function('React', 'number', 'accessoryReportReason', 'formatCp6WibDateTime', code+'\nreturn Report;')(
  React, product.accessoryReportNumber, product.accessoryReportReason, dates.formatCp6WibDateTime)
let reportControls = 0
for (const kind of ['ordinary', 'zero', 'unknown', 'negative']) {
  const {report, row} = fixtures.asrParts()
  if (kind === 'zero') Object.assign(row, {standard_qty: '0', standard_hpp_cost: '0.000000', standard_reimbursement: '0.000000'})
  if (kind === 'unknown') Object.assign(row, {standard_qty: null, delta_qty: null, standard_hpp_cost: null, standard_reimbursement: null})
  if (kind === 'negative') Object.assign(row, {delta_qty: '-2.500000'})
  const virtualConsole = new VirtualConsole()
  virtualConsole.on('jsdomError', e => assert.match(e.message, /Not implemented: window.getComputedStyle\(elt, pseudoElt\)/))
  const dom = new JSDOM(renderToStaticMarkup(React.createElement(Report, {report})), {runScripts: 'outside-only', virtualConsole})
  try {
    const w = dom.window; w.module = {exports: {}}; w.eval(engine)
    for (const details of w.document.querySelectorAll('details')) details.open = true
    const role = w.createRoleEngine(true), lookup = (scope, name, label) => role.queryAll(scope, name+'[name='+JSON.stringify(label)+'s]')
    const results = lookup(w.document, 'region', 'Hasil laporan aksesori'); assert.equal(results.length, 1)
    const tr = results[0].querySelector('tbody > tr')
    assert.equal(role.queryAll(tr, 'rowheader').length, 1)
    const qty = x => x === null ? 'Belum diketahui' : displayed(x)+' '+row.unit
    assert.deepEqual(Array.from(role.queryAll(tr, 'cell'), e => e.textContent), [qty(row.actual_qty), qty(row.standard_qty), qty(row.delta_qty),
      displayed(row.actual_inventory_cost, true), displayed(row.actual_receivable, true), displayed(row.standard_hpp_cost, true), displayed(row.standard_reimbursement, true)])
    const article = lookup(results[0], 'article', 'Sumber pengambilan '+report.actual_sources[0].issue_number)
    assert.equal(article.length, 1); assert.ok(article[0].textContent.includes(report.actual_sources[0].material_id))
    const snapshot = lookup(results[0], 'region', 'Snapshot standar '+report.standard_sources[0].id)
    assert.equal(snapshot.length, 1); assert.ok(snapshot[0].textContent.includes(report.standard_sources[0].bom_version_id))
    reportControls++
  } finally { dom.window.close() }
}

// A failed access reset must never prevent response-listener/context cleanup.
const calls = []
const errors = await cleanupSteps([
  () => calls.push('release'), () => { calls.push('reactivate'); throw new Error('actual-reset-failure') },
  async () => { calls.push('unlisten'); throw new Error('actual-listener-failure') }, () => calls.push('close'),
])
assert.deepEqual(calls, ['release', 'reactivate', 'unlisten', 'close'])
assert.deepEqual(errors, ['Error: actual-reset-failure', 'Error: actual-listener-failure'])
assert.equal(IDS.length, 2); assert.equal(new Set(IDS).size, 2)
console.log(JSON.stringify({status: 'OFFLINE_DRIVER_CONTROLS_PASS', decimal_values: values.length, rendered_product_states: reportControls,
  actual_Playwright_accessible_selector_engine: '1.62.1', cleanup_continues_after_two_errors: true,
  actual_browser_cases: 0, actual_Native_cases: 0, production_go: false, independent_acceptance: false}))
