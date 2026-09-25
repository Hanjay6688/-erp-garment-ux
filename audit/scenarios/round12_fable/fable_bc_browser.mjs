// Fable BC round 12, item 2 (browser, own case): the stock search carried into the Dokumen tab is VISIBLE and CLEARABLE (fix 27e1a05 of GPT-BC-01),
// and while it is active a document whose number does not match the SKU text is hidden (the symptom), then appears after "Hapus pencarian" without
// typing its number. Helpers below are copied from the writer's cp6_bc_browser.mjs (fixture, navigation); the oracle and the case are the auditor's.
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

async function openNotes(ui, user) {
  const p = user.page
  const menu = p.getByRole('button', { name: 'Buka menu', exact: true }); if (await menu.isVisible()) await menu.click()
  const link = p.getByRole('button', { name: '• Nota Ambil Aksesori', exact: true })
  if (!await link.isVisible()) await p.locator('.sidebar .nav-main').filter({ hasText: 'Keuangan' }).click()
  await link.click()
  await ui.expect(p.getByRole('heading', { name: 'Nota Ambil Aksesori', exact: true })).toBeVisible()
  await ui.expect(p.getByRole('button', { name: 'Muat ulang', exact: true })).toBeEnabled()
  return p
}

/** Fills a new note of `qty` PCS at 3.00 for the fixture's accessory; returns the note number. */
async function fillNote(ui, p, fx, mandor, today, qty, hour) {
  const number = fx.code + 'N' + hour
  await p.getByRole('button', { name: 'Nota baru', exact: true }).click()
  await p.getByLabel('Nomor nota aksesori').fill(number)
  await p.getByLabel('Mandor aksesori').selectOption(mandor)
  await p.getByLabel('Gudang aksesori').selectOption(fx.main)
  await p.getByLabel('Waktu ambil aksesori').fill(`${day(today, 1)}T${String(hour).padStart(2, '0')}:00`)
  await p.getByLabel('Cari barang aksesori').fill(fx.code)
  await p.getByRole('button', { name: 'Perbarui harga dan stok', exact: true }).click()
  await p.getByLabel('Tambah aksesori').selectOption(fx.material)
  await p.getByLabel('Jumlah PCS 1').fill(String(qty))
  await p.getByLabel('Harga per PCS 1').fill('3.00')
  return number
}


export async function cases(ui, today) {
  return [
    ['FAB_BROWSER:STOCK_SEARCH_VISIBLE_AND_CLEARABLE_IN_DOCUMENTS', async () => {
      const owner = await ui.login('OWNER', { label: 'fab-tabs' })
      const fx = await accessoryFixture(ui, owner, today)
      const p = await openAccessories(ui, owner)
      await p.getByLabel('Cari stok aksesori').fill(fx.code)
      await p.getByRole('button', { name: 'Cari stok', exact: true }).click()
      await ui.expect(p.getByRole('cell', { name: new RegExp(fx.code) }).first()).toBeVisible()
      await p.getByRole('button', { name: 'Catat transaksi', exact: true }).click()
      await p.getByLabel('Jenis transaksi aksesori').selectOption('FILL_POST')
      await p.getByLabel('Gudang asal').selectOption(fx.main)
      await p.getByLabel('Pos servis tujuan').selectOption(fx.post)
      await p.getByLabel('Waktu fisik (WIB)').fill(`${day(today, 1)}T09:00`)
      await p.getByLabel('Aksesori baris 1').selectOption(fx.material)
      await p.getByLabel('Jumlah baris 1').fill('5')
      await p.getByLabel('Alasan transaksi').fill('FAB isi pos untuk uji filter tab')
      await p.getByRole('button', { name: 'Periksa transaksi', exact: true }).click()
      await p.getByRole('button', { name: 'Sahkan isi pos servis', exact: true }).click()
      await ui.expect.poll(() => stock(ui, fx, fx.post), { timeout: 20000 }).toBe('5')
      const number = ui.sql(`select document_number from erp.bc_documents_v1 where action='FILL_POST' and payload->'items'->0->>'material_id'='${fx.material}'`)
      await p.getByRole('button', { name: 'Dokumen', exact: true }).click()
      const status = p.getByRole('status').filter({ hasText: `Pencarian aktif "${fx.code}"` })
      await ui.expect(status).toBeVisible()
      const open = p.getByRole('button', { name: `Buka ${number}`, exact: true })
      const hiddenWhileNarrowed = !(await open.isVisible())
      await p.getByRole('button', { name: 'Hapus pencarian', exact: true }).click()
      await ui.expect(open).toBeVisible({ timeout: 20000 })
      const statusGone = !(await status.isVisible())
      return { status: hiddenWhileNarrowed && statusGone ? 'PASS' : 'COUNTEREXAMPLE', number, hiddenWhileNarrowed, statusGone,
        oracle: 'a filter that narrows the list must be visible on that tab and clearable there; after clearing, the document appears without typing its number (ACC-D12 search/paging, GPT-BC-01 fix 27e1a05)' }
    }],
  ]
}
