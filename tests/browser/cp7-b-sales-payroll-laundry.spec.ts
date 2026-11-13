import { expect, test, type Page, type TestInfo } from '@playwright/test'
import { asrId, asrParts, asrQuery, asrWorkspace } from '../fixtures/accessoryStandardReport'
import { attendanceChoicePreviewFixture, attendanceChoiceQuery, attendanceChoiceWorkspace } from '../fixtures/attendancePeriodChoice'
import { creditCohort, creditEvent, creditTarget } from '../fixtures/customerCredit'
import { laundryQcInputFixture } from '../fixtures/laundryQcInput'
import { capture, mockApp, navigate, signIn, verifyTransport } from './support/cp7-b-loopback-fixture'
import { capturedAt, salesCase, salesCorrectionFixture, saleRpc, source, vendorCase, vendorDatedRefusal, vendorWorkspace, vendorWriter } from './support/cp7-b-money-ui-fixtures'

const mobile = (info: TestInfo) => info.project.name === 'mobile'
const ownerOrAdmin = (info: TestInfo) => mobile(info) ? 'ADMIN' : 'OWNER'
const salesRights = ['dashboard.view', 'sales.invoice.view', 'sales.invoice.create', 'sales.invoice.edit_draft',
  'sales.invoice.post', 'sales.invoice.reverse', 'finance.ar.view', 'finance.hpp.view', 'sales.return.view',
  'sales.return.create', 'sales.return.post', 'sales.return.reverse']
const selectInvoice = async (page: Page, number: string) => {
  await navigate(page, 'Penjualan', 'Penjualan & Invoice')
  const list = page.getByRole('region', { name: 'Daftar invoice' })
  await list.getByRole('button', { name: new RegExp(number) }).click()
  await expect(page.getByRole('heading', { name: number, exact: true })).toBeVisible()
}
const exactButton = (page: Page, name: string) => page.getByRole('button', { name, exact: true })

test('Sales lists the exact APPLY and REFUND and reaches the source return', async ({ page, context }, info) => {
  const mock = await mockApp(context, { role: ownerOrAdmin(info), rights: salesRights, resolve: saleRpc })
  await signIn(page)
  await selectInvoice(page, source.number)
  const dependencies = page.getByRole('region', { name: `Penggunaan saldo kredit ${source.number}` })
  await dependencies.getByRole('button', { name: 'Lihat penggunaan saldo kredit', exact: true }).click()
  const apply = dependencies.locator(`[data-credit-dependency-id="${creditEvent().id}"]`)
  await expect(apply).toContainText('Pemakaian saldo kredit · Rp80')
  await expect(apply).toContainText('Dipakai pada invoice INV-TARGET')
  await expect(dependencies).toContainText('Pengembalian uang · Rp20')
  const order = dependencies.getByRole('list', { name: 'Langkah membatalkan penggunaan saldo kredit' })
  await expect(order).toContainText('Periksa riwayat kredit')
  await expect(order).toContainText('Nilai dan rekening mengikuti transaksi asli')
  await capture(page, info, 'sales-credit-dependencies')
  await apply.getByRole('button', { name: `Buka retur asal ${creditCohort.return_number}` }).click()
  await expect(page.getByRole('heading', { name: 'Retur Penjualan', exact: true })).toBeVisible()
  await expect(page.locator(`[data-return-id="${creditCohort.return_id}"]`)).toHaveAttribute('data-source-selected', 'true')
  expect(mock.calls.filter(c => c.name === 'erp_cp7_resolve_transaction_source_v1').map(c => c.args))
    .toEqual([{ p_source: { source_type: 'SALES_RETURN', source_id: creditCohort.return_id } }])
  expect(mock.calls.some(c => /(?:save|correct|command)_/.test(c.name))).toBe(false)
  await verifyTransport(mock, info)
})

