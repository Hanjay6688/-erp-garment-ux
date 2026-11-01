# Canonical archive transport

Prepared by Writer A for Current38 run `41291621885`, commit
`08ef3bee814e6452b9193b53efc05d53abca2d9d`. The preceding canonical artifact
was 684,153,883 bytes, beyond the connector's 512 MiB transfer ceiling.

This preparation is inactive. `EXPECTED.json` deliberately does not exist.
Only after the actual original run and job succeed, obtain its immutable
artifact metadata and create that file with the exact repository, head, tree,
run id, job id, attempt, artifact id, artifact name and archive bytes/SHA256.

If the original archive fits the connector, use its normal direct download.
Otherwise, update the existing evidence recovery branch's one workflow with
`WORKFLOW_TEMPLATE.yml.txt`, this script and the exact `EXPECTED.json`. Do not
add a second copy of the old recovery workflow. This evidence-only workflow
checks the terminal API identities, downloads the original once, verifies the
complete ZIP, and splits its bytes into at most four 256 MiB parts. It imports
no ERP code and starts no database or business test.

Download the manifest and part artifacts, verify each outer artifact's API
size/SHA256/CRC, and retain the one safe inner file from each. Then run:

```sh
python -B archive_transport.py join --expected EXPECTED.json \
  --directory /absolute/verified-parts --archive /absolute/ORIGINAL.zip
```

The join refuses missing, changed, reordered or unsafe parts and existing
destinations. The final reconstructed bytes, SHA256 and CRC must match the
original canonical artifact. Run the unchanged Root intake on that complete
original ZIP and its original API metadata. A transport receipt alone gives
zero qualification credit.

Local tests use a synthetic ZIP only. No GitHub fetch or ERP runtime has been
executed by this preparation.
