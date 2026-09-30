# P09 — complete supplier return documents

F03/P09 OPEN; CP6 CLOSED_CONTRACT_SCOPE; independent_acceptance=false; production_go=false. This increment connects the existing native same-supplier, multiple-receipt return contract. It does not introduce paid-source credit carry or a new valuation policy.

## Candidate and actual results

UI/native qualifier source **`a28ad225eff755cd63a2eb1e1f06de6ae0c14150`**, tree `a0b9866cec57dec977082c344586025431693e1d`; [run36657403278](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36657403278) RUNNING. Expected12:6 native,3 committed races,1 real Auth/HTTP and2 desktop/mobile browser cases. Local42 DOM/recovery tests, TypeScript, source/access ownership, Python compilation and browser syntax checks PASS. Local tests do not prove native transactions.

First backend source `05c1e2551844c34a8906285eeb12c50c23c5b0a1`, [run36656767734](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36656767734): **9 PASS/1 INCOMPLETE**. [Original reports](evidence/p09-return-documents/FIRST.json.gz); [source/artifact receipt](evidence/p09-return-documents/FIRST_RECEIPT.json). The INCOMPLETE fixture expected source quantity11 against purchased10 to survive draft-save until POST. Native correctly refused during SAVE. The correction keeps this early refusal, then lawfully transfers8 of the second source away after a valid draft, requiring a POST of3 against remaining warehouse2 to roll back both legs. No business guard or money expectation was weakened.

## Contract and checks

- New paged source picker lists POSTED receipts from the anchor supplier, with complete counts and no financial fields. Each selected receipt loads its entire bounded source/roll workspace at the same outgoing warehouse; malformed, incomplete or mismatched source fails without discarding entered draft fields.
- Explicit SAVE_DOCUMENT/POST_DOCUMENT/REVERSE_DOCUMENT share the existing actor/request/version fence. Every source line is validated; reviewed_purchase_ids must equal the complete native document source set before and after the writer. Existing single-receipt actions keep their original bounded refusal.
- The accepted native writer owns stock, valuation, AP/GRNI, locks, cent allocation and inverse. Callers cannot supply credit prices. No additional ERP DML, new role, or broad execute grant is added. Current authorization is checked before cached replay and after waits. Full26-role stack and exact predecessor body/ACL checks remain required.
- UI creates, edits, reviews and inverses the full document. Exact bigint versions/decimal strings and original draft timestamps remain intact. Shared recovery retains the source warehouse and entire reviewed source set; mobile qualification deliberately loses committed POST_DOCUMENT and requires an identical replay after reload with no selected receipt.

Two FINAL receipts10×10 and10×20, consolidated by ordinary transfer, return2 and3. Expected stock8/7 and AP80/140. The first credit20 can move to the second receipt (AP100/120) then back, with no extra journal, stock or cost effect. Reversal while allocated away is refused; after restoring allocation, full inverse returns stock10/10 and AP100/200. The mixed fabric-estimated/accessory-final branch requires GRNI relief20 and AP relief60. Native tests also cover changed intent, stale revision, cached outcome after inverse, denied financial data, same-request race, competing capacity and permission revocation during an actual row-lock wait.

Browser proof is pending. Its source receipts/transfer are native setup; the actual picker, full draft/edit, review, post, replay and inverse are browser actions. Do not claim whole receipt-to-return UI coverage or visual review before results/screenshots are inspected.