test('Sales opens the server credit correction review for the exact return', async ({ page, context }, info) => {
  const fixture = salesCorrectionFixture()
  const mock = await mockApp(context, { role: ownerOrAdmin(info), rights: salesRights, resolve: fixture.resolve })
  await signIn(page)
  await selectInvoice(page, source.number)
  await exactButton(page, 'Retur fisik invoice').click()
  await exactButton(page, `Edit retur ${creditCohort.return_number}`).click()
  const panel = page.getByRole('region', { name: 'Pembetulan retur tercatat', exact: true })
  const amount = panel.getByRole('textbox', { name: 'Nilai pembetulan retur 1' })
  const submit = exactButton(page, 'Simpan pembetulan retur')
  const review = exactButton(page, 'Periksa dampak saldo kredit')
  await expect(amount).toHaveValue('200.00')
  await expect(panel.locator('article').filter({ hasText: creditEvent().id })).toContainText('Pemakaian saldo kredit · Rp80')
  await expect(panel).toContainText('Pengembalian uang · Rp20')
  await panel.getByLabel('Alasan pembetulan retur', { exact: true }).fill('Nilai retur dan saldo kredit sudah diperiksa')
  await amount.fill('50.00')
  await review.click()
  await expect(panel).toContainText('Batalkan transaksi kredit aktif yang terkait dahulu')
  await expect(panel).toContainText('Saldo setelah pembetulan Rp-50')
  await expect(submit).toBeDisabled()
  expect(mock.calls.some(c => c.name === salesCase.returnWriter)).toBe(false)
  await capture(page, info, 'sales-return-credit-refused')

  await amount.fill('250.00')
  await expect(panel.getByText('Batalkan transaksi kredit aktif yang terkait dahulu', { exact: false })).toHaveCount(0)
  await expect(submit).toBeDisabled()
  await review.click()
  await expect(panel).toContainText('Saldo sekarang Rp100 · Perubahan Rp50 · Saldo setelah pembetulan Rp150')
  await panel.getByLabel('Pembetulan retur sudah diperiksa', { exact: true }).check()
  await capture(page, info, 'sales-return-credit-ready')
  await submit.click()
  await expect(page.locator('[aria-label="Nilai invoice"]')).toContainText('Rp750')
  const writes = mock.calls.filter(c => c.name === salesCase.returnWriter)
  expect(writes).toHaveLength(1)
  expect(writes[0].args).toMatchObject({ p_expected: source.row_version, p_payload: {
    sale_id: source.id, return_id: creditCohort.return_id, credit_review_token: salesCase.readyToken,
    replacement: { physical_at: salesCase.returnAt, items: [{ qty_pcs: '2', refund_amount: '250.00' }] },
  } })
  expect(fixture.effects).toEqual({ return: 1, note: 0, undo: 0 })
  await verifyTransport(mock, info)
})

