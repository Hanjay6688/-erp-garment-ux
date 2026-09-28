# BE revision after independent retest

Starting writer: `23e9c9830c32dce10604c43d17e4476d2707b55d`. Range audit remains pinned to product `616f4ec95b3f78d134647332885af6288d3a992a`.
Input: owner-delivered `BE_WRITER_HANDOFF_20260928.md`, version 2, retest of `e96db5a` on audit `88534ca`; five active findings. The old large-invoice finding is already CLOSED on that candidate.

## Contract and acceptance

- OWN-BE-01: permit a negative, document-sourced CONVERSION component, while retaining a nonnegative final garment HPP and checks against the actual allocation/cost events. Four PO/non-PO × zero/positive new-accessory-cost combinations; stock, FG/COGS, immutable sale snapshot, replay and inverse.
- OWN-BE-02: exclude PO conversion journals (and their reversals) from the non-PO book. Do not rewrite old journals. Keep PO/non-PO roots alive in one test across conversions, sale/return and recost.
- OWN-BE-04: searchable, paged pocket allocation history, including date within a period and ID; desktop/mobile cancellation of the oldest active period after 51 newer cycles. Cancellation must reverse value once without another cloth movement.
- OWN-BE-05: generic rework supports native PO/product lineage; reject a new unsupported non-PO order before any dispatch. Keep AX repair and the cancellation of already-created unsupported orders available. Do not invent a valuation contract for generic non-PO GOOD completion.
- RELATED-01: expose the native four-argument sewing reversal contract, including expected version; calls without a version fail explicitly. Preserve role, idempotency and active-allocation guards.

Keep BD invoice/discount/FREE/WAIVED/recipient/revoked-replay and BF regression. Qualify development SQL and aligned package/rollback separately. Writer evidence is not independent closure. CP6 HOLD; `production_go=false`, `audit_complete=false`.
