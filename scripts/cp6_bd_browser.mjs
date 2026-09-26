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

// Phone width check: the page itself must not scroll sideways (tables scroll inside their own box). On failure the elements
// that reach past the screen outside any scroll box are listed.
const widthOk = async p => p.evaluate(() => {
  const viewport = document.documentElement.clientWidth, page = document.documentElement.scrollWidth, wide = []
  if (page > viewport) for (const el of document.querySelectorAll('body *')) {
    const r = el.getBoundingClientRect()
    if (r.width === 0 || r.right <= viewport + 1) continue
    let a = el.parentElement, boxed = false
    while (a && a !== document.body) { if (['auto', 'scroll', 'hidden', 'clip'].includes(getComputedStyle(a).overflowX)) { boxed = true; break } a = a.parentElement }
    if (!boxed) wide.push({ tag: el.tagName, cls: String(el.className).slice(0, 50), label: el.getAttribute('aria-label'), right: Math.round(r.right), width: Math.round(r.width) })
  }
  return { viewport, page, ok: page <= viewport, wide: wide.slice(-8) }
})
// What a click at the centre of the element would hit (recorded before the click, not a pass condition by itself).
const hitAt = async loc => loc.evaluate(el => {
  const r = el.getBoundingClientRect(), x = r.left + r.width / 2, y = r.top + r.height / 2, top = document.elementFromPoint(x, y)
  const vv = window.visualViewport
  return { rect: [r.left, r.top, r.width, r.height].map(Math.round), hits_self: top === el || el.contains(top),
    top: top ? `${top.tagName}.${String(top.className).slice(0, 40)} ${(top.textContent || '').trim().slice(0, 40)}` : null,
    inner: [innerWidth, innerHeight], visual: vv ? [vv.width, vv.height, vv.offsetLeft, vv.offsetTop, vv.scale].map(v => Math.round(v * 100) / 100) : null, scroll: [scrollX, scrollY] }
})

// D12: pay one vendor document from the payment screen (Laundry -> Harga & tagihan -> Pembayaran vendor): a claim credit first,
// then cash. Returns what the page showed before and after.
async function payOnScreen(ui, owner, vendor, doc, credit, day, sql) {
  const p = await openPricing(ui, owner)
  const reload = async () => ui.expect(p.getByRole('button', { name: 'Muat ulang harga', exact: true })).toBeEnabled({ timeout: 20000 })
  await p.getByRole('button', { name: 'Pembayaran vendor', exact: true }).click()
  await p.getByLabel('Vendor harga laundry', { exact: true }).selectOption(vendor); await reload()
  const box = p.getByRole('region', { name: 'Pembayaran vendor laundry' })
  const read = async () => ({ ledger: (await box.getByRole('status').innerText()).trim(),
    ap: (await box.locator('dl div').filter({ hasText: 'Saldo utang (buku besar)' }).locator('dd').innerText()).trim(),
    row: (await box.getByRole('table', { name: 'Tagihan vendor' }).locator('tbody tr').filter({ hasText: doc.number }).innerText()).replace(/\s+/g, ' ').trim() })
  const before = await read()
  // A step whose database effect does not appear names what the page showed (alert or recovery notice) in the error.
  const waitFor = async (probe, value, step) => {
    try { await ui.expect.poll(probe, { timeout: 20000 }).toBe(value) } catch (e) {
      const shown = await p.locator('[role="alert"], .initial-import-message').allInnerTexts().catch(() => [])
      throw new Error(`${step}: ${String(e.message).split('\n').slice(0, 3).join(' ')} · layar: ${shown.join(' | ').slice(0, 400)}`)
    }
  }
  const common = async () => {
    await box.getByLabel('Tagihan dilunasi', { exact: true }).selectOption(doc.id)
    await box.getByLabel('Tanggal pelunasan', { exact: true }).fill(day)
    await box.getByLabel('Alasan pelunasan', { exact: true }).fill('D12 pelunasan dari layar pembayaran')
  }
  await common()
  await box.getByLabel('Kredit klaim dipakai', { exact: true }).selectOption(credit)
  await box.getByLabel('Nominal kredit klaim', { exact: true }).fill('2000000')
  await box.getByRole('button', { name: 'Pakai kredit klaim', exact: true }).click()
  await waitFor(() => sql.credited(), '2000000.00', 'kredit klaim'); await reload()
  const middle = await read()
  await common()
  const cash = await box.getByLabel('Rekening kas pembayaran', { exact: true }).locator('option').nth(1).getAttribute('value')
  await box.getByLabel('Rekening kas pembayaran', { exact: true }).selectOption(cash)
  await box.getByLabel('Nominal bayar kas', { exact: true }).fill('8000000')
  await box.getByRole('button', { name: 'Bayar kas', exact: true }).click()
  await waitFor(() => sql.remaining(), '0.00', 'bayar kas'); await reload()
  const after = await read()
  const width = await widthOk(p)
  return { before, middle, after, width }
}
const screenOk = (r, doc) => r.before.ledger.startsWith('Cocok') && r.before.row.includes('Rp 10.000.000,00')
  && r.middle.ledger.startsWith('Cocok') && r.after.ledger.startsWith('Cocok') && r.after.ap === 'Rp 0,00'
  && r.after.row.includes('Rp 8.000.000,00') && r.after.row.includes('Rp 2.000.000,00') && r.after.row.includes('Rp 0,00') && r.after.row.includes('Lunas')

