# F03 independent audit: predeclared oracle

Candidate: `eb6b8682e97e94c95f89d431ab81974c54ddcbaf` on `cp7/integration`.
Audit branch: `audit/f03-independent-20261001`. Product files remain unchanged.

This is independently designed and executed verification, not a blind audit: the auditor previously read writer progress and has read the writer handoff. Writer assertions and retained suites are cross-check evidence, never counted as newly designed independent oracles. No peer audit supplies expected outcomes.

## Business oracle and scope

F03 covers P09 procurement, P10 FG, P11 sales/return/payment, P12 attendance/payroll/Nota, and P13 finance/HPP/period. Framework registries and owner decisions govern expected behavior. Final CP7 integration/release and owner production approval remain separate gates.

1. Procurement: receipts, transfers, adjustments and supplier returns conserve exact source quantity/value. Final invoices update certainty; later payment does not repeat stock. Changed request payload and stale review must not silently reuse an old result.
2. FG/sales: draft reserves once, POST preserves that availability, CANCEL releases once. Sizes, ownership, lots and grades cannot silently substitute. Unknown cost must remain unknown. Concurrent intents cannot consume capacity twice.
3. A separate non-round sales worksheet: 10 PCS at cost 10 each, sell 3 PCS at 10.01 with line discount 0.02. Net revenue/AR is 30.01 and COGS is 30.00; available stock is 7 before and after POST. Payments of 10.00 and 20.01 settle exactly, with no extra revenue/stock effect. Payment reversal restores the exact AR and cash delta. A same-key changed intent is refused. A separate unpaid sale permits physical partial return and exact inverse; paid-return policy is not invented.
4. Payroll: approval establishes the lawful entitlement/expense once; partial payment only settles it. Paying/reversing cannot change the production denominator or allocate a new cost. Overpayment and competing settlement must preserve capacity.
5. Finance: cash, sales, AR/AP, inventory, COGS and payroll are checked against independent arithmetic and raw balanced journal facts, not against another product helper. Internal cash transfer nets to zero. Corrections and business-date reports must not rewrite frozen source history.
6. Authority: positive OWNER controls first, then null/inactive/permission-revoked actors, including same UUID and revocation during an observed lock wait. Private helpers must be unreachable by raw REST. Ordinary operational access must not expose money through alternate readers.
7. Connected browser: actual Auth/HTTP and committed DB assertions; reload, stale review, failure/recovery, desktop/mobile. Mocked responses are not business proof. Reused browser suites remain labeled cross-checks.
8. Installation/restoration: full F03 stack on disposable CP6 clone only; unchanged product hash, exact cleanup of data/functions/owners/ACL/platform/Auth. Any setup error is INCOMPLETE, never a product bug or PASS.

## Execution and findings policy

Independently authored native/race/HTTP/browser probes are recorded separately from reruns of retained writer suites. Every case records fixture, expected/actual, source/runtime and cleanup. Test counts are executions, not unique business requirements. A failed assertion is triaged and reproduced before a writer defect is raised. Existing cured findings stay closed unless the frozen candidate actually reproduces them.

Acceptance requires no confirmed material F03 defect and transparent disposition of mandatory coverage. `production_go` remains false. This document is committed before independent probe execution; later additions preserve the original worksheet and explain corrections to the audit fixture.
