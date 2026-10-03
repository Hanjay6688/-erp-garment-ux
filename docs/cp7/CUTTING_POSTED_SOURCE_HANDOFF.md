# Posted cutting source · Native76 candidate

Owner continuation: make source inspection/edit/correction/inverse usable without guessing data. This increment connects posted cutting inspection only. It adds no posted-cutting edit/inverse, pickup writer, Native function change, new RPC, role or business DML privilege. Fresh Native/Auth/browser qualification is pending.

## Actual existing reader and exact source

The frozen cutting draft selector excludes issued or picked-up groups. A different existing Native reader, erp_get_cutting_pickup_queue_v1(ALL,NULL,NULL,100,offset), includes every material_issue_posted group, including pickup/QC and finished PO history. It joins the group's actual PO/model and orders by cut_at, group_number, id. Its current right is production.distribution.view. production.cutting.view alone does not authorize that reader.

Native material issues store source_type=CUTTING_GROUP/source_id=group UUID; their journals use CUTTING_MATERIAL_ISSUE with that same UUID. The read-only source resolver now supports those two kinds as domain CUTTING/route mandor-wip. The existing seven-field document remains closed. Its new CUTTING_GROUP focus contains only group id, actual parent PO id and exact 100-row page offset. Other focus shapes remain unchanged. Three SELECT tables are added only to the existing private read role: cutting_groups, production_orders and product_models. Current access and current distribution view are checked before metadata. Missing groups refuse; unposted groups remain explicitly unsupported by this posted path.

## Frontend boundaries

Mutasi bahan and owning journal source links open the existing Bagi Potongan page. QC receipt-source cards also offer Buka potongan asal using their actual current Native group reference. The page reads the exact ALL page without query or pattern filter and checks group UUID, actual PO UUID, number, status and exact safe Native version against the source receipt. Missing, moved, stale, wrong-PO or denied data retire the detail. A source target never falls back to the first adjacent row. Unsafe large numeric versions refuse rather than pretend they match an exact bigint string.

The bound preview disables allocation inputs, all pickup save/post/delete controls, other selections, filters and paging. It starts no business writer. Current metadata is displayed only after the owning Native read succeeds. Refetch retains the exact target/page. An explicit Tutup transaksi asal retires the preview and performs a fresh normal queue read; a held response cannot revive the old detail. Current permission/actor/navigation generations still retire pending responses. Existing ordinary pickup/recovery writers remain unchanged.

## Predeclared actual qualification

Every original Native69 ID remains. Native76 requires41 DB,4 retained actual schedules,11 Auth/HTTP and20 browsers. The seven additions are:

- CP7_SOURCE_CUTTING_POSTED_EXACT: actual receipt/cutting/pickup/sewing/laundry/QC history; material and journal kinds resolve to the same actual group/PO; the cutting draft selector excludes it; complete Native business state stays unchanged.
- CP7_SOURCE_CUTTING_NATIVE_PAGE100:101 actual Native receipt/cutting posts, target outside the first100, exact server-calculated page and PO, unchanged state after navigation.
- CP7_SOURCE_CUTTING_CURRENT_AUTHORITY: active custom role, cutting-view-only refusal, current distribution view, same-subject revoke before metadata, missing/unposted refusal, no source-role Native writer EXEC or ERP DML.
- CP7_SOURCE_CUTTING_HTTP_EXACT and CP7_SOURCE_CUTTING_HTTP_CURRENT_REVOKE: actual Auth/PostgREST metadata plus owning ALL read, anonymous refusal, unchanged token after current permission revoke, unchanged full Native state.
- CP7_SOURCE_CUTTING_BROWSER_DESKTOP and MOBILE: actual issue journal, material ledger and QC all open the same posted group/PO with current Native readback; every preview writer/input disabled; zero business writer requests; complete Native state unchanged; six unedited screenshots.

Python and browser-script syntax and budget/retained-ID checks pass locally. The22 new unit/DOM controls are authored but not executed locally; React/Vitest are unavailable here. They must pass in full Shell CI. These are separate from the required actual Native76 executions. All existing install/restore/primary/backup/advisor/Auth/browser cleanup gates remain mandatory. Full attention284/F04/retained F03/owning note budgets are not reduced. No full P18/P19, independent P20, installed P21 or production acceptance is inferred.

## Continuation entrypoints

scripts/cp7-src/transactions/source.sql, scripts/cp7_transaction_source_bundle.py, src/transactionSource.ts and src/cuttingSource.ts own the closed source contract. src/ConnectedPickupPage.tsx and src/ConnectedQcFinalPage.tsx own navigation/preview. scripts/cp7_cutting_source_cases.py declares actual DB/HTTP inputs; source browser fixture/script retain all earlier journeys and add the two new executions. Preserve first failures and fix the owning cause without changing a case budget, Native writer/guard or timeout. Posted cutting correction/inverse still needs its own owning contract and proof; this read path cannot supply it.
