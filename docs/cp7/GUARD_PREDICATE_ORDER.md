# Current guard predicate candidate

> 3 October 2026 merge review: Claude’s completed `f4049e4f` handoff is merged into `cp7/integration`. Current source and qualification are controlled by [CLAUDE_MERGE_VERIFICATION_20261003.md](CLAUDE_MERGE_VERIFICATION_20261003.md); the source-specific checkpoints below remain historical. Receipt correction now has a fresh 42/42 Native result at `48fe7c2`; whole CP7 and every-submenu transaction controls remain open.


## Actual failing source

Source0dec1c1d/treefa555adb, run37052402095/job110988741241 executes40:28 DB/4 race/3 Auth-HTTP/2 browser PASS and3 ordinary browser commands incomplete. Exact failure Original and all archive-member hashes are retained in evidence/owning-note-correction/incomplete40-0dec1c1/. Installation, exact restoration, primary, backup, advisor and Auth0→0 pass; runtime is false.

The actual PostgREST sessions are sampled79 times each in the three failed cases. Maximum observed query elapsed is7908.021/7901.450/7919.529ms; sampled waits are null. Their static server error frames stop inside `erp.has_permission`, `erp.require_internal`, `account_id`, Native PO HPP GL refresh, and the owning note's sale/return/payment replay. These are sampled lower bounds, not exact command durations or proof that no short wait occurred.

The previous private timings ran with a PostgreSQL session user. `require_internal` explicitly returns immediately for that session principal, so those timings do not exercise the expensive real PostgREST guard path. They did not establish a JIT cause.

## Guard repair candidate

The declared CP7 internal guard and its payroll/attendance/sales admissions combine context identity and permission checks using SQL `AND`. That expression does not force permission evaluation to wait for a matching context row. A constant permission lookup can become a one-time filter for an irrelevant scope. The actual failing frames and source identify this as a concrete candidate; the speedup and complete timeout closure still require actual HTTP qualification.

The candidate retains indexable PID/transaction filters and gates each permission expression behind `CASE` with the same exact PID, transaction, actor, action and permission identity. Matched-context permission calls, including throwing sales command checks, remain live. The original legacy-role fallback stays at the end. No global authority cache, early legacy-role return, new grant, money formula or timeout is introduced. PostgreSQL conditional semantics: https://www.postgresql.org/docs/17/functions-conditional.html.

Five isolated database controls cover irrelevant permission-read faults, exact fine-only context, immediate fine-right revocation, inactive actor/role, wrong actor/transaction/action, caller GUC spoofing, and a matched sales context whose revoked fine right must still fail before an ADMIN fallback. Local PostgreSQL/WASM is unavailable; no local database qualification is claimed. Actual Native PostgreSQL Shell at source15aca456/tree57338a9d, run37061657821/job111019489876 executes and passes all five controls without skips, all1278 tests in138 files, six shell browser checks, security and build. Both CodeQL jobs111019490235/111019490248 pass. Receipt: evidence/shell/qualified1278-15aca45/RECEIPT.json.

At that exact guard source, cutting57 also qualifies all34 DB/8 race/5 Auth-HTTP/10 browser cases at run37061659760/job111019496261. Every installation/restoration/unchanged-primary/backup/advisor/runtime/Auth0→0 gate passes. Unmodified runtime Originals and every archive-member hash are retained in evidence/f04-native-history/cutting-learning-qualified57-15aca45/. These results do not qualify actual note/F05 HTTP performance or close the preceding timeout cause.

All eight retained F03 buckets now also qualify this exact guard source at run37061659744: P09 132 plus3 separate smokes, P10 34, P11 64, P12 90, P13 50, supplier credit5, cash/installments61 and customer refund10. Every original boundary, Auth, primary, backup and advisor gate passes; every bucket uses bundle02a450d332e65dfba2f1f9d08ed0e680f5f0ec3424553820d5650988f16abbb3. These overlapping controls are not a summed unique total or full-family acceptance. Exact Originals: evidence/f03-full/all-eight-qualified-15aca45/.

The already-integrated receipt implementation also qualifies32=26 DB/3 race/1 Auth-HTTP/2 browser at the same source, run37061659782/job111019498148, with every original boundary/package/primary/backup/advisor/runtime/Auth0→0 gate. Exact Original: evidence/receipt-correction/qualified32-15aca45/. This is a regression of the qualified integrated source, not an import or completion claim for Claude's unfinished section.

Complete Native40 now also qualifies at the same source15aca456, run37061659616/job111019496644:28 DB/4 race/3 Auth-HTTP/5 browser, every package/restoration/primary/backup/advisor/runtime/Auth0→0 gate and zero console errors. Actual successful query samples peak at2174.423/1561.253/1676.913/1673.279ms; no sampled waits or static server error frames appear. These sampled lower bounds and passing cases qualify this exact note source; they do not alone establish complete preceding intermittent timeout cause closure. Exact Original: evidence/owning-note-correction/qualified40-15aca45/.

Complete Native284 now also passes at source15aca456/run37061659770/job111019496822, bundle1c81bf8164d67aeadb17dc79d975e757a32a45063b11806d6fedb00ae3f84bf3, with every original package/restoration/primary/backup/advisor/runtime/Auth0→0 gate. Exact archive11252337076 (347887394 bytes/SHA-2567cc1d2cf2a3cded208c933305815a3a316cb9efec714f57869c372131d4ee4bb) is pinned for read-only Original extraction; retention must still be verified. Every mandatory guard-source family above now passes. That source qualification does not alone close every prior intermittent timeout cause.

The separate E01 mobile refetch reveals a subsequent UI read-visibility defect; its shared-hook repair requires complete current-source qualification in PENDING_SOURCE_READ.md. Original Native financial functions, owners and ACLs remain pinned; original CP6 release files and Claude's receipt/name/final-price implementation are unchanged.

CP6 HOLD; audit_complete=false; production_go=false. Claude's unfinished scope remains deferred. Full family, scale/material, literal-year receipt proof, independent/demo and hosted acceptance remain open.