test('Sales shows used-credit carry, recovers the same note request and reverses the named APPLY on the current note', async ({ page, context }, info) => {
  const fixture = salesCorrectionFixture()
  const mock = await mockApp(context, { role: ownerOrAdmin(info), rights: salesRights, resolve: fixture.resolve })
  await signIn(page)
  await selectInvoice(page, 'INV-TARGET')
  await expect(exactButton(page, 'Benerin nota')).toBeEnabled()
  await exactButton(page, 'Riwayat pembetulan nota').click()
  const history = page.getByRole('region', { name: 'Riwayat pembetulan nota', exact: true })
  await expect(history).toContainText('Saldo kredit terpakai Rp80')
  await expect(history).toContainText(creditEvent().id)
  await exactButton(page, 'Benerin nota').click()
  const form = page.getByRole('form', { name: 'Benerin nota', exact: true })
  const submit = exactButton(page, 'Simpan pembetulan nota')
  await expect(form.getByLabel('Jumlah invoice 1', { exact: true })).toHaveAttribute('readonly', '')
  await form.getByLabel('Alasan simpan invoice', { exact: true }).fill('Harga nota dan saldo kredit sudah diperiksa')
  await form.getByLabel('Harga invoice 1', { exact: true }).fill('7')
  await expect(form).toContainText('Nilai nota ini belum memenuhi syarat')
  await expect(submit).toBeDisabled()
  expect(mock.calls.some(c => c.name === salesCase.noteWriter)).toBe(false)
  await form.getByLabel('Harga invoice 1', { exact: true }).fill('45.00')
  await expect(form).toContainText('Sisa tagihan setelah kredit Rp370')
  await form.getByLabel('Pembetulan nota sudah diperiksa', { exact: true }).check()
  await capture(page, info, 'sales-note-credit-carry')

  await submit.evaluate((button: HTMLButtonElement) => { button.click(); button.click() })
  const recover = exactButton(page, 'Reconcile transaksi')
  await expect(recover).toBeEnabled()
  const writes = () => mock.calls.filter(c => c.name === salesCase.noteWriter)
  expect(writes()).toHaveLength(1)
  const first = writes()[0].args
  expect(first).toMatchObject({ p_expected: '9007199254740997', p_payload: {
    sale_id: creditTarget, item_lineage: [salesCase.targetItem],
    credit_carry_review: { contract_version: 'cp7.note-credit-carry-review.v1', basis_sha256: 'e'.repeat(64),
      transfer_amount: '80.00', replacement_net: '450.00', remaining_amount: '370.00' },
  } })
  expect(first.p_request).toMatch(/^[0-9a-f-]{36}$/)
  await page.reload()
  await navigate(page, 'Penjualan', 'Penjualan & Invoice')
  await expect(recover).toBeEnabled()
  await capture(page, info, 'sales-note-credit-recovery-after-reload')
  await recover.click()
  const newNote = 'INV-TARGET · R1-' + first.p_request.slice(0, 8)
  await expect(page.getByRole('heading', { name: newNote, exact: true })).toBeVisible()
  await expect(page.locator('[aria-label="Nilai invoice"]')).toContainText('Sisa pembayaran Rp370')
  await expect(recover).toHaveCount(0)
  expect(writes().map(c => c.args)).toEqual([first, first])
  expect(fixture.effects.note).toBe(1)

  await selectInvoice(page, source.number)
  await exactButton(page, 'Saldo kredit pelanggan').click()
  await exactButton(page, 'Periksa riwayat kredit').click()
  const original = page.locator('[data-credit-event-id="' + creditEvent().id + '"]')
  await expect(original).toContainText('Rp80')
  await original.getByRole('button', { name: 'Periksa pembatalan pemakaian saldo RET-SOURCE', exact: true }).click()
  await page.getByLabel('Waktu transaksi saldo kredit WIB', { exact: true }).fill('2026-10-20T10:00')
  await page.getByLabel('Alasan tindakan saldo kredit', { exact: true }).fill('Pemakaian asli pada nota sudah diperiksa')
  await exactButton(page, 'Periksa transaksi kredit').click()
  const quote = page.getByRole('region', { name: 'Pemeriksaan transaksi kredit' })
  await expect(quote).toContainText('Kredit tercatat pada nota yang berlaku ' + newNote)
  await expect(quote).toContainText('Saldo sesudah transaksi ini: Rp180')
  await capture(page, info, 'sales-note-credit-exact-undo')
  await quote.getByLabel('Transaksi kredit sudah diperiksa', { exact: true }).check()
  await exactButton(page, 'Simpan transaksi kredit').click()
  await expect.poll(() => fixture.effects.undo).toBe(1)
  await expect(exactButton(page, 'Saldo kredit pelanggan')).toBeEnabled()
  await exactButton(page, 'Saldo kredit pelanggan').click()
  await exactButton(page, 'Periksa riwayat kredit').click()
  await expect(original).toContainText('Sudah dibatalkan')
  const undo = mock.calls.filter(c => c.name === salesCase.creditWriter)
  expect(undo).toHaveLength(1)
  expect(undo[0].args).toMatchObject({ p_payload: { action: 'UNDO', restores_event_id: creditEvent().id },
    p_expected_versions: { [source.id]: source.row_version, [salesCase.replacementNote]: '2' } })
  expect(undo[0].args.p_expected_versions).not.toHaveProperty(creditTarget)
  await exactButton(page, 'Tutup saldo kredit').click()
  await selectInvoice(page, newNote)
  await expect(page.locator('[aria-label="Nilai invoice"]')).toContainText('Sisa pembayaran Rp450')
  expect(fixture.effects).toEqual({ return: 0, note: 1, undo: 1 })
  await verifyTransport(mock, info, [/ERR_FAILED/])
})

