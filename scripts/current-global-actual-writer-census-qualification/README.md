# Current global actual writer census — review material only

Reliable data adalah dewa. Keuangan, laporan, stok, dan HPP adalah raja.

Writer A helper on the exact public D1/E/SKU catalogue source parent
`bce07059f7a351372e40bb7c2e4453876320a2e8`. This namespace neither changes
financial code nor installs a hook. Formal progress stays **5/16**;
`runtime_entry=null`, `actual_Native_credit=0`, `production_go=false`,
`independent_acceptance=false`. The helper is writer work, not independent audit.

## Actual evidence already read

The pinned private SKU archive is from run **41020730202**, head
`7c7204c82debafce217d277514e3f23c8fc2ac69`. That run's concurrency failure remains
retained; this metadata extraction does not turn the run into PASS.
The catalogue in `before.catalog` equals `after.catalog` in
`SKU_COST_RECOVERY_OVER_FIRST_PART_REFUSAL_bcf601d77b56_FULL_CURRENT_CENSUS.json`.
Archive/report hashes and exact counts are in `OBSERVATION_SKU_7C720.json`.
No business row values are copied into this namespace.

| Actual supplied catalogue fact | Count |
| --- | ---: |
| Functions, complete 19-field rows | 2,853 |
| Relations, complete 13-field rows | 2,315 |
| FK definitions | 1,088 |
| Internal and user trigger rows | 5,190 |
| Roles / membership edges | 89 / 26 |
| Actual transaction-column table candidates | 52 |
| Functions with dynamic `EXECUTE` tokens | 35 |

Column-driven discovery finds the three expected missing D1/E relations:
`cp7_credit_correction_de.work_v1`, `.posting_v1`, and
`cp7_credit_note_carry_de.work_v1`. Six D1/E hook definitions are absent;
`cp7_credit.source_request_enter_v1` and `source_request_finish_v1` are already
present. The upcoming actual combined parent must supply all 55 and all eight
hooks. Unknown, empty, wrongly typed, foreign, partitioned, unlogged, and
unexpected-schema candidates are never treated as safe or silently omitted.

The two inventory layers have different review purposes:

| Candidate layer in the SKU observation | Functions | Relations | Physical tables |
| --- | ---: | ---: | ---: |
| Positive references outward from the 19 reader roots and present owning hooks | 141 | 121 | 120 |
| Maximal caller + trigger + both-FK-endpoint + inheritance review envelope | 2,731 | 588 | 572 |

**Neither layer is an approved or complete production lockset.** The maximal
envelope intentionally reaches unrelated daily ERP domains through shared
helpers and FKs. Locking all 572 would create substantial unnecessary conflict.
The printed SQL is a nonexecuted review preview, not a recommendation to deploy.
Narrowing needs an explicit per-edge reason and actual contention witnesses.

## What the code establishes

`census.py` validates the actual all22 ABI, retains its complete metadata,
keeps all function19 fields, role flags and membership admin/inherit/set options,
RLS, policies, views, rules, triggers including internal RI, and FK definitions.
It uses actual column names/types to discover transaction tables. History is
never labelled ephemeral, and a matching context row never grants authority.

The SQL lexer ignores string/comment decoys and records positive source
candidates. Missing matches, unqualified targets, unsupported languages,
unparsed bodies, overloaded calls, dynamic SQL, operators/casts/default effects,
and PL/pgSQL dependency gaps remain **UNKNOWN**. A body with no matched write
is not certified as a reader. Every actual function retains its full19 row.
No number of matching source hashes or local tests can open `require_runtime`.

The all22 provider excludes `pg_catalog`, `information_schema`, `cron`, and
`pg_*` namespaces. This helper makes no further schema exclusion, records that
boundary, and does not claim complete external/scheduler/system writer closure.
The original 38 tables and old actual19 identities are review roots only.

The parent's raw context capture is checked for every role × every discovered
context × all seven captured table privileges. Missing cells, duplicates,
foreign roles, and string booleans refuse. Raw ACL **SQL NULL**, explicit `'{}'`,
and expanded empty ACL arrays remain different observations. The old parent
capture still lacks global function/raw schema/table authority, MAINTAIN,
schema usage/create, and column-specific effective privileges.

## Supplemental capture for the next existing composite run

Use `capture.capture(cur, exact_all22, progress=...)` on the **already installed
committed composite**, under the existing original outer restore machinery.
It makes no connection, takes no URL, installs nothing, and executes no business
function. It requires loopback port 54322, database `cp6_rollback`, PostgreSQL 17,
the administrative disposable role, `READ ONLY`, empty `search_path`, and UTC.
The caller must open that read-only transaction before its first query; do not
try to switch an installer transaction that has already written into read-only.

Bracket the capture with the existing complete all22 + all-table row/hash + all
sequence `(last_value,is_called)` snapshots; require exact equality and retain
the original inverse/reinstall/full outer dump RESTORE evidence. A supplemental
JSON file by itself does not prove these comparisons. No extra standalone
50-minute install is required: use a read transaction during the next existing
composite qualification after its install commits.

