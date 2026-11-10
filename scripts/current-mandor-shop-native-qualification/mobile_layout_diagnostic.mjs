// The real App shell and Payroll + Mandor card components, using synthetic read fixtures.
// No database, Auth service, transaction, qualification credit, or externally served page.
import assert from 'node:assert/strict'
import { execFileSync } from 'node:child_process'
import { mkdir, mkdtemp, readFile, rm, writeFile } from 'node:fs/promises'
import { createHash } from 'node:crypto'
import { dirname, extname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium, expect } from '@playwright/test'
import react from '@vitejs/plugin-react'
import { build } from 'vite'

const here = dirname(fileURLToPath(import.meta.url))
const root = resolve(here, '../..')
const sha256 = (bytes) => createHash('sha256').update(bytes).digest('hex')
const [fixturePath, receiptPath] = process.argv.slice(2)
assert.ok(fixturePath && receiptPath)
const fixtureBytes = await readFile(fixturePath)
assert.equal(sha256(fixtureBytes), '361e15e1d849999337aaa78c884203efbae95f619d57391ea089874450c3208a')
const input = JSON.parse(fixtureBytes)
assert.equal(input.contract, 'cp7.mandor-shop-access-fixture.v1')
assert.equal(input.same_GOOD_source_reused_without_policy_mutation, true)
const goodDay = new Date(input.physical.good_day + 'T00:00:00Z')
const monday = new Date(goodDay)
monday.setUTCDate(goodDay.getUTCDate() + 14 - ((goodDay.getUTCDay() + 6) % 7))
const sunday = new Date(monday)
sunday.setUTCDate(monday.getUTCDate() + 6)
const fixture = {
  payroll_number: input.payroll_number, sale_number: input.sale_number, physical: { sale_at: input.physical.sale_at },
  period_start: monday.toISOString().slice(0, 10), period_end: sunday.toISOString().slice(0, 10),
  payment_date: input.physical.good_day, contractor_name: 'Mandor pengujian',
}
const source = 'a0e7d5616a0ac470876409d31c41388159f17692'
const git = (...args) => execFileSync('git', ['-C', root, ...args], { encoding: 'utf8' }).trim()
assert.equal(git('rev-parse', source), source)
assert.equal(git('diff', '--name-only', source, '--', 'src', 'index.html', 'tests/fixtures', 'package.json', 'package-lock.json'), '')
const temp = await mkdtemp(join(root, '.mandor-mobile-layout-'))
const dist = join(temp, 'dist')
const result = { status: 'INCOMPLETE', source, head: git('rev-parse', 'HEAD'), fixture_sha256: sha256(fixtureBytes),
  method: 'NORMAL_APP_SYNTHETIC_READ_ONLY_LAYOUT', actual_auth: 0, actual_transactions: 0, qualification_credit: 0,
  observations: [], external_requests: [], page_errors: [] }
const styles = [...(await readFile(join(root, 'src/main.tsx'), 'utf8')).matchAll(/^import '(\.\/[^']+\.css)'/gm)]
const shim = {
  name: 'mandor-layout-fixture-bindings',
  enforce: 'pre',
  transform(code, id) {
    const name = {
      [join(root, 'src/auth/AuthProvider.tsx')]: 'useAuth',
      [join(root, 'src/lib/supabase.ts')]: 'getUatSupabaseClient',
    }[id]
    if (!name) return
    const signature = 'export function ' + name + '('
    assert.equal(code.split(signature).length, 2)
    return code.replace(signature, 'function original_' + name + '(') +
      '\nexport { ' + name + ' } from ' + JSON.stringify(join(here, 'mobile_layout_fixture.mjs')) + '\n'
  },
}

function measure(page, expectedWidth, state, settled = false) {
  return page.evaluate(async ({ expectedWidth, state, settled }) => {
    if (settled) {
      await document.fonts.ready
      await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))
    }
    const root = document.documentElement
    const outside = [...document.querySelectorAll('body *')].flatMap(element => {
      const rect = element.getBoundingClientRect()
      const style = getComputedStyle(element)
      if (!rect.width || rect.right <= expectedWidth || style.visibility === 'hidden') return []
      return [{ tag: element.localName, classes: [...element.classList].join(' '),
        parent: element.parentElement?.className?.toString(),
        left: rect.left, right: rect.right, width: rect.width,
        scrollWidth: element.scrollWidth, overflowX: style.overflowX,
        whiteSpace: style.whiteSpace, minWidth: style.minWidth }]
    }).sort((a, b) => b.right - a.right).slice(0, 12)
    return { expectedWidth, state, settled, innerWidth, clientWidth: root.clientWidth, scrollWidth: root.scrollWidth,
      visualWidth: visualViewport.width, visualScale: visualViewport.scale, outside }
  }, { expectedWidth, state, settled })
}

