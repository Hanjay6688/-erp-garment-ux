// BC (writer): the accessory service page (Gudang · Aksesori), its policy settings and the import page's opening accessory
// section in a real browser (auditor round 11, item 4: "browser"), run by the browser mode of the auditor runtime
// (cp6-auditor-scenario.yml, browser_path scripts/cp6_bc_browser.mjs, phase after). Fixtures are made with SQL on the
// disposable copy and the public RPCs; every business action is taken only through the page; results are read back with SQL.
// Label WRITER_SCENARIO: not independent evidence.
// Oracles: filling a service post with 5 of 20 leaves 15 in the warehouse and 5 at the post with no journal, and its reversal
// from the document detail restores 20/0; an owner sets ACC-DEC05 from the settings (status SET, version +1) and clears it
// back to PENDING_POLICY_VALUE (version +2); a posted import with ALL-C03 custody shows the four custody kinds on the import page.
// The note page (Nota Ambil Aksesori) is not driven here: on this chain its read is refused by the pre-existing finding F3
// (seeded contractors with non RFC-4122 ids); its parser is covered by the probe's workspace parse and vitest.
import { randomUUID } from 'node:crypto'

const day = (today, back) => { const d = new Date(`${today}T00:00:00Z`); d.setUTCDate(d.getUTCDate() - back); return d.toISOString().slice(0, 10) }
const code = () => 'BCB' + randomUUID().replaceAll('-', '').slice(0, 11).toUpperCase()

async function call(user, name, args) {
  const r = await user.rpc(name, args)
  if (r.status !== 200) throw new Error(`${name} ${r.status} ${JSON.stringify(r.body).slice(0, 600)}`)
  return r.body
}

/** An accessory counted in PCS with a main warehouse (stock imported through the import RPC) and the three BC areas. */
async function accessoryFixture(ui, owner, today, qty = '20') {
  const c = code()
  const pcs = ui.sql("select unit_code from erp.uom_definitions where upper(unit_code)='PCS' and dimension='COUNT' and is_active limit 1")
  ui.sql(`with cat as (insert into erp.accessory_categories(category_code,category_name,base_uom_code,is_active) values('${c}','BC kancing browser ${c}','${pcs}',true) returning id)
    insert into erp.materials(material_sku,material_name,material_type,unit_code,accessory_category_id) select '${c}','BC kancing browser ${c}','ACCESSORY','${pcs}',id from cat`)
  ui.sql(`insert into erp.locations(location_code,location_name,location_type,is_active) values('${c}W','BC gudang ${c}','RAW_MATERIAL_WAREHOUSE',true)`)
  for (const kind of ['SERVICE_POST', 'INSPECTION', 'DAMAGED']) {
    await call(owner, 'erp_save_accessory_service_action_v1', { p_action: 'REGISTER_ZONE', p_client_request_id: randomUUID(),
      p_payload: { zone_kind: kind, location_code: c + kind.slice(0, 2), location_name: `BC ${kind} ${c}`, reason: 'BC browser area' } })
  }
  const batchCode = 'BCI' + randomUUID().replaceAll('-', '').slice(0, 11)
  const act = (action, payload) => call(owner, 'erp_save_initial_import_action_v1', { p_action: action, p_payload: payload, p_client_request_id: randomUUID() })
  const ws = async batch => (await call(owner, 'erp_get_initial_import_workspace_v1', { p_batch_id: batch })).batch
  const batch = (await act('CREATE', { batch_code: batchCode, cutover_date: day(today, 10) })).batch_id
  const rows = { OPENING_BALANCE_ITEM: [{ balance_type: 'MATERIAL', material_sku: c, location_code: c + 'W', qty, unit_cost: '2.00', control_key: 'STOCK', opening_source_key: 'BCB' }],
    OPENING_CONTROL: [{ control_key: 'STOCK', balance_type: 'MATERIAL', qty, amount: (Number(qty) * 2).toFixed(2) }] }
  for (const [entity, list] of Object.entries(rows)) await act('SAVE_FILE', { batch_id: batch, expected_revision: (await ws(batch)).revision, entity, filename: entity + '.csv',
    rows: list.map((payload, i) => ({ source_row_no: i + 2, payload })) })
  const checked = await act('VALIDATE', { batch_id: batch, expected_revision: (await ws(batch)).revision })
  if (checked.error_rows !== 0) throw new Error('BC_BROWSER_FIXTURE_REFUSED ' + JSON.stringify((await ws(batch)).rows.filter(r => r.errors.length).map(r => [r.entity, r.errors])).slice(0, 1200))
  if ((await act('FINALIZE', { batch_id: batch, expected_revision: (await ws(batch)).revision })).status !== 'POSTED') throw new Error('BC_BROWSER_FIXTURE_NOT_POSTED')
  const q = s => ui.sql(s)
  return { code: c, batch, material: q(`select id from erp.materials where material_sku='${c}'`), main: q(`select id from erp.locations where location_code='${c}W'`),
    post: q(`select id from erp.locations where location_code='${c}SE'`) }
}

