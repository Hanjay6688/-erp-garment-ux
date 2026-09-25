// GPT BC follow-up: legacy UUID read path. Disposable clone only; no hosted reads.
// The failure condition is drawn from M:5304 and M:5311-5313, not writer status.
export async function cases(ui, today) {
  return [['GBC-2:POSTGRES_UUID_OLD_MANDOR_PAGE_READ', async () => {
    const ids = ui.sql("select coalesce(string_agg(id::text, ',' order by id),'') from erp.contractors where contractor_type='MANDOR' and is_active and id::text !~* '^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'")
    const oldIds = ids ? ids.split(',') : []
    if (!oldIds.length) return { status: 'INCOMPLETE', reason: 'NO_OLD_UUID_FIXTURE' }
    const quoted = oldIds.map(x => `'${x}'`).join(',')
    const owner = await ui.login('OWNER', { label: 'gpt-bc-old-uuid' })
    const page = owner.page
    let oldAlert = '', cleanAlert = '', rpcStatus = -1
    try {
      const rpc = await owner.rpc('erp_get_accessory_issue_workspace_v1', { p_filters: {} })
      rpcStatus = rpc.status
      const menu = page.getByRole('button', { name: 'Buka menu', exact: true })
      if (await menu.isVisible()) await menu.click()
      const entry = page.getByRole('button', { name: '• Nota Ambil Aksesori', exact: true })
      if (!await entry.isVisible()) await page.locator('.sidebar .nav-main').filter({ hasText: 'Keuangan' }).click()
      await entry.click()
      await ui.expect(page.getByRole('heading', { name: 'Nota Ambil Aksesori', exact: true })).toBeVisible()
      try { await ui.expect(page.getByRole('alert').first()).toBeVisible({ timeout: 10000 }) } catch { /* observed: no alert */ }
      oldAlert = (await page.getByRole('alert').allTextContents()).join(' | ')

      // Positive control: remove only old seed actors from the disposable copy.
      ui.sql(`update erp.contractors set is_active=false where id in (${quoted})`)
      ui.sql("insert into erp.contractors(contractor_code,contractor_name,contractor_type,attendance_required,is_active) values('GPTBC'||substr(gen_random_uuid()::text,1,12),'GPT valid UUID control','MANDOR',false,true)")
      await page.getByRole('button', { name: 'Muat ulang', exact: true }).click()
      await ui.expect(page.getByRole('button', { name: 'Muat ulang', exact: true })).toBeEnabled()
      try { await ui.expect(page.getByRole('alert')).toHaveCount(0, { timeout: 10000 }) } catch { /* report parser state */ }
      cleanAlert = (await page.getByRole('alert').allTextContents()).join(' | ')
      const oldBlocked = oldAlert.length > 0
      const validLoads = cleanAlert.length === 0
      return {
        status: rpcStatus === 200 && oldBlocked && validLoads ? 'COUNTEREXAMPLE' : 'INCOMPLETE',
        conditional_relevance: 'hosted legacy UUID inventory not established',
        old_uuid_count: oldIds.length, server_rpc_status: rpcStatus,
        old_alert: oldAlert, after_control_alert: cleanAlert,
        old_blocked: oldBlocked, valid_control_loads: validLoads,
      }
    } finally {
      ui.sql(`update erp.contractors set is_active=true where id in (${quoted})`)
      await owner.context.close()
    }
  }]]
}
