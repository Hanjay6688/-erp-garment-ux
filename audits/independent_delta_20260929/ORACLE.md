# Independent delta audit — 29 September 2026

Frozen CP6 source: cce68d37083ac2d477f559e3192c7bc8d459aebf.
CP7 source: 6465825d0f8a865f28264626a4e0af818d66967e.
This is an independent delta review, not a blind audit. Writer handoff and source
were read to delimit impacted paths. Writer tests remain cross-check evidence.
Existing fixture builders and installer are reused; assertions below are new.
No product code changes, production access, merge or deployment are authorized.

## Fixed expectations before execution

1. Supplier return of 2 x 10 leaves 80/100/60 payable. Allocate 7.13 and 2.87:
   payable becomes 90/92.87/57.13, total 240; stock and cost movement facts stay
   unchanged. Replace allocations, then restore original; replay of an older
   UUID never reapplies its obsolete allocation. Same UUID/different amount fails.
2. An allocation made today cannot fund a payment dated yesterday. An original
   purchase with 80 of historic payable cannot pay 90 yesterday after today's
   allocation makes its current payable 100. A valid 70 payment still succeeds.
3. Mutations of already-posted allocation events are refused, including deletion.
4. Commercial identity follows membership at the exact boundary; physical IDs
   and quantities remain unchanged. Scheduled future membership is not current.
5. A new invoice cannot retroactively turn an older HPP snapshot from provisional
   into complete while retaining its old monetary value. Current HPP includes
   the invoice; invoice reversal restores the original unknown cost state.
6. Current-price authority for component FREE/WAIVED/UNKNOWN remains vendor based;
   these states stay distinct when queried after a later paid vendor version.
7. Public supplier reads/writes enforce current permissions under real Auth,
   including replay after permission revocation; private helpers stay private.

CP7 checks separately cover unknown/stale states, shared output, permissions,
source/size conservation, STOP handling, and operational gates. Synthetic shell
tests are not evidence of a connected ERP, training, reminders or WhatsApp send.

Business failures are retained as FAIL; fixture/setup failures as INCOMPLETE.
Results are scoped, not a certification of every CP6/CP7 combination.