let browser
try {
  const index = await readFile(join(root, 'index.html'), 'utf8')
  assert.ok(index.includes('/src/main.tsx'))
  await writeFile(join(temp, 'index.html'), index.replace('/src/main.tsx', '/entry.jsx'))
  await writeFile(join(temp, 'entry.jsx'), [
    "import React from 'react'", "import { createRoot } from 'react-dom/client'", "import App from '../src/App'",
    ...styles.map(match => 'import ' + JSON.stringify('../src/' + match[1].slice(2))),
    "createRoot(document.getElementById('root')).render(<React.StrictMode><App /></React.StrictMode>)",
  ].join('\n'))
  await build({ configFile: false, root: temp, envDir: false, plugins: [shim, react()],
    build: { outDir: dist, target: 'es2020' } })
  browser = await chromium.launch()
  result.chromium = browser.version()
  const context = await browser.newContext({ viewport: { width: 390, height: 844 },
    timezoneId: 'America/Los_Angeles', isMobile: true, hasTouch: true, serviceWorkers: 'block' })
  const origin = 'http://127.0.0.1:54099'
  const types = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css',
    '.svg': 'image/svg+xml', '.woff2': 'font/woff2', '.png': 'image/png' }
  await context.route('**/*', async route => {
    const { origin: target, pathname } = new URL(route.request().url())
    if (target !== origin || route.request().method() !== 'GET') {
      result.external_requests.push({ origin: target, method: route.request().method() })
      return route.abort()
    }
    const path = resolve(dist, '.' + (pathname === '/' ? '/index.html' : decodeURIComponent(pathname)))
    assert.ok(path.startsWith(dist + '/'))
    try {
      const body = await readFile(path)
      await route.fulfill({ contentType: types[extname(path)] ?? 'application/octet-stream', body })
    } catch (error) {
      if (error.code !== 'ENOENT') throw error
      await route.fulfill({ status: 404, body: '' })
    }
  })
  await context.addInitScript(value => { globalThis.__mandorMobileLayoutFixture = value }, fixture)
  const page = await context.newPage()
  page.on('pageerror', error => result.page_errors.push(String(error)))
  await page.goto(origin)
  await page.getByRole('button', { name: 'Buka menu', exact: true }).click()
  const payroll = page.getByRole('button', { name: '• Payroll & Kasbon', exact: true })
  if (!(await payroll.isVisible())) await page.locator('.sidebar .nav-main').filter({ hasText: 'Keuangan' }).click()
  await payroll.click()
  await page.getByLabel('Cari payroll', { exact: true }).fill(fixture.payroll_number)
  await page.getByRole('button', { name: 'Cari payroll', exact: true }).click()
  await page.locator('button.cproc-receipt').filter({ hasText: fixture.payroll_number }).click()

  const launch = page.getByRole('region', { name: 'Tagihan belanja mandor', exact: true })
    .getByRole('button', { name: 'Pasang tagihan belanja', exact: true })
  await expect(launch).toBeEnabled()
  await page.setViewportSize({ width: 320, height: 844 })
  result.observations.push(await measure(page, 320, 'PAYROLL_BEFORE_DIALOG', true))
  await page.setViewportSize({ width: 390, height: 844 })
  await launch.click()
  const dialog = page.getByRole('dialog', { name: 'Pasang tagihan belanja', exact: true })
  await expect(dialog.getByRole('article', { name: 'Nota ' + fixture.sale_number, exact: true })).toBeVisible()
  for (const width of [390, 320, 768, 390]) {
    await page.setViewportSize({ width, height: 844 })
    result.observations.push(await measure(page, width, 'DIALOG_AFTER_RESIZE'))
    result.observations.push(await measure(page, width, 'DIALOG_AFTER_RESIZE', true))
  }
  result.fixture_reads = await page.evaluate(() => globalThis.__mandorMobileLayoutRequests)
  assert.ok(result.fixture_reads.includes('erp_cp7_get_mandor_shop_payroll_v1'))
  assert.ok(result.fixture_reads.every(name => /^erp_cp7_get_/.test(name)))
  assert.deepEqual(result.external_requests, [])
  assert.deepEqual(result.page_errors, [])
  result.failed_observations = result.observations.filter(row => row.innerWidth !== row.expectedWidth || row.scrollWidth > row.expectedWidth)
  result.status = result.failed_observations.length ? 'LAYOUT_FAILURE_REPRODUCED' : 'LAYOUT_FAILURE_NOT_REPRODUCED'
} catch (error) {
  result.error = error.stack || String(error)
  process.exitCode = 1
} finally {
  await browser?.close()
  await rm(temp, { recursive: true, force: true })
  await mkdir(dirname(resolve(receiptPath)), { recursive: true })
  await writeFile(receiptPath, JSON.stringify(result, null, 2) + '\n', { flag: 'wx' })
  console.log(JSON.stringify(result))
}
