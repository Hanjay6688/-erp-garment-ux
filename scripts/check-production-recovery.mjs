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

const materials = read('src/ConnectedMaterialsPage.tsx')
for (const token of ["useProductionMutation('MATERIALS')", 'beginRead()', 'finishRead(ticket)', 'p_request:envelope.id', 'p_expected:p.expected_version', 'parseMaterialOutcome', 'reload:load']) {
  assert.ok(materials.includes(token), `Material recovery omits ${token}`)
}
assert.doesNotMatch(materials, /p_request:\s*(?:globalThis\.)?crypto\.randomUUID/)

const invoices = read('src/PurchaseInvoicePanel.tsx')
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