The 19 read queries capture all supplied schemas/relations/columns/functions
with raw ACLs, all roles and role edges, structural FK endpoints/actions,
internal triggers, view/rule relation dependencies, inheritance, database and
default privileges, and OID dependency edges. Permission matrices cover every
role × schema USAGE/CREATE; every table/view × eight privileges including
MAINTAIN; every function EXECUTE; every sequence SELECT/UPDATE/USAGE; and all
four privileges for every column with an explicit ACL. Every column's raw ACL
is preserved; table-derived access is captured separately. RLS and app-level
authorization are not inferred from these SQL privilege booleans.

Each query emits `STARTED`, then `CAPTURED` with its exact row count. Unsupported
privileges/query errors emit phase + SQLSTATE and raise, never false or an empty
list. No row truncation or exception downgrade exists. Function privilege rows
alone are approximately 254,000 for the current 89 × 2,853 profile, so retain
them privately with the run rather than printing rows. Supplemental validation
checks exact identities and matrix membership, all RI trigger identities,
view/rule coverage, and inherited tables. `pg_depend` remains incomplete for
string/procedural function bodies even after this capture succeeds.

## Barrier decision and required runtime cases

PostgreSQL 17 documents `EXCLUSIVE` as conflicting with `ROW SHARE` and
`ROW EXCLUSIVE` while allowing ordinary `ACCESS SHARE` reads. This is the
candidate mode for a **reviewed, sorted exact table set** with `NOWAIT`.
`SHARE ROW EXCLUSIVE` does not exclude `ROW SHARE`; the parent's separate real
PG17 lock model already demonstrates that distinction. This helper adds no
Native ERP execution credit to that model.

Existing row locks alone cannot exclude a new relevant lot, graph edge, HPP,
stock, or journal row. A table barrier excludes inserted rows on the covered
tables as well as updates/deletes. Referenced FK rows can already carry
`KEY SHARE` locks from a different writer; every incoming/outgoing FK and its
internal triggers must be reviewed. Table locks do not independently freeze
sequences, function definitions, role grants, or app permissions.

The next actual composite case must therefore prove all of the following with
original Native writers and exact current definitions:

1. Preserve existing request/CAS/FG/FGBOOK and producer pocket TRY order. Use
   current D1/E/SKU bodies only; never reload the old complete Native SQL.
2. Acquire the reviewed sorted `EXCLUSIVE NOWAIT` table barrier before any new
   operation/context/materialization row, immutable receipt, Native effect, or
   sequence allocation. Then preserve Native's exact sorted lot row locks.
3. After every earlier wait, re-read the graph keyset and source hash, current
   actor/request/backend/tx/phase, original authorization, period, and review.
   Raw catalogue ACLs are not a substitute for current ERP permission checks.
4. Exercise an existing writer, future insert/phantom, FK key-share holder,
   reversed lock order, plain reader, permission revocation, and stale quote.
   On rejection, compare every table and sequence before/after, not just the
   nominal target. `nextval` is not rolled back; reaching it early is a failure.
5. Prove original Native monetary/FIFO/date/history behavior and an outside
   completion proof before the immutable operation, source work deletion,
   payment early return, and every finish/tail hook. Source-only parent, exact
   catalogue, synthetic control, and job-green alone do not satisfy this.

An unrelated competing writer can allocate a sequence before attempting a
covered table. This barrier does not make every other transaction globally
effect-free; the actual entry/ordering proof must establish the claimed
rejection boundary for each command under review. Role/DDL races also need an
explicit actual proof or a justified administratively closed run boundary.

Primary PostgreSQL 17 references checked for this implementation:
[locking](https://www.postgresql.org/docs/17/explicit-locking.html),
[LOCK](https://www.postgresql.org/docs/17/sql-lock.html),
[sequences](https://www.postgresql.org/docs/17/functions-sequence.html), and
[dependency tracking](https://www.postgresql.org/docs/17/ddl-depend.html).

## Reproduction and controls

```sh
python -B -m unittest discover -s scripts/current-global-actual-writer-census-qualification -p test_census.py -v
```

`probe.py --help` exposes only hash-pinned archive-to-metadata extraction. It
requires explicit JSON pointers for two equal actual all22 observations,
full source head/run identity, expected context membership, and output paths.
Use the exact pins in `OBSERVATION_SKU_7C720.json`; never pass the large business
document as the output. It retains only selected catalogue/authority metadata.

46 local mutation controls pass. The PGlite smoke executes all 19 capture
queries on synthetic catalogues inside a read-only transaction; it is SQL
syntax/ABI evidence only, with Native0. The first smoke found two ambiguous
`text || "char"` expressions in dependency keys; explicit `::text` fixes them,
and the first failure is retained. `VALIDATION.json` pins these local receipts.
No hosted, default/main, Enteng, B, WA, CP7C, or production writes occur.

The subsequent integration candidate and stricter metadata flags are described
in `INTEGRATION_PLAN.md`. It adds counted runner/gate source derivations and a
separate Original with exact-byte readback. The combined local suite is now
73 controls; `INTEGRATION_VALIDATION.json` records this successor. The earlier
`VALIDATION.json` remains the evidence for helper commit `68ec0f57`.
