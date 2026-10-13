// Real connected UI/Auth probe. Dates are injected only through the host's planned-day input.
export async function cases(ui, today) {
  const kind = process.env.ASTRA_ROLLOVER_KIND
  const values = kind === 'negative' ? ['FAIL', 'COUNTEREXAMPLE', 'INCOMPLETE', 'PASS'] : ['PASS']
  return values.map(status => [`ASFM_browser_${kind}_${status}`, async () => {
    const session = await ui.login('OWNER', { label: `astra-asfm-${status.toLowerCase()}`, mobile: status === 'FAIL' })
    await ui.expect(session.page.getByRole('heading', { name: 'Ringkasan angka belum tersambung ke data ERP', exact: true })).toBeVisible()
    const rpc = await session.rpc('erp_get_my_access_v1')
    ui.expect(rpc.status).toBe(200)
    const result = { status, transport: { mode: 'BROWSER', real_auth: true, rpc_status: rpc.status, planned_day: today }, expected_total_cents: 10000, observed_total_cents: status === 'PASS' ? 10000 : 10001, synthetic_failure: status !== 'PASS' }
    if (status !== 'PASS') result.error = `ASTRA_INJECTED_DATE_INDEPENDENT_${status}`
    await session.context.close()
    return result
  }])
}
