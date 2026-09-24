# Payroll source follow-up

Candidate: `9add57ea8c2b6b2dc37c0134717d4d39ba30b5dc`.

This review occurred after the original phase-1 lock. It adds bounded source coverage, not native acceptance. The reviewing agent modified no product, database, external system, existing report, scenario or probe. No local follow-up file was created because workspace execution remained unavailable. The lead persisted this supplied Markdown to the isolated audit branch through GitHub.

## Outcome

Two payroll hypotheses were eliminated in the inspected source:

- Production wages are not multiplied by GOOD output or withheld until laundry return.
- Duplicate component rows cannot bypass the inspected work-completion capacity check through different snapshot identities.

A separate **UNVERIFIED source risk** remains: automatic BS component baselines can attribute aggregate completed work to the BS pieces without evidence identifying those pieces. That baseline can suppress later rework entitlement. Manual classification provides a correction path before rework, so this is not an established unavoidable underpayment.

Special-policy compliance remains **UNVERIFIED** because its precise normative passage could not be reread. No native case was executed.

## Oracle and retrieval

The retained Master rule, M3824. Provenance: root-supplied excerpt; independently read in Master3810–3829 before the outage, but not reread for this follow-up:

> Upah berbeda dari reimbursement: upah reguler mengikuti selesai dijahit dikurangi komponen BS/Stuck yang belum dikerjakan; GOOD bukan pengali upah. Reimburse aksesori tetap pada entitlement/BOM yang sah. Approval mengakui kewajiban; pembayaran menyelesaikan, tidak mengakui biaya kedua.

M3816,3818,3820 additionally require immutable posted facts, atomic commands and valid separated dates.

Source was retrieved through read-only GitHub calls pinned to the candidate. All 67 migration files and four AW–AZ development files were fetched to search definitions and dynamic successors; **fetching/searching those files is not whole-file review**.

The compressed baseline was retrieved as base64 and decompressed within the tool runtime without filesystem access:

- Blob: `f7e970d72e0bcd44015c8f7d092fcc725baeb158`
- Compressed/uncompressed: 308,353 / 2,126,909 bytes
- GZIP length and CRC32 verified: `1271493035`
- Decompressed SQL: 37,044 lines

Only the targeted bodies and schema below were reviewed. Writer comments and tests were not used as business policy.

## Source ledger

Paths are relative to the candidate repository.

| Alias | File |
|---|---|
| B | `supabase/tests/fixtures/erp_enteng_cp45a_catalog_bootstrap.sql.gz` |
| CP14c | `supabase/migrations/20260901023200_erp_v2_6_14c_attendance_hpp_uat_alignment.sql` |
| CP14d | `supabase/migrations/20260901023400_erp_v2_6_14d_cp3_r4_race_and_reversal_hardening.sql` |
| CP15 | `supabase/migrations/20260901161322_erp_v2_6_15_payroll_component_entitlement.sql` |
| AC | `supabase/migrations/20260915031500_erp_v2_6_20ac_cp6_temporal_surface_closure.sql` |
| AI | `supabase/migrations/20260916090022_erp_v2_6_20ai_cp6_work_source_lineage.sql` |
| AX | `supabase/dev/cp6_ax_t1_family.sql` |

| Reviewed body/schema | Source range | Bounded conclusion |
|---|---|---|
| `v_payroll_production_work_eligibility` | CP15:36–122 | POSTED component qty_payable supplies entitlement. Subtracts allocations in every non-REVERSED payroll. Laundry sent/returned quantities are metadata; they do not cap wages. No later replacement was found. |
| Work-line schema and uniqueness | B:2457–2465,2973,3023,3771–3777 | Integer completed/payable quantities; payable≤completed; generated amount equals payable×rate. One snapshot per PO/component and one line per completion/snapshot. |
| `ensure_po_work_component_snapshots` | AC:2561–2612 | Locks PO and BOM/rate keys. Selects effective model BOM and contractor/model/component rate at supplied basis time, falling back to BOM default. Existing snapshots are returned unchanged. |
| Contractor rate guards | B:9120–9134,11177–11194 | Same contractor/model/component effective ranges cannot overlap. Used rate economics cannot be changed/deleted; end-date change cannot invalidate committed snapshot time. |
| `validate_work_completion` | AI:118–153 | Checks event PO/contractor and exact PO/component snapshot; source rate overwrites the submitted line rate. |
| `guard_work_completion_posting_consistency` | AI:154–243 | Rechecks current source at posting; locks cutting group; requires pickup and valid chronology; caps aggregate prior completed/payable quantity per component against cutting quantity. |
| `post_work_completion` | AC:5790–5805 | Requires DRAFT, matching PO/contractor/group, snapshots and nonempty lines; status transition invokes guards, then accrues generated component amounts to WIP/CONTRACTOR_PAYABLE at WIB source date. |
| `record_sewing_terminal_v1` | CP14c:613–756 | Final body supersedes CP14. References already-POSTED work, preserves its date/lineage, checks business-period/pool restrictions and cumulative physical capacity. It does not create wage component quantities. |
| `validate_payroll_work_item_source` | AX:520–587 | Source/component advisory lock; current source eligibility, PO/component/contractor identity and aggregate non-reversed allocation cap. |
| `merge_eligible_work_into_payroll_v2` | AX:588–681 | Locks payroll and source rows, checks version/contractor/period end/current remaining quantity, and copies the source rate rather than accepting a caller rate. |
| `reverse_work_completion` | AC:7717–7779 | Requires linked sewing-terminal reversal and cancellation/reversal of active payroll allocations before retracting work; requires original wage journal where value exists. |
| BS automatic baseline | B:23607–23640; trigger30291 | Seeds each BS component from aggregate posted component completion up to detection time. This is the unresolved attribution risk below. |
| BS validation/classification | B:8940–8978,25227–25231; AC:2320–2396 | Numerical lifetime limits exist. Connected classification can replace component baseline before rework lines exist; component classification becomes frozen after rework begins. |
| `prepare_rework_component_line` | B:15470–15555 | Locks order/component; newly payable=min(performed, BS quantity−completed-before-BS−prior newly completed). Resolves effective recipient rate, or same-contractor PO snapshot fallback; different contractor requires explicit rate. No successor replacement was found. |

