# C6 review amendment — exact candidate 9dd7bc2

This is an auditor proposal, not an owner ratification. D06 / GATE-16 remains HOLD. It extends the eleven-row review in `gpt_round8_c6_review.md` with all 75 original scenario IDs in `gpt_c6_75_case_crosswalk.{md,json}`. Do not erase the original IDs or call the crosswalk 75 PASS.

| C6 row | Contract reconciliation | Required amendment |
|---|---|---|
| ACC-01 | M1691, M1066–1071 and M5254–5261 already bind exact PCS/manual retail and existing financial invariants | Keep BASELINE; retain A01–A08 and applicable D01–D12. Seven PCS passing alone is not the full row. ACC-DEC02 was already superseded; no new owner price-choice request. |
| ACC-02 | Existing CP5 entitlement/BOM lineage; M1697 prohibits deferring old findings | Keep BASELINE; verify no duplicate reimbursement through normal FG, BS/rework, reversal and conversion paths. |
| ACC-03 | M1691, M3820 and M6632 bind current/as-of recost and conservation | Keep BASELINE; AZ family result alone does not accept every descendant path. CP6-03 residual remains separately HOLD. |
| ACC-04 | M1692 recommends the new accessory wave; M1697 explicitly permits owner deferral of NEW features but not old defects | Split ACC-04a BASELINE existing transfer/internal-use/return/settlement safety and ACC-04b NEW service-pos, inspection, recovered accessory and conversion workflow. Classify each extension CR-MASUK/CR-TUNDA by source inventory; owner approves only the actual extension scope. |
| LAU-01 | Existing authoritative delivery/receipt/QC/FG is baseline, M1691/M4479 | Keep BASELINE. T3's ten WIP-output browser cases are not proof of all laundry billing/custody cases. |
| LAU-02 | Existing claims and usable source selectors; M1697 and LAU-T29 require residual paths | Keep BASELINE. A5 selector repair and claim recovery/compensation interactions require separate case links. |
| LAU-03 | Existing new-stock identity checks, M3822 and M4479 | Keep BASELINE; exact family/case evidence, not an inherited CP5 badge. |
| LAU-04 | D04 date-local detectors, M3825/M4475; price unknown is not zero | Keep BASELINE. Owner estimate must not silently decide all sales/payment eligibility or future package pricing. |
| LAU-05 | M4479 already approves vendor masters, package/component concept, known process with unknown price, and invoice-pending distinction; M1697 still allows NEW implementation scope deferral | Split existing vendor/process/rate/immutable physical-accounting behavior from new component/package/invoice-allocation mechanics. Approved requirement is not the same as implemented/accepted feature. No blanket CR-TUNDA for existing behavior; no blanket BASELINE for every new extension without scope decision. |
| LAU-06 | Existing rewash is different from the proposed recoloring-to-new-SKU feature | Keep existing rewash safety BASELINE. Only the specifically deferred new destination/color workflow can be CR-TUNDA if source inventory confirms absence. “Free” must be explicit authorized zero, not inferred from missing price. |
| LAU-07 | M4448 and M4479 say vendor master and several concepts are settled; M4472–4477 leave six precise pricing/accounting choices | Replace generic “tarif/vendor/retur/servis belum diputus” with LAU-DEC01..06, their current authoritative decisions and only the affected scope. Do not reopen vendor-master approval or block unrelated physical work. |

## Source inventory actually reviewed

- `src/ConnectedAccessoryIssuePage.tsx:64–94`: native SAVE_DRAFT/POST/DELETE/REVERSE actions, with the single public action facade. This establishes an existing nota/reversal route. It does not prove a new accessory receipt/inspection/service workflow exists or is absent globally.
- `supabase/migrations/20260922135615_erp_v2_6_20ap_cp6_connected_import_materials.sql`: `erp.save_accessory_issue_action_v1` distinguishes view/create/post/reverse permission before required-payload validation; supplier/native helpers and cumulative sources remain material to baseline.
- `src/ConnectedLaundryPage.tsx:21,53–68,90–101`: existing POST_DELIVERY/POST_RECEIPT/POST_FAILED_WASH/REVERSE routes, vendor and wash-process selectors, snapshot rate resolution. This is positive evidence of existing scope, not a complete negative search for package/invoice functionality.
- `src/ConnectedBsResolutionPage.tsx:287–307`: existing rewash sends to a vendor, records physical time and explicitly separates work fee from accessory reimbursement; it does not expose a new target-SKU/color field in that form. Do not equate this existing route with every proposed recoloring CR.
- Candidate-wide absence of each proposed CR is still UNVERIFIED. A filename search or lack of a field in one form is insufficient. Writer must enumerate the actual public entrypoints and storage for each CR before the owner can approve a precise final C6 scope.

## Cross-review disagreement

Fable's proposed blanket promotion of ACC-04 and LAU-05 to BASELINE is too broad for M1697. Writer's blanket deferral is also too broad for the existing behaviors and M1757. Split both rows at the actual feature boundary, retain old findings, then classify implemented extensions. This follows the contract's express scope rule without inventing new acceptance or new product policy.

## Continuation

1. Attach actual implementation inventory and exact test/run links to the 75 original IDs; existing partial results may be reused with honest scope.
2. Writer emits a revised C6 with split rows and no unresolved “vendor master approval” question.
3. Owner ratifies only that concrete scope; then the auditor assesses GATE-16. Document approval alone is not runtime acceptance.
