# P12 attendance and roster — continuation boundary

29 September 2026. Source inspection complete; connected source editing and its runtime qualification remain OPEN. This is not a new business-policy decision or a runtime PASS. [Exact accepted source inventory](evidence/p12-attendance/SOURCE_INVENTORY.json) binds the nine native definitions and the five existing attendance permissions. CP6 stays closed within its accepted scope; production_go=false.

The current `src/attendance/AttendancePage.tsx` is simulation state. Its controls cover roster, effective rate history, employment episodes, deliberate marks, bulk preview, posting and correction. Connecting it must replace simulated data/actions with authoritative reads and current access, not preserve the seeded values as a fallback after a failed read.

The accepted native roster save records initial rate and employment episode together. Initial rate must cover the start date. A worker cannot move to another mandor, change the original start date, or introduce an employment change that contradicts posted attendance. Deactivation/reactivation dates preserve prior episodes and cannot take immediate effect on a future date. Rate changes append dated immutable versions with an exact worker version. Roster/rate mutation currently requires native OWNER/ADMIN authority; attendance draft/post/reverse additionally has the existing permission catalog. Do not silently invent delegated rate authority.

The attendance source is a dated period with explicit worker/day cells. DRAFT is not payroll entitlement. POST requires every eligible DAILY/HYBRID worker/day to be recorded with an effective native rate. Blank cells must stay unrecorded, never turn into ABSENT/OFF. Native HALF_DAY fractions may not exceed0.5. Payroll takes effective date-based rates; the legacy workspace's `current_daily_rate` must not stand in for historical rates. Historical workers must remain discoverable when an employment episode overlaps the chosen period, even if inactive now.

Correction/reversal must retain the complete original lineage. A period consumed by any non-reversed payroll cannot be corrected or reversed first. A correction explicitly supersedes every original attendance row; reversing that correction restores its original source. Posting attendance itself is not payroll cost approval or payment. The settlement candidate separately proves attendance accrual at APPROVED, followed by cash settlement at PAID.

The connected source increment must cover:

- Exact string money/versions, paged contractor/roster/period/detail/history reads, current finance.attendance.view access, explicit dates, and stale/failed-read retirement.
- Native worker creation/rate change and employment stop/reactivation through their existing authority; no rewritten wage formula or direct business-table browser writes.
- Explicit draft marks, native preview and complete-cell refusal; ordinary SAVE/POST/correction/REVERSE with stable request identity and lost-reply recovery.
- Current permission revocation during waits/replay, historical rate/employment boundaries, and consumed-attendance correction ordering.
- Browser-created roster/rate/attendance feeding selected Nota → prepare → approve → pay, preserving the native amount and one-time accrual. Existing native fixtures prove their bounded cases, not this connected source journey.

Opening advances/payables/carry and E05 partial cash payment remain separate open P12 obligations. Existing full-net payment and capped kasbon deduction do not close partial cash payment. P11/R10, P13 and combined family acceptance remain open.
