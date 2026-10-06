# CAT-01: distinguish catalog ordering from function replacement

E05 and E06 share the complete canonical public-catalog comparator, rather than separate business fixes. It preserves every field, signature/hash pair, relation, row and multiplicity. Its controls refuse changed definitions, signatures, missing or duplicate functions, changed relations and changed public rows. Pair ordering alone is not an equality failure.

An unordered aggregate does not prove function OIDs changed. Where the first failure retained only signature/hash pairs, the first cause remains unproven: a later successful run cannot retrospectively identify who changed an earlier function. Those first failures remain immutable. Do not assert that an unchanged definition proves an unchanged OID, or that changed pair order necessarily proves DROP/CREATE.

At `4b264493`, E03 qualifies10/10 with complete raw signature/hash, OID, owner and tuple-location witnesses. All three main and five refund before/after transitions preserve the exact function signature/OID/owner set, with no changed tuple locations. Originals are retained at `evidence/integration-4b26/e03-10-catalog-identity`.

The successor enables the **same existing** read-only location witness in E05, E06 and all retained F03 Native groups. No comparator field/member is dropped and no database trigger, grant, Native body, business assertion, case budget or timeout changes. The witness rejects a replaced function identity or changed owner even when the definition hash happens to match. Tuple-only relocation is retained explicitly for diagnosis, not interpreted as replacement. These observations add zero product case credit.

Actual source `56c48b6e2e8e2dabdc10311aa55b113826d25622` qualifies E05 **26/26** (run37468011631), E06 **5/5** (run37468011561) and all eight complete F03 components (run37468011716). Every planned case, complete catalog field/member/multiplicity, exact identity transition and restoration gate has been read from the complete Originals. E05 retains42 snapshots/41 stable transitions; E06 retains10/9. Their fresh runs have zero changed OIDs, owners, tuple locations or pair orders.

| Complete F03 component | Native groups with identity witnesses | Complete snapshots | Exact signature/OID/owner transitions | Changed tuple locations |
| --- | ---: | ---: | ---: | ---: |
|P09 |12 |188 |176 |0 |
|P10 |3 |48 |45 |0 |
|P11 |5 |92 |87 |0 |
|P12 |8 |116 |108 |0 |
|P13 |4 |72 |68 |0 |
|Supplier credit |1 |4 |3 |0 |
|Cash/installments |4 |84 |80 |0 |
|Customer refund |2 |10 |8 |0 |

These39 Native groups retain614 complete snapshots and575 adjacent identity transitions. P11 commands include two additional public-catalog reads inside the dispatch-equivalence fixture (`cp7_p19_sales_dispatch_equivalence.py`); therefore its16 snapshots are all checked, without inventing case-to-snapshot indices from a14-snapshot formula. Every case's own boundary/schema/session assertions still pass. Complete Originals and the additional read-only case/catalog review are at `evidence/integration-56c4/full-f03/CASE_AND_CATALOG_REVIEW.json`; E05/E06 Originals are in the adjacent directories. Counts describe witness observations, not additional or unique business cases.

Writer CAT-01 repair and qualification remain distinct from independent auditor closure. A fresh stable identity set establishes the fresh run's schema invariance; it does not resolve an unobserved historical OID cause. PRE-07 can point to its scoped E06 evidence and this shared finding without inventing a second root cause.

## Additional observed order difference at source0bd

At product source `0bd60f2c073d490e34060305b37709c9b479eeae`, the fresh complete F03 run37474166739 qualifies all eight components. Its39 Native groups again retain614 complete catalog snapshots and575 unchanged adjacent identity transitions. E05 run37474166664 and E06 run37474166707 separately qualify26/26 and5/5, with42/10 raw snapshots and no identity, tuple-location or order changes in those two runs.

The complete F03 customer-refund artifact11418923303 provides a useful counterexample to inferring replacement from unordered output. In `F03_E03_NATIVE_CUSTODY_SERVICE_INVERSE`, snapshots2→3 contain all156 functions. Forty-two signature/hash pairs change their output positions, while the complete signature→OID/owner/tuple-slot/definition maps are equal and every canonical public-catalog field/member/multiplicity is preserved. For example, `erp_cp7_get_production_policy_v1(uuid[])` moves5→6 and `erp_cp7_get_source_identity_v1(uuid)` moves6→5. The complete42-member positional diff is retained in [OBSERVED_ORDER_WITHOUT_IDENTITY_CHANGE](evidence/p19/utf8-receiver-native-0bd/OBSERVED_ORDER_WITHOUT_IDENTITY_CHANGE.json), alongside the unmodified raw snapshots.

This proves that this fresh output-order difference has no observed function identity or tuple-location change at those boundaries. It does not identify the cause of the older E05/E06 failures. The P18 bridge still emits only its legacy catalog summary, including one order-only transition and no full location/raw-snapshot witness; that summary is retained explicitly with its narrower scope, not promoted to an identity proof. These reviews execute zero ERP cases and confer no independent P20 or production acceptance.
