# GPT browser/HTTP oracle freeze — 25 September 2026
Candidate tool9dd7bc2,producta095a9d. AUDITOR_SCENARIO. No product edits, no hosted calls.
Hashes (verified by CI before execution):
- gpt_browser_fixture.py: 87ff3f918a5bfc802623d3471619ad65e8e09f9b25e22dcdb4bb9d3df324bb1a
- gpt_http_and_adjustment.py: 16ed21eda002d40531edd22ebe943ffc595d13ab6a3e053833fde2bb89bd0f43
- gpt_wib_browser.mjs: 8e489094a647e405b5275c90404d063ea836e211323f2c0c3f0938280710dca3
- ../c0_round8/gpt_c0_oracles.py: 7c2c19b6e722d325ba902cfd9eb1ae2f98d4e2ec27245070ab485df0af9e66a7

Twelve browser cases: Potongan SAVE_DRAFT, BagiPotongan SAVE_DRAFT, BS CREATE_MANUAL_BS × Asia/Jakarta, UTC, Etc/GMT+12, Pacific/Kiritimati. Each signs in through real Auth form, selects a real UI transaction, fills yesterday00:30WIB, clicks Save, captures the actual browser RPC request/response, then reads the stored UTC instant. Oracle M3820 / CP6-01: all zones must store yesterday00:30+07, regardless of browser timezone; response not mocked. Native setup uses ordinary receipt/cutting fixtures and restores ERP-schema grants BEFORE browser login/actions. Separate masters/receipt/PO per case; changes only in disposable browser copy.

Three realAuth HTTP cases: (1) owner read/unauthorized role matrix using null default batch and genuine SAVE_DRAFT instead of nonexistent batch/invalid action; (2) revoked owner blocked on accessory read; (3) prepared helper reachability at unchanged public-only endpoint/schema grants. Third is a scoped observation, not proof every legacy/private-client path safe.

One native C0 retry: business oracle remains the same frozen7c2c19b6… file. The receipt helper `scripts/cp6_initial_import_receipt_trial.py:7–12` unconditionally revokes the temporary native ERP schemaUSAGE after reverse. Wrapper restores the strict runner's existing temporary grant for subsequent report read; no product function or expected amount/date changed. HTTP/browser use their own committed copies WITHOUT native grant. Rev1INCOMPLETE retained.

Whole CP6 HOLD. Record run and job IDs immediately; extract each case, console errors and Auth/DB cleanup. Failed setup is INCOMPLETE. If UI async selection prevents a save, inspect actual interaction before claiming product failure. Do not mark whole browser/report gate accepted from these bounded cases.
