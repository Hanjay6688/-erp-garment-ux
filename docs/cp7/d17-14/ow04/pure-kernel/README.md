# Isolated OW04 arithmetic proposal

This directory contains a PostgreSQL arithmetic kernel and an executable PGlite
oracle. It is not an ERP migration, a source collector, a posting boundary, or
Native evidence. It does not create tables or journal entries, choose dates,
resolve accounting periods, select accounts, grant permissions, or authorize a
refund/application. No file here is installed in the product.

The literal oracles were written before the SQL or driver was executed.
`EXPECTED_RECEIPT.json` pins their hash. The first executable run passed, so no
`FIRST_FAILURE.json` exists. If a future run fails, the driver creates that file
once and preserves it across subsequent runs.

## Running

```sh
OW04_PGLITE_MODULE=/absolute/path/to/pglite/dist/index.js node docs/cp7/d17-14/ow04/pure-kernel/oracle.mjs
```

The driver defaults to the optional `@electric-sql/pglite` module. Set
`OW04_PGLITE_MODULE` to an absolute installed module path/URL when using an external verification runtime.
It uses a new in-memory database and writes `RESULT.json` only after all cases
pass. `kernel.sql` uses built-in PostgreSQL 14+ features and PL/pgSQL. All six
functions are `IMMUTABLE SECURITY INVOKER` with an empty search path.

## Recognition boundary

`ow04_pure_kernel.recognition_plan_v1(before jsonb, added jsonb)` accepts two
arrays of normalized immutable source contributions. Every event has exactly:

```json
{
  "id": "immutable-event-id",
  "kind": "NET",
  "amount": "-200.00",
  "economic_date": "2026-10-19",
  "transaction_date": "2026-10-20",
  "source_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
}
```

`kind` is `NET` or `FUNDING`. A sale increases NET, a return decreases NET,
and their real inverse events have the opposite sign. Raw funding consists of
payments plus credit applications, with their real inverse events. Recognition
of customer credit itself is not raw funding. An inverse has its own event ID;
the original event remains in the vector.

`before` contains the complete retained raw source history for the proposed
context. `added` can contain any signed compound changes. The kernel validates
the complete before and after snapshots; it does not require the arbitrary
serialization order inside `added` to form valid transient snapshots. An added
repair cannot conceal an invalid before snapshot.

Every amount must be JSON string decimal text with optional sign, no leading
zero except `0`, and zero to two fractional digits. Exponents, non-finite values,
JSON numeric values, and fractional cents are refused. Normalization emits two
fractional digits and canonical zero. Arithmetic uses PostgreSQL `numeric`,
without a storage precision assumption. The caller must enforce its own ledger
column bounds. IDs are nonblank strings of at most 512 characters and unique
across both arrays. Dates are real canonical Gregorian `YYYY-MM-DD` dates from
year 0001 through 9999. Every transaction date must be on/after its economic
date. Source hashes must be lowercase 64-character hexadecimal strings.

For every pair of source-date breakpoints, cumulative NET and FUNDING must each
be nonnegative in both snapshots. Funding may exceed NET. The collector/poster
must supply the actual immutable dates. For example, the source floor of a new
return's book date must be established by its real posting boundary; the kernel
does not invent or move that date.

The arithmetic is:

\[
F(e,b)=\max(0,\;\text{FUNDING}(e,b)-\text{NET}(e,b)),\qquad
D(e,b)=F_{after}(e,b)-F_{before}(e,b).
\]

Both source contributions are visible only when their economic date is at/before
`e` **and** transaction date is at/before `b`. A component is the mixed finite
difference of D across the previous economic and transaction breakpoints.
Components may be positive or negative. Signed compound additions may also
produce negative D and negative current K.

The output has these fields:

| Field | Meaning |
| --- | --- |
| `contract_version` | `ow04.pure-recognition-plan.v1` |
| `kernel_version` | `ow04-2d-difference-v1` |
| `before_source_sha256`, `after_source_sha256` | Digests of complete normalized source vectors |
| `before_events`, `added_events` | Exact normalized vectors, each sorted by ID |
| `support` | All before/added IDs and source hashes, sorted by ID |
| `components` | Nonzero signed recognition atoms, sorted by economic then transaction date |
| `net_current_k` | Signed sum of all atoms; also the upper-right current D |
| `has_recognition_effect` | Whether any atom exists, including net-zero histories |

