# P12 opening sources → payroll — writer checkpoint

30 September 2026 WIB. **Candidate, NOT_RUN in PostgreSQL/browser yet.** The previously qualified 80-case source remains `5082fbec159095c3452c14c6ad500839f28a166b`. This increment adds 10 cases, making an explicitly gated 90-case run. No product SQL, product UI or accepted CP6 function changes are proposed: the connected initial import already supplies the opening allocations; this checkpoint proves their connection to CP7 payroll.

## Fixed financial oracle

The browser imports three old documents through CSV → save → validate → finalize. Recognized wages 90 less 25 paid before cutover leaves 65 payable; old reimbursement adds 20; old cash advance leaves 30 receivable. A sewing entitlement has 40 earned, 10 previously paid and 4 carry at 2.50. Its recognized amount is 65; only 2 carry units are allocated to this payroll, adding 5 when approved. Two ordinary current FG work cards contribute 6000.

PREPARE must preserve the selected work and all reviewed opening allocations: `6000 + 65 + 20 + 5 - 30 = 6060`. Repeated PREPARE creates no GL or stock/HPP effect. APPROVE adds only `Dr LABOR_COST 5 / Cr CONTRACTOR_PAYABLE 5`; the old 85 is not accrued again. PAY settles all three opening documents, disburses 6060 and leaves two carry units. Exact replay creates no second payment. REVERSE restores payable 65 + 20, advance 30 and carry 4, with GL neutral against the post-import baseline. Original opening journals and physical/HPP facts remain intact. Unpaid cancellation also reverses the carry expense and releases reservations.

## Predeclared additions

| Cases | Scope |
| --- | --- |
| P12_OPENING_LIFECYCLE | Import, allocations, repeat prepare, approval, exact payment replay and inverse |
| P12_OPENING_EDIT_RELEASE | Change allocations, exact decimal carry and zero release |
| P12_OPENING_STALE_REVIEW | Old CP7 review and stale payroll version denied after opening edit |
| P12_OPENING_GUARDS | Carry limit, wrong mandor and approved payroll refusal |
| P12_OPENING_CANCEL | Approved unpaid cancellation restores opening sources and GL |
| P12_OPENING_RACE_REPLAY | Concurrent identical opening request produces one allocation |
| P12_OPENING_RACE_RESERVATION | Concurrent competing payroll requests share one finite carry source |
| P12_OPENING_HTTP | Real Auth allocation/replay and deactivation denial |
| P12_OPENING_BROWSER_DESKTOP_CYCLE | CSV source entry, Nota, opening allocation and full payroll cycle |
| P12_OPENING_BROWSER_MOBILE_RECOVERY | Same connected cycle; committed carry response lost, reload, identical retry |

The workflow retains all 80 predecessor cases, CP6 exact restoration, advisor and Auth/database cleanup gates. The new report is `CP7_P12_OPENING_PAYROLL.json`; observed case count must equal 90. A green workflow alone is not evidence of 90 PASS. Screenshots require actual inspection before visual review is claimed.

**P12/F03 OPEN.** E05 partial cash payment remains separate and open; capped kasbon and this full payment are not partial cash. P11/R10, P13, the remaining P09 scope, combined release/install/recovery and independent family acceptance remain open. CP6 stays CLOSED_CONTRACT_SCOPE; `production_go=false`, `independent_acceptance=false`. The owner permits F04 takeover after F03 is complete, subject to rereading its handoff and current writer heads before editing.
