# Independent remaining release gates

Frozen product: `08065a3b4da71c51ffbbab77f0a6b1ac7e6638ec`.
This continuation changes only the independent audit runner and its notes. It
does not change product SQL, guard pins, application source, UAT, or production.
Provenance disclosure: an early broad setup search incidentally returned old
AW/BA evidence labels, including LAU-T14 oracle labels. No writer/peer business
test file was opened or run. Those incidental labels were not used to author
the build/install assertions; this runner reuses no business verdict or oracle.

## Official build

Run `python audits/independent_bd_20260927/release_gaps.py build` from the audit
checkout after `npm ci` and Node 24 setup, before the browser step.

The runner executes the literal `npm run build`, including `prebuild` and
`postbuild`. If it fails, the runner executes the installed `tsc -b` and
`vite build` binaries separately, without editing the source ownership gate.
Those diagnostic compile results never substitute for the official gate.
Evidence is `audit-results/release-build.json` and three possible log files.
A completed build refusal is recorded evidence; only an incomplete runner
causes the Python command to return nonzero.

Local official-gate observation, before native CI: literal `npm run build`
exits 1 during `prebuild`; the unchanged
`scripts/check-source-ownership.mjs` fails with `Browser RPC ownership drift`.
The actual ownership list has six additional entries: two in
`BeReworkTargetFields.tsx`, three in `ConnectedProductConversionPage.tsx`, and
one in `ConnectedBsResolutionPage.tsx`. This is a finding about the frozen
shared repository. Its attribution to the BD change alone is not established.
Local evidence is `release-build-local-official.json` and its log.

Run 16 (`36338382541`, audit head
`c6787516e320d77be9665f907c4ecf3e8bba83ee`) independently confirms the same
official build failure after `npm ci` under Node `v24.21.0` / npm `11.19.0`.
Literal `npm run build` exits 1 in the ownership prebuild gate. The separately
executed `tsc -b` and `vite build` each exit 0. Their successful compilation
does not satisfy the official lifecycle gate, which stopped before the later
access/CSS checks and postbuild artifact scan.

The six actual additional ownership entries are:

| Source | RPC |
| --- | --- |
| `src/BeReworkTargetFields.tsx` | `erp_get_laundry_bd_workspace_v1` |
| `src/BeReworkTargetFields.tsx` | `erp_get_product_conversion_workspace_v1` |
| `src/ConnectedBsResolutionPage.tsx` | `erp_save_product_conversion_action_v1` |
| `src/ConnectedProductConversionPage.tsx` | `erp_get_accessory_service_workspace_v1` |
| `src/ConnectedProductConversionPage.tsx` | `erp_get_product_conversion_workspace_v1` |
| `src/ConnectedProductConversionPage.tsx` | `erp_save_product_conversion_action_v1` |

`release-build.json` SHA-256:
`79f490a6013141dd5fd4a539c8f4041d13176d40386acf2d385c4d7d7317620b`.
All three log hashes were checked against the downloaded artifact. BD-only
attribution remains `NOT_ESTABLISHED`.

## Source55 plus dev AW–BD

This is a separate installation experiment. The existing main audit installs
the hosted-aligned release package. That installation cannot establish whether
the unchanged source migrations and the dev T1 files install successfully.
The two paths intentionally have different admitted guard pins.

Use a separate job with a fresh Supabase PG17 `17.6.1.165` runtime and the same
client/setup versions as the main independent job. Check out the audit branch
as `auditor` and frozen base `1bdca3766f7c9800d68295ff5122798060b8a05d` as `base`.
Neither the candidate/harness checkouts nor archived bootstrap artifact
`10392910720` are required for this path. No inherited business test is run.

1. In the base checkout, start the same isolated Supabase runtime.
2. In the base checkout, run
   `python ../auditor/audits/independent_bd_20260927/release_gaps.py bootstrap`.
   This executes only the two exact frozen workflow commands that verify and
   restore the immutable CP4.5a catalog/config fixture. There is no hosted
   alignment or later migration in this step.
3. In the audit checkout, provision `cp6_maintenance_admission` and clone the
   fixture database to `cp6_rollback` using the main job's existing guarded
   provisioning/clone step. Keep the primary fixture database unused.
4. In the audit checkout, run
   `python audits/independent_bd_20260927/release_gaps.py source55`.
5. Always upload `auditor/audit-results/`, and always stop the isolated runtime.

Required job environment: `PGURL` is the existing exact loopback `postgres`
URL, `CP6_DATABASE_CONTAINER=supabase_db_cp5-local`, and
`CP6_MAINTENANCE_CONFIRM_DATABASE=cp6_rollback`. The provisioning step exports
the ephemeral `CP6_ADMISSION_CONTROL_PGURL` as in the main job.

Concrete job header and new runner steps:

