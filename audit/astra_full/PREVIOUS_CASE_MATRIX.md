# Pre-registered independent cases

All rows initially NOT_RUN. Oracles below were written from the contracts before reading the corresponding
implementation. Test IDs may have separately counted subchecks, but a parent passes only when all mandatory
subchecks run. Writer fixtures and inherited suites are explicitly labelled; they do not replace these oracles.
Amounts below are synthetic test values, never production settings. Test time may be simulated only in a copy
and must be labelled. Native runtime evidence is required for behavioral claims.

| ID | Area | Independent experiment and oracle |
|---|---|---|
| AS20-01 | Access | Revoke an actor after creating a result; old UUID, new UUID, cached/page/AI/report/reminder reads must all enforce current permissions. |
| AS20-02 | Access | Enumerate every private CP7 function/table/schema; anon/authenticated/service_role have no direct unauthorized route. Real REST attempts complement ACL inspection. |
| AS20-03 | Access/race | Revoke while command waits on its final business lock; after release, no write from revoked actor. Compare complete affected facts before/after. |
| AS20-04 | Idempotence | Same UUID/body creates one effect; same UUID/different body refuses atomically; same UUID across actor or action never replays another command. |
| AS20-05 | Recovery | Drop one successful response, reconnect/reload, reconcile by original UUID; no second stock, journal, payment or plan effect. |
| AS20-06 | Finance | Use 73 units at 12.37, finish 41, sell 13 at 29.91, return 4 from their original lot. Independently calculate each balance in Decimal, then reconcile to source/journal/reports. |
| AS20-07 | Finance | Post amounts around 21,474,836.48 and a 22,000,000.01 control, with zero and nonzero discount; finite schema-valid values must not overflow a narrower intermediate. |
| AS20-08 | Finance | Odd cents across unequal quantities; total allocated exactly equals source, no charge to ineligible size. Every journal balances. |
| AS20-09 | Time | Transactions either side of WIB midnight and late recost; economic date follows approved max-date/closed-period rules, never silently UTC date. |
| AS20-10 | Finance | Unknown laundry price with ALLOW_PENDING allows sale but remains nonfinal and blocks affected close; later price completes valuation without changing physical quantities. |
| AS20-11 | AP | Receipt before invoice, partial late invoice, supplier payment, return and credit: AP, GRNI, cash and inventory reconcile independently without double counting. |
| AS20-12 | AP | Correct paid invoice both up/down; preserve original/payment, link inverse/replacement or credit, don't manufacture cash refunds or future dated capacity. |
| AS20-13 | AR | Draft reserves once; posting does not reserve again; partial return restores original lot quantity/cost and updates AR exactly once. |
| AS20-14 | AR | Correct price after partial return/payment and replay; net revenue and receivable follow quantities actually retained, old documents remain immutable. |
| AS20-15 | Stock | Independent mixed quantities: 137 input = 103 WIP + 27 FG + 7 BS; replay and two competing completions cannot exceed source. |
| AS20-16 | SKU | Change commercial membership before/after physical commitments and conversion/reversal; posted identity/cost history immutable, legal future membership change allowed. |
| AS20-17 | Stock/cost | Backdated correction before/after close and return; physical prefix and every cost destination reconcile, no new stock/work from a value-only correction. |
| AS20-18 | Payroll | Same-name/different-code workers remain distinct; attendance is not wage; BS repair compensation is payable once, negative net is explicit. |
| AS20-19 | Payroll | Carry accessory credit once to earliest eligible next payroll; cancel/recreate/competing claims cannot double-pay or lose the credit. |
| AS20-20 | Models | Independent SES 8,18,28 with alpha .5 yields 13 then20.5; compare model folds using only knowledge available at fold cutoff, no holdout tuning. |
| AS20-21 | Matching | Wrong color/model/size/physical source is rejected by integrated allocator even with a forged candidate label; shortage remains visible. |
| AS20-22 | Planning | Parent/child WIP and stages not double-counted; priority follows dated need/deadline with deterministic tie-breaks and integer PCS. |
| AS20-23 | Schedule | Capacity overflow carries forward, past-calendar remainder UNKNOWN; accessory/material shortage never converted into feasible supply. |
| AS20-24 | PL5 | Compute one-sided90% Wilson lower bound independently for own completed-group data; floor to0.1%; 180-day,5-group,200-PCS boundaries and same-model fallback. |
| AS20-25 | PL5/PL8 | Stale exhaust proof or changed group facts cannot hide available supply or use false yield; a valid exhausted group stays in history without entering available supply. |
| AS20-26 | Staged | Freshly seed 5,000 distinct targets, preserve all once, compare header/page identities using independent SHA256; every page <=8,000,000 UTF8bytes, every call uses8s limit. |
| AS20-27 | Staged | 5,001 targets refuses honestly without truncated result; empty and non-ASCII boundary cases retain exact identity/order/byte count. |
| AS20-28 | Staged | Pause/reload with same UUID, two step workers, read DONE repeatedly: one completed unit/effect and no completed-work recompute. |
| AS20-29 | Snapshot | Commit a source transaction in flight during capture; freshness detects it after commit while original pages/hash remain identical. |
| AS20-30 | Snapshot | Compare optimized source checks with full authoritative checks after changes in each monitored source category, including deletion. |
| AS20-31 | Plan v2 | After snapshot change stock, material, WIP, need, policy, access and product in turn; apply checks live data atomically and gives honest numeric refusal. |
| AS20-32 | Plan race | Two different targets share capacity: v2/v2 and v1/v2 competing applications cannot exceed capacity; two plans for one cut source cannot both consume it. |
| AS20-33 | BR v2 | Old snapshot analysis plus actual dated financial sources after later transactions; sections labelled distinctly and values independently reconciled. |
| AS20-34 | BR race | Two publishers or revision change during seal: exactly one coherent report or atomic refusal, never mixed snapshot/current sections. |
| AS20-35 | Reminder | Resolve/pay source between capture and claim, and again between claim and finish; no stale delivery and no reminder-induced business writes. Local sink only. |
| AS20-36 | AI | Prompt injection-like free text and foreign IDs cannot broaden brief/data/permissions; own authorized bound <=25 gap +20 chosen targets, no invented money or side effects. |
| AS20-37 | K2 | At just before/after 7-day completed/cancelled/failed expiry, every reader and consumer agrees; unfinished older run remains; historical documents/logs survive. |
| AS20-38 | K3 | Before/after DONE cleanup, compare every retained final/header/page/hash/time/index/document/log; only listed intermediates disappear. |
| AS20-39 | K3 | Corrupt each validation component in separate disposable fixtures; cleanup must refuse and delete nothing. Keep negative controls and rollback evidence. |
| AS20-40 | K3 race | Repeated cleaners, active progress, RUNNING/FAILED run and injected mid-delete failure: no premature cleanup or partial loss; restored transactions match before. |
| AS20-41 | K3 consumers | Reopen DONE and execute planv2/BRv2/reminderv2/AIv2 after cleanup with same immutable source; no missing result or recompute. |
| AS20-42 | K3 scale | Measure5k before/after with independent pg_column_size sums and relation sizes separately. State TOAST/allocated-storage distinction, exact targets/pages and hashes. |
| AS20-43 | Scheduler | No install without approval flag; execute real pg_cron tick in disposable runtime, verify job identity/schedule and uninstall removes only intended jobs. |
| AS20-44 | Backup | Back up used copy then restore into distinct DB; all user tables counts+independent digest and relevant catalog/roles/grants match. Restore is mandatory before verified flag. |
| AS20-45 | Backup | 15 successful simulated nights retain14 verified backups; failed dump/restore/receipt nights never prune last good backup; source==scratch rejected. |
| AS20-46 | Integrity | Compare976f→2e test changes and declared IDs/counts: no deleted invariant, narrowed coverage or ignored first failure. Job status alone is not evidence. |
| AS20-47 | UI | Recount routes/commands/rights; cover connected desktop/mobile, demo labelling, denial, stale loading, replay recovery and read-only financial redaction. |
| AS20-48 | P21 | Independent full composition install→pre-use rollback→reinstall→committed use→post-use refusal→backup restore, including ops and cleanup tables. |
| AS20-49 | Detector | Each relied-on detector has a controlled corruption that raises it and rollback that clears it; immutable facts separately resist tamper. Scope detector proof to controlled paths. |
| AS20-50 | Whole-flow | Trace independent purchase→cut→vendor→FG→sale→partialreturn→lateinvoice→reports, physical/value/dates/auth/rollback, including material/accessory obligations. |

Implementation-specific probes may be added after source review, without changing the above expected behavior.
PR44 timeline optimization remains explicitly subject to another auditor's acceptance.
