# Independent internal writer source review — Native58 opening return ordering

Candidate reviewed: `7613621553b6cb8f2227d2b6dcca695ae019f15a`. Initial diagnosis was locked to root before receiving any current helper conclusions. Read-only source inspection; no database commands, runtime claims, product edits, or external audit claim. Next-scope work is paused in `ow04-next-scope-proposal/INITIAL_LOCKED_ASSESSMENT.md`.

## Exact finding

The frozen fractional money oracle remains valid. The new projection describes the whole return vector from actual reconciled before-book to cumulative after-target. Native's opening status trigger currently posts that whole vector first in a separate lifecycle journal. The later SALES_RETURN builder therefore sees no HPP delta. Its exact projected-line guard correctly refuses. With refund zero, it produces no SALES_RETURN journal at all, and the old NO_JOURNAL physical proof correctly rejects a positive stored HPP snapshot.

The important causal ordering is:

1. AH `post_sales_return` sets current stored six-decimal item HPP and writes SALE_RETURN physical movements at release lines303–306.
2. AH line317 updates return status DRAFT→POSTED. This makes the return visible to cumulative net-sold targets.
3. The installed bootstrap attaches `trg_sync_opening_hpp_after_return_status AFTER UPDATE OF status ON erp.sales_returns`, executing `erp.sync_opening_hpp_after_return_status()`.
4. AC release11028–11038 implements the trigger. It selects affected OPENING lots **only when an `opening_lot_hpp_gl_state` row exists**, then calls Native opening synchronization on today's Jakarta business date.
5. BE release4068–4140 is current opening synchronization. It retains exact source-cost validation4100–4117, invokes cumulative nonPO synchronization4118–4119, and refreshes raw diagnostics afterward.
6. BE cumulative synchronization3400–3459 computes target−actual-book, posts its complete vector as `NON_PO_HPP_GL_SYNC_V2620F`, and records an event before returning. Lines3420–3439 carry product dimension and no customer; lines3442–3457 link the event to the opening HPP version rather than the return.
7. Only after the trigger returns does AH331–336 calculate return target−book. This is now zero. AH414–417 posts SALES_RETURN only when at least two constructed lines exist.
8. Coordinator `03_native_initial_callbacks.sql`217–220 correctly requires exact full projected SALES_RETURN lines. `source/member-proof.sql`86–96 correctly admits old NO_JOURNAL only for refund0/snapshot0 and exact physical proof.

All source paths above are under `supabase/release/cp6-t3/`. Current bootstrap is `supabase/tests/fixtures/erp_enteng_cp45a_catalog_bootstrap.sql.gz`; only read/decompression was used to verify trigger attachment. The current AC definitions replace bootstrap's older function bodies.

## Why this source differs from old44

The genuine fractional fixture creates a DRAFT opening with initial cost0, calls unchanged Native `post_opening_balance`, then calls unchanged Native `post_opening_hpp_correction` with a high-precision numeric unit. See `hpp-fractional/cp7_ow04_fractional_hpp_cases.py`135–166. AC4606–4634 shows that correction creates a real successor HPP version, a real correction record, then calls synchronization. That call establishes `opening_lot_hpp_gl_state`, activating the existing status trigger on subsequent sale/adjustment/return actions. No fake state is needed to reproduce this failure.

Reported first CI result was50PASS/8INCOMPLETE out of58; this review did not execute it. The eight reported failures fit the exact source branch:

| Scenario | Frozen economic result | What current source does first | Consequence |
|---|---|---|---|
| NONPO_SECOND_RETURN_CARRY | Prior ordinary refund0 return must post Dr FG.33/Cr COGS.33; reviewed second must post .34/−.34 | Prior return's opening trigger posts the .33 transfer | Prior family NO_JOURNAL proof rejects positive snapshot before quote |
| NONPO_FG_ZERO_HPP_JOURNAL | Full return vector FG0/COGS−.01/OTHER+.01, real HPP journal | Opening trigger posts Dr OTHER.01/Cr COGS.01 | No SALES_RETURN journal; positive snapshot old NOJ proof rejects |
| NONPO_OTHER_POSITIVE | FG+.33/COGS−.34/OTHER+.01 | Lifecycle journal consumes full vector | SALES_RETURN revenue/AR-only differs from projected full journal |
| NONPO_OTHER_NEGATIVE | FG+.34/COGS−.33/OTHER−.01 | Same | Same |
| TWO_LOTS_SAME_NONPO_PRODUCT | Joint FG+.66/COGS−.66 | First affected-lot sync reconciles complete product; later lot sync is zero | Same |
| NATIVE_RECOST_STALE_QUOTE_REFUSED fresh quote | Old quote refuses; current2/3 unit quote expects .66/−.66 | Genuine recost retained; later return trigger consumes fresh vector | Fresh settlement journal differs |
| TWO_ALLOCATIONS_SAME_LOT_GROUPED | One joint .67/−.67 vector | One whole-product lifecycle transfer | Same |
| DEBITS_PER_GROUP_BEFORE_NETTING | Separate signed vectors retain group dimensions/scalar | Trigger consumes each product vector | Same |

