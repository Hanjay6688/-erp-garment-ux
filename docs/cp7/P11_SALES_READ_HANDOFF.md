# P11 — invoice source reader

30 September 2026 WIB. **Implemented candidate; native/HTTP/browser qualification pending. R10 stays OPEN.** CP6 remains CLOSED_CONTRACT_SCOPE. `independent_acceptance=false`; `production_go=false`.

This increment replaces the invoice/list simulation in the disposable connected runtime with one public, read-only source facade and a paged invoice/detail workspace. The accepted sales/reservation/payment/return writers are unchanged. It does not provide connected sales commands, refund controls or historical AS_KNOWN reporting.

## Source and access contract

`public.erp_cp7_get_sales_v1(jsonb)` resolves `sales_headers`, complete `sales_items`, current native posted returns/payments and active reservation movements. `sales.invoice.view` is required on every call. Monetary fields additionally require `finance.ar.view`; operational payloads contain neither invoice money nor item prices. The private reader has SELECT and the five declared identity/access function grants, with no ERP DML or native writer EXECUTE. The frontend clears the previous document and money on refresh, failure, selection mismatch or access remount.

Draft quantity is reserved once but the draft amount is explicitly a preview, with no receivable balance. Posted net equals gross less posted return value, using the accepted native zero floor; posted payment is separate. Cancelled/reversed documents have no active receivable display. This is a current native document projection, not a new GL/report oracle. Historical commercial SKU is resolved at the invoice time, separately from physical product SKU. The bounded detail refuses above100 source lines instead of silently truncating; list pages are complete with native total and next offset.

## Predeclared proof:11 cases

| Cases | Count | Fixed oracle |
|---|---:|---|
| P11_READ_DRAFT_CANCEL | 1 | Draft4 PCS reserves4; cancellation releases4; reader writes nothing |
| P11_READ_NATIVE_LIFECYCLE | 1 | Invoice80, payment30, return1 PCS/value20 → net60 and receivable30; native inverses restore GL |
| P11_READ_EXACT_CENTS | 1 | 3×10.01−0.02=30.01; exact full payment leaves0 |
| P11_READ_FINANCIAL_REDACTION | 1 | Operational invoice permission cannot retrieve money; current revocation refuses |
| P11_READ_PRIVATE_READ_ONLY | 1 | No business DML/writer EXECUTE; private helpers inaccessible |
| P11_READ_COMPLETE_PAGES | 1 | Three documents across three pages, complete unique IDs and global total |
| P11_READ_QUERY_REFUSAL | 1 | Invalid limits/status/types and unsupported historical query refused |
| P11_READ_EMPTY_MISSING | 1 | Explicit empty result; selected missing document fails |
| P11_READ_HTTP_CURRENT_AUTH | 1 | Real Auth/PostgREST, deactivation and anonymous refusal |
| P11_READ_BROWSER_DESKTOP / MOBILE_OPERATIONS | 2 | Connected read/reload, financial redaction, source and money retired on failed refresh |

Browser source writes are **native fixture controls**. The browser itself only reads. This cannot close R10's browser sale/cancellation/return/payment obligation. The desktop shows native invoice80/payment30/return20/balance30; mobile has operational permissions and no monetary response/render. All reads must leave stock and GL unchanged. Qualification includes exact source hash,11-case count, accepted-package restore, advisor delta and real Auth/database cleanup. Screenshots need actual inspection after execution.

Six local DOM/contract cases cover exact quantities/versions/money, malformed payload rejection, draft-vs-AR distinction, refresh clearing, operational access and late responses across authority changes. The initial DOM harness declaration was corrected before these tests were executed; no runtime rule changed.

## Next dependent work

Connect controlled draft creation/edit/reservation, post/cancel, selected-allocation physical return, payment/inverse and their lost-response recovery to the accepted native functions. Extend the facade with source-bound review and existing permission contexts; do not allow direct browser table access or recompute stock in React. Prove ordinary browser source-to-return/cash journeys, including Grade B/return eligibility where the accepted contract applies, before closing R10. P13 finance/report/close, E05's precise partial-settlement mechanism, remaining P09 scope and full F03 acceptance/release remain open. F04 takeover waits for F03 completion and a fresh branch/handoff check.
