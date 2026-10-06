# CAT-01: distinguish catalog ordering from function replacement

E05 and E06 share the complete canonical public-catalog comparator, rather than separate business fixes. It preserves every field, signature/hash pair, relation, row and multiplicity. Its controls refuse changed definitions, signatures, missing or duplicate functions, changed relations and changed public rows. Pair ordering alone is not an equality failure.

An unordered aggregate does not prove function OIDs changed. Where the first failure retained only signature/hash pairs, the first cause remains unproven: a later successful run cannot retrospectively identify who changed an earlier function. Those first failures remain immutable. Do not assert that an unchanged definition proves an unchanged OID, or that changed pair order necessarily proves DROP/CREATE.

At `4b264493`, E03 qualifies10/10 with complete raw signature/hash, OID, owner and tuple-location witnesses. All three main and five refund before/after transitions preserve the exact function signature/OID/owner set, with no changed tuple locations. Originals are retained at `evidence/integration-4b26/e03-10-catalog-identity`.

The successor enables the **same existing** read-only location witness in E05, E06 and all retained F03 Native groups. No comparator field/member is dropped and no database trigger, grant, Native body, business assertion, case budget or timeout changes. The witness rejects a replaced function identity or changed owner even when the definition hash happens to match. Tuple-only relocation is retained explicitly for diagnosis, not interpreted as replacement. Fresh E05(26), E06(5) and full-F03 qualification is required on this tool successor. These observations add zero product case credit.

Writer CAT-01 repair and qualification remain distinct from independent auditor closure. A fresh stable identity set establishes the fresh run's schema invariance; it does not resolve an unobserved historical OID cause. PRE-07 can point to its scoped E06 evidence and this shared finding without inventing a second root cause.
