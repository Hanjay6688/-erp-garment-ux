# Durable audit evidence

Original JSON artifact ZIPs are retained byte-for-byte and checked against GitHub's artifact SHA256. Own-case JSON is compressed losslessly. The complete decoded job logs (including first failures) are gzip-compressed losslessly after a trailing-newline normalization on file saving. No status is rewritten. `CASE_LEDGER.jsonl.gz` is an index of the original case observations, not a substitute for those archives.

Original CI artifact metadata and digests are in `ARTIFACT_REGISTER.json`; source, expected values and source hashes are in the predeclared manifests. `RUN_REGISTER.json` records every run started here. Full CI artifacts additionally contain synthetic SQL clone exports and screenshots; those redundant files are not counted as separate test evidence. The retained JSON contains the installed file/object inventory, detailed case evidence, restore and cleanup results. No production dump or hosted query is included.

Tools: `python audit/astra_cp17_r5/reconcile_evidence.py` reads the expanded decoded logs under ignored `raw/`; decompress the matching evidence log into that directory to reproduce reconciliation. Every failed first attempt remains visible in both the ledger and raw evidence.