The automatic baseline and rate/BS guard bodies above had no later named replacement located in the migration/development source scan. Installed-catalog equivalence remains a separate native requirement.

## Independent small examples

**Regular wages versus GOOD.** Ten garments have component A completed/payable on all ten at100; component B completed/payable on eight at25, with B unfinished on two BS/Stuck pieces.

Expected regular wage: `10×100 + 8×25 = 1,200`.

Using GOOD8×full rate125 would incorrectly produce1,000. The reviewed eligibility view takes the component quantities and therefore supports1,200, provided the upstream facts are valid. Laundry return or later GOOD count does not change that component entitlement.

**Allocation conservation.** A source component has quantity10. Payrolls reserve4 and3: remaining3. Reversing the first payroll releases4, leaving remaining7. CP15 subtracts all non-reversed allocations; AX enforces the aggregate cap under a source/component lock. This is positive source evidence, not an executed concurrency proof.

**Snapshot preservation.** If a valid committed source rate is100, changing a later master rate must not rewrite that source's payable amount. The inspected first-use snapshot and used-rate guards support preservation. Whether a caller selected the contractually correct first-use date is still unproved.

## UNVERIFIED risk: BS default baseline can suppress genuine new work

B:23621–23632 computes:

`completed_before_bs_qty = min(BS quantity, sum(posted component qty_completed in the PO/cutting group up to BS detection))`

The sum does not identify which physical pieces received that component.

Consider the regular-wage example above:

1. Group10; component A completed10; component B completed8.
2. The eight completed B pieces are the GOOD pieces.
3. The two BS pieces specifically lack B.
4. A BS case for those two pieces is created after the work event.

The automatic baseline predicts B completed-before-BS=`min(2,8)=2`, although the case-specific factual value is0. `prepare_rework_component_line` then computes remaining new B entitlement=`2−2−0=0`. Performing B on both BS pieces can consequently produce zero newly payable B quantity, whereas the independent actual-work oracle expects `2×25=50`.

The connected reader exposes that baseline; `ConnectedBsResolutionPage.tsx:250,283–293` initially selects components according to server remaining entitlement and submits performed quantities through SAVE_REWORK. Thus this is more than an isolated unused arithmetic expression.

**Material counterargument:** classification is editable. AC:2365–2383 can replace the baseline before any rework lines exist. `ConnectedBsResolutionPage.tsx:159–195` exposes completed-before-BS quantities for correction. If the operator explicitly sets B's baseline to0 first, the inspected rework formula supports the expected50.

Therefore the current disposition is **source-supported attribution risk; native NOT_RUN/UNVERIFIED**, with no assigned confirmed finding or claim that underpayment is inevitable. Native investigation must establish whether the supported automatic path requires case-specific verification before the inferred baseline is consumed.

## Reproduction specification — NOT_RUN

Use a disposable exact-candidate installation with legitimate ordinary actors and recorded committed grants. Do not add schema USAGE to claim ordinary reachability.

1. Establish a lawful PO/cutting/pickup source of10 pieces, snapshots A100/B25, and actual work A10/B8. Record which two pieces lack B.
2. Post work through its supported route; verify generated wage liability1,200 and eligibility from component quantities.
3. Create a lawful BS2 source through the connected production/BS path. Observe the automatic B baseline and its provenance.
4. Without classifying the case again, use the connected rework flow to perform B on those two pieces; complete required downstream resolution.
5. Observe qty_newly_payable, rework wage journal and payroll eligibility. A confirmed counterexample requires lawful source facts, a supported route and actual lost50 entitlement.
6. Control: in an isolated equivalent fixture, classify B completed-before-BS=0 before rework. Expected new entitlement2/value50.
7. Control: if B was already completed on both BS pieces, repeated B must not create a second entitlement.
8. Verify source immutability, exact replay, reversal and cleanup independently.

