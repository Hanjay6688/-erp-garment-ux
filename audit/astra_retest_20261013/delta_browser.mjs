import { join } from 'node:path'
export async function cases(ui) {
  return ['OWNER','ADMIN'].flatMap(role => [false,true].map(mobile => [`ASD-UI-${role}-${mobile ? 'MOBILE' : 'DESKTOP'}`, async () => {
    const {page,context,rpc} = await ui.login(role,{label:'astra-delta-dashboard',mobile})
    await ui.expect(page.getByRole('heading',{name:'Ringkasan angka belum tersambung ke data ERP',exact:true})).toBeVisible()
    const text = await page.locator('main').innerText()
    ui.expect(text).not.toMatch(/Rp\s*[\d]|\d[.,]\d\s*(?:jt|%|pcs)/)
    for (const selector of ['.kpi-grid','.dashboard-grid','.chart-wrap','.flow-strip','.attention-panel']) await ui.expect(page.locator(selector)).toHaveCount(0)
    const policy = await rpc('erp_cp7_get_history_yield_policy_v1')
    ui.expect(policy.status).toBe(200)
    ui.expect(policy.body.manage_allowed).toBe(role === 'OWNER')
    const overflow=await page.evaluate(()=>document.documentElement.scrollWidth > window.innerWidth + 1)
    ui.expect(overflow).toBe(false)
    await page.screenshot({path:join(process.env.ASTRA_EVIDENCE_DIR,`dashboard-${role}-${mobile ? 'mobile' : 'desktop'}.png`),fullPage:true})
    await context.close()
    return {status:'PASS',role,mobile,no_fabricated_figures:true,policy_manage_allowed:policy.body.manage_allowed,horizontal_overflow:overflow}
  }]))
}