async function openAccessories(ui, owner) {
  const p = owner.page
  const menu = p.getByRole('button', { name: 'Buka menu', exact: true }); if (await menu.isVisible()) await menu.click()
  const link = p.getByRole('button', { name: '• Aksesori', exact: true })
  if (!await link.isVisible()) await p.locator('.sidebar .nav-main').filter({ hasText: 'Gudang' }).click()
  await link.click()
  await ui.expect(p.getByRole('heading', { name: 'Pemakaian & Pengembalian Aksesori', exact: true })).toBeVisible()
  await ui.expect(p.getByRole('button', { name: 'Muat ulang', exact: true })).toBeEnabled()
  return p
}

const stock = (ui, fx, location) => ui.sql(`select coalesce(sum(qty_signed),0)::numeric(24,0) from erp.material_stock_movements where material_id='${fx.material}' and location_id='${location}'`)

export async function cases(ui, today) {
  return [
    ['BC_BROWSER:FILL_POST_AND_REVERSE', async () => {
      const owner = await ui.login('OWNER', { label: 'bc-fill' })
      const fx = await accessoryFixture(ui, owner, today)
      const journals = () => ui.sql("select count(*) from erp.journal_entries where source_type in('MATERIAL_TRANSFER')")
      const j0 = journals()
      const p = await openAccessories(ui, owner)
      await p.getByLabel('Cari stok aksesori').fill(fx.code)
      await p.getByRole('button', { name: 'Cari stok', exact: true }).click()
      await ui.expect(p.getByRole('cell', { name: new RegExp(fx.code) }).first()).toBeVisible()
      await p.getByRole('button', { name: 'Catat transaksi', exact: true }).click()
      await p.getByLabel('Jenis transaksi aksesori').selectOption('FILL_POST')
      await p.getByLabel('Gudang asal').selectOption(fx.main)
      await p.getByLabel('Pos servis tujuan').selectOption(fx.post)
      await p.getByLabel('Waktu fisik (WIB)').fill(`${day(today, 1)}T09:00:00`)
      await p.getByLabel('Aksesori baris 1').selectOption(fx.material)
      await p.getByLabel('Jumlah baris 1').fill('5')
      await p.getByLabel('Alasan transaksi').fill('Isi pos servis dari browser')
      await p.getByRole('button', { name: 'Periksa transaksi', exact: true }).click()
      await p.getByRole('button', { name: 'Sahkan isi pos servis', exact: true }).click()
      await ui.expect.poll(() => stock(ui, fx, fx.post), { timeout: 20000 }).toBe('5')
      const filled = { main: stock(ui, fx, fx.main), post: stock(ui, fx, fx.post), journals: Number(journals()) - Number(j0) }
      const number = ui.sql(`select document_number from erp.bc_documents_v1 where action='FILL_POST' and payload->'items'->0->>'material_id'='${fx.material}'`)
      await p.getByRole('button', { name: 'Dokumen', exact: true }).click()
      await p.getByRole('button', { name: `Buka ${number}`, exact: true }).click()
      await ui.expect(p.getByRole('heading', { name: new RegExp(number) })).toBeVisible()
      await p.getByLabel('Alasan dokumen aksesori').fill('Salah pos, dibatalkan dari browser')
      await p.getByRole('button', { name: 'Periksa pembatalan', exact: true }).click()
      await p.getByRole('button', { name: `Sahkan pembatalan ${number}`, exact: true }).click()
      await ui.expect.poll(() => stock(ui, fx, fx.post), { timeout: 20000 }).toBe('0')
      const reversed = { main: stock(ui, fx, fx.main), post: stock(ui, fx, fx.post), status: ui.sql(`select status from erp.bc_documents_v1 where document_number='${number}'`) }
      await owner.context.close()
      const ok = filled.main === '15' && filled.post === '5' && filled.journals === 0 && reversed.main === '20' && reversed.post === '0' && reversed.status === 'REVERSED'
      return { status: ok ? 'PASS' : 'FAIL', filled, reversed, document: number }
    }],
    ['BC_BROWSER:POLICY_SET_AND_CLEAR_BY_OWNER', async () => {
      const owner = await ui.login('OWNER', { label: 'bc-policy' })
      const read = () => ui.sql("select status||'|'||version from erp.bc_policy_settings_v1 where policy_key='ACC_DEC05'")
      const [status0, version0] = read().split('|')
      const p = await openAccessories(ui, owner)
      await p.getByRole('button', { name: 'Kebijakan & area', exact: true }).click()
      await p.getByLabel('Kebijakan yang diubah').selectOption('ACC-DEC05')
      await p.getByLabel('Cara kredit retur').selectOption('CREDIT_UNPAID_ONLY')
      await p.getByLabel('Kondisi dikredit').fill('USABLE')
      await p.getByLabel('Alasan kebijakan aksesori').fill('Keputusan owner di browser')
      await p.getByRole('button', { name: 'Tetapkan ACC-DEC05', exact: true }).click()
      await ui.expect.poll(read, { timeout: 20000 }).toBe(`SET|${Number(version0) + 1}`)
      await ui.expect(p.getByRole('row', { name: /ACC-DEC05.*Ditetapkan/ })).toBeVisible()
      // The page reloads after a saved change; the settings form starts again from the first policy.
      await p.getByLabel('Kebijakan yang diubah').selectOption('ACC-DEC05')
      await p.getByLabel('Alasan kebijakan aksesori').fill('Owner menunda keputusan di browser')
      await p.getByRole('button', { name: 'Kembalikan ACC-DEC05 ke menunggu', exact: true }).click()
      await ui.expect.poll(read, { timeout: 20000 }).toBe(`PENDING_POLICY_VALUE|${Number(version0) + 2}`)
      await owner.context.close()
      return { status: status0 === 'PENDING_POLICY_VALUE' ? 'PASS' : 'FAIL', start: status0, end: read() }
    }],
    ['BC_BROWSER:IMPORT_PAGE_OPENING_ACCESSORIES', async () => {
      const owner = await ui.login('OWNER', { label: 'bc-import' })
      const fx = await accessoryFixture(ui, owner, today, '4')
      const c = code(), act = (action, payload) => call(owner, 'erp_save_initial_import_action_v1', { p_action: action, p_payload: payload, p_client_request_id: randomUUID() })
      const ws = async batch => (await call(owner, 'erp_get_initial_import_workspace_v1', { p_batch_id: batch })).batch
      const batch = (await act('CREATE', { batch_code: c, cutover_date: day(today, 10) })).batch_id
      const rows = { CUSTOMER: [{ customer_code: c, customer_name: 'BC pelanggan browser' }],
        OPENING_BALANCE_ITEM: [{ balance_type: 'MATERIAL', material_sku: fx.code, location_code: fx.code + 'IN', qty: '2', unit_cost: '2.00', control_key: 'STOCK', opening_source_key: 'KARANTINA' }],
        OPENING_CONTROL: [{ control_key: 'STOCK', balance_type: 'MATERIAL', qty: '2', amount: '4.00' }],
        OPENING_ACCESSORY_CUSTODY: [
          { custody_kind: 'PENDING_VALUE', custody_key: c + '-K1', material_sku: fx.code, location_code: fx.code + 'IN', condition: 'WAITING', qty: '4', notes: 'bongkaran lama' },
          { custody_kind: 'UNRETURNED', custody_key: c + '-K2', material_sku: fx.code, qty: '1', holder: 'Pak Budi', owner_kind: 'COMPANY' },
          { custody_kind: 'CUSTOMER_GARMENT', custody_key: c + '-K3', customer_code: c, description: 'Celana pelanggan browser', qty: '1' }] }
      for (const [entity, list] of Object.entries(rows)) await act('SAVE_FILE', { batch_id: batch, expected_revision: (await ws(batch)).revision, entity, filename: entity + '.csv',
        rows: list.map((payload, i) => ({ source_row_no: i + 2, payload })) })
      const checked = await act('VALIDATE', { batch_id: batch, expected_revision: (await ws(batch)).revision })
      if (checked.error_rows !== 0) throw new Error('BC_BROWSER_IMPORT_REFUSED ' + JSON.stringify((await ws(batch)).rows.filter(r => r.errors.length).map(r => [r.entity, r.errors])).slice(0, 1200))
      await act('FINALIZE', { batch_id: batch, expected_revision: (await ws(batch)).revision })
      const p = owner.page
      const menu = p.getByRole('button', { name: 'Buka menu', exact: true }); if (await menu.isVisible()) await menu.click()
      const link = p.getByRole('button', { name: '• Impor data awal', exact: true })
      if (!await link.isVisible()) await p.locator('.sidebar .nav-main').filter({ hasText: 'Pengaturan & Audit' }).click()
      await link.click()
      await ui.expect(p.getByRole('heading', { name: 'Impor data awal', exact: true })).toBeVisible()
      await p.getByLabel('Batch impor').selectOption(batch)
      await ui.expect(p.getByRole('heading', { name: 'Aksesori saldo awal' })).toBeVisible()
      const seen = {}
      for (const [label, text] of [['pending', 'Titipan belum dinilai'], ['quarantine', 'Area pemeriksaan (bernilai di buku)'], ['unreturned', 'Belum kembali'], ['customer', 'Titipan pelanggan']])
        seen[label] = await p.getByRole('cell', { name: text, exact: true }).first().isVisible()
      await owner.context.close()
      return { status: Object.values(seen).every(Boolean) ? 'PASS' : 'FAIL', seen }
    }],
  ]
}
