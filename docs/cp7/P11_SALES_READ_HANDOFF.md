# P11 — invoice source reader

## Draft source candidate — CREATE/EDIT through connected UI

The next candidate extends the same reviewed boundary with public CREATE and full EDIT of1–100 invoice lines. Complete customer and stock selectors use real sources; stock availability is explicitly current, and commercial SKU labels use the chosen invoice time. Direct/malformed client IDs do not bypass native availability or the active-product/customer/warehouse checks. Header expected revision and full review token bind EDIT. Exact string PCS/price/discount reject lossy fractions, missing prices and injected HPP. Optional lusin+PCS assistance only replaces the exact quantity after an explicit click. The form retains all other line values, notes, terms, due date and the original full timestamp when its displayed minute is unchanged. Pending replies use the same persistent SALES recovery domain with CREATE/EDIT admitted; no separate second writer is introduced.

**33 cases declared, native execution pending:** previous22 +7 native draft cases,1 stock race (7+7 against10),1 realAuth source/create/replay and2 browser source-to-create/edit/post cycles. Native two-product oracle110.01→109.99 leaves stock5/9 and AR109.99/COGS60 at POST; native inverse restores10/10 and every GL account. Browser oracle13×20 +2×10.01−0.02=280, edit first quantity to5→120, availability17/28→25/28 with no GL during CREATE/EDIT, unchanged availability on POST. Mobile loses committed CREATE response and must replay exactly after reload. Complete remaining line/notes/payment terms/due date/timestamp must survive EDIT. Fifteen targeted DOM/contract and30 common recovery tests pass locally, as do TypeScript/source/access checks. These do not replace PostgreSQL execution. The22-case qualification below remains bound to its earlier source; R10 return/payment/refund and full P11/F03 remain OPEN.

**Qualified22/22 PASS** on `6d3b019df6054b2cc77c6ab5bd44f7164494cee9`, tree `b8f0a1cf025b79a1bb3a2e91357cbbd783ce0ec2`; [run36623475713](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36623475713), [full receipt/hashes](evidence/p11-sales/TRANSITIONS_VERIFICATION.json). All14 native,2 races,2 realAuth and4 browser cases pass. POST keeps available6 and books AR80/COGS40 once; CANCEL restores10 without GL change. Actual lock-wait revocation, child-price review and actor-bound replay pass. Mobile loses committed POST response, reloads, replays the exact request and shows the committed invoice. CP6 restore/advisor/Auth/database cleanup and both app workflows pass. All4 final screenshots were inspected. Earlier pending statements below are historical. Browser source creation/edit, return/payment/refund, full R10/P11/P13 and F03 remain OPEN; this is writer evidence only.

## Current continuation — draft transitions candidate

The first reader run on `a130b329c1b2c73ec4bc1a4a590c23907a97d5dd` (tree `060f6caf3a844adb1ba95df8709393c480970196`), [36622292726](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36622292726), recorded **10 PASS /0 FAIL /1 INCOMPLETE /0 NOT_RUN**. All8 native, realAuth and desktop reader passed. The mobile fixture stayed authenticated after creating its native draft and its administrative role-setup query correctly failed on `app_roles`. The fixture now explicitly resets to its existing test administrator; no client/business grants were added. CP6 restore/advisor/Auth/database cleanup passed. Only desktop was visually inspected. The full failed result, hashes and screenshot are preserved in [READ_RUN1_RECEIPT.json](evidence/p11-sales/READ_RUN1_RECEIPT.json).

The two app runs also stopped at the access catalogue gate: expected86 RPC boundaries, actual87. The next candidate explicitly registers the two P11 read/write boundaries in that gate and includes them in the total without modifying frozen CP5 evidence.

The next candidate adds reviewed POST and CANCEL for existing native drafts through `public.erp_cp7_save_sale_v1`. Review binds exact string header revision and complete header/items/allocation/movement token. Source locks use the accepted FG native order; live authority is rechecked after waits and before/after effects. The command principal owns only actor/request/context metadata; it has no ERP table or native writer execution grant. A private postgres-owned adapter verifies context then invokes unchanged native post/cancel. Recovery is exact actor-bound UUID/action/payload/version, remains replayable after later inverse, and requires current permission before cached results. POST requires invoice.post and AR authority; CANCEL requires invoice.edit_draft and AR authority, plus invoice.view for both. The UI retires review on reload, locks on pending recovery, and checks outcome identity before clearing its envelope.

**22 cases declared, PostgreSQL/browser pending for this candidate:** prior11 +6 native command cases (post/GL, cancellation, child-price review, header/status, actor/replay/access, private/closed fields),2 committed races (POST vs CANCEL and live revocation during actual FG lock wait),1 realAuth command case,2 browser transitions. Fixed post oracle: draft4 from10 leaves6 available; POST retains6, AR+80/revenue−80/FG−40/COGS+40; native inverse control restores10 and GL. CANCEL releases4 with unchanged GL. Both browsers cancel one source draft then post another; mobile loses committed POST reply and reconciles identical request after reload. Draft creation remains a native fixture. Browser creation/edit/return/payment, GradeB and full R10 remain OPEN. Nine local DOM/contract tests plus30 common recovery tests pass; TypeScript/source ownership pass.

Earlier sections below preserve the reader-only increment and its original predeclared scope; this continuation does not convert fixture writes into browser proof.

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