## Minimal safe integration contract

Keep status POSTED before cumulative return target construction: targets subtract only POSTED returns, so simply moving status to the end is wrong. Keep the frozen expected file digest `f53001d8ec87289a7fc7ca1a6f69752f994480418256923133329e6395a37d4c`, exact return-line guard, and strict snapshot0 NOJ proof.

A narrowly bound hook may defer the **financial opening status synchronization** for the exact own DRAFT→POSTED initial return. It must establish, from protected server state, current backend/transaction/actor, exact pending ordinary/reviewed RETURN context, current own work phase ENTERED, exact return/header/items, return id, and affected locked lot set. It cannot be a caller flag or a blanket setting. It must not alter unchanged Native, native-empty, correction/reversal, foreign-return, or other status transitions.

This must support both ORDINARY and REVIEWED_SETTLEMENT initial work: fixture303–305 creates a real ordinary refund0 prior return before requesting the second quote. Restricting deferral only to reviewed settlements leaves SECOND_RETURN_CARRY failing.

Bind and lock the complete relevant opening state rows, corrections, and version/source identities before the existing period/account boundary; reread under Read Committed after lock expansion. Currently `initial_hpp_support_v1`223–259 has lot/HPP/movement/return/conversion/journal support but no opening state or opening correction rows. Explicit absence of state matters: do not create a state during post-return refresh if the trigger was ineligible before. Lock order must remain FG envelope → complete source set → mapping/account/cash → period. Reentry may only reread already-locked source; it may not acquire new source locks below period.

Do not hide Native's source correction check when deferring. For every state-present affected opening lot, require before product target==actual book, no source total change, and `round(hv.total_cost,2)-round(lot.initial_qty_pcs*state.current_hpp,2)=0`. In the genuine tested source this is0. A stale state or large-basis six-decimal rounding mismatch must remain closed until a separate proven path supports it.

After the exact SALES_RETURN journal is posted, validate actual source/date/full line dimensions against the sealed projection and require every after-target==actual after-book vector. Then refresh the unchanged Native opening diagnostics for captured state-present lots in deterministic order, while proving the refresh creates **no financial journal or sync event** and preserves actual supporting book lines. At this point Native cumulative synchronization should see delta0 and return without posting. Any unexpected source delta or new financial event aborts the same transaction. The refreshed mutable diagnostics may change; historical versions, correction rows, journals, movements, and physical timestamps remain intact.

Current useful hook anchor: `native_return_complete` is inserted by admission transform03:43–46 immediately after the Native journal branch, before AH's target assertions419–427 and sale-status update429–431. It can validate/refresh before `store_initial_plan_v1` at coordinator04:227. `store_initial_plan_v1`89–104 already demands actual own journal/source/line/date proof; it should retain that proof rather than accept an unrelated lifecycle journal.

The later sale-status trigger needs its original behavior: it runs after the return journal/book is reconciled and therefore has no further monetary delta. The exact initial-return trigger deferral must not become a global trigger bypass.

## Date and immutable-history constraints

The opening trigger uses today's Jakarta date (AC11037), while the frozen return contract demands original physical economic date and selected lawful/causal book date (`hpp-fractional`529–531; coordinator03:184–203). An unrelated lifecycle journal cannot be relabelled or backdated into the return. Its missing customer dimension and HPP-version source identity also make it unsuitable as the return's actual financial member.

Do not remove an opening correction/state row to make the fixture avoid the trigger, rewrite a posted version or journal, force the unit to exact cents, or inject projected HPP into `p_lines` after the trigger already posted it. The latter would double-post a valid before→after transfer.

## Focused qualification witnesses for root

- Existing58 including both the ordinary prior return and fresh-after-recost path; old44 remain unchanged.
- Frozen exact return journal source/id/date/dimensions and full group vector, physical current six-decimal snapshots, source history preservation, replay identity, cash unchanged for CREDIT/HPP-only.
- State-present opening return refresh: before/after lifecycle event+journal set identical; only allowed opening diagnostics refresh and actual return journal/materialization are new.
- State-absent opening lot: no new state created by this deferral/refresh; original financial construction stays valid.
- Foreign return/status/reversal/correction/direct-native/native-empty context cannot receive the initial own-return deferral.
- Source state/version/correction set changed after quote: old review refuses atomically, fresh lawful quote recomputes; pending source-total mismatch refuses atomically.
- Any final injected failure restores status, stock, source-state diagnostics, journals, private scopes, and request receipt.

No product implementation or runtime qualification was performed by this subagent.
