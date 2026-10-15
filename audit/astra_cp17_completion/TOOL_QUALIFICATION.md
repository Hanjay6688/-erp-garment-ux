# Astra tool qualifications — all original attempts retained

Frozen product and original case IDs/oracles remain unchanged. This document records tool defects, not product failures.

- First matrix/retained attempt: run 38791612672, control c839a3c51a4511342d0ce46e8adc5202401a2b4b. All four jobs failed before Python or any case. Destination `auditor/audit` did not exist, so cp renamed the copied directory to `audit`; the declared probe path was absent. Full logs retained.
- One allowed identical-scope pre-case retry: run 38792368517, control adc91c0f47ffd8d0ec877767c3016953b5535076. The inserted newline was inside a YAML quoted multiline string and folded into a space. The parsed command became `mkdir -p ../auditor/audit cp -R ...`; mkdir rejected option R. All affected jobs have zero cases. This attempt is INCOMPLETE/TOOL_ERROR and is closed, not credited as a product pass.
- The new integration workflow at aae283cfb9a492d68abcbbfcd6b251cec0514c69 inherited that same parsed-command defect (run 38792810239). It is preserved as the first qualification attempt for its two predeclared IDs.
- Tool correction qualification under Pro Max §16.3: set the run field as a parsed string with four explicit command newlines, serialize YAML, read it back and compare exact strings, run bash -n, and execute the copy path against a temporary synthetic directory with a dummy Python probe. Both workflows passed that LOCAL_QUALIFIED check. No product file, case ID, data, seed, timeout, assertion, expected result, permission gate, or branch pin changed. This is not an identical rerun to search for green.

The first two attempts remain part of the final receipt; this qualification cannot erase them. The run's acceptance is determined from actual per-case output and restoration gates, not workflow color. Candidate stays dfab13bf62398a69a02bf6221c06d29075e5e40b.

## Matrix readiness qualification

Run 38793203625 preserved raw PASS records even where lazy workspace content was not loaded: 70/96 disposable and 56/96 UAT snapshots explicitly contain `Memuat workspace dan guardrail transaksi.` Source App.tsx WorkspaceFallback proves these are loading states. They are protocol INCOMPLETE for finished-page inventory, not product success. Header text plus `waitForLoadState(networkidle)` was insufficient on SPA navigation.

Under Pro Max §16.3, fix the tool to wait for that exact lazy fallback to disappear, then for all page requests to settle and remain idle for 800 ms. Assert the fallback is absent in the captured result. Same 288 stable IDs, candidate, mode/viewport, source and no-overflow/no-pageerror/no-5xx oracles; no transaction case is rerun. Prior results and artifacts remain retained. This strengthens observation readiness rather than changing product expectations.

## Production locator qualification

Run 38793203672/job116622792645: ASTRA_CHAIN_CUT_TO_FG is INCOMPLETE after a successful browser cutting POST (raw100/value1000 ->40/value400; WIP600). `getByLabel('Mandor',{exact:true})` timed out. Captured body and frozen ConnectedPickupPage.tsx prove the select exists; its wrapping label also includes the explanatory text `Mandor dikunci mengikuti penugasan Production Order.`, so the exact accessible label is longer. No backend pickup command was sent.

Correction under §16.3: locate the single combobox within `.cpick-setup` with accessible name starting Mandor, then assert its selected value is the fixture contractor. No fixture/oracle/seed/timeout/product changes. Run only the same ASTRA_CHAIN_CUT_TO_FG ID; successful ASTRA_CHAIN_ACCESSORY_NOTA_TO_CASH is not rerun. Preserve old INCOMPLETE, screenshot, trace, requests and logs.
