import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const read = (path) => readFileSync(path, 'utf8')
const hook = read('src/useProductionMutation.ts')
const storage = read('src/productionRecovery.ts')
for (const token of [
  'busyRef.current', '!readyRef.current', 'sessionRef.current !== session',
  "mode: 'exclusive', ifAvailable: true", 'current.signature !== readySignature.current',
  'if (!input || !isDefiniteInitialRejection(result.error))',
  'handlers.validate(result.data, envelope)', 'handlers.retire(result.data, envelope)',
  'clearProductionEnvelope(scope, domain, envelope)', 'await handlers.reload()',
]) assert.ok(hook.includes(token), `Shared production recovery guard missing: ${token}`)
assert.ok(hook.indexOf('handlers.retire(result.data, envelope)') < hook.lastIndexOf('await handlers.reload()'), 'Committed forms must retire before refresh')
for (const token of [
  "'erp.cp5'", "'erp.cp6'", 'pending-mutation.v1:', 'erp.production.revision.v1:',
  'value.fingerprint !== JSON.stringify', 'current?.id !== envelope.id',
  'current.fingerprint !== envelope.fingerprint', "globalThis.addEventListener('storage'",
]) assert.ok(storage.includes(token), `Shared production storage contract missing: ${token}`)
for (const [path, domain] of [
  ['src/ConnectedAccessoryIssuePage.tsx', 'ACCESSORY_ISSUE'],
  ['src/ConnectedBsResolutionPage.tsx', 'BS'], ['src/ConnectedCuttingPage.tsx', 'CUTTING'],
  ['src/ConnectedPickupPage.tsx', 'PICKUP'], ['src/ConnectedWipStatusPage.tsx', 'WIP'],
  ['src/useLaundryQcWorkspace.ts', 'LAUNDRY_QC'],
  ['src/ConnectedInitialImportPage.tsx', 'INITIAL_IMPORT'],
  ['src/ConnectedPocketFabricPage.tsx', 'POCKET_FABRIC'],
]) {
  const source = read(path)
  assert.ok(source.includes(`useProductionMutation('${domain}')`), `${path} bypasses shared recovery`)
  for (const token of ['beginRead()', 'finishRead(ticket)', 'p_client_request_id: envelope.id', 'p_payload: envelope.payload']) {
    assert.ok(source.includes(token), `${path} omits ${token}`)
  }
  assert.doesNotMatch(source, /p_client_request_id:\s*globalThis\.crypto\.randomUUID/, `${path} bypasses persistent UUID`)
}
for (const path of ['src/ConnectedCuttingPage.tsx', 'src/ConnectedPickupPage.tsx', 'src/ConnectedBsResolutionPage.tsx']) {
  assert.doesNotMatch(read(path), /event\.target\.value\.replace\(/, `${path} silently rewrites numeric input`)
}
const procurement = read('src/ConnectedProcurementPage.tsx')
for (const token of ["useProductionMutation('PROCUREMENT')", 'beginRead()', 'finishRead(ticket)', 'p_request: envelope.id', 'p_expected: p.expected_version', 'parseProcurementOutcome', 'reload: load']) {
  assert.ok(procurement.includes(token), `Procurement recovery omits ${token}`)
}
assert.doesNotMatch(procurement, /p_request:\s*(?:globalThis\.)?crypto\.randomUUID/)
console.log('Production recovery ownership passed: shared envelope, lock and stale-read generation including procurement exact version transport.')
// R3-03 (owner D16-1): the connected Reminder page keeps one request UUID per attempt and the version it read.
const reminders = read('src/ConnectedRemindersPage.tsx')
for (const token of ["useProductionMutation('REMINDER')", 'beginRead()', 'finishRead(ticket)', 'p_request: e.id', 'p_expected: e.expectedVersion', 'validateReminderOutcome', 'reload: load']) {
  assert.ok(reminders.includes(token), `Reminder recovery omits ${token}`)
}
assert.doesNotMatch(reminders, /p_request:\s*(?:globalThis\.)?crypto\.randomUUID/)

const materials = read('src/ConnectedMaterialsPage.tsx')
for (const token of ["useProductionMutation('MATERIALS')", 'beginRead()', 'finishRead(ticket)', 'p_request:envelope.id', 'p_expected:p.expected_version', 'parseMaterialOutcome', 'reload:load']) {
  assert.ok(materials.includes(token), `Material recovery omits ${token}`)
}
assert.doesNotMatch(materials, /p_request:\s*(?:globalThis\.)?crypto\.randomUUID/)

const invoices = read('src/PurchaseInvoicePanel.tsx')
const supplierPayments = read('src/SupplierPaymentPanel.tsx')
for (const token of ["useProductionMutation('SUPPLIER_PAYMENT')", 'beginRead()', 'finishRead(ticket)',
  'p_request: envelope.id', 'parseSupplierPaymentOutcome', 'useFinancialRecoveryGate', 'setCommittedTarget',
  'selected_payment_id']) {
  assert.ok((supplierPayments + read('src/supplierPaymentContract.ts')).includes(token), `Supplier payment recovery omits ${token}`)
}
assert.doesNotMatch(supplierPayments, /p_request:\s*(?:globalThis\.)?crypto\.randomUUID/)
for (const token of ["useProductionMutation('PURCHASE_INVOICE')", 'beginRead()', 'finishRead(ticket)', 'p_request:envelope.id', 'p_expected:p.expected_version', 'parsePurchaseInvoiceOutcome']) {
  assert.ok(invoices.includes(token), `Invoice recovery omits ${token}`)
}
assert.doesNotMatch(invoices, /p_request:\s*(?:globalThis\.)?crypto\.randomUUID/)

const supplierReturns = read('src/SupplierReturnPanel.tsx')
for (const token of ["useProductionMutation('SUPPLIER_RETURN')", 'beginRead()', 'finishRead(ticket)', 'p_request:e.id', 'p_expected:p.expected_version', 'parseSupplierReturnOutcome']) {
  assert.ok(supplierReturns.includes(token), `Supplier return recovery boundary missing ${token}`)
}

const materialCount = read('src/ConnectedMaterialCountPage.tsx')
for (const token of ["useProductionMutation('MATERIAL_COUNT')", 'beginRead()', 'finishRead(ticket)', 'p_request:envelope.id', 'p_expected:p.expected_version', 'parseCountOutcome', 'reload:load']) {
  assert.ok(materialCount.includes(token), `Material count recovery omits ${token}`)
}
assert.doesNotMatch(materialCount, /p_request:\s*(?:globalThis\.)?crypto\.randomUUID/)

const payroll = read('src/ConnectedPayrollPage.tsx')
for (const token of ["useProductionMutation('PAYROLL')", 'beginRead()', 'finishRead(ticket)', 'p_request:e.id', 'p_expected:p.expected_version', 'parsePayrollOutcome', 'reload:load']) {
  assert.ok(payroll.includes(token), `Payroll recovery omits ${token}`)
}
assert.doesNotMatch(payroll, /p_request:\s*(?:globalThis\.)?crypto\.randomUUID/)

const sales = read('src/ConnectedSalesPage.tsx')
for (const token of ["useProductionMutation('SALES')", 'beginRead()', 'finishRead(ticket)', 'p_request:e.id', 'p_expected:p.expected_version', 'parseSalesOutcome', 'reload:load']) {
  assert.ok(sales.includes(token), `Sales recovery omits ${token}`)
}
assert.doesNotMatch(sales, /p_request:\s*(?:globalThis\.)?crypto\.randomUUID/)

const period = read('src/FinancePeriodPanel.tsx')
for (const token of ["useProductionMutation('FINANCE_PERIOD')", 'beginRead()', 'finishRead(ticket)', 'p_request:e.id', 'p_payload:e.payload', 'parsePeriodOutcome']) {
  assert.ok(period.includes(token), `Period recovery omits ${token}`)
}
assert.doesNotMatch(period, /p_request:\s*(?:globalThis\.)?crypto\.randomUUID/)

const hppPool = read('src/AttendanceHppPoolPanel.tsx')
for (const token of ["useProductionMutation('HPP_POOL')", 'beginRead()', 'finishRead(ticket)', 'p_request: e.id', 'p_payload: e.payload', 'parseHppPoolOutcome']) {
  assert.ok(hppPool.includes(token), `HPP pool recovery omits ${token}`)
}
assert.doesNotMatch(hppPool, /p_request:\s*(?:globalThis\.)?crypto\.randomUUID/)
const recost = read('src/RecostQueuePanel.tsx')
assert.match(recost, /useProductionMutation\('HPP_RECOST'\)/)
assert.match(recost, /parseRecostOutcome/)

// WA-4 (owner D17-3..D17-6): the Sambungan WhatsApp writes keep their request ids in memory only (no recovery envelope,
// no browser storage: the settings carry the owner's phone number), and the CallMeBot key is read from an uncontrolled
// password input when it is sent, with a fresh request id, and the input is emptied right after.
const wa = read('src/WaConnectionPanel.tsx')
const waContract = read('src/waContract.ts')
const waSystem = read('src/SystemRemindersPanel.tsx')
for (const [path, source] of [['src/WaConnectionPanel.tsx', wa], ['src/waContract.ts', waContract], ['src/SystemRemindersPanel.tsx', waSystem]]) {
  assert.doesNotMatch(source, /useProductionMutation|productionRecovery|localStorage|sessionStorage|indexedDB|console\./, `${path} persists or logs WhatsApp data`)
}
for (const token of ["client.rpc('erp_cp7_set_wa_key_v1', { p_key: input.value, p_request: crypto.randomUUID() })", "input.value = ''",
  'ref={keyInput} type="password"', "client.rpc('erp_cp7_save_wa_settings_v1', { p: payload, p_request: request })", 'parseWaSaveResult', 'waKeyErrorText']) {
  assert.ok(wa.includes(token), `WhatsApp connection omits ${token}`)
}
assert.equal((wa.match(/p_key/g) ?? []).length, 1, 'The CallMeBot key may travel in one request only')
assert.doesNotMatch(wa.split('\n').find((line) => line.includes('ref={keyInput}')) ?? '', /\bvalue=|defaultValue=/, 'The key input must stay uncontrolled')
console.log('WhatsApp connection passed: in-memory request ids, write-only key from an uncontrolled input, nothing stored or logged.')