test('S05 keeps the 31st mandor, filtered sources, unknown standard and access refusal distinct', async ({ page, context }, info) => {
  let mode: 'known' | 'unknown' | 'revoked' = 'known'
  const mandors = [
    { id: asrId(1), name: 'Mandor Satu', active: true },
    ...Array.from({ length: 30 }, (_, i) => ({ id: asrId(100 + i), name: `Mandor ${String(i + 2).padStart(2, '0')}`, active: true })),
  ]
  const last = mandors.at(-1)!
  const noteRpc = 'erp_get_accessory_issue_workspace_v1'
  const reportRpc = 'erp_cp7_get_accessory_standard_report_v1'
  const mock = await mockApp(context, { role: ownerOrAdmin(info),
    rights: ['dashboard.view', 'finance.contractor_accessory.view', 'finance.hpp.view'], resolve: ({ name, args }) => {
      if (name === noteRpc) return { body: {
        filters: args.p_filters, contractor_id: null, location_id: null, physical_local: '2026-10-16T12:00:00',
        contractors: [], locations: [], orders: [], materials: [], material_count: 0, history: [], history_count: 0, document: null,
        history_page: { offset: 0, limit: 50, next_offset: null, list: { q: '', status: null, order: 'SOURCE' } },
      } }
      if (name !== reportRpc) return undefined
      if (mode === 'revoked') return { status: 403, body: { code: '42501', message: 'CP7_ACCESSORY_REPORT_ACCESS_CHANGED' } }
      const query = asrQuery({ period_start: args.p_start, period_end: args.p_end, contractor_id: args.p_contractor,
        po_id: args.p_po, q: args.p_query, offset: args.p_offset, limit: args.p_limit })
      const data = asrWorkspace(query)
      data.contractors = { offset: query.offset, limit: query.limit, total: mandors.length,
        next_offset: query.offset + query.limit < mandors.length ? query.offset + query.limit : null,
        rows: mandors.slice(query.offset, query.offset + query.limit) }
      if (query.contractor_id !== null) {
        data.selected_contractor = last
        const p = asrParts(data)
        Object.assign(p.lot, { contractor_id: last.id })
        Object.assign(p.standard, { contractor_id: last.id })
        if (mode === 'unknown') {
          Object.assign(p.standard, { unit_known: false, unit: null, unit_reference: 'LUSIN' })
          Object.assign(p.row, { comparison_status: 'UNKNOWN', reasons: ['HISTORICAL_UNIT_UNKNOWN'], unit: null, delta_qty: null })
          p.report.status = 'UNKNOWN'
        }
      }
      return { body: data }
    },
  })
  await signIn(page)
  await navigate(page, 'Keuangan', 'Nota Ambil Aksesori')
  await exactButton(page, 'Diambil vs standar GOOD').click()
  const report = page.getByRole('region', { name: 'Laporan aksesori mandor' })
  const result = report.getByRole('region', { name: 'Hasil laporan aksesori' })
  await expect(report).toContainText('31 mandor cocok · halaman 1')
  await report.getByLabel('Mulai periode aksesori').fill('2026-10-16')
  await report.getByLabel('Akhir periode aksesori').fill('2026-10-16')
  await report.getByRole('button', { name: 'Muat laporan', exact: true }).click()
  await report.getByRole('button', { name: 'Mandor berikutnya' }).click()
  await expect(report).toContainText('31 mandor cocok · halaman 2')
  await report.getByRole('button', { name: last.name, exact: true }).click()
  const row = result.getByRole('row').filter({ has: page.getByRole('rowheader', { name: /^Kancing/ }) })
  await expect(row.getByRole('cell')).toHaveText(['7 PCS', '5 PCS', '2 PCS', 'Rp14', 'Rp22,75', 'Rp7,5', 'Rp0'])
  await report.getByLabel('PO laporan aksesori').selectOption(asrId(3))
  await expect(row.getByRole('cell')).toHaveText(['0 PCS', '5 PCS', '−5 PCS', 'Rp0', 'Rp0', 'Rp7,5', 'Rp0'])
  await expect(result.getByText('Jejak sumber pengambilan (0)', { exact: true })).toBeVisible()
  const lastRead = () => mock.calls.filter(c => c.name === reportRpc).at(-1)?.args
  expect(lastRead()).toMatchObject({ p_start: '2026-10-16', p_end: '2026-10-16', p_contractor: last.id, p_po: asrId(3) })
  await capture(page, info, 's05-filtered-po')
  mode = 'unknown'
  await report.getByLabel('PO laporan aksesori').selectOption('')
  await expect(result).toContainText('Satuan historis belum terbukti')
  await expect(row.getByRole('cell').nth(2)).toHaveText('Belum diketahui')
  await capture(page, info, 's05-unknown-unit')
  mode = 'revoked'
  await report.getByRole('button', { name: 'Muat laporan', exact: true }).click()
  await expect(report.getByRole('alert')).toContainText('Hak akses laporan sudah berubah')
  await expect(result).toHaveCount(0)
  await capture(page, info, 's05-access-denied')
  expect([...new Set(mock.calls.map(c => c.name))].sort()).toEqual(['erp_get_my_access_v1', noteRpc, reportRpc].sort())
  await verifyTransport(mock, info, [/403/])
})

