# Recovered frozen scenario bytes

Candidate: 9add57ea8c2b6b2dc37c0134717d4d39ba30b5dc.
Source: CP6_PHASE1_LOCKED_9add57e.zip, recovered from the original saved archive.

| File | Planned cases | SHA256 | Native status |
|---|---:|---|---|
| stock_import_scenario.py | 4 | ff92e8d973ebb75c05ba8ac6b47da96565c9b50760c91b247f331a765d18df81 | NOT_RUN |
| money_dates_scenario.py | 4 | cfa1157b7ea39e6f5162d85a540ed5e22c30d8fef9ddfe840b5a9bf2f631d9ef | NOT_RUN |

These are the exact eight frozen cases, not a reconstructed version of the later fifteen-case combined payload. The final six-case advance revision and one-case selector revision have not been recovered byte-for-byte. The older business checkpoint has a different hash and includes four held COUNT cases; it must not silently replace the final default batch. See AUDIT_PROGRESS.md for receipts and remaining work.

No new native workflow was dispatched during this recovery. External auditors' related native results, if validated, are labeled REUSED_EVIDENCE and do not turn these original case IDs into executed tests. Restoring source files does not validate their fixtures on the installed candidate.
