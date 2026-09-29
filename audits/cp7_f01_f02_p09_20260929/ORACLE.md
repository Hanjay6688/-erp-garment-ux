# Independent F01 / F02 repair / P09 continuation audit

Frozen product: `ee8699829bc53799e5f840bb5490059e456fa81a`; documentation checkpoint `e3ddcec94c4db2b6fe299cdadc82f50d57781bfc`. Later P10 is outside this candidate. No product modifications. Disposable accepted CP6 install only; no hosted writes.

This is disclosed retesting, not a blind audit. Original F02 oracle and case bodies are copied unchanged from the prior independent audit. New cases use ordinary public writers and independently chosen quantities. Existing writer fixtures create masters / valid prerequisites; reuse does not make their expectations independent.

## Independent expectations, recorded before execution

1. Original QC/receipt BS reversals restore `[100,100,0,0,0,0]`; GOOD-only, rework inverse and source-cap controls retain original expectations.
2. Repeated QC/cancel/re-QC must retire only cancelled BS, conserve 100, and preserve previous archived snapshots.
3. Matcher/allocator: 17 XS, yield 2/3 permits at most 11 GOOD. Missing matching facts cannot be FEASIBLE. RED to BLUE, required unknown evidence, stale target/source refs, mismatched snapshot and duplicate facts must fail closed. Same-facts RED to RED must succeed. These are private-kernel checks; authoritative public planner capture remains a separate future integration gate.
4. F01: two actors sharing a UUID cannot see or replace each other's snapshots. Current deactivation blocks replay/read. A finance grant cannot manufacture previously uncaptured amounts; revocation hides previously captured amounts immediately. Admin source fixtures for this reader test are explicitly synthetic, not transaction acceptance.
5. P09: a one-line invoice for 22,000,000 must post, preserve quantity, book matching supplier AP and reverse exactly. Two receipts at 7×13 and 11×17 give 278 with no source duplication; reversing must restore both physical quantities and prior ledgers.
6. Physical counts: two actual stock items 10/10 counted as 8/7 produce independent deltas -2/-3, and inverse restores both. A formerly zero-delta reviewed item changed before posting invalidates the entire old count, not just its changing line. Quantities and basis come from public reads, no posted stock inserts.
7. UUID reuse across transfer/count commands cannot reuse a different action's result or partially create a second document. Public/private ACL and Auth separation stay enforced with P09 installed.
8. Own HTTP: after ordinary QC reversal, public combined WIP capture gives 100 WIP and replay is stable; another actor cannot read the run, and current deactivation denies cached replay.

## Regression / evidence separation

Rerun writer's complete P09 native/race/HTTP/browser suite with the frozen product, plus writer's focused F02 repair and matching cases. Label writer reruns separately from independent cases. Existing safe F01/F02 results remain evidence at their original candidate; do not claim all historical cases were re-executed.

A setup error is INCOMPLETE until corrected without weakening the oracle. A concrete violated expected behavior is a counterexample, not a general claim about production. Preserve first-run evidence. Full P09/F03 is not accepted merely because the implemented increment passes; handoff explicitly leaves material issues, multi-input/zero-history UI, mixed-source and paid-source returns open. `production_go=false` throughout.
