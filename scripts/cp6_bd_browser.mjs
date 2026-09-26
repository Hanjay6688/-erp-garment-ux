// BD (writer): the Laundry page's "Harga & tagihan" tab and the import page's ALL-W05 claim actions in a real browser, run by
// the browser mode of the auditor runtime (cp6-auditor-scenario.yml, browser_path scripts/cp6_bd_browser.mjs, phase after).
// Fixtures are imported through the same public RPC the import page uses; every business action is taken only through the
// page; results are read back with SQL. Label WRITER_SCENARIO: not independent evidence.
// Oracles: the owner sets LAU-DEC04 from the policy section (status SET, version +1) and returns it to PENDING_POLICY_VALUE
// (version +2); an opening laundry claim of 1 of 8 pieces shows the held piece on the opening WIP row, a recovery of 1 from
// the page returns it to the remaining WIP (remaining 7 -> 8) and its reversal from the page holds it again (8 -> 7); an
// opening uninvoiced return with an unknown value is listed "Belum diketahui" for PRODUKSI_QC with no estimate input and no
// invoice section (money hidden), and the owner's estimate of 8,000.00 from the page books the opening accrual once and
// lifts the close blocker BD_OPENING_LAUNDRY_PRICE_UNKNOWN.
import { randomUUID } from 'node:crypto'

const day = (today, back) => { const d = new Date(`${today}T00:00:00Z`); d.setUTCDate(d.getUTCDate() - back); return d.toISOString().slice(0, 10) }

async function importBatch(owner, today, rows) {
  const code = 'BDB' + randomUUID().replaceAll('-', '').slice(0, 11)
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
  if (checked.error_rows !== 0) throw new Error('BD_BROWSER_FIXTURE_REFUSED ' + JSON.stringify((await ws(batch)).rows.filter(r => r.errors.length).map(r => [r.entity, r.errors])).slice(0, 1500))
  const posted = await call('FINALIZE', { batch_id: batch, expected_revision: (await ws(batch)).revision })
  if (posted.status !== 'POSTED') throw new Error('BD_BROWSER_FIXTURE_NOT_POSTED')
  return { batch, code }
}

/** The auditor's W05 fixture: 8 pieces of PO {C} still at laundry {C} (40.00), 1 of them claimed MISSING before cutover. */
const w05Rows = today => ({
  MODEL: [{ model_code: '{C}', model_name: 'BD model {C}' }], SIZE: [{ size_code: '{C}' }], BRAND: [{ brand_code: '{C}', brand_name: 'BD brand {C}' }],
  PRODUCT: [{ sku: '{C}P', product_name: 'BD produk {C}', model_code: '{C}', brand_code: '{C}', color_name: 'Blue', size_code: '{C}' }],
  LOCATION: [{ location_code: '{C}G', location_name: 'BD gudang FG {C}', location_type: 'FG_WAREHOUSE' }],
  CONTRACTOR: [{ contractor_code: '{C}', contractor_name: 'BD mandor {C}', contractor_type: 'MANDOR' }],
  LAUNDRY_VENDOR: [{ vendor_code: '{C}', vendor_name: 'BD laundry {C}' }],
  OPEN_PO: [{ po_number: '{C}', model_code: '{C}', target_qty_pcs: '12', status: 'LAUNDRY', current_stage: 'LAUNDRY', contractor_code: '{C}' }],
  OPENING_BALANCE_ITEM: [{ balance_type: 'WIP', po_number: '{C}', model_code: '{C}', size_code: '{C}', stage: 'LAUNDRY', qty: '8', unit_cost: '5', amount: '40.00',
    opening_source_key: 'WIP', control_key: 'WIP', accessory_cost_included: 'true', product_sku: '{C}P', brand_code: '{C}', color_name: 'Blue', vendor_code: '{C}' }],
  OPENING_CONTROL: [{ control_key: 'WIP', balance_type: 'WIP', qty: '8', amount: '40.00' }],
  OPENING_LAUNDRY_CLAIM: [{ claim_number: '{C}-KL1', source_key: 'WIP', vendor_code: '{C}', claim_type: 'MISSING', qty: '1', claim_date: day(today, 12), dispatch_number: 'KRM-LAMA-7' }],
})

