// R2-09 (Sol SOL-R1-004/005; best practice D17): every menu of a static build, opened on a 390 px phone, must satisfy
// document.documentElement.scrollWidth <= window.innerWidth. Usage: node scripts/ui_phone_width_census.mjs <build-dir> [report.json]
// Serves the build itself (no backend: demo build), walks the sidebar the way a user does, and exits 1 on any overflow.
// R4-04 (Astra ASTRA-R3-03): on the same walk every visible text must keep at least 2:1 contrast with the background it is
// painted on (the measure of scripts/cp7_r4_readable_browser.mjs); a text below that also exits 1.
import { chromium } from 'playwright'
import { createServer } from 'node:http'
import { mkdir, readdir, readFile, writeFile } from 'node:fs/promises'
import { dirname, extname, join } from 'node:path'
import { measure as readable } from './cp7_r4_readable_browser.mjs'
const [root, report = 'ui-phone-width.json'] = process.argv.slice(2)
if (!root) throw new Error('usage: ui_phone_width_census.mjs <build-dir> [report.json]')
const types = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.svg': 'image/svg+xml', '.png': 'image/png', '.woff2': 'font/woff2', '.json': 'application/json' }
// The build is read into memory first and served by exact path only, so a request path never reaches the file system.
const files = new Map()
const walk = async (dir, prefix) => { for (const e of await readdir(dir, { withFileTypes: true })) { const key = `${prefix}/${e.name}`; if (e.isDirectory()) await walk(join(dir, e.name), key); else if (e.isFile()) files.set(key, await readFile(join(dir, e.name))) } }
await walk(root, '')
const index = files.get('/index.html')
if (!index) throw new Error(`no index.html in ${root}`)
const server = createServer((req, res) => {
  let key = ''
  try { key = decodeURIComponent(new URL(req.url, 'http://census.local').pathname) } catch { key = '' }
  const body = files.get(key)
  if (body) { res.writeHead(200, { 'content-type': types[extname(key)] || 'application/octet-stream' }); res.end(body) }
  else { res.writeHead(200, { 'content-type': 'text/html' }); res.end(index) }
})
await new Promise(resolve => server.listen(0, '127.0.0.1', resolve))
const url = `http://127.0.0.1:${server.address().port}/`
const browser = await chromium.launch(process.env.CHROMIUM_PATH ? { executablePath: process.env.CHROMIUM_PATH } : {})
const page = await browser.newPage({ viewport: { width: 390, height: 844 } })
const openMenu = async () => { if (await page.locator('.sidebar.sidebar-open').count()) return; const open = page.getByRole('button', { name: 'Buka menu', exact: true }); if (await open.isVisible()) await open.click() }
const measure = async () => ({ ...(await width()), unreadable: (await page.evaluate(readable, { selector: '.main-panel *' })).rows.filter(r => r.ratio < 2) })
const width = () => page.evaluate(() => ({ scrollWidth: document.documentElement.scrollWidth, innerWidth: window.innerWidth,
  widest: [...document.querySelectorAll('body *')].filter(e => { const r = e.getBoundingClientRect(), p = e.parentElement.getBoundingClientRect(); return r.right > innerWidth + 1 && p.right <= innerWidth + 1 })
    .slice(0, 3).map(e => `${e.tagName.toLowerCase()}.${String(e.className).trim().split(/\s+/)[0]} right=${Math.round(e.getBoundingClientRect().right)}`) }))
await page.goto(url); await page.waitForLoadState('networkidle')
const rows = [{ menu: 'Dashboard', ...(await measure()) }]
await openMenu()
const sections = await page.locator('.sidebar .nav-section > button.nav-main').allInnerTexts()
for (const raw of sections) {
  const section = raw.replace(/[›⌄]/g, '').trim()
  await openMenu(); await page.locator('.sidebar .nav-section > button.nav-main').filter({ hasText: section }).first().click()
  const items = await page.locator('.sidebar .submenu > button').allInnerTexts()
  for (const item of items) {
    await openMenu()
    const sub = page.locator('.sidebar .submenu > button').filter({ hasText: item.trim() })
    if (!await sub.first().isVisible()) await page.locator('.sidebar .nav-section > button.nav-main').filter({ hasText: section }).first().click()
    await sub.first().click(); await page.waitForTimeout(400)
    rows.push({ menu: `${section} › ${item.replace(/^•\s*/, '').trim()}`, ...(await measure()) })
  }
}
const failed = rows.filter(r => r.scrollWidth > r.innerWidth), unreadable = rows.filter(r => r.unreadable.length)
await mkdir(dirname(report), { recursive: true })
await writeFile(report, JSON.stringify({ viewport: '390x844', rule: 'scrollWidth <= innerWidth; every text at least 2:1 contrast', menus: rows.length, failed: failed.length, unreadable: unreadable.length, rows }, null, 1) + '\n')
console.log(JSON.stringify({ menus: rows.length, failed: failed.map(r => [r.menu, r.scrollWidth, r.widest]), unreadable: unreadable.map(r => [r.menu, r.unreadable.slice(0, 3)]) }))
await browser.close(); server.close()
process.exit(failed.length || unreadable.length ? 1 : 0)
