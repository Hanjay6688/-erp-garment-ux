// Fable r3 screen census for owner D16-1 (oracles 1 and 2 in audit/fable_cp17_r2/OWNER_DECISION_TO_AUDITOR_20261016_UNHIDE.md).
// Same capture function as the dfab13bf/r2 census (fable_cp17c_screens.mjs). Menu list = 47 menus after D16-5 ("Tutup
// Periode" merged into "Laporan & Tutup Buku" as the tab "Tutup Buku"). Run once per build: AUDITOR_UI_MODE=DISPOSABLE or
// ENTENG (FABLE_UI_MODE in the Fable workflow). Oracles, fixed before the run:
//  * OWNER desktop 1440 px: every menu opens; no page says SIMULASI / DATA CONTOH / contoh; no "belum tersambung" boundary;
//    no horizontal overflow. Any menu failing one of these -> COUNTEREXAMPLE (INCOMPLETE only when it could not be opened
//    for a tool reason, recorded with the error).
//  * OWNER phone 390 px: same, every menu.
//  * Restricted role (GUDANG): every menu in its sidebar opens with the same three checks; no finance menu in its sidebar.
//  * Laporan & Tutup Buku shows a "Tutup Buku" tab for OWNER.
import { MENUS as OLD, capture } from './fable_cp17c_screens.mjs'
export const MENUS = OLD.filter(([, item]) => item !== 'Tutup Periode')

async function open(page, group, item) {
  const burger = page.getByRole('button', { name: 'Buka menu', exact: true })
  if (await burger.isVisible().catch(() => false)) await burger.click()
  if (!group) { await page.locator('.nav-main').filter({ hasText: item }).first().click(); return }
  const link = page.getByRole('button', { name: `• ${item}`, exact: true })
  if (!await link.isVisible().catch(() => false)) await page.locator('.nav-main').filter({ hasText: group }).first().click()
  await link.click({ timeout: 15000 })
}

async function boundaryText(page) {
  return page.evaluate(() => /belum tersambung/i.test((document.querySelector('.page-wrap') || document.body).innerText || ''))
}

async function census(page, menus, mobile) {
  const out = {}
  for (const [group, item] of menus) {
    try {
      await open(page, group, item)
      const c = await capture(page)
      c.boundary = await boundaryText(page)
      if (mobile) await page.keyboard.press('Escape').catch(() => {})
      out[item] = { opened: true, ...c }
    } catch (e) { out[item] = { opened: false, error: String(e).slice(0, 300) } }
  }
  return out
}

function verdict(menus) {
  const bad = Object.entries(menus).filter(([, v]) => v.opened && (v.sample_label || v.boundary || v.overflow)).map(([k, v]) =>
    ({ menu: k, sample_label: v.sample_label, boundary: v.boundary, overflow: v.overflow }))
  const notOpened = Object.entries(menus).filter(([, v]) => !v.opened).map(([k, v]) => ({ menu: k, error: v.error }))
  return { status: bad.length ? 'COUNTEREXAMPLE' : (notOpened.length ? 'INCOMPLETE' : 'PASS'), violations: bad, not_opened: notOpened }
}

export function cases(ui, today) {
  const mode = (process.env.AUDITOR_UI_MODE || 'DISPOSABLE').toUpperCase()
  const owner = (mobile) => async () => {
    const user = await ui.login('OWNER', { label: 'fable-r3-owner-' + (mobile ? 'phone' : 'desk'), mobile })
    try {
      await user.page.locator('.nav-main, .mobile-menu').first().waitFor({ state: 'attached', timeout: 60000 })
      const menus = await census(user.page, MENUS, mobile)
      return { ui_mode: mode, viewport: mobile ? 390 : 1440, ...verdict(menus), menus }
    } finally { await user.context.close() }
  }
  const gudang = async () => {
    const user = await ui.login('GUDANG', { label: 'fable-r3-gudang' }), p = user.page
    try {
      await p.locator('.nav-main').first().waitFor({ state: 'attached', timeout: 60000 })
      const sections = await p.locator('.sidebar .nav-main').allInnerTexts()
      const visible = []
      for (const [group, item] of MENUS) {
        if (group && !sections.some(s => s.includes(group))) continue
        if (!group) { visible.push([group, item]); continue }
        await p.locator('.sidebar .nav-main').filter({ hasText: group }).first().click().catch(() => {})
        if (await p.getByRole('button', { name: `• ${item}`, exact: true }).isVisible().catch(() => false)) visible.push([group, item])
      }
      const menus = await census(p, visible, false)
      const finance = sections.some(s => /Keuangan/.test(s))
      const v = verdict(menus)
      return { ui_mode: mode, role: 'GUDANG', ...v, status: finance ? 'COUNTEREXAMPLE' : v.status, finance_section_visible: finance,
        sections, menus_visible: visible.map(([, i]) => i), menus }
    } finally { await user.context.close() }
  }
  const closeTab = async () => {
    const user = await ui.login('OWNER', { label: 'fable-r3-tutup-buku' }), p = user.page
    try {
      await p.locator('.nav-main').first().waitFor({ state: 'attached', timeout: 60000 })
      await open(p, 'Keuangan', 'Laporan & Tutup Buku')
      await p.waitForTimeout(1500)
      const tab = await p.getByRole('tab', { name: /Tutup Buku/ }).count() + await p.getByRole('button', { name: /^Tutup Buku$/ }).count()
      return { ui_mode: mode, status: tab > 0 ? 'PASS' : 'COUNTEREXAMPLE', tutup_buku_controls: tab }
    } finally { await user.context.close() }
  }
  return [
    [`FABLE_R3_SCREENS_${mode}:OWNER_DESKTOP_1440`, owner(false)],
    [`FABLE_R3_SCREENS_${mode}:OWNER_PHONE_390`, owner(true)],
    [`FABLE_R3_SCREENS_${mode}:GUDANG_DESKTOP`, gudang],
    [`FABLE_R3_SCREENS_${mode}:TUTUP_BUKU_TAB`, closeTab],
  ]
}
