# P01 — contract lock and fixture charter

Status: contract and fixture charter ready for family 1 review. Native planning/WIP engine oracles remain NOT_RUN in their downstream packets. Dependency: P00 receipt and source catalogue; independent acceptance remains pending.

## Locked inputs

The unchanged v2 shape, TypeScript types, reasons and examples are in `framework-v2/contracts/`. `scripts/cp7_contract_receipt.py` verifies all 48 original digests and exact parity with the S0 contract copies. It never edits the source bundle. The requirement/case crosswalk remains the original 271 groups and 84 cases; owner delta rows overlap those groups.

The current `AnalysisResult` example declares `SYNTHETIC_CONTRACT_ORACLE`. It is not a live transport contract. P02 must introduce an explicitly versioned live envelope and validate untrusted payloads before any consumer receives them. A TypeScript cast and `assertFixtureCoherence` are insufficient. Do not silently change the meaning of the v2 fixture discriminant.

## Independent fixture charter

| Case | Fixed oracle from owner framework | Required proof still outstanding |
|---|---|---|
| O01 | FG18, target48, directed12, candidate10 → base18 / conditional8; FG stays18 | Native engine returns the same values with source trace |
| O04 | One shared60 source, gaps42+30 → allocations42+18; second gap12 | Same capacity after filters, alternative scenarios isolated |
| O15 | Parent100 → WIP80 + FG15 + BS5 | Native lineage normalization; document counters never summed as fresh supply |
| X07 | PCS0.5 refused; valid money/meters preserve scale; signed loss allowed | Input, SQL and response boundaries with exact decimals |
| E22 | Read/compute/export/ACK cannot change operations | Actor with poisoned mutator grants; before/after rows, counters, journals and locks |

Expected results are retained from the owner framework. Do not generate them using the production computation under test. A fixture identifier must map to the independent source/oracle hash, run identity, expected/actual values, cleanup and remaining limits.

## Permissions and fact semantics

- One server result feeds all consumers. S0 OWNER/OPERATIONS toggles are presentation examples, not authentication or authorization.
- Map current active actor and existing permission catalogue to a server allowlist. Unresolved capabilities default to denied. Recheck on initial read, cached replay, export, report and apply; no service-role client.
- The audited S0 fix withholds both metrics and plan comparisons for OPERATIONS. Any new financial field, prose, ranking or reference must enter the same server classification before exposure. Client removal is not the permission boundary.
- UNKNOWN, CONFLICT and NOT_APPLICABLE retain their reasons. Decimal strings remain exact; quantities never default to zero after missing/malformed reads.
- Physical root/size/lot and dated commercial SKU membership remain distinct. Source counts and timestamps alone do not establish complete history or a stale vector.
- Native P00 catalogue records actual function definitions, ACLs and triggers. Its textual PL/pgSQL call candidates require review before being used as a dependency map.

## Next deliverable

Resolve the minimum P02 source set against the native catalogue, then define the live capture envelope, quality/completeness, authorization projection, immutable fact keys and dependency vector. Keep R10/P11 and mandor payroll/P12 visible in the packet ledger; they are not closed by shell or contract checks.

## P01 implementation delta

`tests/cp7/sourceProbeContract.ts` validates the first diagnostic live-source shape separately from the unchanged synthetic `AnalysisResult`. It checks six complete source pages, root/exact size, unique source keys, signed movement versus unsigned PCS, exact decimal IDR, missing HPP as UNKNOWN, one statement cutoff and microsecond future knowledge. It rejects extra fields in the diagnostic tests; it is not wired into the application until there is an authorized server consumer. This parser validates transport shape; it cannot authorize an actor or verify the database snapshot hash as a cryptographic signature. The P02 query remains internal to the disposable runner. Independent O01/O04/O15 engine outputs and E22 actor proof remain NOT_RUN.

At `67f3b0f`, ten local negative/shape tests and the [CP7 shell CI](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36480942635) passed. The [P02 native diagnostic](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36480942787) passed its first source fixture; this does not satisfy the P01 engine or authorization oracles in the table above.

## Family 1 actor delta

The [P02 actor family](P02_FACADE_HANDOFF.md) now provides server authorization, immutable persisted runs, real Auth/HTTP, source-change and concurrent-capture evidence at `735056db3b42cc7fc3999149b42e2cadac7b42b2`. It supplies the bounded capture/poisoned-principal portion of E22; export, ACK and downstream consumers retain their own open obligations. The original diagnostic decoder remains a diagnostic contract and is not silently reused for the versioned actor page envelope. No application consumer has been connected by this work. O01/O04/O15 engine outputs must be verified when those engines exist; their expected values remain locked above.