test('Attendance shows both approved treatments for a period with no sewn pieces', async ({ page, context }, info) => {
  test.skip(mobile(info), 'S03 already has retained browser evidence. This adds one Owner App route check.')
  const workspace = attendanceChoiceWorkspace()
  const previewRpc = 'erp_cp7_preview_attendance_choice_v1'
  const mock = await mockApp(context, { role: 'OWNER', rights: ['dashboard.view', 'finance.hpp.view', 'finance.hpp.manage'],
    resolve: ({ name, args }) => {
      if (name === 'erp_get_sku_hpp_v1') return { body: { at: capturedAt, page: 1, page_size: 50, total: 0, groups: [] } }
      if (name === 'erp_cp7_get_recost_queue_v1') return { body: { contract_version: 'cp7.recost-queue.v1', captured_at: capturedAt,
        scope: 'CURRENT_QUEUE_ALL_ENTITIES', batch_semantics: 'AT_MOST_20_ELIGIBLE_UNLOCKED_NATIVE_JOBS',
        counts: { pending: '0', running: '0', failed: '0', done: '0', eligible: '0', exhausted: '0' },
        page: { rows: [], total: '0', offset: 0, limit: 25, next_offset: null } } }
      if (name === 'erp_cp7_get_hpp_pools_v1') return { body: { contract_version: 'cp7.hpp-pools.v1', business_DML: false, captured_at: capturedAt,
        offset: args.p_offset, limit: args.p_limit, total: 0, next_offset: null, closed_through: null, can_manage: true, pools: [], periods: [], preview: null } }
      if (name === 'erp_cp7_get_attendance_choice_v1' && args.p_period_start === workspace.period_start && args.p_period_end === workspace.period_end) return { body: workspace }
      if (name === previewRpc) return { body: attendanceChoicePreviewFixture(workspace, args.p_payload, args.p_action) }
      return undefined
    },
  })
  await signIn(page)
  await navigate(page, 'Keuangan', 'HPP & Rekalkulasi')
  const panel = page.getByRole('region', { name: 'Pilihan biaya absensi per periode' })
  await panel.getByLabel('Mulai periode asal').fill(attendanceChoiceQuery.period_start)
  await panel.getByLabel('Akhir periode asal').fill(attendanceChoiceQuery.period_end)
  await panel.getByRole('button', { name: 'Muat ulang periode' }).click()
  await expect(panel.getByText('0 pcs', { exact: true })).toBeVisible()
  await panel.getByLabel('Tindakan pilihan biaya').selectOption('CHOOSE')
  const choice = panel.getByRole('combobox', { name: 'Pilihan biaya absensi', exact: true })
  await expect(choice.locator('option')).toHaveText(['Pilih perlakuan biaya', 'Menunggu periode jahit berikutnya', 'Beban periode ini'])
  await panel.getByRole('textbox', { name: 'Alasan pilihan biaya absensi' }).fill('Biaya tanpa hasil jahit sudah diperiksa')
  const preview = panel.getByRole('region', { name: 'Tinjauan perubahan biaya' })
  await choice.selectOption('CARRY')
  await panel.getByRole('button', { name: 'Periksa perubahan biaya' }).click()
  await expect(preview).toContainText('Diteruskan ke periode jahit berikutnya')
  await expect(preview).toContainText('Tidak membuat jurnal baru')
  await capture(page, info, 'attendance-carry')
  await choice.selectOption('EXPENSE')
  await expect(preview).toHaveCount(0)
  await panel.getByRole('button', { name: 'Periksa perubahan biaya' }).click()
  await expect(preview).toContainText('Beban periode ini')
  await expect(preview).toContainText('6200 · Beban periode absensi')
  await expect(preview).toContainText('Tanggal ekonomi: 2026-10-07 · tanggal buku: 2026-10-07')
  await expect(panel.getByRole('button', { name: 'Simpan pilihan biaya' })).toBeDisabled()
  await capture(page, info, 'attendance-expense')
  expect(mock.calls.filter(c => c.name === previewRpc).map(c => c.args.p_payload.choice)).toEqual(['CARRY', 'EXPENSE'])
  expect(mock.calls.some(c => c.name === 'erp_cp7_save_attendance_choice_v1')).toBe(false)
  await verifyTransport(mock, info)
})

