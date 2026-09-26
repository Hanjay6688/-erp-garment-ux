// D11 no.11 / LAU-DEC04: pending cost is visible, then a real browser price fill
// propagates to 8 unsold + 2 sold PCS. The sale itself is a native fixture; the
// sales page is still a demo, so this does not claim browser posting of a sale.
import { execFileSync } from 'node:child_process'

const fixture = (operation, payload) => JSON.parse(execFileSync('python',
  ['../auditor/scripts/cp6_bd_completion_fixture.py', operation, typeof payload === 'string' ? payload : JSON.stringify(payload)],
  { cwd: '../writer', encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] }).trim())
const micros = text => {
  if (!/^-?\d+(\.\d{1,6})?$/.test(text)) throw new Error('Expected exact decimal amount: ' + text)
  const [whole, fraction = ''] = text.replace('-', '').split('.')
  return BigInt(whole + fraction.padEnd(6, '0')) * (text.startsWith('-') ? -1n : 1n)
}

export async function cases(ui, today) {
  return [['BD_COMPLETION:ALLOW_PENDING_VISIBLE_AND_BROWSER_RECOST', async () => {
    const fx = fixture('create', today)
    const owner = await ui.login('OWNER', { label: 'gpt-bd-pending' })
    const p = owner.page
    try {
      const menu = p.getByRole('button', { name: 'Buka menu', exact: true })
      if (await menu.isVisible()) await menu.click()
      const link = p.getByRole('button', { name: '• Laundry', exact: true })
      if (!await link.isVisible()) await p.locator('.sidebar .nav-main').filter({ hasText: 'Produksi' }).click()
      await link.click()
      await p.getByRole('button', { name: 'Harga & tagihan', exact: true }).click()
      const ready = () => ui.expect(p.getByRole('button', { name: 'Muat ulang harga', exact: true })).toBeEnabled({ timeout: 20000 })
      await ready()
      await p.getByLabel('Vendor harga laundry', { exact: true }).selectOption(fx.vendor)
      await ready()
      await p.getByRole('button', { name: 'Harga belum diketahui', exact: true }).click()
      const pending = p.getByRole('region', { name: 'HPP belum final', exact: true })
      const goodsTable = pending.getByRole('table', { name: 'Barang jadi HPP belum final', exact: true })
      const salesTable = pending.getByRole('table', { name: 'Penjualan saat harga laundry belum diketahui', exact: true })
      await ui.expect(goodsTable.locator('tbody tr')).toHaveCount(1)
      await ui.expect(salesTable.locator('tbody tr')).toHaveCount(1)
      const beforeScreen = { goods: await goodsTable.locator('tbody').innerText(), sales: await salesTable.locator('tbody').innerText() }
      const box = p.getByRole('region', { name: 'Harga laundry belum diketahui', exact: true })
      await box.getByLabel('Alasan', { exact: true }).fill('GPT BD bukti harga vendor akhirnya diketahui')
      await box.getByLabel(`Harga per PCS ${fx.label}`, { exact: true }).fill('1000')
      await box.getByRole('button', { name: `Isi harga ${fx.label}`, exact: true }).click()
      await ui.expect.poll(() => ui.sql(`select rate_status from erp.bd_laundry_charge_lines_v1 where id='${fx.charge}'`), { timeout: 20000 }).toBe('KNOWN')
      await ready()
      await ui.expect(pending.getByText('Tidak ada barang jadi dengan HPP belum final.', { exact: true })).toBeVisible()
      await ui.expect(salesTable.getByText('Sudah dihitung ulang dengan harga laundry', { exact: true })).toBeVisible()
      const after = fixture('read', fx)
      const originalSale = fx.before.view.sales.find(s => s.sale_id === fx.sale)
      const recostedSale = after.view.sales.find(s => s.sale_id === fx.sale)
      const checks = {
        pending_visible: beforeScreen.goods.includes('HPP belum final') && beforeScreen.sales.includes('HPP belum final'),
        original_close_blocked: JSON.stringify(fx.before.blockers) === JSON.stringify(['BD_LAUNDRY_COMPONENT_PRICE_UNKNOWN']),
        lot_adds_10000: micros(after.lot_value) - micros(fx.before.lot_value) === 10000000000n,
        remaining_fg_adds_8000: micros(after.fg) - micros(fx.before.fg) === 8000000000n,
        sold_cogs_adds_2000: micros(after.cogs) - micros(fx.before.cogs) === 2000000000n,
        blocker_clears: after.blockers.length === 0,
        sale_snapshot_immutable: JSON.stringify(after.sale) === JSON.stringify(fx.before.sale),
        sale_recosted: originalSale?.hpp_state === 'NOT_FINAL' && recostedSale?.hpp_state === 'RECOSTED'
          && originalSale.unit_hpp_at_sale === recostedSale.unit_hpp_at_sale,
        no_pending_goods: !after.view.goods.some(g => g.lot_id === fx.lot),
      }
      return { status: Object.values(checks).every(Boolean) ? 'PASS' : 'FAIL', checks,
        fixture_setup: 'native sale commands; browser sale posting NOT covered',
        before_screen: beforeScreen, before: fx.before, after }
    } finally { await owner.context.close() }
  }]]
}
