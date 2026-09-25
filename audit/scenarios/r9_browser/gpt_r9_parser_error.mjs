// Real Auth/browser/PostgREST; deliberately inherited invalid UUID seed is input evidence.
// W11 oracle: a server-answered parser error is described as invalid data,
// whereas an aborted unanswered request is described as unreachable.
async function navigate(page, label) {
  const target = page.locator('.sidebar .submenu button').filter({ hasText: label })
  if (await target.isVisible()) { await target.click(); return }
  const groups = page.locator('.sidebar .nav-main')
  for (let i = 0; i < await groups.count(); i++) {
    await groups.nth(i).click()
    if (await target.isVisible()) { await target.click(); return }
  }
  throw new Error('NAV_TARGET_MISSING:' + label)
}

async function parserVsNetwork(ui) {
  const client = await ui.login('OWNER', { label: 'gpt-r9-parser-vs-network' })
  const { page } = client
  const observed = { auth_role: 'OWNER', source: 'inherited disposable cp3 seed; no production data altered' }
  const rpc = '**/rpc/erp_get_laundry_qc_workspace_v1'
  try {
    const control = await client.rpc('erp_get_laundry_qc_workspace_v1', { p_scope: 'LAUNDRY', p_query: null })
    const body = JSON.stringify(control.body)
    observed.control_http_status = control.status
    observed.bad_source_ids_present = body.includes('a1000000-0000-0000-0000-000000000001')
      || body.includes('a2000000-0000-0000-0000-000000000001')
    if (control.status !== 200 || !observed.bad_source_ids_present) {
      return { status: 'INCOMPLETE', stage: 'INVALID_UUID_SEED_CONTROL', ...observed }
    }

    let aborts = 0
    const abort = async route => {
      if (route.request().method() === 'POST'
          && route.request().postDataJSON()?.p_scope === 'LAUNDRY') {
        aborts++
        await route.abort('failed')
      } else await route.continue()
    }
    await page.route(rpc, abort)
    await navigate(page, 'Laundry')
    const error = page.locator('.clq-alert.error')
    await ui.expect(error).toBeVisible()
    const unreachable = await error.innerText()
    observed.aborted_requests = aborts
    observed.unanswered_message = unreachable
    if (aborts < 1) return { status: 'INCOMPLETE', stage: 'UNANSWERED_FAULT_NOT_TRIGGERED', ...observed }
    await page.unroute(rpc, abort)

    const reply = page.waitForResponse(response => response.url().endsWith('/rpc/erp_get_laundry_qc_workspace_v1')
      && response.request().method() === 'POST'
      && response.request().postDataJSON()?.p_scope === 'LAUNDRY')
    await page.getByRole('button', { name: 'Muat ulang data', exact: true }).click()
    const refetch = await reply
    observed.answered_http_status = refetch.status()
    await ui.expect(error).toBeVisible()
    await page.waitForTimeout(250)
    const answered = await error.innerText()
    observed.answered_message = answered
    if (refetch.status() !== 200) return { status: 'INCOMPLETE', stage: 'ANSWERED_REFETCH_CONTROL', ...observed }
    const correct = /Layanan UAT belum dapat dihubungi/i.test(unreachable)
      && /ID Mandor bukan UUID valid\./i.test(answered)
      && !/Layanan UAT belum dapat dihubungi/i.test(answered)
    return { status: correct ? 'PASS' : 'COUNTEREXAMPLE', ...observed,
      oracle: 'M:3825 unknown/error must not appear as confirmed zero; W11 keeps answered parser refusal distinct from transport failure. Input seed is deliberately malformed.' }
  } catch (error) {
    return { status: 'INCOMPLETE', ...observed, error: String(error.stack || error).slice(0, 2800) }
  } finally {
    await client.context.close()
  }
}

export async function cases(ui, today) {
  return [['G9UI:W11:PARSER_ERROR_VS_NETWORK', () => parserVsNetwork(ui)]]
}
