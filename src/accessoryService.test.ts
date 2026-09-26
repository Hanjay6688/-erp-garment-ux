import { describe, expect, it } from 'vitest'
import { parseAccessoryServiceWorkspace, policyValue, validateServiceResult, wibTimestamp } from './accessoryService'
import { parseInitialImportBC } from './initialImportBC'
import { parseAccessoryWorkspace, previewAccessoryLine } from './accessoryIssue'

// Trimmed copies of real server reads (BC probe cases ALL:C03_CUSTODY_STATES and DEC02:SPECIAL_FREE_LINE on the local disposable chain).
const service = {
 "card": null,
 "lots": [
  {
   "id": "8c38eb9c-0554-4107-91c8-8f88706df9cf",
   "sku": "BC0F9C4DE143",
   "name": "BC kancing silver",
   "state": {
    "open": "4.000000",
    "usable": "3.000000",
    "damaged": "1.000000",
    "waiting": "0.000000",
    "credited": "0.000000",
    "received": "4.000000",
    "inspected_usable": "3.000000",
    "inspected_damaged": "1.000000"
   },
   "document": null,
   "reference": "Opname awal BBded322f2ba94-K1 — bongkaran lama",
   "owner_kind": "COMPANY",
   "location_id": "932ff54f-fd2d-4ba2-b8d7-5404975de8f7",
   "material_id": "aea82006-ecc8-4a14-9422-7e548e66918b",
   "source_kind": "OPENING_PENDING_VALUE",
   "note_item_id": null,
   "value_status": "Belum dinilai",
   "received_local": "2026-09-15 00:00",
   "opening_note_line_id": null
  },
  {
   "id": "9e9bc025-defc-4d4c-b3df-2212e9042101",
   "sku": "BC0F9C4DE143",
   "name": "BC kancing silver",
   "state": {
    "open": "2.000000",
    "usable": "2.000000",
    "damaged": "0.000000",
    "waiting": "0.000000",
    "credited": "0.000000",
    "received": "2.000000",
    "inspected_usable": "2.000000",
    "inspected_damaged": "0.000000"
   },
   "document": null,
   "reference": "Opname awal area pemeriksaan (saldo awal 04382213-6390-44fa-9936-dd94ae17f86f)",
   "owner_kind": "COMPANY",
   "location_id": "932ff54f-fd2d-4ba2-b8d7-5404975de8f7",
   "material_id": "aea82006-ecc8-4a14-9422-7e548e66918b",
   "source_kind": "OPENING_QUARANTINE",
   "note_item_id": null,
   "value_status": "Bernilai di buku",
   "received_local": "2026-09-15 00:00",
   "opening_note_line_id": null
  }
 ],
 "page": 1,
 "notes": null,
 "stock": [
  {
   "qty": "5.000000",
   "sku": "BC0F9C4DE143",
   "kind": "SERVICE_POST",
   "name": "BC kancing silver",
   "unit": "PCS",
   "value": "10.00",
   "bucket": "Di pos servis — siap dipakai",
   "category": "BC kancing",
   "location": "BC SERVICE_POST",
   "location_id": "50b7f7ba-331a-463a-943f-6597b2d125f9",
   "material_id": "aea82006-ecc8-4a14-9422-7e548e66918b",
   "updated_local": "2026-09-26 00:21"
  },
  {
   "qty": "1002.000000",
   "sku": "BC0F9C4DE143",
   "kind": "MAIN",
   "name": "BC kancing silver",
   "unit": "PCS",
   "value": "2004.00",
   "bucket": "Di gudang — siap dipakai",
   "category": "BC kancing",
   "location": "BC W",
   "location_id": "383b4b4c-46e6-4b1b-96e4-d61470952845",
   "material_id": "aea82006-ecc8-4a14-9422-7e548e66918b",
   "updated_local": "2026-09-26 00:21"
  }
 ],
 "users": [
  {
   "id": "c8c00000-0000-4000-8000-000000000001",
   "name": "CP6 Race Owner"
  }
 ],
 "filters": {
  "document_id": "231de4c1-7a3d-4c9c-a4c4-12d3934667d5"
 },
 "accounts": [
  {
   "id": "de240b9e-e10f-4457-9c51-606f21da033f",
   "code": "1000",
   "name": "Kas",
   "type": "ASSET"
  },
  {
   "id": "a84867d2-58c3-469e-bfdf-d5e5be3338d8",
   "code": "1010",
   "name": "Bank",
   "type": "ASSET"
  }
 ],
 "document": {
  "id": "231de4c1-7a3d-4c9c-a4c4-12d3934667d5",
  "links": [
   {
    "id": "52f05936-686c-41f2-8496-3fabdf52f5ac",
    "kind": "TRANSFER"
   }
  ],
  "action": "INSPECT",
  "events": [
   {
    "id": "2aa0b7b1-5433-45ca-8de8-c3d3bf2296ea",
    "qty": "0.000000",
    "kind": "INSPECT",
    "carry": null,
    "amount": null,
    "lot_id": "9e9bc025-defc-4d4c-b3df-2212e9042101",
    "refund": null,
    "unpaid": null,
    "condition": null,
    "inspector": "Ani",
    "qty_usable": "2.000000",
    "qty_damaged": "0.000000",
    "carry_remaining": null,
    "carry_payroll_lines": null
   }
  ],
  "number": "BCA-231DE4C17A3D4C9C",
  "status": "POSTED",
  "payload": {
   "lot_id": "9e9bc025-defc-4d4c-b3df-2212e9042101",
   "reason": "BC probe periksa",
   "inspector": "Ani",
   "qty_usable": "2",
   "inspected_at": "2026-09-25T09:00:00+07:00",
   "usable_location_id": "383b4b4c-46e6-4b1b-96e4-d61470952845"
  },
  "row_version": "1",
  "carry_payrolls": [],
  "policy_versions": {},
  "reversal_reason": null
 },
 "is_admin": true,
 "policies": [
  {
   "key": "ACC-DEC01",
   "value": null,
   "set_at": "2026-09-25T17:21:46.49687+00:00",
   "status": "PENDING_POLICY_VALUE",
   "version": "1"
  },
  {
   "key": "ACC-DEC03",
   "value": {
    "unit_value_cap": "MOVING_AVERAGE",
    "credit_account_id": "00295850-33a0-41c3-805d-04e7bc8efdbb"
   },
   "set_at": "2026-09-25T17:21:50.458582+00:00",
   "status": "SET",
   "version": "2"
  },
  {
   "key": "ACC-DEC04",
   "value": null,
   "set_at": "2026-09-25T17:21:46.49687+00:00",
   "status": "PENDING_POLICY_VALUE",
   "version": "1"
  },
  {
   "key": "ACC-DEC05",
   "value": null,
   "set_at": "2026-09-25T17:21:46.49687+00:00",
   "status": "PENDING_POLICY_VALUE",
   "version": "1"
  },
  {
   "key": "ACC-DEC06",
   "value": null,
   "set_at": "2026-09-25T17:21:46.49687+00:00",
   "status": "PENDING_POLICY_VALUE",
   "version": "1"
  },
  {
   "key": "ACC-DEC07",
   "value": null,
   "set_at": "2026-09-25T17:21:46.49687+00:00",
   "status": "PENDING_POLICY_VALUE",
   "version": "1"
  },
  {
   "key": "ERP-DEC02",
   "value": null,
   "set_at": "2026-09-25T17:21:46.49687+00:00",
   "status": "PENDING_POLICY_VALUE",
   "version": "1"
  }
 ],
 "customers": null,
 "documents": [
  {
   "id": "42f59a0b-2136-4034-a09f-1cf029bcd8fa",
   "links": 1,
   "action": "VALUE_CUSTODY",
   "number": "BCA-42F59A0B21364034",
   "reason": "nilai pulih",
   "status": "REVERSED",
   "reference": null,
   "responsible": null,
   "row_version": "2",
   "physical_local": "2026-09-25 12:00",
   "recorded_local": "2026-09-26 00:21"
  },
  {
   "id": "5586594c-c446-4719-a141-376a696be6ef",
   "links": 0,
   "action": "INSPECT",
   "number": "BCA-5586594CC4464719",
   "reason": "BC probe periksa",
   "status": "POSTED",
   "reference": null,
   "responsible": null,
   "row_version": "1",
   "physical_local": "2026-09-25 11:00",
   "recorded_local": "2026-09-26 00:21"
  }
 ],
 "locations": [
  {
   "id": "30b35f44-7ec1-4940-9a46-f15b5a74c812",
   "code": "BC0F9C4DE143DA",
   "kind": "DAMAGED",
   "name": "BC DAMAGED",
   "label": "Rusak — menunggu disposisi"
  },
  {
   "id": "932ff54f-fd2d-4ba2-b8d7-5404975de8f7",
   "code": "BC0F9C4DE143IN",
   "kind": "INSPECTION",
   "name": "BC INSPECTION",
   "label": "Menunggu pemeriksaan"
  }
 ],
 "materials": [
  {
   "id": "aea82006-ecc8-4a14-9422-7e548e66918b",
   "sku": "BC0F9C4DE143",
   "name": "BC kancing silver",
   "unit": "PCS"
  }
 ],
 "page_size": 25,
 "variances": [],
 "categories": [
  {
   "id": "1d6b83be-4a5d-4118-a5e4-293feb40af25",
   "name": "BC kancing"
  }
 ],
 "outstanding": [
  {
   "id": "7e7849f5-bdd0-44e6-9edb-6e92ee77300f",
   "label": "Belum kembali",
   "holder": "Pak Budi",
   "expected": "1.000000",
   "received": "0.000000",
   "reference": "Opname awal BBded322f2ba94-K2",
   "owner_kind": "COMPANY",
   "description": null,
   "material_id": "aea82006-ecc8-4a14-9422-7e548e66918b",
   "source_kind": "OPENING_UNRETURNED"
  }
 ],
 "stock_total": 2,
 "can_see_value": true,
 "cash_accounts": [
  {
   "id": "68a97436-4b27-4771-9a8e-839cf2f08e92",
   "name": "BB bank"
  },
  {
   "id": "9fc70bc6-d07c-4998-913f-317bcb9772a7",
   "name": "BC bank"
  }
 ],
 "opening_notes": null,
 "documents_total": 4,
 "customer_custody": [
  {
   "id": "b231b559-e5c4-4674-9f4b-5cea52a932c6",
   "qty": "1.000000",
   "customer": "BB pelanggan",
   "returned": false,
   "description": "Celana pelanggan servis",
   "received_local": "2026-09-15 00:00"
  }
 ]
}
const importBC = {
 "accessory_note_lines": [],
 "accessory_custody": [
  {
   "key": "Celana pelanggan servis",
   "qty": "1.000000",
   "kind": "CUSTOMER_GARMENT",
   "value_status": "Milik pelanggan",
   "customer_code": "BBded322f2ba94"
  },
  {
   "key": "Opname awal BBded322f2ba94-K1 — bongkaran lama",
   "qty": "4.000000",
   "kind": "PENDING_VALUE",
   "state": {
    "open": "4.000000",
    "usable": "0.000000",
    "damaged": "0.000000",
    "waiting": "4.000000",
    "credited": "0.000000",
    "received": "4.000000",
    "inspected_usable": "0.000000",
    "inspected_damaged": "0.000000"
   },
   "material_sku": "BC0F9C4DE143",
   "value_status": "Belum dinilai"
  },
  {
   "key": "Opname awal area pemeriksaan (saldo awal 04382213-6390-44fa-9936-dd94ae17f86f)",
   "qty": "2.000000",
   "kind": "QUARANTINE_VALUED",
   "state": {
    "open": "2.000000",
    "usable": "0.000000",
    "damaged": "0.000000",
    "waiting": "2.000000",
    "credited": "0.000000",
    "received": "2.000000",
    "inspected_usable": "0.000000",
    "inspected_damaged": "0.000000"
   },
   "material_sku": "BC0F9C4DE143",
   "value_status": "Bernilai di buku"
  },
  {
   "key": "Opname awal BBded322f2ba94-K2",
   "qty": "1.000000",
   "kind": "UNRETURNED",
   "holder": "Pak Budi",
   "owner_kind": "COMPANY",
   "description": null,
   "material_sku": "BC0F9C4DE143",
   "value_status": "Belum kembali"
  }
 ]
}
// The seeded CP3 contractors (ids a1000000-0000-0000-...) are not in this copy; the D08 case below adds one (canonical, non RFC-4122).
const note = {
 "orders": [],
 "filters": {
  "location_id": "59f32a77-e2b8-4642-acff-39290b314aac",
  "physical_at": "2026-09-24T08:00:00+07:00",
  "contractor_id": "68b1885e-c163-424e-acf8-4f883105da07",
  "material_query": "bc9c9f5b9804"
 },
 "history": [],
 "document": null,
 "locations": [
  {
   "id": "59f32a77-e2b8-4642-acff-39290b314aac",
   "name": "BC W"
  },
  {
   "id": "e0b14d8c-3733-4bf5-84b4-08017129ca9a",
   "name": "BC W2"
  }
 ],
 "materials": [
  {
   "id": "09504f01-d253-41f9-aa51-97100d7cc83b",
   "sku": "BC9C9F5B9804",
   "free": {
    "category_id": "d4a21cc2-d9a5-4346-9725-665d319cf72d",
    "policy_version": "2"
   },
   "name": "BC kancing silver",
   "unit": "PCS",
   "stock": "1000.000000",
   "factor": null,
   "category": "BC kancing",
   "price_unit": null,
   "master_price": null,
   "price_version_id": null
  }
 ],
 "contractors": [
  {
   "id": "68b1885e-c163-424e-acf8-4f883105da07",
   "name": "BC mandor"
  }
 ],
 "location_id": "59f32a77-e2b8-4642-acff-39290b314aac",
 "contractor_id": "68b1885e-c163-424e-acf8-4f883105da07",
 "history_count": 0,
 "material_count": 1,
 "physical_local": "2026-09-24T08:00:00"
}
const clone = <T,>(v: T): T => structuredClone(v)