export async function cases(ui, today) {
  return [
    ['BD_BROWSER:LAU_T36_PHONE_MIXED_COVERAGE', async () => {
      // LAU-T36 (UI laundry desktop/HP, mixed coverage): on a 390 px phone the owner sets a component-priced vendor from the
      // "Harga vendor" section (terms COMPONENTS per PCS, component GAR known 5,000.00, component SPR unknown), sends 2 PCS of a
      // ready batch from "Kirim dengan harga" with GAR covering 2 and SPR covering 1, sees SPR listed "Belum diketahui" (known
      // subtotal 10,000.00, not complete), and fills SPR at 3,000.00 from "Harga belum diketahui" (13,000.00, complete). The page
      // must never scroll sideways. Only 2 PCS are taken, so the batch keeps stock for the D08 case. Desktop use of the same tab
      // is covered by the other BD browser cases.
      const tag = 'T36' + randomUUID().replaceAll('-', '').slice(0, 10)
      const vendor = ui.sql(`insert into erp.laundry_vendors(vendor_code,vendor_name,is_active) values('${tag}','T36 laundry ${tag}',true) returning id`)
      const process = ui.sql(`insert into erp.wash_processes(process_code,process_name,is_active) values('${tag}','T36 cuci ${tag}',true) returning id`)
      const wib = back => ui.sql(`select to_char(clock_timestamp() at time zone 'Asia/Jakarta' - interval '${back} minutes','YYYY-MM-DD"T"HH24:MI')`)
      const phone = await ui.login('OWNER', { label: 'bd-t36-phone', mobile: true })
      const ready = ((await phone.rpc('erp_get_laundry_qc_workspace_v1', { p_scope: 'LAUNDRY', p_query: null })).body?.ready_batches ?? [])
        .map(b => ({ b, size: b.sizes.find(z => z.available_qty_pcs >= 2) })).filter(x => x.size).sort((x, y) => Number(!RFC.test(x.b.contractor_id)) - Number(!RFC.test(y.b.contractor_id)))[0]
      const widths = {}
      if (!ready) { await phone.context.close(); return { status: 'FAIL', reason: 'no ready batch with 2 PCS available' } }
      const p = await openPricing(ui, phone)
      widths.open = await widthOk(p)
      const reload = async () => ui.expect(p.getByRole('button', { name: 'Muat ulang harga', exact: true })).toBeEnabled({ timeout: 20000 })
      const until = async (sql, value) => ui.expect.poll(() => ui.sql(sql), { timeout: 20000 }).toBe(value)
      // Master: the section remounts after every save, so the reason and start time are filled again each time.
      await p.getByRole('button', { name: 'Harga vendor', exact: true }).click()
      await p.getByLabel('Vendor harga laundry', { exact: true }).selectOption(vendor); await reload()
      const m = p.getByRole('region', { name: 'Harga vendor' })
      const master = async () => { await m.getByLabel('Alasan', { exact: true }).fill('T36 harga vendor dari HP'); await m.getByLabel('Berlaku sejak (WIB)', { exact: true }).fill(wib(60)) }
      await master()
      await m.getByLabel('Cara harga vendor', { exact: true }).selectOption('COMPONENTS'); await m.getByLabel('Satuan harga vendor', { exact: true }).selectOption('PCS')
      await m.getByRole('button', { name: 'Simpan ketentuan', exact: true }).click()
      await until(`select coalesce((select pricing_mode||'/'||pricing_unit from erp.bd_laundry_vendor_terms_v1 where vendor_id='${vendor}'),'')`, 'COMPONENTS/PCS'); await reload()
      for (const [code, n] of [['GAR', '1'], ['SPR', '2']]) {
        await master()
        await m.getByLabel('Kode komponen', { exact: true }).fill(code); await m.getByLabel('Nama komponen', { exact: true }).fill(`T36 ${code}`)
        await m.getByRole('button', { name: 'Tambah komponen', exact: true }).click()
        await until(`select count(*) from erp.bd_laundry_components_v1 where vendor_id='${vendor}'`, n); await reload()
      }
      for (const [code, status, n] of [['GAR', 'KNOWN', '1'], ['SPR', 'UNKNOWN', '2']]) {
        await master()
        await m.getByLabel('Komponen harga', { exact: true }).selectOption({ label: code })
        await m.getByLabel('Status harga komponen', { exact: true }).selectOption(status)
        if (status === 'KNOWN') await m.getByLabel('Harga per PCS', { exact: true }).fill('5000')
        await m.getByRole('button', { name: 'Simpan versi harga komponen', exact: true }).click()
        await until(`select count(*) from erp.bd_laundry_component_rates_v1 r join erp.bd_laundry_components_v1 c on c.id=r.component_id where c.vendor_id='${vendor}'`, n); await reload()
      }
      widths.master = await widthOk(p)
      // Priced send: 2 PCS, GAR covers 2, SPR covers 1.
      await p.getByRole('button', { name: 'Kirim dengan harga', exact: true }).click()
      const k = p.getByRole('region', { name: 'Kirim laundry dengan harga BD' })
      await k.getByLabel('Batch kirim berharga', { exact: true }).selectOption(ready.b.distribution_batch_id)
      await k.getByLabel('Proses kirim berharga', { exact: true }).selectOption(process)
      await k.getByLabel('Warna kirim berharga', { exact: true }).fill('NAVY')
      await k.getByLabel('Waktu kirim berharga', { exact: true }).fill(wib(3))
      await k.getByLabel('Bukti serah terima', { exact: true }).fill('T36 kirim berharga dari HP')
      await k.getByLabel(`Qty kirim berharga ${ready.size.size_code}`, { exact: true }).fill('2')
      await k.getByLabel('Cakupan GAR', { exact: true }).fill('2'); await k.getByLabel('Cakupan SPR', { exact: true }).fill('1')
      await k.getByLabel('Vendor, batch, ukuran, jumlah, warna, waktu, dan harga sudah dicocokkan dengan serah-terima.', { exact: true }).check()
      widths.send = await widthOk(p)
      await k.getByRole('button', { name: 'Catat kiriman berharga', exact: true }).click()
      const delivery = () => ui.sql(`select coalesce((select id::text from erp.laundry_deliveries where vendor_id='${vendor}' and status<>'REVERSED' limit 1),'')`)
      await ui.expect.poll(delivery, { timeout: 20000 }).not.toBe('')
      const sent = delivery(); await reload()
      const state = () => ui.sql(`select coalesce((select string_agg(total_known::text||'|'||total_complete::text,',') from erp.bd_laundry_priced_lines_v1 where delivery_id='${sent}'),'')`)
      const charges = () => ui.sql(`select coalesce(string_agg(c.label||':'||c.covered_qty||':'||c.rate_status,',' order by c.line_no),'') from erp.bd_laundry_charge_lines_v1 c
        join erp.bd_laundry_priced_lines_v1 l on l.delivery_line_id=c.delivery_line_id where l.delivery_id='${sent}'`)
      const afterSend = { state: state(), charges: charges() }
      // Unknown price: listed "Belum diketahui" on the phone, then filled from the page.
      await p.getByRole('button', { name: 'Harga belum diketahui', exact: true }).click()
      const unknownBox = p.getByRole('region', { name: 'Harga laundry belum diketahui' })
      const unknownShown = await unknownBox.getByText('Belum diketahui', { exact: true }).count()
      const label = ui.sql(`select c.label from erp.bd_laundry_charge_lines_v1 c join erp.bd_laundry_priced_lines_v1 l on l.delivery_line_id=c.delivery_line_id
        where l.delivery_id='${sent}' and c.rate_status='UNKNOWN' limit 1`)
      widths.unknown = await widthOk(p)
      await unknownBox.getByLabel('Alasan', { exact: true }).fill('T36 harga SPR dari vendor')
      await unknownBox.getByLabel(`Harga per PCS ${label}`, { exact: true }).fill('3000')
      const fillButton = unknownBox.getByRole('button', { name: `Isi harga ${label}`, exact: true })
      await fillButton.scrollIntoViewIfNeeded()
      const hit = await hitAt(fillButton)
      try { await fillButton.click({ timeout: 20000 }) } catch (e) {
        const diag = { hit, hit_again: await hitAt(fillButton), widths: { ...widths, at_error: await widthOk(p) }, after_send: afterSend }
        await phone.context.close()
        return { status: 'INCOMPLETE', error: String(e.message).slice(0, 400), diag }
      }
      await until(`select coalesce((select string_agg(total_known::text||'|'||total_complete::text,',') from erp.bd_laundry_priced_lines_v1 where delivery_id='${sent}'),'')`, '13000.00|true')
      await reload()
      const po = ui.sql(`select po_id from erp.laundry_deliveries where id='${sent}'`)
      const accrual = ui.sql(`select erp.desired_laundry_accrual('${po}')::text||'|'||coalesce((select sum(l.credit-l.debit) from erp.journal_lines l
        where l.po_id='${po}' and l.account_id=erp.account_id('ACCRUED_MANUFACTURING')),0)::text`)
      const afterFill = { state: state(), charges: charges(), accrual }
      widths.filled = await widthOk(p)
      await phone.context.close()
      const [desired, booked] = accrual.split('|').map(Number)
      const checks = {
        send_known_part_only: afterSend.state === '10000.00|false',
        mixed_coverage: afterSend.charges === 'GAR:2:KNOWN,SPR:1:UNKNOWN' || afterSend.charges.split(',').sort().join(',') === ['GAR:2:KNOWN', 'SPR:1:UNKNOWN'].join(','),
        unknown_listed_on_phone: unknownShown > 0,
        filled_complete: afterFill.state === '13000.00|true' && !afterFill.charges.includes('UNKNOWN'),
        accrual_matches: desired === booked,
        no_sideways_scroll: Object.values(widths).every(w => w.ok),
      }
      return { status: Object.values(checks).every(Boolean) ? 'PASS' : 'FAIL', checks, batch: ready.b.distribution_batch_id, size: ready.size.size_code,
        delivery: sent, after_send: afterSend, after_fill: afterFill, widths, hit }
    }],
    ['BD_BROWSER:D12_PAYMENT_SCREEN_DAILY_CLAIM', async () => {
      // D12 (owner 26 Sep 2026), daily claim: 2 PCS of a ready batch go to a fresh vendor (10,000,000 a piece), 1 comes back and is
      // invoiced (10,000,000); then the other piece is claimed MISSING (the reject is later than the invoice), approved with
      // 2,000,000 compensation. On the payment screen the owner applies the claim credit to that invoice and pays 8,000,000 cash:
      // the invoice row shows cash 8,000,000, claim credit 2,000,000, remaining 0 and "Lunas", the ledger line stays "Cocok" and
      // the vendor's AP is 0. The fixture (vendor, rate, laundry send/receive, invoice, claim) goes through the public RPCs; the
      // invoice policies LAU-DEC02/06 are set for the case and returned to pending at its end.
      const tag = 'D12' + randomUUID().replaceAll('-', '').slice(0, 10)
      const vendor = ui.sql(`insert into erp.laundry_vendors(vendor_code,vendor_name,is_active) values('${tag}','D12 laundry ${tag}',true) returning id`)
      const process = ui.sql(`insert into erp.wash_processes(process_code,process_name,is_active) values('${tag}','D12 cuci ${tag}',true) returning id`)
      ui.sql(`insert into erp.laundry_vendor_rate_versions(vendor_id,wash_process_id,rate_per_pcs,effective_from,notes) values('${vendor}','${process}',10000000,'2020-01-01','D12 browser rate')`)
      const owner = await ui.login('OWNER', { label: 'bd-d12-daily' })
      const call = async (fn, args) => { const r = await owner.rpc(fn, args); if (r.status !== 200) throw new Error(`${fn} ${r.status} ${JSON.stringify(r.body).slice(0, 400)}`); return r.body }
      const bd = (action, payload) => call('erp_save_laundry_bd_action_v1', { p_action: action, p_payload: payload, p_client_request_id: randomUUID() })
      const lq = (action, payload, version) => call('erp_save_laundry_qc_action_v1', { p_action: action, p_payload: payload, p_client_request_id: randomUUID(), p_expected_version: version })
      const bs = (action, payload, version) => call('erp_save_bs_resolution_action_v1', { p_action: action, p_payload: payload, p_client_request_id: randomUUID(), p_expected_version: version })
      const policy = async (key, value) => {
        const version = ui.sql(`select version from erp.bd_policy_settings_v1 where policy_key='${key}'`)
        return bd('SET_POLICY', { policy_key: key, operation: value ? 'SET' : 'CLEAR', expected_version: version, reason: 'D12 browser case', ...(value ? { value } : {}) })
      }
      const wib = back => ui.sql(`select to_char(clock_timestamp() at time zone 'Asia/Jakarta' - interval '${back} minutes','YYYY-MM-DD"T"HH24:MI:SS')`) + '+07:00'
      const dayNow = ui.sql(`select (clock_timestamp() at time zone 'Asia/Jakarta')::date`)
      const ready = ((await owner.rpc('erp_get_laundry_qc_workspace_v1', { p_scope: 'LAUNDRY', p_query: null })).body?.ready_batches ?? [])
        .map(b => ({ b, size: b.sizes.find(z => z.available_qty_pcs >= 2) })).filter(x => x.size)[0]
      if (!ready) { await owner.context.close(); return { status: 'FAIL', reason: 'no ready batch with 2 PCS available' } }
      await policy('LAU_DEC02', { billable: ['GOOD', 'BS', 'FAILED_ATTEMPT'] }); await policy('LAU_DEC06', { variance_mode: 'PRODUCT_COST', after_payment: 'REFUSE' })
      const sent = await lq('POST_DELIVERY', { distribution_batch_id: ready.b.distribution_batch_id, vendor_id: vendor, wash_process_id: process, target_dyeing_color: 'NAVY',
        physical_at: wib(30), reason: 'D12 kirim 2 PCS', lines: [{ size_id: ready.size.size_id, qty_sent_pcs: 2 }] }, String(ready.b.cutting_group_row_version))
      const delivery = sent.delivery_id
      const sizeLine = ui.sql(`select x.id from erp.laundry_delivery_batch_size_lines x join erp.laundry_delivery_lines l on l.id=x.delivery_line_id where l.delivery_id='${delivery}'`)
      const rec = await lq('POST_RECEIPT', { delivery_id: delivery, wash_process_id: process, physical_at: wib(20), reason: 'D12 kembali 1 PCS',
        lines: [{ delivery_batch_size_line_id: sizeLine, qty_good_received: 1, qty_bs_laundry: 0, bs_product_id: null }] },
        Number(ui.sql(`select row_version from erp.laundry_deliveries where id='${delivery}'`)))
      const receiptLine = ui.sql(`select id from erp.laundry_receipt_lines where receipt_id='${rec.receipt_id}'`)
      const number = 'INV-' + tag
      const draft = await bd('SAVE_INVOICE_DRAFT', { vendor_id: vendor, invoice_number: number, invoice_date: dayNow, header_total: '10000000.00',
        lines: [{ line_kind: 'BILL', receipt_line_id: receiptLine, category: 'GOOD', qty: 1, amount: '10000000.00' }] })
      const invoice = (await bd('POST_INVOICE', { invoice_id: draft.invoice_id, expected_version: draft.row_version })).invoice_id
      const claimNo = 'KL-' + tag
      await bs('SAVE_CLAIM', { action: 'SAVE', claim_number: claimNo, vendor_id: vendor, delivery_id: delivery, qty_claimed: 1, claim_type: 'MISSING',
        compensation_amount: 0, opened_at: wib(10), change_reason: 'D12 1 PCS tidak kembali' }, null)
      const claim = ui.sql(`select id from erp.laundry_claims where claim_number='${claimNo}'`)
      const version = () => Number(ui.sql(`select row_version from erp.laundry_claims where id='${claim}'`))
      await bs('SAVE_CLAIM', { id: claim, action: 'SAVE', status: 'ACCEPTED', compensation_amount: 2000000, resolution_date: dayNow, change_reason: 'D12 vendor setuju ganti' }, version())
      await bs('RESOLVE_CLAIM', { laundry_claim_id: claim, resolution: 'SETTLED', change_reason: 'D12 klaim disetujui' }, version())
      const sql = { credited: () => ui.sql(`select coalesce(sum(amount),0)::numeric(18,2) from erp.vendor_payments where vendor_invoice_id='${invoice}' and status='POSTED' and payment_method='CLAIM_CREDIT'`),
        remaining: () => ui.sql(`select (total_amount-coalesce((select sum(amount) from erp.vendor_payments where vendor_invoice_id=h.id and status='POSTED'),0))::numeric(18,2) from erp.vendor_invoices h where id='${invoice}'`) }
      // The invoice policies go back to pending even when a step fails, so later cases see the settings they expect.
      let screen
      try { screen = await payOnScreen(ui, owner, vendor, { id: invoice, number }, claim, dayNow, sql) }
      finally { await policy('LAU_DEC02', null); await policy('LAU_DEC06', null); await owner.context.close() }
      const state = ui.sql(`select status||'|'||(select coalesce(sum(l.credit-l.debit),0)::numeric(18,2) from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id
        where j.status in('POSTED','REVERSED') and l.account_id=erp.account_id('AP_VENDOR') and l.vendor_id='${vendor}') from erp.vendor_invoices where id='${invoice}'`)
      const ok = screenOk(screen, { number }) && state === 'PAID|0.00' && screen.width.ok
      return { status: ok ? 'PASS' : 'FAIL', invoice: number, claim: claimNo, screen, state }
    }],
    ['BD_BROWSER:D12_PAYMENT_SCREEN_OPENING_CLAIM', async () => {
      // D12, opening claim: the import holds an unpaid opening payable INV-LAMA 10,000,000 of the laundry vendor (dated 40 days
      // back) and a claim of 1 of its 8 pieces (12 days back, before cutover). After cutover the claim is approved with 2,000,000
      // (fixture, through the import facade); on the payment screen the owner applies the credit to the old payable and pays
      // 8,000,000 cash: the payable row shows cash 8,000,000, claim credit 2,000,000, remaining 0, "Lunas"; the ledger stays "Cocok".
      const owner = await ui.login('OWNER', { label: 'bd-d12-opening' })
      const rows = w05Rows(today)
      rows.OPENING_BALANCE_ITEM.push({ balance_type: 'VENDOR_PAYABLE', vendor_code: '{C}', amount: '10000000.00', control_key: 'VENDOR_PAYABLE',
        document_number: 'INV-LAMA-{C}', original_amount: '10000000.00', settled_before_cutover: '0.00', document_date: day(today, 40) })
      rows.OPENING_CONTROL.push({ control_key: 'VENDOR_PAYABLE', balance_type: 'VENDOR_PAYABLE', amount: '10000000.00' })
      const { batch, code } = await importBatch(owner, today, rows)
      const vendor = ui.sql(`select id from erp.laundry_vendors where vendor_code='${code}'`)
      const ws = (await owner.rpc('erp_get_initial_import_workspace_v1', { p_batch_id: batch })).body.batch
      const src = ws.production_sources.find(x => x.balance_type === 'WIP'), claim = src.bd.claims[0]
      const dayNow = ui.sql(`select (clock_timestamp() at time zone 'Asia/Jakarta')::date`)
      const r = await owner.rpc('erp_save_initial_import_action_v1', { p_action: 'WIP_OUTPUT', p_client_request_id: randomUUID(), p_payload: { batch_id: batch,
        opening_item_id: src.opening_item_id, expected_remaining: String(src.remaining_qty_pcs), operation: 'RESOLVE_CLAIM', reason: 'D12 klaim saldo awal disetujui',
        claim_id: claim.claim_id, expected_version: claim.row_version, resolution: 'SETTLED', compensation_amount: '2000000.00', date: dayNow } })
      if (r.status !== 200) throw new Error('D12 resolve ' + JSON.stringify(r.body).slice(0, 400))
      const event = ui.sql(`select e.id from erp.bd_opening_laundry_claim_events_v1 e where e.claim_id='${claim.claim_id}' and e.event_kind='RESOLVE' and e.reversed_at is null`)
      const balance = ui.sql(`select id from erp.opening_subledger_balances where vendor_id='${vendor}' and party_type='VENDOR' and direction='PAYABLE'`)
      const number = 'INV-LAMA-' + code
      const sql = { credited: () => ui.sql(`select coalesce(sum(s.amount),0)::numeric(18,2) from erp.opening_subledger_settlements s join erp.bb_opening_credits_v1 c on c.settlement_id=s.id
          where s.balance_id='${balance}' and s.status='POSTED' and c.credit_kind='VENDOR_CLAIM_APPLY'`),
        remaining: () => ui.sql(`select (original_amount-settled_amount)::numeric(18,2) from erp.opening_subledger_balances where id='${balance}'`) }
      let screen
      try { screen = await payOnScreen(ui, owner, vendor, { id: balance, number }, event, dayNow, sql) } finally { await owner.context.close() }
      const state = ui.sql(`select status||'|'||(select coalesce(sum(l.credit-l.debit),0)::numeric(18,2) from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id
        where j.status in('POSTED','REVERSED') and l.account_id=erp.account_id('AP_VENDOR') and l.vendor_id='${vendor}') from erp.opening_subledger_balances where id='${balance}'`)
      const ok = screenOk(screen, { number }) && state === 'SETTLED|0.00' && screen.width.ok
      return { status: ok ? 'PASS' : 'FAIL', payable: number, screen, state }
    }],
    ['BD_BROWSER:D08_LAUNDRY_QC_CANONICAL_IDS', async () => {
      // D08: the seeded CP3 mandor/model rows stay active. The Laundry read carries a ready batch of the seeded mandor; the case
      // sends it from the Laundry page to a fresh v4 vendor and process (per-PCS rate, no BD terms) and receives it back as Good,
      // so the QC read then carries the seeded ids too. Both pages must load with no error and no "bukan UUID valid".
      const rfc = "'^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'"
      const seeds = () => ui.sql(`select (select count(*) from erp.contractors where is_active and id::text !~* ${rfc})||'|'||(select count(*) from erp.product_models where id::text !~* ${rfc})`)
      const before = seeds()
      const owner = await ui.login('OWNER', { label: 'bd-d08' })
      const rawRead = async scope => owner.rpc('erp_get_laundry_qc_workspace_v1', { p_scope: scope, p_query: null })
      const read = async scope => {
        const r = await rawRead(scope)
        if (r.status !== 200) return { status: r.status, non_rfc: 0, v4: 0 }
        const ids = idsIn(r.body)
        return { status: r.status, non_rfc: ids.non_rfc.size, v4: ids.v4.size, non_rfc_sample: [...ids.non_rfc].sort().slice(0, 3) }
      }
      const page = async (item, heading) => {
        const p = await openPage(ui, owner, 'Produksi', item, heading)
        let loaded = false
        try { await ui.expect(p.locator('.clq-loading')).toHaveCount(0, { timeout: 20000 }); loaded = true } catch { loaded = false }
        const uuidError = await p.getByText(/bukan UUID valid/).count()
        return { p, view: { loaded, error: await laundryRead(p), uuid_error_text: uuidError } }
      }
      const laundryIds = await read('LAUNDRY'), qcBefore = await read('QC')
      const { p, view: laundry } = await page('Laundry', 'Laundry')
      // A ready batch of a seeded mandor, sent and received through the page.
      const ready = ((await rawRead('LAUNDRY')).body?.ready_batches ?? []).find(b => !RFC.test(b.contractor_id) && b.sizes.some(z => z.available_qty_pcs > 0))
      let flow = { ready_batch: ready?.distribution_batch_id ?? null }
      if (ready) {
        const tag = 'D08' + randomUUID().replaceAll('-', '').slice(0, 10)
        const vendor = ui.sql(`insert into erp.laundry_vendors(vendor_code,vendor_name,is_active) values('${tag}','D08 laundry ${tag}',true) returning id`)
        const process = ui.sql(`insert into erp.wash_processes(process_code,process_name,is_active) values('${tag}','D08 cuci ${tag}',true) returning id`)
        ui.sql(`insert into erp.laundry_vendor_rate_versions(vendor_id,wash_process_id,rate_per_pcs,effective_from,notes) values('${vendor}','${process}',1000,'2020-01-01','D08 browser rate')`)
        const wib = back => ui.sql(`select to_char(clock_timestamp() at time zone 'Asia/Jakarta' - interval '${back} minutes','YYYY-MM-DD"T"HH24:MI')`)
        await p.getByRole('button', { name: 'Muat ulang data', exact: true }).click()
        await ui.expect(p.getByRole('button', { name: 'Muat ulang data', exact: true })).toBeEnabled({ timeout: 20000 })
        await p.getByRole('button', { name: 'Kirim ke Laundry', exact: true }).click()
        await p.getByLabel('BATCH DISTRIBUSI AUTHORITATIVE', { exact: true }).selectOption(ready.distribution_batch_id)
        await p.getByRole('button', { name: 'Isi dari sisa siap', exact: true }).click()
        await p.getByRole('combobox', { name: /^VENDOR LAUNDRY/ }).selectOption(vendor)
        await p.getByLabel('PROSES CUCI TARGET', { exact: true }).selectOption(process)
        await p.getByLabel('WARNA TARGET', { exact: true }).fill('NAVY')
        await p.getByLabel('WAKTU FISIK KELUAR', { exact: true }).fill(wib(3))
        await p.getByLabel('ALASAN / BUKTI SERAH TERIMA', { exact: true }).fill('D08 kirim batch mandor seed')
        await p.locator('.clq-confirm input').check()
        await p.getByRole('button', { name: 'Post pengiriman atomic', exact: true }).click()
        // The vendor is this case's own, so its one delivery is the batch just sent.
        const delivery = () => ui.sql(`select coalesce((select id::text from erp.laundry_deliveries where vendor_id='${vendor}' and status<>'REVERSED' limit 1),'')`)
        await ui.expect.poll(delivery, { timeout: 20000 }).not.toBe('')
        const sent = delivery()
        await ui.expect(p.getByRole('button', { name: 'Muat ulang data', exact: true })).toBeEnabled({ timeout: 20000 })
        await p.getByRole('button', { name: 'Terima kembali', exact: true }).click()
        await p.getByLabel('SURAT KIRIM AKTIF', { exact: true }).selectOption(sent)
        await p.getByLabel('PROSES AKTUAL', { exact: true }).selectOption(process)
        await p.getByLabel('WAKTU FISIK KEMBALI', { exact: true }).fill(wib(1))
        await p.getByLabel('ALASAN / BUKTI PENERIMAAN', { exact: true }).fill('D08 terima batch mandor seed')
        const lines = ui.sql(`select coalesce(string_agg(s.size_code||'='||x.qty_sent_pcs, ',' order by s.size_code), '') from erp.laundry_delivery_batch_size_lines x
          join erp.laundry_delivery_lines l on l.id=x.delivery_line_id join erp.sizes s on s.id=x.size_id where l.delivery_id='${sent}'`)
        for (const pair of lines.split(',').filter(Boolean)) {
          const [code, qty] = pair.split('=')
          await p.getByLabel(`Good kembali size ${code}`, { exact: true }).fill(qty)
        }
        await p.locator('.clq-confirm input').check()
        await p.getByRole('button', { name: 'Post penerimaan atomic', exact: true }).click()
        const received = () => ui.sql(`select count(*) from erp.laundry_receipts where delivery_id='${sent}' and status='POSTED'`)
        await ui.expect.poll(received, { timeout: 20000 }).toBe('1')
        flow = { ...flow, delivery: sent, sizes: lines, receipts: received(), contractor: ready.contractor_id }
      }
      const qcIds = await read('QC')
      const { view: qc } = await page('QC & Final SKU', 'QC & Final SKU')
      await owner.context.close()
      const after = seeds()
      const [mandors] = before.split('|').map(Number)
      const ok = mandors > 0 && after === before && laundryIds.status === 200 && qcIds.status === 200 && Boolean(flow.delivery) && flow.receipts === '1'
        && laundryIds.non_rfc > 0 && laundryIds.v4 > 0 && qcIds.non_rfc > 0 && qcIds.v4 > 0
        && laundry.loaded && laundry.error === 'OK' && laundry.uuid_error_text === 0 && qc.loaded && qc.error === 'OK' && qc.uuid_error_text === 0
      return { status: ok ? 'PASS' : 'FAIL', seeds_active_before_after: [before, after], laundry_read_ids: laundryIds, qc_read_ids_before_flow: qcBefore,
        qc_read_ids: qcIds, flow, laundry, qc }
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
    ['BD_BROWSER:DEC06_CORRECTION_UP_DOWN_ON_SCREEN', async () => {
      // Owner decision no. 13 (LAU-DEC06 PRODUCT_COST + CORRECTION_DOCUMENT) from the screen: 1 PCS of a ready batch goes to a fresh
      // vendor at 7,000 and comes back; invoice INV 7,000 is posted and paid in full (fixture through the public RPCs). On the
      // invoice screen the owner then posts an upward correction +2,000 and a downward correction -1,500, both linked to INV (its
      // sources are INV's billed lines). On the payment screen the downward correction's credit settles 1,500 of the upward one and
      // 500 is paid in cash: the upward row shows correction credit 1,500, cash 500, remaining 0 and "Lunas", the credit row names
      // INV, the ledger line stays "Cocok", AP 0; INV keeps its status and its one cash payment. Runs last (it takes 1 PCS).
      const tag = 'D13' + randomUUID().replaceAll('-', '').slice(0, 10)
      const vendor = ui.sql(`insert into erp.laundry_vendors(vendor_code,vendor_name,is_active) values('${tag}','D13 laundry ${tag}',true) returning id`)
      const process = ui.sql(`insert into erp.wash_processes(process_code,process_name,is_active) values('${tag}','D13 cuci ${tag}',true) returning id`)
      ui.sql(`insert into erp.laundry_vendor_rate_versions(vendor_id,wash_process_id,rate_per_pcs,effective_from,notes) values('${vendor}','${process}',7000,'2020-01-01','D13 browser rate')`)
      const owner = await ui.login('OWNER', { label: 'bd-d13-correction' })
      const call = async (fn, args) => { const r = await owner.rpc(fn, args); if (r.status !== 200) throw new Error(`${fn} ${r.status} ${JSON.stringify(r.body).slice(0, 400)}`); return r.body }
      const bd = (action, payload) => call('erp_save_laundry_bd_action_v1', { p_action: action, p_payload: payload, p_client_request_id: randomUUID() })
      const lq = (action, payload, version) => call('erp_save_laundry_qc_action_v1', { p_action: action, p_payload: payload, p_client_request_id: randomUUID(), p_expected_version: version })
      const policy = async (key, value) => {
        const version = ui.sql(`select version from erp.bd_policy_settings_v1 where policy_key='${key}'`)
        return bd('SET_POLICY', { policy_key: key, operation: value ? 'SET' : 'CLEAR', expected_version: version, reason: 'D13 browser case', ...(value ? { value } : {}) })
      }
      const wib = back => ui.sql(`select to_char(clock_timestamp() at time zone 'Asia/Jakarta' - interval '${back} minutes','YYYY-MM-DD"T"HH24:MI:SS')`) + '+07:00'
      const dayNow = ui.sql(`select (clock_timestamp() at time zone 'Asia/Jakarta')::date`)
      const ready = ((await owner.rpc('erp_get_laundry_qc_workspace_v1', { p_scope: 'LAUNDRY', p_query: null })).body?.ready_batches ?? [])
        .map(b => ({ b, size: b.sizes.find(z => z.available_qty_pcs >= 1) })).filter(x => x.size)[0]
      if (!ready) { await owner.context.close(); return { status: 'FAIL', reason: 'no ready batch with 1 PCS available' } }
      await policy('LAU_DEC02', { billable: ['GOOD', 'BS', 'FAILED_ATTEMPT'] }); await policy('LAU_DEC06', { variance_mode: 'PRODUCT_COST', after_payment: 'CORRECTION_DOCUMENT' })
      let result
      try {
        const sent = await lq('POST_DELIVERY', { distribution_batch_id: ready.b.distribution_batch_id, vendor_id: vendor, wash_process_id: process, target_dyeing_color: 'NAVY',
          physical_at: wib(30), reason: 'D13 kirim 1 PCS', lines: [{ size_id: ready.size.size_id, qty_sent_pcs: 1 }] }, String(ready.b.cutting_group_row_version))
        const sizeLine = ui.sql(`select x.id from erp.laundry_delivery_batch_size_lines x join erp.laundry_delivery_lines l on l.id=x.delivery_line_id where l.delivery_id='${sent.delivery_id}'`)
        const rec = await lq('POST_RECEIPT', { delivery_id: sent.delivery_id, wash_process_id: process, physical_at: wib(20), reason: 'D13 kembali 1 PCS',
          lines: [{ delivery_batch_size_line_id: sizeLine, qty_good_received: 1, qty_bs_laundry: 0, bs_product_id: null }] },
          Number(ui.sql(`select row_version from erp.laundry_deliveries where id='${sent.delivery_id}'`)))
        const receiptLine = ui.sql(`select id from erp.laundry_receipt_lines where receipt_id='${rec.receipt_id}'`)
        const number = 'INV-' + tag
        const draft = await bd('SAVE_INVOICE_DRAFT', { vendor_id: vendor, invoice_number: number, invoice_date: dayNow, header_total: '7000.00',
          lines: [{ line_kind: 'BILL', receipt_line_id: receiptLine, category: 'GOOD', qty: 1, amount: '7000.00' }] })
        const origin = (await bd('POST_INVOICE', { invoice_id: draft.invoice_id, expected_version: draft.row_version })).invoice_id
        const cashAccount = ui.sql(`select id from erp.cash_accounts where is_active order by cash_account_code limit 1`)
        await bd('PAY_VENDOR_DOCUMENT', { target_kind: 'VENDOR_INVOICE', target_id: origin, amount: '7000.00', date: dayNow, cash_account_id: cashAccount, reason: 'D13 bayar lunas' })
        const originRow = () => ui.sql(`select h.status||'|'||(select string_agg(p.payment_method||':'||p.amount::text||':'||p.status,',' order by p.id) from erp.vendor_payments p where p.vendor_invoice_id=h.id) from erp.vendor_invoices h where h.id='${origin}'`)
        const origin0 = originRow()
        const p = await openPricing(ui, owner)
        const reload = async () => ui.expect(p.getByRole('button', { name: 'Muat ulang harga', exact: true })).toBeEnabled({ timeout: 20000 })
        await p.getByLabel('Vendor harga laundry', { exact: true }).selectOption(vendor); await reload()
        const correct = async (docNumber, amount) => {
          await p.getByRole('button', { name: 'Invoice vendor', exact: true }).click()
          const box = p.getByRole('region', { name: 'Invoice vendor laundry' })
          await box.getByLabel('Koreksi atas invoice', { exact: true }).selectOption(origin)
          await box.getByLabel('Nomor invoice vendor', { exact: true }).fill(docNumber)
          await box.getByLabel('Tanggal invoice', { exact: true }).fill(dayNow)
          await box.getByLabel('Total invoice', { exact: true }).fill(amount)
          await box.getByRole('button', { name: 'Tambah baris', exact: true }).click()
          await box.getByLabel('Sumber baris 1', { exact: true }).selectOption('r:' + receiptLine)
          await box.getByLabel('Nominal baris 1', { exact: true }).fill(amount)
          await box.getByRole('button', { name: 'Simpan draf invoice', exact: true }).click()
          const state = () => ui.sql(`select coalesce((select status from erp.bd_laundry_invoices_v1 where vendor_id='${vendor}' and invoice_number='${docNumber}' and status<>'CANCELLED'),'-')`)
          await ui.expect.poll(state, { timeout: 20000 }).toBe('DRAFT'); await reload()
          await p.getByRole('button', { name: 'Invoice vendor', exact: true }).click()
          await p.getByRole('region', { name: 'Invoice vendor laundry' }).getByRole('button', { name: `Posting ${docNumber}`, exact: true }).click()
          await ui.expect.poll(state, { timeout: 20000 }).toBe('POSTED'); await reload()
          return ui.sql(`select id from erp.bd_laundry_invoices_v1 where vendor_id='${vendor}' and invoice_number='${docNumber}' and status='POSTED'`)
        }
        const up = await correct('KN-' + tag, '2000'), down = await correct('KT-' + tag, '-1500')
        const links = ui.sql(`select string_agg(invoice_number||':'||header_total::text||':'||(corrects_invoice_id='${origin}')::text,',' order by header_total desc) from erp.bd_laundry_invoices_v1 where id in('${up}','${down}')`)
        await p.getByRole('button', { name: 'Pembayaran vendor', exact: true }).click()
        const box = p.getByRole('region', { name: 'Pembayaran vendor laundry' })
        const common = async () => {
          await box.getByLabel('Tagihan dilunasi', { exact: true }).selectOption(up)
          await box.getByLabel('Tanggal pelunasan', { exact: true }).fill(dayNow)
          await box.getByLabel('Alasan pelunasan', { exact: true }).fill('D13 pelunasan koreksi naik')
        }
        await common()
        await box.getByLabel('Kredit klaim dipakai', { exact: true }).selectOption(down)
        await box.getByLabel('Nominal kredit klaim', { exact: true }).fill('1500')
        await box.getByRole('button', { name: 'Pakai kredit klaim', exact: true }).click()
        const credited = () => ui.sql(`select coalesce(sum(amount),0)::numeric(18,2) from erp.vendor_payments where vendor_invoice_id='${up}' and status='POSTED' and payment_method='CORRECTION_CREDIT'`)
        await ui.expect.poll(credited, { timeout: 20000 }).toBe('1500.00'); await reload()
        await common()
        const cash = await box.getByLabel('Rekening kas pembayaran', { exact: true }).locator('option').nth(1).getAttribute('value')
        await box.getByLabel('Rekening kas pembayaran', { exact: true }).selectOption(cash)
        await box.getByLabel('Nominal bayar kas', { exact: true }).fill('500')
        await box.getByRole('button', { name: 'Bayar kas', exact: true }).click()
        const remaining = () => ui.sql(`select (total_amount-coalesce((select sum(amount) from erp.vendor_payments where vendor_invoice_id=h.id and status='POSTED'),0))::numeric(18,2) from erp.vendor_invoices h where id='${up}'`)
        await ui.expect.poll(remaining, { timeout: 20000 }).toBe('0.00'); await reload()
        const ledger = (await box.getByRole('status').innerText()).trim()
        const row = (await box.getByRole('table', { name: 'Tagihan vendor' }).locator('tbody tr').filter({ hasText: 'KN-' + tag }).innerText()).replace(/\s+/g, ' ').trim()
        const creditRow = (await box.getByRole('table', { name: 'Kredit klaim vendor' }).locator('tbody tr').filter({ hasText: 'KT-' + tag }).innerText()).replace(/\s+/g, ' ').trim()
        const ap = ui.sql(`select coalesce(sum(l.credit-l.debit),0)::numeric(18,2) from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id
          where j.status in('POSTED','REVERSED') and l.account_id=erp.account_id('AP_VENDOR') and l.vendor_id='${vendor}'`)
        const origin1 = originRow(), width = await widthOk(p)
        const checks = {
          linked_documents: links === `KN-${tag}:2000.00:true,KT-${tag}:-1500.00:true`,
          screen_row: row.includes(`koreksi naik atas ${number}`) && row.includes('Rp 1.500,00') && row.includes('Rp 500,00') && row.includes('Lunas'),
          credit_row: creditRow.includes(`koreksi turun atas ${number}`) && creditRow.includes('Rp 1.500,00'),
          ledger_matches: ledger.startsWith('Cocok') && ap === '0.00',
          origin_untouched: origin0 === origin1 && origin0 === 'PAID|CASH:7000.00:POSTED',
          no_sideways_scroll: width.ok,
        }
        result = { status: Object.values(checks).every(Boolean) ? 'PASS' : 'FAIL', checks, links, row, credit_row: creditRow, ledger, ap, origin: origin1 }
      } finally { await policy('LAU_DEC02', null); await policy('LAU_DEC06', null); await owner.context.close() }
      return result
    }],
  ]
}
