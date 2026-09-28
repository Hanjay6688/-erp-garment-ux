# Writer continuation — 28 September 2026

Owner mandate: finish the handover, then continue the laundry/vendor authority,
pending kontra bon, relevant PR30 findings, and same-supplier return credit family.
Stop writing and inform Hansen if another writer pushes. Unpushed work in another
chat cannot be observed. CP6 HOLD; audit_complete=false; production_go=false.

## Baseline

- Writer head: df2c09f6a9c5b5e6aaa2e500d46f9cfa8dd45f72.
- Tree: 928e2d74d2d422fad7ba0417c27d0402cc891b25.
- Full context: ERP_Kesiapan_Takeover_Writer_20260928.md, retained handover.
- Product source authority correction was documentation only at that head.
- Earlier BF 125 combined results do not establish vendor tariff authority: some
  laundry fixtures incorrectly configured monetary rates in the SKU master.

## Owner oracle

1. Vendor master owns process/package/component rates. A known combination and
   separately checked components are alternative selections for a delivery.
   SKU history suggests selections and past amounts only.
2. Details may be empty until kontra bon. Price stays unknown, rate NULL, with no
   invented component or FREE/WAIVED price. Physical receipt/QC may continue.
3. Invoice establishes actual cost by its physical source; partial billing leaves
   remaining cost pending. Reversal reopens it. No quote changes after billing.
4. Credit settles other unpaid documents of the same legal counterparty without
   reducing aggregate AP twice. Laundry AP_VENDOR and supplier AP_SUPPLIER remain
   separate. Fabric and accessory supplier cases both need explicit evidence.
5. PR30 D01: withdraw the proposed size-tariff activation as an owner requirement.
   Preserve explicit BD policy handling; a wave binding cannot change authority.
6. PR30 D02: before first work snapshot, revalidate wave membership at the service
   time; refuse stale references and require explicit rebind. Preserve prior pins.
7. PR30 D03: group, membership and product reads all use the requested instant;
   optimistic-write revision remains the latest master revision.

## Source impact and verification

- BF laundry builder / rate helpers / SKU edit UI: remove monetary SKU authority,
  preserve old snapshots, use vendor versions and exact receiver quantities.
- BF work + workspace reader: first-use membership and historical projection.
- BD pricing/receipt/invoice/completeness functions extended by BF: no-charge
  pending delivery, invoice settlement, HPP/accrual/close/reversal consumers.
- Laundry send/unknown/invoice UI: real optional details and selection assistance.
- Supplier return allocation, payments, ledger checks and connected UI: inspect
  separately; current return code reduces source purchase AP and rejects an
  already-paid source. It is not proof of a reusable cross-document credit.
- Disposable native cases, real Auth, contention, browser and build evidence.
  Outcomes and exact pins will be appended as obtained; source inspection is not
  a native PASS. Old failures and invalid oracles remain in their original files.

Supabase changelog fetch timed out twice during preparation; database trigger
documentation was accessible. No platform/dependency upgrade is part of this work.

## Owner clarification, 16:53 WIB

Credit remains applicable to its original purchase as well as other bills of the
same supplier. It may be split over multiple eligible bills within its balance;
reallocation must preserve actual cash history and release the previous use.
Slogan: **Reliable data adalah dewa; Keuangan (termasuk laporan), stok, HPP adalah
raja.** Identity: **VENI. VIDI. VICI. ERP. — I CONQUERED ERP.**
