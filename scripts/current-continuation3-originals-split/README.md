# Read-only recovery of one oversized D1 continuation3 Original

PREPARED transport utility, not a new Native run or financial acceptance. The
existing successful job is not itself proof that its financial/package report
passes: the unmodified raw report and all restoration gates still need review.

The fixed source is run40958135976, attempt1, job123743552217, artifact12937065328
(`cp7-a-credit-d1-current-parent-continuation3-1`) in Hanjay6688/-erp-garment-ux.
Headcde78b2cc82e0a286174098458dab9815fdfd072 has tree
915103541d247f544c4492db25953b4268d9c2e3. Workflow path/branch, job name,
completed/success, artifact name/nonexpiry/run/head/bytes/digest are checked
before downloading. Failed metadata, transport, size or hash is a refusal.

The Original ZIP is **671127620 bytes**, SHA256
`609ebff9739f359d39239d0e502aad20d4613f5a037a4e0e83f31b04b4b7652e`.
The GitHub connector's536870912-byte bound prevents downloading that single
artifact. This workflow streams that exact immutable ZIP through `gh api` into
two consecutive raw files, each335563810 bytes. It keeps at most one1MiB read
block in memory and never creates a third complete archive copy or extracts
ERP data. Each raw part is uploaded as a **separate** compression-level0
artifact; a third small artifact contains the reconstruction manifest.

| Order | Byte offset | Raw file | Separate transport artifact |
| --- | ---: | --- | --- |
| 1 | 0 | original-artifact.zip.part-001 | cp7-d1-continuation3-original-12937065328-part-001 |
| 2 | 335563810 | original-artifact.zip.part-002 | cp7-d1-continuation3-original-12937065328-part-002 |

The small artifact is `cp7-d1-continuation3-original-12937065328-manifest`,
containing `CONTINUATION3_ORIGINALS_SPLIT.json`. It is emitted only after the
whole original digest/size and download subprocess exit code all pass. It lists
exact order, offsets, sizes, calculated partSHA256, wholeSHA256, fixed source
identity and zero new ERP/DB/Native/Auth/browser execution credit. Actual part
digests remain unknown until real recovery; no local fixture digest is used.

The GitHub-uploaded transport ZIPs wrap the raw part files. Their transport
archive hashes/sizes must be checked against their own immutable artifact
metadata. They are not the Original ZIP and must not be concatenated directly.
Download the manifest wrapper first, then the two part wrappers sequentially.
Verify each wrapper, extract only its one expected raw part with its exact
manifest size/hash, then remove that wrapper before downloading the next one.
Keep only the two raw parts. Read them as one seekable virtual concatenation,
check the original whole size/SHA256 and ZIP member CRCs, then read only the
required original reports. Do not allocate another full671MB ZIP plus a full
extraction on the constrained local disk. Preserve original member bytes; a
derived local receipt never substitutes for them.

The only CLI argument is a new local output directory; source is static in
`split.py`, not caller-selected. The workflow accepts no source inputs, uses
contents:read/actions:read, existing pinned checkout/setup-python/upload action
SHAs and a20-minute limit. GH_TOKEN is supplied only by the GitHub runner.
Metadata/redirect URLs, token values and subprocess stderr are never logged or
saved. No ERP code, DB/engine/server, Auth fixture, install, remote mutation or
financial calculation is invoked.

Local controls (standard library only, no network):

```sh
PYTHONDONTWRITEBYTECODE=1 python -B -m unittest discover -s scripts/current-continuation3-originals-split -p test_split.py -v
```

Root remains the sole publisher/dispatcher. Execution leaf:
`astra-a/continuation3-originals-split-20261030`. This prepared commit does not
claim that the parts exist or that actual recovery/financial review passed.
