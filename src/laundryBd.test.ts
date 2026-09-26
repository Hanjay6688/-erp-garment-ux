import { describe, expect, it } from 'vitest'
import { parseLaundryBdWorkspace, policyValue, validateBdResult } from './laundryBd'

// Shapes captured from erp.get_laundry_bd_workspace_v1 on the local BD chain (a components vendor with an UNKNOWN component
// price and a delivery priced with it; a rate vendor with one posted invoice and its billable receipt line).
const REAL = {
 "accounts": [
  {
   "code": "1000",
   "id": "de240b9e-e10f-4457-9c51-606f21da033f",
   "name": "Kas",
   "type": "ASSET"
  },
  {
   "code": "1010",
   "id": "a84867d2-58c3-469e-bfdf-d5e5be3338d8",
   "name": "Bank",
   "type": "ASSET"
  }
 ],
 "billable_receipts": [
  {
   "billed": {
    "BS": 0,
    "FAILED_ATTEMPT": 0,
    "GOOD": 4
   },
   "capacity": {
    "BS": 0,
    "FAILED_ATTEMPT": 0,
    "GOOD": 10
   },
   "delivery_number": "LDR-260923-B03F6F31F4D34E2884C2AA116DF6C36E",
   "estimate": "70000.00",
   "failed_attempt": false,
   "po_number": "AA-INV-PO-907b776c-fdda-4f94-9602-bbcdca46a9a5",
   "price_known": true,
   "receipt_line_id": "b992e229-b2a3-42f6-a9ba-7abe0665da22",
   "receipt_number": "LRC-260923-B7719A0C6B514B6D94BDE05FB3E5C965",
   "received_local": "2026-09-23T13:00:00",
   "released": "28000.00"
  }
 ],
 "can_manage_master": true,
 "can_set_price": true,
 "components": [
  {
   "code": "GARMENT",
   "current": {
    "from": "2026-09-23T00:00:00",
    "rate": "5000.00",
    "status": "KNOWN"
   },
   "id": "1e024a0d-5292-41bb-b5c2-4a422dfc5a1a",
   "is_active": true,
   "name": "BD GARMENT",
   "vendor_id": "fffb0bc1-a14c-45ff-b8c6-0f63ac2580fb"
  },
  {
   "code": "SPRAY",
   "current": {
    "from": "2026-09-23T00:00:00",
    "rate": null,
    "status": "UNKNOWN"
   },
   "id": "b0cee733-0f4f-468c-a3c4-d1801c4b0db2",
   "is_active": true,
   "name": "BD SPRAY",
   "vendor_id": "fffb0bc1-a14c-45ff-b8c6-0f63ac2580fb"
  }
 ],
 "invoices": [
  {
   "discount_amount": "0.00",
   "due_date": null,
   "header_total": "28000.00",
   "invoice_date": "2026-09-23",
   "invoice_id": "faa508ad-6f0f-4a72-af96-50a9a0bee945",
   "invoice_number": "INV-a2a49e48c3",
   "journal_id": "918b3602-5dd2-4b91-8f7e-cc8c4b5bb333",
   "lines": [
    {
     "amount": "28000.00",
     "category": "GOOD",
     "completes_source": false,
     "discount_share": "0.00",
     "id": "670d18d5-ad03-47ec-89ce-e767024f7ea6",
     "line_kind": "BILL",
     "line_no": 1,
     "net_amount": "28000.00",
     "note": null,
     "opening_uninvoiced_id": null,
     "po_id": "907b776c-fdda-4f94-9602-bbcdca46a9a5",
     "product_variance": "0.00",
     "qty": 4,
     "receipt_line_id": "b992e229-b2a3-42f6-a9ba-7abe0665da22",
     "released_estimate": "28000.00",
     "rounding_share": "0.00",
     "variance": "0.00"
    }
   ],
   "paid": "0.00",
   "policy_versions": {
    "LAU_DEC02": 2,
    "LAU_DEC06": 2
   },
   "reversal_journal_id": null,
   "rounding_amount": "0.00",
   "row_version": "2",
   "status": "POSTED",
   "tax_amount": "0.00",
   "variance_mode": "PRODUCT_COST",
   "vendor_code": "BD-0f82879e0eff",
   "vendor_id": "af869b2f-43f5-46f3-a612-6f22533179b1",
   "document_kind": "INVOICE",
   "corrects_invoice_id": null,
   "corrects_invoice_number": null
  }
 ],
 "is_owner": true,
 "money_visible": true,
 "opening_uninvoiced": [],
 "packages": [],
 "policies": [
  {
   "key": "LAU-DEC01",
   "reason": "Default fail-closed: belum ditetapkan owner",
   "set_at": "2026-09-26T03:55:42",
   "status": "PENDING_POLICY_VALUE",
   "value": null,
   "version": "1"
  },
  {
   "key": "LAU-DEC02",
   "reason": "BD probe owner setting LAU_DEC02",
   "set_at": "2026-09-26T03:55:56",
   "status": "SET",
   "value": {
    "billable": [
     "BS",
     "FAILED_ATTEMPT",
     "GOOD"
    ]
   },
   "version": "2"
  },
  {
   "key": "LAU-DEC03",
   "reason": "Default fail-closed: belum ditetapkan owner",
   "set_at": "2026-09-26T03:55:42",
   "status": "PENDING_POLICY_VALUE",
   "value": null,
   "version": "1"
  },
  {
   "key": "LAU-DEC04",
   "reason": "Default fail-closed: belum ditetapkan owner",
   "set_at": "2026-09-26T03:55:42",
   "status": "PENDING_POLICY_VALUE",
   "value": null,
   "version": "1"
  },
  {
   "key": "LAU-DEC05",
   "reason": "Default fail-closed: belum ditetapkan owner",
   "set_at": "2026-09-26T03:55:42",
   "status": "PENDING_POLICY_VALUE",
   "value": null,
   "version": "1"
  },
  {
   "key": "LAU-DEC06",
   "reason": "BD probe owner setting LAU_DEC06",
   "set_at": "2026-09-26T03:55:56",
   "status": "SET",
   "value": {
    "after_payment": "REFUSE",
    "variance_account_id": null,
    "variance_mode": "PRODUCT_COST"
   },
   "version": "2"
  }
 ],
 "priced_deliveries": [
  {
   "charges": [
    {
     "amount": "50000.00",
     "covered_qty": 10,
     "id": "ce0cb74f-788e-4bfd-853d-eab7f5a9572a",
     "included_components": null,
     "kind": "COMPONENT",
     "label": "BD GARMENT",
     "line_no": 1,
     "rate_status": "KNOWN",
     "ref_id": "1e024a0d-5292-41bb-b5c2-4a422dfc5a1a",
     "unit_rate": "5000.00"
    },
    {
     "amount": null,
     "covered_qty": 10,
     "id": "f296d848-7fcb-44bd-bf4b-93dcf3a8e4cb",
     "included_components": null,
     "kind": "COMPONENT",
     "label": "BD SPRAY",
     "line_no": 2,
     "rate_status": "UNKNOWN",
     "ref_id": "b0cee733-0f4f-468c-a3c4-d1801c4b0db2",
     "unit_rate": null
    }
   ],
   "delivery_id": "bec57fb9-7a4f-42ca-be84-07073880eb15",
   "delivery_line_id": "083a7900-799f-40c7-b650-357f47997ec9",
   "delivery_number": "LDR-260923-BEC57FB97A4F42CABE8407073880EB15",
   "mode": "COMPONENTS",
   "physical_local": "2026-09-23T11:00:00",
   "policy_versions": {},
   "qty_sent": 10,
   "sizes": [
    {
     "complete": false,
     "delivery_batch_size_line_id": "ffc9e6da-0a9b-457a-8b4f-bd8f725daeb6",
     "known_amount": "50000.00",
     "qty_sent": 10,
     "size_id": "c8c10000-0000-4000-8000-000000000002"
    }
   ],
   "status": "SENT",
   "total_complete": false,
   "total_known": "50000.00",
   "unit": "PCS"
  }
 ],
 "process_rates": [
  {
   "from": "2026-09-23T00:00:00",
   "id": "01087649-58b7-4bff-a3d3-35f9155ef987",
   "rate": "7000.00",
   "to": null,
   "vendor_id": "af869b2f-43f5-46f3-a612-6f22533179b1",
   "wash_process_id": "e9004082-657f-430f-842b-2e67513ea50d"
  }
 ],
 "processes": [
  {
   "code": "BDP-b00c40204100",
   "id": "18024e16-7825-4e24-808f-603dcd36f62d",
   "name": "BD wash WS"
  },
  {
   "code": "BDP-0f82879e0eff",
   "id": "e9004082-657f-430f-842b-2e67513ea50d",
   "name": "BD wash WS2"
  },
  {
   "code": "CP6-RACE-WASH",
   "id": "c8c20000-0000-4000-8000-000000000003",
   "name": "CP6 Race Wash"
  }
 ],
 "scoped_rates": [],
 "vendors": [
  {
   "bd_priced": true,
   "code": "BD-b00c40204100",
   "id": "fffb0bc1-a14c-45ff-b8c6-0f63ac2580fb",
   "minimum_charge": null,
   "name": "BD vendor WS",
   "pricing_mode": "COMPONENTS",
   "pricing_unit": "PCS",
   "terms_version": "1"
  },
  {
   "bd_priced": false,
   "code": "BD-0f82879e0eff",
   "id": "af869b2f-43f5-46f3-a612-6f22533179b1",
   "minimum_charge": null,
   "name": "BD vendor WS2",
   "pricing_mode": "RATE",
   "pricing_unit": "PCS",
   "terms_version": "0"
  }
 ],
 "pending_cost": {
  "goods": [
   {
    "sku": "CP6-E-BD-92b78d08",
    "lot_id": "97c3bebd-6b00-484c-9bed-79b39251565e",
    "qty_now": 8,
    "qty_sold": 2,
    "hpp_state": "NOT_FINAL",
    "po_number": "AA-INV-PO-d7a64e1d-ed88-445c-8851-2d0934c2bebd",
    "lot_number": "FGP-260923-92217A086FCE4E2EB08B251F9FD04B03-CP6EBD92b78d08-eb0c5a8d",
    "product_name": "CP6 E BD-92b78d08",
    "hpp_per_pcs_so_far": "5010.00"
   }
  ],
  "sales": [
   {
    "id": "7a249b7f-3e63-45ce-9d12-3ef74628d6df",
    "qty": 2,
    "sku": "CP6-E-BD-92b78d08",
    "sale_id": "59c1d83b-f9d2-45e4-9ad6-bd7b05b96ff9",
    "hpp_state": "NOT_FINAL",
    "sale_date": "2026-09-23",
    "lot_number": "FGP-260923-92217A086FCE4E2EB08B251F9FD04B03-CP6EBD92b78d08-eb0c5a8d",
    "recorded_at": "2026-09-26T12:33:15",
    "sale_number": "BD-SALE-4c8e21f161",
    "product_name": "CP6 E BD-92b78d08",
    "policy_version": "2",
    "unit_hpp_at_sale": "5010.00"
   }
  ]
 }
}

