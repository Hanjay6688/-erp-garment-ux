// Sample for the browser mode of the auditor runtime (scripts/cp6_auditor_browser_host.mjs): the writer's smoke check that
// the mode works. The auditor supplies their own module through the workflow input browser_b64.
export async function cases(ui, today) {
  return [
    ['SAMPLE_BROWSER:LOGIN_PAGE_WITHOUT_SESSION', async () => {
      const { page, context } = await ui.anonPage()
      await ui.expect(page.getByLabel('Email akun ERP')).toBeVisible()
      await ui.expect(page.getByLabel('Kata sandi')).toBeVisible()
      await context.close()
      return { status: 'PASS' }
    }],
    ['SAMPLE_BROWSER:OWNER_SIGNS_IN_GUDANG_REFUSED_PREFLIGHT', async () => {
      const owner = await ui.login('OWNER', { label: 'owner' })
      const title = await owner.page.locator('.top-title strong').innerText()
      const store = await ui.login('GUDANG', { label: 'gudang', mobile: true })
      const args = { p_through: String(today) }
      const a = await owner.rpc('erp_accounting_close_preflight_v1', args)
      const b = await store.rpc('erp_accounting_close_preflight_v1', args)
      await owner.context.close(); await store.context.close()
      const ok = a.status === 200 && a.body && typeof a.body === 'object' && 'status' in a.body && b.status >= 400
      return { status: ok ? 'PASS' : 'FAIL', owner_title_seen: Boolean(title), owner: { status: a.status, readiness: a.body?.status },
        gudang: { status: b.status, message: b.body?.message } }
    }],
  ]
}
