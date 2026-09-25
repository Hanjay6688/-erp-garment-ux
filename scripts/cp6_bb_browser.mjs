// BB (writer): the continuation panels of the import page in a real browser (auditor handoff T2: UI for OPENING_SETTLEMENT,
// PURCHASE_COMMITMENT and PAYROLL_ENTITLEMENT), run by the browser mode of the auditor runtime (cp6-auditor-scenario.yml,
// browser_b64, phase after). The owner imports the fixture through the same public RPC the page uses, then acts only
// through the page; results are read back from the disposable copy. Label WRITER_SCENARIO: not independent evidence.
// Oracles: a settlement of 20.00 on an opening payable of 65.00 leaves 45.00 and its reversal restores 65.00; cancelling 4
// of an open order of 10 leaves 6; a carried 2 of 4 enters the chosen draft payroll at the entitlement rate (2 x 2.50).
import { randomUUID } from 'node:crypto'

const day = (today, back) => { const d = new Date(`${today}T00:00:00Z`); d.setUTCDate(d.getUTCDate() - back); return d.toISOString().slice(0, 10) }

async function importBatch(owner, today, rows) {
  const code = 'BWB' + randomUUID().replaceAll('-', '').slice(0, 11)
  const call = async (action, payload) => {
    const r = await owner.rpc('erp_save_initial_import_action_v1', { p_action: action, p_payload: payload, p_client_request_id: randomUUID() })
    if (r.status !== 200) throw new Error(`${action} ${r.status} ${JSON.stringify(r.body).slice(0, 600)}`)
    return r.body
  }
  const ws = async batch => (await owner.rpc('erp_get_initial_import_workspace_v1', { p_batch_id: batch })).body.batch
  const fill = v => typeof v === 'string' ? v.replaceAll('{C}', code) : v
  const batch = (await call('CREATE', { batch_code: code, cutover_date: day(today, 10) })).batch_id
  for (const [entity, list] of Object.entries(rows)) {
    await call('SAVE_FILE', { batch_id: batch, expected_revision: (await ws(batch)).revision, entity, filename: entity + '.csv',
      rows: list.map((p, i) => ({ source_row_no: i + 2, payload: Object.fromEntries(Object.entries(p).map(([k, v]) => [k, fill(v)])) })) })
  }
  const checked = await call('VALIDATE', { batch_id: batch, expected_revision: (await ws(batch)).revision })
  if (checked.error_rows !== 0) throw new Error('BB_BROWSER_FIXTURE_REFUSED ' + JSON.stringify((await ws(batch)).rows.filter(r => r.errors.length).map(r => [r.entity, r.errors])).slice(0, 1500))
  const posted = await call('FINALIZE', { batch_id: batch, expected_revision: (await ws(batch)).revision })
  if (posted.status !== 'POSTED') throw new Error('BB_BROWSER_FIXTURE_NOT_POSTED')
  return { batch, code }
}

async function openImport(ui, owner, batch) {
  const p = owner.page
  const menu = p.getByRole('button', { name: 'Buka menu', exact: true }); if (await menu.isVisible()) await menu.click()
  const link = p.getByRole('button', { name: '• Impor data awal', exact: true })
  if (!await link.isVisible()) await p.locator('.sidebar .nav-main').filter({ hasText: 'Pengaturan & Audit' }).click()
  await link.click()
  await ui.expect(p.getByRole('heading', { name: 'Impor data awal', exact: true })).toBeVisible()
  await ui.expect(p.getByRole('button', { name: 'Muat ulang', exact: true })).toBeEnabled()
  await p.getByLabel('Batch impor').selectOption(batch)
  await ui.expect(p.getByText('Sudah disahkan')).toBeVisible()
  return p
}

const bank = { CHART_ACCOUNT: [{ account_code: '{C}B', account_name: 'BB bank', account_type: 'ASSET', report_group: 'CURRENT_ASSETS', normal_balance: 'DEBIT' }],
  CASH_ACCOUNT: [{ cash_account_code: '{C}', cash_account_name: 'BB bank {C}', coa_account_code: '{C}B', account_kind: 'BANK' }] }