// D12: the payment screen the local BD probe read for the owner example (INV-JUN 10,000,000: cash 8,000,000 + claim credit 2,000,000).
const PAYABLES = {
 "vendor_id": "7af76762-dde2-4d8d-88f2-eaa7472943bb",
 "documents": [
  {
   "id": "add92244-d6f4-4b4a-92af-6a01eecd4608",
   "date": "2026-06-15",
   "kind": "VENDOR_INVOICE",
   "total": "10000000.00",
   "number": "INV-JUN-41876b",
   "status": "PAID",
   "paid_cash": "8000000.00",
   "remaining": "0.00",
   "settlements": [
    {
     "id": "3c6ece91-ca24-48f6-a954-1c2f2624aa11",
     "date": "2026-09-25",
     "amount": "8000000.00",
     "method": "CASH",
     "number": "VP-3C6ECE91CA2448F6",
     "status": "POSTED",
     "reference": null
    },
    {
     "id": "53af0216-3f47-4d36-a1e9-bca6cc6acd26",
     "date": "2026-09-25",
     "amount": "2000000.00",
     "method": "CLAIM_CREDIT",
     "number": "KK-53AF02163F474D36",
     "status": "POSTED",
     "reference": "KL-JUL-815b2c"
    }
   ],
   "claim_credit": "2000000.00",
   "correction_credit": "0.00",
   "corrects": null
  }
 ],
 "credits": [
  {
   "id": "2f9ac007-af46-4bd8-a86b-9be7e0e22966",
   "kind": "DAILY_CLAIM",
   "active": true,
   "amount": "2000000.00",
   "number": "KL-JUL-815b2c",
   "applied": "2000000.00",
   "available": "0.00",
   "vendor_id": "7af76762-dde2-4d8d-88f2-eaa7472943bb",
   "approved_date": "2026-09-25"
  }
 ],
 "cash_accounts": [
  {
   "id": "5b0e4a1c-2f7d-4c55-9a0e-3c1d2b4a5f60",
   "code": "KAS-01",
   "name": "Kas besar"
  }
 ],
 "ledger": {
  "matches": true,
  "ap_balance": "0.00",
  "credit_available": "0.00",
  "documents_remaining": "0.00"
 }
} as Record<string, any>