test('Laundry distinguishes claim credit and vendor receivable and shows the dated source refusal', async ({ page, context }, info) => {
  const mock = await mockApp(context, { role: ownerOrAdmin(info),
    rights: ['dashboard.view', 'production.laundry.view', 'finance.ap.view', 'finance.hpp.manage'], resolve: ({ name, args }) => {
      if (name === 'erp_get_laundry_qc_workspace_v1' && args.p_scope === 'LAUNDRY') return { body: laundryQcInputFixture('LAUNDRY') }
      if (name === 'erp_get_laundry_bd_workspace_v1') return { body: vendorWorkspace(args.p_filters.vendor_id === vendorCase.vendorId) }
      if (name === vendorWriter && ['APPLY_CLAIM_CREDIT', 'RECEIVE_VENDOR_REFUND'].includes(args.p_action)) {
        return { status: 400, body: { code: 'P0001', message: vendorDatedRefusal } }
      }
      return undefined
    },
  })
  await signIn(page)
  await navigate(page, 'Produksi', 'Laundry')
  await exactButton(page, 'Harga & tagihan').click()
  const prices = page.getByRole('region', { name: 'Harga dan tagihan laundry' })
  await prices.getByRole('button', { name: 'Pembayaran vendor', exact: true }).click()
  await prices.getByLabel('Vendor harga laundry').selectOption(vendorCase.vendorId)
  const payment = prices.getByRole('region', { name: 'Pembayaran vendor laundry', exact: true })
  const refund = payment.getByRole('region', { name: 'Pengembalian piutang vendor', exact: true })
  const receivable = payment.locator('dl > div').filter({ has: page.locator('dt').filter({ hasText: /^Piutang ke vendor$/ }) }).locator('dd')
  await expect(receivable).toHaveText('Rp 100,00')
  await expect(payment.getByRole('table', { name: 'Kredit klaim vendor' })).toContainText('CLM-RUSAK-A')
  await expect(payment.getByLabel('Kredit klaim dipakai').locator('option')).toHaveCount(3)
  await expect(refund.getByLabel('Piutang vendor dikembalikan').locator('option')).toHaveCount(2)
  await expect(refund.getByLabel('Piutang vendor dikembalikan').locator('option')).not.toContainText(['CLM-RUSAK-A'])
  const refuse = async () => {
    await expect(prices.getByRole('alert')).toContainText('saldo piutang vendor tidak cukup pada tanggal ekonomi atau tanggal buku', { ignoreCase: true })
    await expect(receivable).toHaveText('Rp 100,00')
    await expect(prices.getByRole('button', { name: 'Reconcile transaksi' })).toHaveCount(0)
  }
  await payment.getByLabel('Tagihan dilunasi').selectOption(vendorCase.targetInvoice)
  await payment.getByLabel('Tanggal pelunasan').fill(vendorCase.beforeBookDate)
  await payment.getByLabel('Alasan pelunasan').fill('Periksa tanggal buku sumber koreksi')
  await payment.getByLabel('Kredit klaim dipakai').selectOption(vendorCase.correctionId)
  await payment.getByLabel('Nominal kredit klaim').fill('30,01')
  await payment.getByRole('button', { name: 'Pakai kredit klaim' }).click()
  await refuse()
  await capture(page, info, 'laundry-apply-dated-refusal')
  await refund.getByLabel('Piutang vendor dikembalikan').selectOption(vendorCase.correctionId)
  await refund.getByLabel('Rekening penerima pengembalian vendor').selectOption(vendorCase.cashAccount)
  await refund.getByLabel('Nominal pengembalian vendor').fill('25,10')
  await refund.getByLabel('Tanggal pengembalian vendor').fill(vendorCase.beforeBookDate)
  await refund.getByLabel('Alasan pengembalian vendor').fill('Periksa pengembalian sebelum tanggal buku')
  await refund.getByRole('button', { name: 'Catat uang diterima dari vendor' }).click()
  await refuse()
  await capture(page, info, 'laundry-refund-dated-refusal')
  const commands = mock.calls.filter(c => c.name === vendorWriter).map(c => c.args)
  expect(commands).toHaveLength(2)
  expect(commands[0]).toMatchObject({ p_action: 'APPLY_CLAIM_CREDIT', p_payload: {
    source_kind: 'INVOICE_CORRECTION', source_id: vendorCase.correctionId, target_kind: 'VENDOR_INVOICE',
    target_id: vendorCase.targetInvoice, amount: '30.01', date: vendorCase.beforeBookDate } })
  expect(commands[1]).toMatchObject({ p_action: 'RECEIVE_VENDOR_REFUND', p_payload: {
    source_id: vendorCase.correctionId, cash_account_id: vendorCase.cashAccount, amount: '25.10', date: vendorCase.beforeBookDate } })
  expect(new Set(commands.map(c => c.p_client_request_id)).size).toBe(2)
  await verifyTransport(mock, info, [/400/, /400/])
})
