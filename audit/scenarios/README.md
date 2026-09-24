# CP6 native scenario preparation

Candidate product: `9add57ea8c2b6b2dc37c0134717d4d39ba30b5dc`.

**Fifteen case sources are prepared. Native status: NOT_RUN. Run ID: null. Job ID: null.**
Syntax, pure case registration,15uniqueIDs, exact embedding and hashes were checked locally. No business operation or database test was executed by those checks.

| Member | Cases | Provenance | SHA256 |
|---|---:|---|---|
|stock_import_scenario.py|4|FROZEN_EXACT|`ff92e8d973ebb75c05ba8ac6b47da96565c9b50760c91b247f331a765d18df81`|
|money_dates_scenario.py|4|FROZEN_EXACT|`cfa1157b7ea39e6f5162d85a540ed5e22c30d8fef9ddfe840b5a9bf2f631d9ef`|
|business_scenarios_reconstructed.py|6|RECONSTRUCTED_POST_LOCK|`90625484eded3a0a68e8852f9c19e9e9286887c1d905821abc89931b42029618`|
|import_selector_reconstructed.py|1|RECONSTRUCTED_POST_LOCK|`66d0524c7665a5a68b55f3dbf6934bc5742395ed5832ffbd2301cd7d70d5e6ac`|

The original eight frozen cases remain unchanged. The advance6 and import-selector1 files are post-lock reconstructions from reviewed source, with new IDs/hashes where stated. They are not the lost final originals.

Self-contained payload: [combined_native15_reconstructed.py](combined_native15_reconstructed.py).
- SHA256: `cec2ad521835476cf702119486e637d3eff4b62d8f72197a9ca2c2d50cf1fadb`
- Bytes: 47183; base64 characters: 62912.
- Full case manifest and limitations: [native15_manifest.json](native15_manifest.json).
- Rebuild from repo root: `python3 audit/tools/build_native15.py`.

The payload embeds each member byte-for-byte; the approved workflow receives just this one file through scenario_b64, phase=after. It checks member hashes, planned IDs and allowed result vocabulary. Build verification does not validate fixture legality on the live candidate.

Before execution, review writer-branch changes against9add. Record the exact checkout/tool commit separately if it moved. Do not label a new-head job as9add. Use the already authorized disposable CP6 auditor workflow and supply base64 directly from file bytes. No credentials should be requested or extracted. The current GPT connector lacks custom workflow-dispatch POST; an authorized dispatch-capable executor is required.

Oracle qualifications:
- SI01 optional-product binding remains unresolved; raw COUNTEREXAMPLE is not automatically an accepted defect.
- SI04 ordinary DRAFT-edit privilege and latest-control fixture still need native validation.
- Money DOWN uses the preserved ROUND_HALF_UP endpoint oracle; compare authoritative posted rounding rather than assuming the script defines policy.
- Advance dated-capacity interpretation is explicitly inferential; arbitrary refusal is INCOMPLETE.
- Import selector covers UI discovery from recent50; known-UUID public retrieval is a positive control. It is not the BS101 case.
- No Auth/HTTP/browser, two-session race, release rollback, or product fix is supplied by this batch.

Review existing Claude native evidence separately as REUSED_EVIDENCE; do not relabel these original/reconstructed case IDs as executed.