// Owner decision no. 13: the invoices and payment screen the local BD chain read after invoice INV-A-1 70,000 (paid in cash), an
// upward correction KOR-NAIK-1 +2,000 and a downward correction KOR-TURUN-1 -1,500 (both linked to INV-A-1), 1,000 of whose
// credit settles KOR-NAIK-1.
const CORRECTION = {
 "invoices": [
  {
   "paid": "0.00",
   "lines": [
    {
     "id": "dd5eec33-b487-4734-9f6e-4f6d9d3aafcf",
     "qty": 0,
     "note": null,
     "po_id": "4c93c007-7ee9-47f8-9188-31aecd37db3b",
     "amount": "-1500.00",
     "line_no": 1,
     "category": "GOOD",
     "variance": "-1500.00",
     "line_kind": "CORRECTION",
     "net_amount": "-1500.00",
     "discount_share": "0.00",
     "rounding_share": "0.00",
     "receipt_line_id": "20a49ee7-92fe-44a9-8640-054121048005",
     "completes_source": false,
     "product_variance": "-1500.00",
     "released_estimate": "0.00",
     "opening_uninvoiced_id": null
    }
   ],
   "status": "POSTED",
   "due_date": null,
   "vendor_id": "7d477831-a0e7-406d-97b3-70f7c882f99c",
   "invoice_id": "a080f3c8-7666-4b8f-a000-8de7a6fcf6be",
   "journal_id": "f3f8a6e8-1ab7-44fb-be64-bfd13f260feb",
   "tax_amount": "0.00",
   "row_version": "2",
   "vendor_code": "BD-f6301cad3be3",
   "header_total": "-1500.00",
   "invoice_date": "2026-09-25",
   "document_kind": "CORRECTION_DOWN",
   "variance_mode": "PRODUCT_COST",
   "invoice_number": "KOR-TURUN-1",
   "discount_amount": "0.00",
   "policy_versions": {
    "LAU_DEC02": 2,
    "LAU_DEC06": 2
   },
   "rounding_amount": "0.00",
   "corrects_invoice_id": "efe86724-d2ef-4bcf-8647-ee37321bb841",
   "reversal_journal_id": null,
   "corrects_invoice_number": "INV-A-1"
  },
  {
   "paid": "1000.00",
   "lines": [
    {
     "id": "dc761bf7-a8ea-4e7a-88ed-f577698132d0",
     "qty": 0,
     "note": null,
     "po_id": "4c93c007-7ee9-47f8-9188-31aecd37db3b",
     "amount": "2000.00",
     "line_no": 1,
     "category": "GOOD",
     "variance": "2000.00",
     "line_kind": "CORRECTION",
     "net_amount": "2000.00",
     "discount_share": "0.00",
     "rounding_share": "0.00",
     "receipt_line_id": "20a49ee7-92fe-44a9-8640-054121048005",
     "completes_source": false,
     "product_variance": "2000.00",
     "released_estimate": "0.00",
     "opening_uninvoiced_id": null
    }
   ],
   "status": "POSTED",
   "due_date": null,
   "vendor_id": "7d477831-a0e7-406d-97b3-70f7c882f99c",
   "invoice_id": "805f2fd5-b1e9-4dc5-97a0-2633169edc3e",
   "journal_id": "5174fab2-4fe5-4459-b8dd-4c7e19a6ea4e",
   "tax_amount": "0.00",
   "row_version": "2",
   "vendor_code": "BD-f6301cad3be3",
   "header_total": "2000.00",
   "invoice_date": "2026-09-25",
   "document_kind": "CORRECTION_UP",
   "variance_mode": "PRODUCT_COST",
   "invoice_number": "KOR-NAIK-1",
   "discount_amount": "0.00",
   "policy_versions": {
    "LAU_DEC02": 2,
    "LAU_DEC06": 2
   },
   "rounding_amount": "0.00",
   "corrects_invoice_id": "efe86724-d2ef-4bcf-8647-ee37321bb841",
   "reversal_journal_id": null,
   "corrects_invoice_number": "INV-A-1"
  },
  {
   "paid": "70000.00",
   "lines": [
    {
     "id": "541f2bfe-4c61-4239-a9f6-f2acd3bf9083",
     "qty": 10,
     "note": null,
     "po_id": "4c93c007-7ee9-47f8-9188-31aecd37db3b",
     "amount": "70000.00",
     "line_no": 1,
     "category": "GOOD",
     "variance": "0.00",
     "line_kind": "BILL",
     "net_amount": "70000.00",
     "discount_share": "0.00",
     "rounding_share": "0.00",
     "receipt_line_id": "20a49ee7-92fe-44a9-8640-054121048005",
     "completes_source": true,
     "product_variance": "0.00",
     "released_estimate": "70000.00",
     "opening_uninvoiced_id": null
    }
   ],
   "status": "POSTED",
   "due_date": null,
   "vendor_id": "7d477831-a0e7-406d-97b3-70f7c882f99c",
   "invoice_id": "efe86724-d2ef-4bcf-8647-ee37321bb841",
   "journal_id": "4d6d2a97-402b-4dfe-9146-4c28edf8af7e",
   "tax_amount": "0.00",
   "row_version": "2",
   "vendor_code": "BD-f6301cad3be3",
   "header_total": "70000.00",
   "invoice_date": "2026-07-25",
   "document_kind": "INVOICE",
   "variance_mode": "PRODUCT_COST",
   "invoice_number": "INV-A-1",
   "discount_amount": "0.00",
   "policy_versions": {
    "LAU_DEC02": 2,
    "LAU_DEC06": 2
   },
   "rounding_amount": "0.00",
   "corrects_invoice_id": null,
   "reversal_journal_id": null,
   "corrects_invoice_number": null
  }
 ],
 "payables": {
  "ledger": {
   "matches": true,
   "ap_balance": "500.00",
   "credit_available": "500.00",
   "documents_remaining": "1000.00"
  },
  "credits": [
   {
    "id": "a080f3c8-7666-4b8f-a000-8de7a6fcf6be",
    "kind": "INVOICE_CORRECTION",
    "active": true,
    "amount": "1500.00",
    "number": "KOR-TURUN-1",
    "applied": "1000.00",
    "corrects": "INV-A-1",
    "available": "500.00",
    "vendor_id": "7d477831-a0e7-406d-97b3-70f7c882f99c",
    "approved_date": "2026-09-25"
   }
  ],
  "documents": [
   {
    "id": "efe86724-d2ef-4bcf-8647-ee37321bb841",
    "date": "2026-07-25",
    "kind": "VENDOR_INVOICE",
    "total": "70000.00",
    "number": "INV-A-1",
    "status": "PAID",
    "corrects": null,
    "paid_cash": "70000.00",
    "remaining": "0.00",
    "settlements": [
     {
      "id": "768d3c29-2a11-447f-84c5-11ad81021f2b",
      "date": "2026-07-25",
      "amount": "70000.00",
      "method": "CASH",
      "number": "BDPAY-13fe9f36ec",
      "status": "POSTED",
      "reference": null
     }
    ],
    "claim_credit": "0.00",
    "correction_credit": "0.00"
   },
   {
    "id": "805f2fd5-b1e9-4dc5-97a0-2633169edc3e",
    "date": "2026-09-25",
    "kind": "VENDOR_INVOICE",
    "total": "2000.00",
    "number": "KOR-NAIK-1",
    "status": "PARTIAL_PAID",
    "corrects": "INV-A-1",
    "paid_cash": "0.00",
    "remaining": "1000.00",
    "settlements": [
     {
      "id": "8c681075-5b8e-4088-a830-47a952d96c98",
      "date": "2026-09-25",
      "amount": "1000.00",
      "method": "CORRECTION_CREDIT",
      "number": "KR-8C6810755B8E4088",
      "status": "POSTED",
      "reference": "KOR-TURUN-1"
     }
    ],
    "claim_credit": "0.00",
    "correction_credit": "1000.00"
   }
  ],
  "vendor_id": "7d477831-a0e7-406d-97b3-70f7c882f99c",
  "cash_accounts": [
   {
    "id": "b800939d-896c-4d74-881c-be9fd6a38370",
    "code": "CASH-MAIN",
    "name": "Kas Utama"
   }
  ]
 }
} as Record<string, any>

