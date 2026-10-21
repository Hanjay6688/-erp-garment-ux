# Actual patch counter — opening fractional HPP return

Internal writer source review only. No database or Native execution, product edit, commit, nested agent, external browsing, or external audit claim. Candidate base76136215 with root's uncommitted opening integration patch reviewed. Initial diagnosis was locked before other helper conclusions.

## Result at latest reviewed source

No additional source contract blocker found in the narrowed CP7 ORDINARY + REVIEWED_SETTLEMENT repair. Runtime58 remains required. Direct fractional Native EMPTY is explicitly outside this repair; its original opening status trigger behavior remains.

### Accepted changes versus initial counter

- `coordinator/02_initial_projection.sql`156–158 acquires complete present opening-state locks and correction history locks alongside existing full lot/HPP/PO source set, before the explicit account/period boundary.
- `02_hpp_book.sql`223–230 builds a separate full opening source profile: state rows and complete correction history, including state absence.
- Projection group reads bracket that profile200/242–243 and retain it249. Full private projection is hashed by the quote426–428.
- `03_opening_return_hpp.sql`27–37 requires exact current own initial work/native scope, actual paid guard values, actor/request/operation, ENTERED phase and POSTED own return. Both ordinary and reviewed origins are covered.
- `defer_opening_return_hpp_v1`48 admits only actual DRAFT→POSTED. Lines52–54 reread every sealed group's opening source, including absence; selected eligible lots56–62 must lie within the prelocked lot ids. No new caller flag, generic bypass, alternate Native authority, or direct grants are added.
- Direct Native EMPTY has no initial work; owner helper39–41 returns null and the original trigger loop remains. No new direct early-source lock/seal is needed for this narrowed scope.
- `03_native_admission_transform.py`41–47 retains the exact Native journal construction and post_return_journal guard, inserts flush only after that journal branch, then runs existing complete callback. It does not add HPP lines after another journal posted them.
- `flush_opening_return_hpp_v1`80–89 asserts target/book before and after refresh and compares immutable actual posted support. Mutable opening diagnostics are deliberately excluded from this post-refresh comparison.
- `03_opening_hpp_diagnostics.sql`20–33 requires exact deferred own lot, nonPO OPENING, original source movement, current HPP and state, Native expected source-basis delta0, and canonical target/book equality.
- Diagnostics helper34–64 is byte-for-byte equal to the diagnostic tail of current Native BE opening sync. It updates only Native's diagnostic state and does not invoke the financial or global conversion synchronization functions.

### Improvement over my initial integration suggestion

My initial source-only direction proposed invoking unchanged Native opening synchronization after actual book closure and proving no money. Root's diagnostics-only tail is safer: BE `sync_non_po_product_hpp_to_gl_v2620f`3384–3386 can call `be_nonpo_sync_all_v1`; BE633–647 then prepares all admitted nonPO conversions and synchronizes every nonPO product. Even a zero own-product delta can therefore traverse unrelated products. The copied exact tail avoids this expansion while keeping the original financial guard and current source function unchanged.

### Capture and rollback/source identity

- New trigger transformer `opening_return_status`59–65 accepts only original AC body hash5bd16275…, preserves the unchanged-status guard and entire original loop, and adds one private deferral call. Captured pg_proc metadata including invoker security remain unchanged in the composed plan.
- `admission.SPECS`210 adds the Native trigger function. `derive_plan.NATIVE/REQUIRED/TARGETS` derives its census from SPECS, so actual before/after function capture, trusted predecessor comparison, install verification and restore include it. Function count now derives from the exact entries rather than hard-coded19.
- Owning bundle captures and exactly verifies real trigger attachment210–228, original Native sync full definition/body/metadata264–265/367, and the pending work table's actual constraints/closure trigger231–237. It also verifies unchanged original Native sync and trigger attachment on uninstall.
- Source-derived diagnostics helper pins current Native body59d22a90… and required owner/security/config in its SQL source guard.

## Bounded source checks actually performed

Read/decompressed the installed bootstrap fixture to verify the real AFTER UPDATE OF status trigger attachment. Read current AC/AH/BE canonical bodies and current coordinator/admission/assembler files. No SQL was run.

A pure file extraction/hash comparison proved:

- Current Native opening sync body hash:59d22a90beecddbe2cd4ca8cd246493c61f2ec9ad882311e7f974819cd117a1e.
- Original status trigger body hash:5bd16275dc867461f672526766b7ea0f999f8a7ce8a2ab4760a750d02d811a01.
- Diagnostics tail exact byte equality and tail hash:a18f1660895f97549dd3dce98a73e0a16e57f5d313da4c8b6a3e9fdf32fe5783.
- Frozen expected file remains f53001d8ec87289a7fc7ca1a6f69752f994480418256923133329e6395a37d4c.

Machine-readable source check: `NATIVE58_SOURCE_TAIL_RECHECK.json` in this directory.

## Remaining limits requiring honest qualification

- Source expected-basis mismatch (including a large initial basis whose six-decimal stored unit rounds to a different cent total) still refuses atomically. The tested basis3 examples have delta0. This does not establish universal fractional source correction support.
- Positive stored snapshot + true zero full monetary/HPP vector stays fail-closed under existing strict NO_JOURNAL proof. No relaxation was reviewed.
- This patch fixes bounded CP7 return construction only. It does not claim direct fractional Native EMPTY support or correction/reversal/consumption completion.
- The first failed run remains50PASS/8INCOMPLETE; no successful replacement runtime was observed by this reviewer. Frozen exact line/date/source/cash/physical/replay assertions must pass in actual58 qualification.