```yaml
source55:
  runs-on: ubuntu-24.04
  timeout-minutes: 45
  env:
    PGURL: postgresql://postgres:postgres@127.0.0.1:54322/postgres
    CP6_DATABASE_CONTAINER: supabase_db_cp5-local
    CP6_MAINTENANCE_CONFIRM_DATABASE: cp6_rollback
  steps:
    - uses: actions/checkout@v4
      with: {path: auditor, fetch-depth: 0}
    - uses: actions/checkout@v4
      with: {path: base, fetch-depth: 0, ref: 1bdca3766f7c9800d68295ff5122798060b8a05d}
    # Copy the setup/start steps identified in the table below here.
    - name: Restore only the exact clean CP4.5a fixture
      working-directory: base
      run: python ../auditor/audits/independent_bd_20260927/release_gaps.py bootstrap
    # Copy "Provision isolated maintenance and clone" unchanged here.
    - name: Independently install unchanged source55 and dev AW through BD
      working-directory: auditor
      run: python audits/independent_bd_20260927/release_gaps.py source55
    - uses: actions/upload-artifact@v4
      if: always()
      with:
        name: bd-independent-source55-${{ github.run_id }}
        path: auditor/audit-results/
        retention-days: 14
    - name: Stop isolated source55 runtime
      if: always()
      working-directory: base
      run: supabase stop --workdir cp5-local --no-backup
```

The comments above refer to these exact existing main-job steps, in this order:

| Position | Existing step to copy unchanged |
| --- | --- |
| Before bootstrap | `actions/setup-python@v5` with Python `3.12` |
| Before bootstrap | `Install disposable database clients` (psycopg 3.2.10, PyYAML 6.0.2, verified PGDG signing key, PostgreSQL client 17, GITHUB_PATH) |
| Before bootstrap | `supabase/setup-cli@ab058987d8d6c725971f6cf9d0b5c98467e30bd1` with version `2.116.0` |
| Before bootstrap | `Start isolated Supabase runtime`, working directory `base`; first add `mkdir -p ../auditor/audit-results` before its log redirect |
| After bootstrap | `Provision isolated maintenance and clone`, working directory `auditor`, including the exact role, masks, GITHUB_ENV export, and guarded clone command |

The extra directory creation is necessary in the new job because the main
job's product-identity step normally creates `audit-results` before runtime
startup. Copying that product-identity step as well is an equivalent option.

The installer verifies every source byte against the frozen product commit.
It executes exactly 55 source migrations from v2.6.18 through AV, followed by
the eight dev T1 files AW, AX, AY, AZ, BA, BB, BC, BD. BE is excluded. The
original source guards all execute; the first refusal stops the chain and is
recorded verbatim with its SQLSTATE.

Platform ledger serialization follows the frozen native workflow: v18 through
v19b use empty statement arrays; v19c uses its full source; v20 through v20f
use the source with only its terminal LF omitted from the *ledger value*;
all later source migrations use full source text. Executed SQL is always the
complete unchanged file. Every new platform row is checked exactly after
installation. The dev T1 files create their own application markers and do
not invent platform ledger rows.

AO through AV use the unchanged `cp6_t3_release_package.Applier` only as an
installer: the database closes admission and drains sessions; it unwraps only
the reviewed outer transaction, executes all original guards, and inserts the
exact source ledger row in that transaction. No capture, repinning, release
package substitutions, guard removal, or `if false` transformation is used.

Evidence is `source55-bootstrap.json`, bootstrap logs, and
`source55-install.json`. A full success requires 55 source migrations and
eight dev files, 111 application versions, 118 platform rows, unchanged
original platform ledger rows, and unchanged primary marker/ledger/empty
state. A completed source refusal is an audit result, not a successful install.
An incomplete harness returns nonzero; the JSON status is authoritative.

Local verification completed: Python syntax check, source inventory check,
all 63 files byte-identical to the frozen product, 55 source migrations,
eight closed-admission source files, eight dev files, and original ledger
serialization branches confirmed against the frozen workflow.

Run 16 independently executed this path on PostgreSQL `17.6` and returned
`PASS_SOURCE55_PLUS_DEV_AW_BD`. The artifact review recomputed all 63 source
hashes and all 55 ledger digests from the frozen source bytes. All eight
closed-admission migrations AO through AV installed with the original guards.
Application markers grew exactly from 48 to 111 and platform rows from 63 to
118; all original 63 platform rows remained unchanged. All eight dev markers
AW through BD are present, BE is absent, auth users/app users/audit rows remain
zero, and admission is open. The separate primary fixture's measured marker,
ledger, and empty state remained unchanged.

Source55 artifact ID: `10938366480`; ZIP SHA-256:
`056ce6a437ec74d9070a4a952f2d995a4bc4242748b3b50d1020fb4c6bd7aa35`.
`source55-install.json` SHA-256:
`cf2bff1edbd74010e6772a4c71b81f670c2702eec7b3ff8bd364a061047b7af8`.
The report's runner SHA matches the independently authored runner. This result
confirms installation on the fresh unaligned fixture. The main business audit
continues to exercise the separately installed aligned release package.