const clone = () => JSON.parse(JSON.stringify(REAL)) as Record<string, any>
describe('laundry BD workspace boundary', () => {
  it('reads the real workspace: an unknown price stays unknown, never zero', () => {
    const ws = parseLaundryBdWorkspace(clone())
    const charge = ws.priced_deliveries[0].charges.find(c => c.rate_status === 'UNKNOWN')!
    expect(charge.amount).toBeNull()
    expect(ws.priced_deliveries[0].total_complete).toBe(false)
    expect(ws.invoices?.[0].lines[0].released_estimate).toBe('28000.00')
    expect(ws.billable_receipts?.[0].capacity.GOOD).toBe(10)
  })
  it('refuses a missing collection (an incomplete read is never "nothing")', () => {
    for (const key of ['policies', 'vendors', 'priced_deliveries', 'opening_uninvoiced', 'pending_cost']) {
      const ws = clone(); delete ws[key]
      expect(() => parseLaundryBdWorkspace(ws)).toThrow()
    }
  })
  it('refuses amounts shown to a reader without the money permission', () => {
    const ws = clone(); ws.money_visible = false
    expect(() => parseLaundryBdWorkspace(ws)).toThrow()
    ws.invoices = null; ws.billable_receipts = null; ws.accounts = null
    for (const v of ws.vendors) v.minimum_charge = null
    for (const c of ws.components) if (c.current) c.current.rate = null
    for (const r of ws.process_rates) r.rate = null
    for (const d of ws.priced_deliveries) { d.total_known = null; for (const c of d.charges) { c.unit_rate = null; c.amount = null } }
    expect(() => parseLaundryBdWorkspace(ws)).toThrow(/HPP sementara tampil tanpa hak/)
    for (const g of ws.pending_cost.goods) g.hpp_per_pcs_so_far = null
    for (const x of ws.pending_cost.sales) x.unit_hpp_at_sale = null
    expect(parseLaundryBdWorkspace(ws).money_visible).toBe(false)
  })
  it('refuses an unknown price that carries an amount and a complete flag that contradicts its lines', () => {
    const priced = clone(); priced.priced_deliveries[0].charges[1].amount = '0.00'
    expect(() => parseLaundryBdWorkspace(priced)).toThrow()
    const complete = clone(); complete.priced_deliveries[0].total_complete = true
    expect(() => parseLaundryBdWorkspace(complete)).toThrow()
  })
  it('reads the D12 payment screen of one vendor: cash and claim credit settle the older invoice, the ledger check agrees', () => {
    const ws = clone(); ws.payables = JSON.parse(JSON.stringify(PAYABLES))
    const p = parseLaundryBdWorkspace(ws).payables!
    expect(p.documents[0]).toMatchObject({ total: '10000000.00', paid_cash: '8000000.00', claim_credit: '2000000.00', remaining: '0.00', status: 'PAID' })
    expect(p.documents[0].settlements.map(x => x.method).sort()).toEqual(['CASH', 'CLAIM_CREDIT'])
    expect(p.credits[0]).toMatchObject({ amount: '2000000.00', applied: '2000000.00', available: '0.00' })
    expect(p.ledger).toEqual({ ap_balance: '0.00', documents_remaining: '0.00', credit_available: '0.00', matches: true })
  })
  it('refuses a payment screen for a reader without the money permission, an unknown settlement method and a missing ledger check', () => {
    const hidden = clone(); hidden.payables = JSON.parse(JSON.stringify(PAYABLES)); hidden.money_visible = false
    hidden.invoices = null; hidden.billable_receipts = null; hidden.accounts = null
    for (const v of hidden.vendors) v.minimum_charge = null
    for (const c of hidden.components) if (c.current) c.current.rate = null
    for (const r of hidden.process_rates) r.rate = null
    for (const d of hidden.priced_deliveries) { d.total_known = null; for (const c of d.charges) { c.unit_rate = null; c.amount = null } }
    for (const g of hidden.pending_cost.goods) g.hpp_per_pcs_so_far = null
    for (const x of hidden.pending_cost.sales) x.unit_hpp_at_sale = null
    expect(() => parseLaundryBdWorkspace(hidden)).toThrow(/Pembayaran vendor tampil tanpa hak/)
    const odd = clone(); odd.payables = JSON.parse(JSON.stringify(PAYABLES)); odd.payables.documents[0].settlements[0].method = 'CHEQUE'
    expect(() => parseLaundryBdWorkspace(odd)).toThrow()
    const partial = clone(); partial.payables = JSON.parse(JSON.stringify(PAYABLES)); delete partial.payables.ledger
    expect(() => parseLaundryBdWorkspace(partial)).toThrow()
  })
  it('reads linked correction documents (decision no. 13): up is a payable, down is a vendor credit that settles documents', () => {
    const ws = clone(); ws.invoices = JSON.parse(JSON.stringify(CORRECTION.invoices)); ws.payables = JSON.parse(JSON.stringify(CORRECTION.payables))
    const r = parseLaundryBdWorkspace(ws)
    const byNumber = Object.fromEntries(r.invoices!.map(i => [i.invoice_number, i]))
    expect(byNumber['INV-A-1']).toMatchObject({ document_kind: 'INVOICE', corrects_invoice_id: null })
    expect(byNumber['KOR-NAIK-1']).toMatchObject({ document_kind: 'CORRECTION_UP', corrects_invoice_number: 'INV-A-1', header_total: '2000.00' })
    expect(byNumber['KOR-TURUN-1']).toMatchObject({ document_kind: 'CORRECTION_DOWN', corrects_invoice_number: 'INV-A-1', header_total: '-1500.00' })
    const p = r.payables!, up = p.documents.find(d => d.number === 'KOR-NAIK-1')!
    expect(up).toMatchObject({ corrects: 'INV-A-1', correction_credit: '1000.00', remaining: '1000.00' })
    expect(up.settlements.map(x => x.method)).toEqual(['CORRECTION_CREDIT'])
    expect(p.credits).toEqual([expect.objectContaining({ kind: 'INVOICE_CORRECTION', number: 'KOR-TURUN-1', corrects: 'INV-A-1', amount: '1500.00', applied: '1000.00', available: '500.00' })])
    expect(p.ledger.matches).toBe(true)
  })
  it('refuses a correction document without its origin, an invoice with one, and a sign that contradicts the kind', () => {
    const base = () => { const ws = clone(); ws.invoices = JSON.parse(JSON.stringify(CORRECTION.invoices)); return ws }
    const down = (ws: Record<string, any>) => ws.invoices.find((i: any) => i.invoice_number === 'KOR-TURUN-1')
    const orphan = base(); down(orphan).corrects_invoice_id = null; down(orphan).corrects_invoice_number = null
    expect(() => parseLaundryBdWorkspace(orphan)).toThrow(/invoice asal/)
    const linked = base(); linked.invoices.find((i: any) => i.invoice_number === 'INV-A-1').corrects_invoice_id = down(linked).corrects_invoice_id
    expect(() => parseLaundryBdWorkspace(linked)).toThrow()
    const sign = base(); down(sign).header_total = '1500.00'
    expect(() => parseLaundryBdWorkspace(sign)).toThrow(/Tanda total/)
    const credit = clone(); credit.payables = JSON.parse(JSON.stringify(CORRECTION.payables)); delete credit.payables.credits[0].corrects
    expect(() => parseLaundryBdWorkspace(credit)).toThrow()
  })
  it('reads goods and sales whose HPP is not final while a laundry price is unknown (decision no. 11), never as final', () => {
    const r = parseLaundryBdWorkspace(clone())
    expect(r.pending_cost.goods[0]).toMatchObject({ qty_now: 8, qty_sold: 2 })
    expect(r.pending_cost.sales[0]).toMatchObject({ qty: 2, hpp_state: 'NOT_FINAL' })
    const odd = clone(); odd.pending_cost.goods[0].hpp_state = 'FINAL'
    expect(() => parseLaundryBdWorkspace(odd)).toThrow(/Status HPP/)
    const partial = clone(); delete partial.pending_cost.sales
    expect(() => parseLaundryBdWorkspace(partial)).toThrow()
  })
  it('matches a priced delivery answer by its request id and the laundry writer action', () => {
    expect(() => validateBdResult({ action: 'POST_DELIVERY', request_id: 'r', client_request_id: 'r' }, 'POST_PRICED_DELIVERY', 'r')).not.toThrow()
    expect(() => validateBdResult({ action: 'POST_INVOICE', request_id: 'x' }, 'POST_INVOICE', 'r')).toThrow()
  })
  it('builds only owner values the server accepts (a variance account is required for VARIANCE_ACCOUNT)', () => {
    expect(policyValue('LAU-DEC06', { variance_mode: 'VARIANCE_ACCOUNT', after_payment: 'REFUSE' }, {})).toBeTypeOf('string')
    expect(policyValue('LAU-DEC02', {}, { GOOD: true, BS: false })).toEqual({ billable: ['GOOD'] })
  })
})