describe('accessory service workspace (BC)', () => {
  it('parses a real read with every collection and exact-text quantities', () => {
    const w = parseAccessoryServiceWorkspace(clone(service))
    expect(w.policies).toHaveLength(7)
    expect(w.lots.every(l => /^\d+\.\d{6}$/.test(l.state.open))).toBe(true)
  })
  it('refuses an incomplete read instead of showing nothing', () => {
    for (const key of ['stock', 'lots', 'outstanding', 'customer_custody', 'variances', 'documents', 'materials', 'policies']) {
      const w = clone(service) as Record<string, unknown>; delete w[key]
      expect(() => parseAccessoryServiceWorkspace(w)).toThrow()
    }
  })
  it('refuses a lot quantity sent as a JSON number and a value shown to a role without value rights', () => {
    const w = clone(service) as { lots: { state: Record<string, unknown> }[]; stock: { value: unknown }[]; can_see_value: boolean }
    if (w.lots.length) { w.lots[0].state.open = 4; expect(() => parseAccessoryServiceWorkspace(w)).toThrow() }
    const v = clone(service) as { stock: { value: unknown }[]; can_see_value: boolean }
    if (v.stock.length) { v.can_see_value = false; expect(() => parseAccessoryServiceWorkspace(v)).toThrow() }
  })
  it('refuses a pending policy that carries a value and a missing policy', () => {
    const w = clone(service) as { policies: { status: string; value: unknown }[] }
    const pending = w.policies.find(p => p.status === 'PENDING_POLICY_VALUE')!
    pending.value = { mode: 'X' }
    expect(() => parseAccessoryServiceWorkspace(w)).toThrow()
    const m = clone(service) as { policies: unknown[] }; m.policies.pop()
    expect(() => parseAccessoryServiceWorkspace(m)).toThrow()
  })
  it('checks the action result against the request it answers', () => {
    const request = '11111111-1111-4111-8111-111111111111'
    expect(() => validateServiceResult({ request_id: request, action: 'FILL_POST', status: 'POSTED', document_id: request, row_version: '1' }, 'FILL_POST', request, null)).not.toThrow()
    expect(() => validateServiceResult({ request_id: request, action: 'FILL_POST', status: 'POSTED', document_id: '22222222-2222-4222-8222-222222222222', row_version: '1' }, 'FILL_POST', request, null)).toThrow()
    expect(() => validateServiceResult({ request_id: request, action: 'SET_POLICY', status: 'SAVED', document_id: null, row_version: null }, 'SET_POLICY', request, null)).not.toThrow()
  })
  it('builds policy values without inventing defaults', () => {
    expect(typeof policyValue('ACC-DEC05', { mode: 'CREDIT_UNPAID_ONLY', credit_conditions: '' })).toBe('string')
    expect(policyValue('ACC-DEC05', { mode: 'CREDIT_UNPAID_ONLY', credit_conditions: 'USABLE' })).toEqual({ mode: 'CREDIT_UNPAID_ONLY', credit_conditions: ['USABLE'] })
    expect(typeof policyValue('ACC-DEC04', {})).toBe('string')
    expect(policyValue('ACC-DEC07', { approval_mode: 'ABOVE', owner_approval_above: '5' })).toEqual({ owner_approval_above: '5.00' })
    // Owner decision no. 6: "no approval for now" is an explicit value, not a threshold of 0 (which would require approval for every cost).
    expect(policyValue('ACC-DEC07', { approval_mode: 'NONE' })).toEqual({ approval: 'NONE' })
    expect(policyValue('ACC-DEC07', { owner_approval_above: '0' })).toBeTypeOf('string')
  })
  it('reads where a carried due went and which payroll is next (decision no. 4), and refuses a payroll without the next flag', () => {
    const w = clone(service) as any
    const payroll = { id: '11111111-1111-4111-8111-111111111111', number: 'BCP-1', status: 'DRAFT', period_end: '2026-09-25' }
    w.document.carry_payrolls = [{ ...payroll, is_next: true }]
    w.document.events[0].carry_payroll_lines = [{ payroll_id: payroll.id, payroll_number: 'BCP-0', status: 'REVERSED', amount: '9.00', period_end: '2026-09-24' }]
    const d = parseAccessoryServiceWorkspace(w).document!
    expect(d.carry_payrolls[0].is_next).toBe(true)
    expect(d.events[0].carry_payroll_lines).toEqual([expect.objectContaining({ status: 'REVERSED', amount: '9.00' })])
    const missing = clone(service) as any; missing.document.carry_payrolls = [payroll]
    expect(() => parseAccessoryServiceWorkspace(missing)).toThrow(/payroll berikutnya/)
  })
  it('writes WIB times with the +07:00 offset only', () => {
    expect(wibTimestamp('2026-09-24T08:00')).toBe('2026-09-24T08:00:00+07:00')
    expect(wibTimestamp('24/09/2026')).toBeNull()
  })
})

