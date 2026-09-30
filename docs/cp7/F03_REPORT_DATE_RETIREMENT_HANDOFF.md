# F03 report date retirement — source-bound repair

CP6 CLOSED_CONTRACT_SCOPE; F03 OPEN; independent_acceptance=false; production_go=false. This repairs the existing connected report UI; no native SQL, money/HPP rule, role/grant, historical filing or hosted environment is changed.

## Actual defect and resulting behavior

`ConnectedFinanceReportPage` previously changed date inputs without retiring its displayed snapshot or pending read. A successful response for the old period could repaint money after editing or submitting an invalid new range. Header refresh also read the last loaded dates, even when the inputs had changed. That violates the existing no-stale-financial-facts contract.

On any of the three date edits, the page now retires its snapshot, original filing, comparison children and pending-response generation immediately. It waits for explicit submit/refresh. Invalid submit keeps the validation error and cannot accept the old response. Refresh uses the entered valid dates; when dates are unchanged, it preserves the selected immutable filing and pagination. Period-control post-commit refetch follows the same current-date refresh boundary. Financial values still come through the unchanged closed native report parser; no optimistic or second money calculation.

Four regression tests first ran against the unmodified48ae339 product: original8 tests PASS, all four new tests FAIL. The original failure report and exact changed-source hashes are retained in [local receipt](evidence/f03-report-dates/LOCAL_RECEIPT.json). A fifth regression checks a period post-commit callback captured before the date edit: it must refresh the latest entered dates. After the final repair:13 report tests and the impacted cash/analysis/period controls total34 PASS; full local suite821 PASS. Build/type/source/access/CSS/security and secret scan pass. The first local security command stalled in its unchanged sandboxed bash -n subprocess; the same complete command passed in the working runtime with full predecessor history. The interrupted log remains retained; no guard was weakened.

## Declared actual qualification

Extend the inherited cash6 qualifier with two actual report-date browser journeys (desktop/mobile), for8 declared cases: native3,real Auth/HTTP1,browser4. Previous cash6 remains separately source-qualified on3c825db; its count is not changed retrospectively. New actual result must bind this product/test SHA/tree, complete report, package/advisor/restore/Auth cleanup and screenshots.

Both new browsers use the existing actual source fixture, load Laporan & Tutup Buku with real OWNER Auth, compare the complete public report to native, and change the period. Old money must disappear; header refresh must request the entered period. Then an actual successful native HTTP200 response is held while the operator enters/submits an invalid range; delivering it must not repaint old money or remove the validation error. Explicit valid refresh must recover. Read-only source state must remain identical. The held response is actual native HTTP, not a mock financial payload.

The original33-journal cash worksheet and its6 cases remain included unchanged: exact25+8 source pages,137.50 net cash,1337.50 debit,1200.00 credit, original/linked inverse dates and current403 retirement. These overlapping retained cases are not additional family coverage.

Native/Auth/browser qualification is pending until its actual complete result is retained. Whole E12/E13/E14/F03 and independent acceptance remain open. See [remaining contract](F03_REMAINING_CONTRACT.md) and [takeover/context](F03_WRITER_TAKEOVER_20260930.md).