No executable case was added: initial work creation/public-route reachability and the complete lawful BS fixture need qualification first. B grants ordinary DML on work event/line tables, but table grants alone do not prove schema/RLS/HTTP reachability. No current connected work-entry caller was established by this follow-up.

## Special-policy boundary

Source mechanics were inspected, but **normative compliance remains UNVERIFIED**:

- CP14c:167–306 stores explicit effective-dated Special and attendance flags with expected-policy identity.
- CP14d:273–319 dynamically moves the contractor advisory lock before the row lock and blocks policy changes affecting active attendance-HPP pools. Ignoring this patch would give the wrong effective setter.
- CP14c:852–981 filters Special out of the inspected attendance-HPP pool numerator and denominator.
- The production-work eligibility view contains no Special-name/flag filter.

These facts do not authorize a wage exemption, validate the attendance allocation policy, or establish the intended treatment of named contractors. Writer comments are not policy evidence.

## Remaining scope

- Native work producer and legitimate ordinary entry route, including raw integer/rate validation and source-time selection.
- BS/Stuck component attribution and whether automatic defaults require confirmation before rework.
- Precise Master clauses for Special, attendance and effective-rate policy.
- Complete rework counter reconstruction, cross-contractor rate lifecycle and source reversal races.
- Installed triggers/ACL equivalence and native payroll/source concurrency.

This follow-up narrows the earlier payroll coverage gap and supplies one reproducible source-risk specification. It does not complete payroll or CP6 acceptance.

## Lead counter-review after persistence

The lead separately read the candidate's connected classification editor and rework action. ConnectedBsResolutionPage.tsx:250 initializes selection from server defaults; :256 defines canStart using OPEN/PARTIAL status, positive available quantity and no active orders. The inspected UI condition has no case-specific component confirmation. Lines285–293 allow manual component selection and submit performed quantities. This narrows the frontend counterargument. The subsequent bounded backend check below closes the mandatory-confirmation counterargument at source level; the lawful native fixture remains to be qualified. No native finding is promoted.

## Final bounded backend countercheck

Exact candidate remains9add57e. Searching the retained67 migrations and four AW–AZ bodies found this effective source path:

| Path | Function/lines | Result |
|---|---|---|
| CP19 `20260903070932_erp_v2_6_19_cp5_bs_resolution_recovery.sql` | public.erp_save_bs_resolution_action_v1:1127–1138; grants1140–1147 | Public wrapper forwards; authenticated execute is present. This alone does not prove the complete ordinary native actor/ACL context. |
| CP19 | erp.save_bs_resolution_action_v1:858–1105; SAVE_REWORK928–937 | New order requires an existing OPEN/PARTIAL case, then directly calls save_rework_order_v2. |
| CP19a `20260903151034_erp_v2_6_19a_cp5_rework_accessory_lineage.sql` | erp.save_rework_order_v2:300–586; inserts477–492 | Validates request/accessory/order facts; inserts supplied component IDs and quantities. No mandatory case-specific classification, confirmation or correction of completed_before_bs_qty on this path. |
| Baseline B | prepare_rework_component_line:15470–15555; BEFORE INSERT trigger30839 | Payable=min(performed,max(BS qty−existing baseline−prior newly completed,0)). |
| Baseline B | rebuild_bs_component_counters:15817–15866 | Updates lifetime newly-completed/paid counters, leaving the initial completed-before baseline unchanged. |

Relevant guards were checked: B validate_rework_quantity_state25886–25920, validate_bs_component_qty25227–25231, guard_bs_case_component_state8940–8978, protect_rework_component_line15795–15813; final AG guard_child_by_parent_status150–208 and CP19 refresh_bs_case_status290–327. They provide lifecycle, capacity, locking and immutability checks, without establishing the affected BS pieces' component history.

The lead separately fetched the exact SAVE_REWORK dispatcher928–937 and the CP19a300–586 body; reviewed the relevant creation guards and component inserts477–492. CLASSIFY_BS remains an optional correction path before rework. It is not a mandatory prerequisite on the inspected source path, and the baseline is frozen once rework lines exist.

**Disposition unchanged:** source-supported attribution risk, native NOT_RUN/UNVERIFIED. Source inspection narrows the guard counterargument; it does not prove lawful initial fixture creation, installed trigger/ACL equivalence, actual lost wage50, or the complete downstream payroll lifecycle. No confirmed finding/priority is assigned and no native run ID exists for this example.