describe('import page: opening accessories (BC)', () => {
  it('parses both collections from a real read', () => {
    const bc = parseInitialImportBC(clone(importBC))!
    expect(bc.accessory_custody.map(c => c.kind).sort()).toEqual(['CUSTOMER_GARMENT', 'PENDING_VALUE', 'QUARANTINE_VALUED', 'UNRETURNED'])
  })
  it('treats a server without BC as no accessory section, and one collection without the other as incomplete', () => {
    expect(parseInitialImportBC({})).toBeNull()
    expect(() => parseInitialImportBC({ accessory_note_lines: [] })).toThrow()
  })
})

describe('note page: Special free line (ERP-DEC02)', () => {
  it('offers free only for an accessory the policy covers, at zero, with the policy version', () => {
    const w = parseAccessoryWorkspace(clone(note))
    const m = w.materials[0]
    const line = { material_id: m.id, qty: '3', mode: 'FREE' as const, manual_price: '' }
    expect(previewAccessoryLine(line, m)).toMatchObject({ amount: 0n, payload: { mode: 'FREE', free_policy_version: m.free!.policy_version } })
    expect(previewAccessoryLine(line, { ...m, free: null }).payload).toBeNull()
  })
})

describe('D08: note page with the seeded CP3 contractor (canonical, non RFC-4122 id)', () => {
  it('reads a note workspace whose contractor has a non-RFC id next to a v4 one, and still refuses a malformed id', () => {
    const w = clone(note) as Record<string, unknown> & { contractors: { id: string; name: string }[] }
    w.contractors = [{ id: 'a1000000-0000-0000-0000-000000000001', name: 'Mandor seed CP3' }, ...w.contractors]
    w.contractor_id = 'a1000000-0000-0000-0000-000000000001'
    const parsed = parseAccessoryWorkspace(w)
    expect(parsed.contractor_id).toBe('a1000000-0000-0000-0000-000000000001')
    expect(parsed.contractors.map(c => c.id)).toEqual(['a1000000-0000-0000-0000-000000000001', '68b1885e-c163-424e-acf8-4f883105da07'])
    expect(() => parseAccessoryWorkspace({ ...w, contractor_id: 'a1000000-0000-0000-0000-00000000001' })).toThrow()
    expect(() => parseAccessoryWorkspace({ ...w, contractors: [{ id: 'a1000000-0000-0000-0000-00000000000z', name: 'x' }] })).toThrow()
  })
})