Each component has `amount`, `economic_date`, `transaction_date`,
`previous_economic_date`, `previous_transaction_date`, and `corners`. The previous
date is null at its first axis breakpoint. `corners` contains exact two-decimal
strings `d_here`, `d_prev_economic`, `d_prev_transaction`, and `d_prev_both`.
The amount is `d_here - d_prev_economic - d_prev_transaction + d_prev_both`.
A missing-axis corner is zero. Nonzero components cannot have a transaction date
before their economic date. Gross positive component totals are not entitlement.

Hashes use the normalized vector sorted by `id COLLATE "C"`, serialized by
PostgreSQL `jsonb::text`, converted to UTF-8, then built-in SHA-256 as lowercase
hex. Object keys and money normalization therefore follow this SQL contract;
this is not an RFC 8785/ordinary JavaScript `JSON.stringify` hash. Array order and
equivalent money spellings do not change the digest. Every retained event,
including earlier returns and zero-effect inputs, remains in its dependency
fingerprint. Hash format validation does not prove the source hash is truthful.

## Capacity boundary

`ow04_pure_kernel.credit_capacity_v1(components jsonb, consumptions jsonb,
economic_date text, transaction_date text)` takes **all retained signed credit
components** and **all signed consumption/inverse events** relevant to the
capacity being checked. Each movement has exactly `id`, `amount`,
`economic_date`, `transaction_date`, and `source_sha256`, with the same scalar
validation as source events. IDs are unique across both movement arrays.
Positive components create credit; negative components extinguish it. Positive
consumptions use credit; negative inverse events restore it.

The helper computes cumulative credit minus consumption at each 2D breakpoint.
It returns `minimum_available`, the signed minimum over all pairs with economic
date at/after the proposed economic date and transaction date at/after the
proposed transaction date. The proposed pair itself is an inserted breakpoint;
the current upper-right pair is included. The result is not clamped to zero.
This checks the proposed movement's entire later orthant, not only current
credit, separate one-axis margins, or availability at its first date.

The result also contains `requested_pair_balance`, `current_balance`,
`source_prefixes_nonnegative`, `limiting_pairs`, both normalized movement vector
hashes, the proposed dates, `contract_version=ow04.pure-credit-capacity.v1`, and
the same kernel version. `source_prefixes_nonnegative` means all resulting
credit-balance prefixes are nonnegative, including earlier pairs outside the
proposed orthant. A false flag is a source consistency refusal for a caller;
it is not repaired merely because later capacity is positive.

A positive proposed consumption is arithmetically supported only when the
source consistency flag is true and its exact amount is at most
`minimum_available`. This condition does not prove an inverse is paired with its
real original, that a cohort belongs to the customer, that the source vector is
complete/current, or that refund cash/application rights exist. A fixture shows
that an unbound negative consumption can mathematically inflate capacity. A real
collector and immutable ledger admission must prove those facts under locks.
Rechecking through this helper alone cannot replace that boundary.

## Evidence and limits

`RESULT.json` records 57 passing results: 23 literal planning cases, 12 literal
capacity cases, 17 malformed input refusals, one compound protocol/immutability
control, and four capacity input refusals. The driver independently reconstructs
all 2D prefixes with JavaScript BigInt cents, verifies each component's four
corners and both dated margins, and compares capacity with a full later-orthant
scan. It also checks complete vector hash dependencies, input-order invariance,
exact cents beyond JavaScript numeric precision, session date/time-zone
independence, and immutable invoker metadata.

This evidence does not exercise Native journal posting, stock/HPP, account
validation, cash-date balances, permissions, UUID-only admission, transaction
atomicity, concurrency, dependency reversal, or UI workflows. It is a portable
arithmetic proposal for review of the whole OW04 feature.
