# OW04 initial settlement in the actual application source

The nine existing UI escrow files are now applied to the working product
source, with all six base-source SHA256 checks satisfied. They were previously
only installed by the disposable browser harness. No second implementation
was created, and the original escrow remains unchanged for provenance.

The active connected return form quotes through its fixed public facade and
dispatches RETURN_SETTLEMENT through the existing shared mutation envelope,
UUID, lock, stale-read and reload/recovery machinery. It never falls back to
the old RETURN action when settlement quote/permission/data are unavailable.
Blank physical/refund times and explicit CREDIT/REFUND/account choices remain.
Both new RPC boundaries are enumerated in source ownership and access-catalog
censuses; the total is checked strictly rather than bypassed.

The invoice, receivables and customer-history current summaries now label the
legacy `paid_total` wire field as effective settlement E=P+U−I. Original PAYMENT
events retain their actual payment P. A specific DOM case distinguishes P1000
from summary E800 after credit I200, including both values in the same event
row with the appropriate labels. No frontend financial engine was added.

## Verification and preserved failures

LOCAL_UI_RECEIPT.json pins the current source files and each latest case result.
182unique local cases pass across the eight-file initial run and the12-case
history retest. These are not194unique cases. The initial181PASS/1FAIL report
is retained: the new history assertion first assumed ungrouped1000, then
incorrectly rejected E800 anywhere in a row that deliberately contains the
current invoice summary as well as the original payment. The corrected test
checks the distinct actual payment amount element and labelled summary.
No money oracle or product calculation was changed to make those tests pass.

The first build failed because the strict access census correctly saw291
boundaries instead of289. Its log is retained. Explicitly adding the two
owned boundaries to the access census, while keeping the exact total check,
resolved it. The complete production build, source/access/CSS checks and
compiled-client secret scan then passed. React review covered hook/event
ownership, current-session/read fences, accessible controls, exact contracts,
no unsafe HTML, no shared mutable data, and no extra data-fetch waterfall.

This is WRITER_LOCAL_DOM_AND_BUILD evidence, not Native/Auth/HTTP/real browser
or independent acceptance. The backend remains the entire atomic owning
composition; default product installation and active-source real-browser
qualification still need to be joined and proved. The browser harness now
accepts the exact 13-file active-source manifest and verifies the two shared
unchanged prerequisites plus the original escrow. Its seven local source
controls pass; actual browser execution on this composition is still pending.

OW04 remains open for the explicitly listed backend/customer-credit lifecycle
gaps, complete composition, dependency routes and the2s save target. Nothing
is installed hosted and production_go=false.