async function openPage(ui, user, group, item, heading) {
  const p = user.page
  const menu = p.getByRole('button', { name: 'Buka menu', exact: true }); if (await menu.isVisible()) await menu.click()
  const link = p.getByRole('button', { name: `• ${item}`, exact: true })
  if (!await link.isVisible()) await p.locator('.sidebar .nav-main').filter({ hasText: group }).click()
  await link.click()
  await ui.expect(p.getByRole('heading', { name: heading, exact: true })).toBeVisible()
  return p
}

// Recorded, not a pass condition: the Laundry/QC read of the page (run 36190024230 found the pricing tab gated on it; the tab
// now reads its own workspace, and a failed Laundry/QC read only locks the priced-send section).
async function laundryRead(p) {
  const alert = p.locator('.clq-alert.error')
  return await alert.count() ? (await alert.first().innerText()).slice(0, 300) : 'OK'
}

async function openPricing(ui, user) {
  const p = await openPage(ui, user, 'Produksi', 'Laundry', 'Laundry')
  await p.getByRole('button', { name: 'Harga & tagihan', exact: true }).click()
  await ui.expect(p.getByRole('heading', { name: 'Harga laundry dan invoice vendor', exact: true })).toBeVisible()
  await ui.expect(p.getByRole('button', { name: 'Muat ulang harga', exact: true })).toBeEnabled({ timeout: 20000 })
  return p
}

// D08 (owner, 26 Sep 2026): the Laundry and QC pages accept any canonical UUID. The page reads are scanned for ids: at least one
// canonical non RFC-4122 id (the CP3 seed mandors/models, left active) and at least one v4 id (the control) must be in the read.
const RFC = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i
const V4 = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i
const CANONICAL = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i
function idsIn(value, out = { non_rfc: new Set(), v4: new Set() }) {
  if (typeof value === 'string') { if (CANONICAL.test(value)) { if (!RFC.test(value)) out.non_rfc.add(value); else if (V4.test(value)) out.v4.add(value) } }
  else if (Array.isArray(value)) for (const v of value) idsIn(v, out)
  else if (value && typeof value === 'object') for (const v of Object.values(value)) idsIn(v, out)
  return out
}