export async function cases(ui, today) {
  return [
    ['BB_BROWSER:OPENING_SETTLEMENT_PAY_AND_REVERSE', async () => {
      const owner = await ui.login('OWNER', { label: 'bb-oss' })
      const { batch, code } = await importBatch(owner, today, { ...bank,
        SUPPLIER: [{ supplier_code: '{C}', supplier_name: 'BB supplier lama', supplier_type: 'MATERIAL' }],
        OPENING_BALANCE_ITEM: [{ balance_type: 'CASH_BANK', cash_account_code: '{C}', amount: '200.00', control_key: 'CASH' },
          { balance_type: 'SUPPLIER_PAYABLE', supplier_code: '{C}', amount: '65.00', control_key: 'AP', document_number: 'INV-{C}',
            document_date: day(today, 50), original_amount: '100.00', settled_before_cutover: '35.00' }],
        OPENING_CONTROL: [{ control_key: 'CASH', balance_type: 'CASH_BANK', amount: '200.00' }, { control_key: 'AP', balance_type: 'SUPPLIER_PAYABLE', amount: '65.00' }] })
      const p = await openImport(ui, owner, batch)
      await ui.expect(p.getByRole('heading', { name: 'Pelunasan saldo awal' })).toBeVisible()
      await p.getByLabel('Rekening pelunasan').selectOption({ label: `BB bank ${code}` })
      await p.getByLabel('Nominal saldo awal').fill('20,00')
      await p.getByLabel('Tanggal pelunasan saldo awal').fill(today)
      await p.getByLabel('Alasan pelunasan saldo awal').fill('Transfer sebagian dari browser')
      await p.getByRole('button', { name: 'Bayar', exact: true }).click()
      await ui.expect(p.getByText(/· Dibukukan/)).toBeVisible()
      const balance = `(select b.id from erp.opening_subledger_balances b join erp.initial_import_financial_sources f on f.opening_item_id=b.opening_item_id where f.batch_id='${batch}')`
      const paid = ui.sql(`select original_amount-settled_amount from erp.opening_subledger_balances where id=${balance}`)
      await p.getByLabel('Alasan pelunasan saldo awal').fill('Salah rekening')
      await p.getByRole('button', { name: /^Batalkan / }).first().click()
      await ui.expect(p.getByText(/· Dibatalkan/)).toBeVisible()
      const back = ui.sql(`select original_amount-settled_amount from erp.opening_subledger_balances where id=${balance}`)
      await owner.context.close()
      const ok = paid === '45.00' && back === '65.00'
      return { status: ok ? 'PASS' : 'FAIL', remaining_after_pay: paid, remaining_after_reverse: back }
    }],
    ['BB_BROWSER:PURCHASE_COMMITMENT_CANCEL_REMAINDER', async () => {
      const owner = await ui.login('OWNER', { label: 'bb-po' })
      const { batch } = await importBatch(owner, today, {
        SUPPLIER: [{ supplier_code: '{C}', supplier_name: 'BB supplier PO', supplier_type: 'MATERIAL' }],
        LOCATION: [{ location_code: '{C}', location_name: 'BB gudang PO', location_type: 'RAW_MATERIAL_WAREHOUSE' }],
        MATERIAL: [{ material_sku: '{C}', material_name: 'BB benang PO', material_type: 'OTHER', unit_code: 'PCS' }],
        OPEN_PURCHASE_ORDER: [{ po_number: 'PO-{C}', po_line_number: '1', po_date: day(today, 15), supplier_code: '{C}', location_code: '{C}',
          material_sku: '{C}', ordered_qty: '10', received_before_cutover_qty: '0', cancelled_before_cutover_qty: '0', remaining_qty: '10', unit_price: '3' }] })
      const p = await openImport(ui, owner, batch)
      await ui.expect(p.getByRole('heading', { name: 'PO pembelian yang masih terbuka' })).toBeVisible()
      await p.getByLabel('Baris PO dibatalkan').selectOption({ index: 1 })
      await p.getByLabel('Jumlah PO dibatalkan').fill('4')
      await p.getByLabel('Tanggal pembatalan PO').fill(today)
      await p.getByLabel('Alasan PO').fill('Supplier tidak sanggup kirim sisa 4')
      await p.getByRole('button', { name: 'Batalkan sisa', exact: true }).click()
      await ui.expect(p.getByRole('cell', { name: /^6(\.0+)?$/ })).toBeVisible()
      const remaining = ui.sql(`select erp.bb_commitment_line_remaining_v1(l.id) from erp.bb_purchase_commitment_lines_v1 l join erp.bb_purchase_commitments_v1 c on c.id=l.commitment_id where c.batch_id='${batch}'`)
      await owner.context.close()
      const ok = Number(remaining) === 6
      return { status: ok ? 'PASS' : 'FAIL', remaining }
    }],
    ['BB_BROWSER:PAYROLL_ENTITLEMENT_CARRY_TO_PAYROLL', async () => {
      const owner = await ui.login('OWNER', { label: 'bb-y02' })
      const pending = 'BWJ' + randomUUID().replaceAll('-', '').slice(0, 11)
      ui.sql(`insert into erp.work_components(component_code,component_name,component_category,is_active) values('${pending}','BB Y02 jahit browser','LABOR',true)`)
      const d = day(today, 22)
      const { batch, code } = await importBatch(owner, today, { ...bank,
        CONTRACTOR: [{ contractor_code: '{C}', contractor_name: 'BB Epi browser', contractor_type: 'MANDOR', attendance_required: 'true' }],
        OPENING_BALANCE_ITEM: [{ balance_type: 'CONTRACTOR_PAYABLE', contractor_code: '{C}', amount: '134.00', control_key: 'CP', document_number: 'NJ-{C}',
          document_date: d, original_amount: '209.00', settled_before_cutover: '75.00' },
          { balance_type: 'CASH_BANK', cash_account_code: '{C}', amount: '1000.00', control_key: 'CASH' }],
        OPENING_CONTROL: [{ control_key: 'CP', balance_type: 'CONTRACTOR_PAYABLE', amount: '134.00' }, { control_key: 'CASH', balance_type: 'CASH_BANK', amount: '1000.00' }],
        OPENING_PAYROLL_ENTITLEMENT: [
          { kind: 'SEWING_WORK', contractor_code: '{C}', document_number: 'NJ-{C}', line_number: '1', document_date: d, rate: '2.50',
            work_component_code: pending, earned_qty: '40', paid_before_qty: '10', carry_qty: '4' },
          { kind: 'ATTENDANCE', contractor_code: '{C}', document_number: 'NJ-{C}', line_number: '2', document_date: d, rate: '20',
            worker_name: 'Epi A', period_start: day(today, 30), period_end: day(today, 24), days: '5.5', paid_before_amount: '50' },
          { kind: 'ACCESSORY_REIMBURSEMENT', contractor_code: '{C}', document_number: 'NJ-{C}', line_number: '3', document_date: d, rate: '0.75',
            category_code: 'ACC', good_qty: '12', paid_before_amount: '0' }] })
      const payroll = ui.sql(`insert into erp.payroll_settlements(payroll_number,contractor_id,period_start,period_end,manual_adjustment,payment_date,payment_cash_account_id)
        select 'BBB-${code}',c.id,'${today}','${today}',0,'${today}',k.id from erp.contractors c,erp.cash_accounts k where c.contractor_code='${code}' and k.cash_account_code='${code}' returning payroll_number`)
      const p = await openImport(ui, owner, batch)
      await ui.expect(p.getByRole('heading', { name: 'Hak upah sebelum saldo awal' })).toBeVisible()
      await p.getByLabel('Payroll carry').selectOption({ index: 1 })
      await p.getByLabel('Jumlah carry').fill('2')
      await p.getByRole('button', { name: 'Simpan carry ke payroll', exact: true }).click()
      await ui.expect(p.getByText(new RegExp(`${payroll} · 2`))).toBeVisible()
      const line = ui.sql(`select r.opening_carry_qty||'|'||r.amount from erp.payroll_reimbursements r join erp.payroll_settlements s on s.id=r.payroll_id where s.payroll_number='${payroll}'`)
      await owner.context.close()
      const [qty, amount] = line.split('|')
      const ok = Number(qty) === 2 && amount === '5.00'
      return { status: ok ? 'PASS' : 'FAIL', payroll_line: line }
    }],
  ]
}