export async function cases(ui, today) {
  return [
    ['BD_BROWSER:D08_LAUNDRY_QC_CANONICAL_IDS', async () => {
      const rfc = "'^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'"
      const seeds = () => ui.sql(`select (select count(*) from erp.contractors where is_active and id::text !~* ${rfc})||'|'||(select count(*) from erp.product_models where id::text !~* ${rfc})`)
      const before = seeds()
      const owner = await ui.login('OWNER', { label: 'bd-d08' })
      const read = async scope => {
        const r = await owner.rpc('erp_get_laundry_qc_workspace_v1', { p_scope: scope, p_query: null })
        if (r.status !== 200) return { status: r.status, non_rfc: 0, v4: 0 }
        const ids = idsIn(r.body)
        return { status: r.status, non_rfc: ids.non_rfc.size, v4: ids.v4.size, non_rfc_sample: [...ids.non_rfc].sort().slice(0, 3) }
      }
      const laundryIds = await read('LAUNDRY'), qcIds = await read('QC')
      const page = async (item, heading) => {
        const p = await openPage(ui, owner, 'Produksi', item, heading)
        let loaded = false
        try { await ui.expect(p.locator('.clq-loading')).toHaveCount(0, { timeout: 20000 }); loaded = true } catch { loaded = false }
        const uuidError = await p.getByText(/bukan UUID valid/).count()
        return { loaded, error: await laundryRead(p), uuid_error_text: uuidError }
      }
      const laundry = await page('Laundry', 'Laundry')
      const qc = await page('QC & Final SKU', 'QC & Final SKU')
      await owner.context.close()
      const after = seeds()
      const [mandors] = before.split('|').map(Number)
      const ok = mandors > 0 && after === before && laundryIds.status === 200 && qcIds.status === 200
        && laundryIds.non_rfc > 0 && laundryIds.v4 > 0 && qcIds.non_rfc > 0 && qcIds.v4 > 0
        && laundry.loaded && laundry.error === 'OK' && laundry.uuid_error_text === 0 && qc.loaded && qc.error === 'OK' && qc.uuid_error_text === 0
      return { status: ok ? 'PASS' : 'FAIL', seeds_active_before_after: [before, after], laundry_read_ids: laundryIds, qc_read_ids: qcIds, laundry, qc }
    }],
    ['BD_BROWSER:OWNER_POLICY_SET_AND_CLEAR', async () => {
      const policy = () => ui.sql("select status||'|'||version from erp.bd_policy_settings_v1 where policy_key='LAU_DEC04'")
      const before = policy()
      const owner = await ui.login('OWNER', { label: 'bd-policy' })
      const p = await openPricing(ui, owner)
      await p.getByLabel('Kebijakan yang diubah').selectOption('LAU-DEC04')
      await p.getByLabel('Penjualan').selectOption('REFUSE')
      await p.getByLabel('Alasan', { exact: true }).fill('Owner menolak jual sebelum harga laundry diketahui')
      await p.getByRole('button', { name: 'Tetapkan LAU-DEC04', exact: true }).click()
      const version = Number(before.split('|')[1])
      await ui.expect.poll(policy, { timeout: 20000 }).toBe(`SET|${version + 1}`)
      await ui.expect(p.getByRole('button', { name: 'Muat ulang harga', exact: true })).toBeEnabled({ timeout: 20000 })
      await p.getByLabel('Kebijakan yang diubah').selectOption('LAU-DEC04')
      await p.getByLabel('Alasan', { exact: true }).fill('Kembali menunggu keputusan owner')
      await p.getByRole('button', { name: 'Kembalikan LAU-DEC04 ke menunggu', exact: true }).click()
      await ui.expect.poll(policy, { timeout: 20000 }).toBe(`PENDING_POLICY_VALUE|${version + 2}`)
      const laundryQcRead = await laundryRead(p)
      await owner.context.close()
      return { status: 'PASS', before, after: policy(), laundry_qc_read: laundryQcRead }
    }],
    ['BD_BROWSER:W05_CLAIM_RECOVER_AND_REVERSE', async () => {
      const owner = await ui.login('OWNER', { label: 'bd-claim' })
      const { batch, code } = await importBatch(owner, today, w05Rows(today))
      const item = ui.sql(`select s.opening_item_id from erp.initial_import_production_sources s where s.batch_id='${batch}'`)
      const state = () => ui.sql(`select erp.bd_opening_claim_held_qty_v1('${item}')||'|'||(select count(*) from erp.bd_opening_laundry_claim_events_v1 e join erp.bd_opening_laundry_claims_v1 c on c.id=e.claim_id where c.opening_item_id='${item}' and e.reversed_at is null)`)
      const p = await openPage(ui, owner, 'Pengaturan & Audit', 'Impor data awal', 'Impor data awal')
      await ui.expect(p.getByRole('button', { name: 'Muat ulang', exact: true })).toBeEnabled()
      await p.getByLabel('Batch impor').selectOption(batch)
      await ui.expect(p.getByText('Sudah disahkan')).toBeVisible()
      await p.getByLabel('Rincian produksi awal').selectOption(item)
      await ui.expect(p.getByText('Diklaim ke laundry 1 pcs')).toBeVisible()
      const shown = await p.getByText(`${code}-KL1`).first().isVisible()
      const before = state()
      await p.getByLabel('Catatan klaim laundry').fill('Satu potong ditemukan di vendor')
      await p.getByLabel('Jumlah klaim laundry').fill('1')
      await p.getByLabel('Tanggal klaim laundry').fill(today)
      await p.getByRole('button', { name: 'Catat potongan kembali', exact: true }).click()
      await ui.expect.poll(state, { timeout: 20000 }).toBe('0|1')
      await ui.expect(p.getByRole('button', { name: `Batalkan kejadian ${today}`, exact: true })).toBeVisible({ timeout: 20000 })
      await p.getByLabel('Catatan klaim laundry').fill('Salah catat, potongan belum kembali')
      await p.getByRole('button', { name: `Batalkan kejadian ${today}`, exact: true }).click()
      await ui.expect.poll(state, { timeout: 20000 }).toBe('1|0')
      await owner.context.close()
      return { status: before === '1|0' && shown ? 'PASS' : 'FAIL', before, after: state(), claim_listed: shown }
    }],
    ['BD_BROWSER:W05_OPENING_ESTIMATE_QC_HIDDEN', async () => {
      const owner = await ui.login('OWNER', { label: 'bd-estimate' })
      const { batch, code } = await importBatch(owner, today, {
        LAUNDRY_VENDOR: [{ vendor_code: '{C}', vendor_name: 'BD laundry {C}' }],
        OPENING_LAUNDRY_UNINVOICED: [{ document_number: '{C}-TRM', vendor_code: '{C}', receipt_date: day(today, 12), category: 'FAILED_ATTEMPT', qty: '2' }] })
      const doc = `${code}-TRM`
      const source = ui.sql(`select id from erp.bd_opening_laundry_uninvoiced_v1 where batch_id='${batch}'`)
      const blocked = () => ui.sql(`select count(*) from erp.period_blockers_v1(current_date,null) where reference->>'opening_uninvoiced_id'='${source}'`)
      const blockedBefore = blocked()
      const qc = await ui.login('PRODUKSI_QC', { label: 'bd-qc' })
      const q = await openPricing(ui, qc)
      await q.getByRole('button', { name: 'Laundry saldo awal', exact: true }).click()
      await ui.expect(q.getByRole('cell', { name: new RegExp(doc) })).toBeVisible()
      const qcInput = await q.getByLabel(`Estimasi ${doc}`).count()
      await q.getByRole('button', { name: 'Invoice vendor', exact: true }).click()
      const invoiceHidden = await q.getByText('Hak melihat nominal diperlukan untuk invoice vendor.').isVisible()
      const laundryQcRead = await laundryRead(q)
      await qc.context.close()
      const p = await openPricing(ui, owner)
      await p.getByRole('button', { name: 'Laundry saldo awal', exact: true }).click()
      await p.getByLabel('Alasan', { exact: true }).fill('Estimasi dari catatan vendor')
      await p.getByLabel(`Estimasi ${doc}`).fill('8000')
      await p.getByRole('button', { name: `Isi estimasi ${doc}`, exact: true }).click()
      const estimated = () => ui.sql(`select coalesce(estimated_amount::text,'-')||'|'||(select count(*) from erp.journal_entries where source_type='BD_OPENING_LAUNDRY_ACCRUAL' and source_id='${source}') from erp.bd_opening_laundry_uninvoiced_v1 where id='${source}'`)
      await ui.expect.poll(estimated, { timeout: 20000 }).toBe('8000.00|1')
      const blockedAfter = blocked()
      await owner.context.close()
      const ok = blockedBefore === '1' && qcInput === 0 && invoiceHidden && blockedAfter === '0'
      return { status: ok ? 'PASS' : 'FAIL', blocked_before: blockedBefore, qc_estimate_inputs: qcInput, invoice_hidden: invoiceHidden, estimated: estimated(), blocked_after: blockedAfter, laundry_qc_read: laundryQcRead }
    }],
  ]
}
