Independent bounded trigger-catalogue counter, read only

The current integrated fix resolves the one concrete transition defect found after the independently locked initial assessment. No further deterministic blocker was found in the inspected install, verify, Native entry/completion, and uninstall catalogue paths. This is source/metadata review with pure Python synthetic controls, not PostgreSQL17.6 or Native execution.

TG-C1 — preserved predecessor identities

The original `expected_transition` compared rows only for OID keys present in both snapshots. It therefore accepted recreating an already existing FK and its internal RI triggers with new OIDs/names, while keeping the same source semantics. It also accepted replacing only those RI attachments. This contradicted the function promise that existing constraints and attachments retain their identities.

Root corrected the actual product guard at `scripts/cp7_customer_credit/integration/source_triggers/trigger_guard.py:191-203`: for every common source-semantic FK, the complete actual FK and associated internal-trigger rows are compared as Counters. The exact original counterexample now refuses with `PREEXISTING_FK_OR_RI_RECREATED`. The RI-only variant refuses too. Clean predecessor→OW04, OW04→Native EMPTY, and Native EMPTY→predecessor transitions still accept in the explicitly synthetic models. The first accepted-bad and corrected outputs are preserved separately.

Inspected integration sequence

`owning_bundle.install` first verifies the complete predecessor, captures all selected-table triggers as postgres under empty search_path, and validates the source-owned predecessor census. After complete composition it validates the phase transition before rendering the callable guard. Native EMPTY adds only its exact second phase and gets a newly rendered guard. Each phase stores the complete accepted actual catalogue snapshot; normal verify demands exact equality, including OIDs, raw pg_proc fields, definitions and ACLs. Uninstall restores the approved original functions first, removes new private schemas, validates the reverse source-owned phase, then requires exact equality with the original predecessor capture.

The runtime renderer hashes the actual catalogue using the same PostgreSQL `cp7_credit.pg_jsonb_sha256` helper used by the installer on the already source-validated snapshot. It does not substitute Python JSON hashing for PostgreSQL jsonb canonicalization. Complete raw snapshots remain available in state. The request-entry call precedes source effects. The second call in `source_operation_native_complete_v1` occurs before the final Z snapshot/completion is recorded.

Source census and boundaries

The declared FK counts are99/117/119, deriving210/246/250 RI attachments on the six selected ERP tables. Trigger capture has no enabled/internal filter; unknown, disabled, or replica-only attachments refuse. RI SQL identity qualification, internal C entry-name binding, check/action trigger event types, counterpart relation and noaction-only deferrability show no mismatch in this closed source set. Selected names are fixed lowercase qualified relation/function identities; the raw RI identity is compared as text rather than executed as an unquoted SQL identifier.

The source parser is intentionally incomplete. Pure controls demonstrate that an unnamed ALTER ADD FOREIGN KEY and DDL inside a dollar-quoted dynamic block yield no extracted FK; NOT followed by a newline before DEFERRABLE is also misread. Current newly relevant FK declarations use the recognized direct inline CREATE TABLE grammar, and any omitted actual FK/trigger still fails the exact live census. Do not generalize the parser to arbitrary dynamic SQL or regard masked code as absent executable behavior.

Accepted P00 evidence identifies PostgreSQL17.6. The inspected capture uses PG17 catalogue fields; there is no explicit live server-version gate. No PG18 compile result is evidence of PG17.6 Native behavior. ROW EXCLUSIVE locks protect selected tables against conflicting trigger/table DDL; they are not locks against privileged concurrent pg_proc edits or proof of an entire dynamic call graph. These limitations remain explicit.

At the final bounded source read, root was still regenerating repository pins after the guard changes; only owning_bundle.py and reconciliation/06_source_coordinator.sql differed from their pinned versions. The guard must refuse these stale pins until root regenerates the final manifest. Do not relax equality.

Evidence

- INITIAL_ASSESSMENT.json: independently locked before any current reviewer conclusions.
- ACCEPTED_BAD_REPRO.json: original defect reproduced without DB.
- CORRECTED_REPRO.json: root fix gives five of five expected results.
- repro_common_fk_recreation.py: reproducible pure controls; no SQL execution.
- FINAL_SOURCE_RECHECK.json: exact reviewed file hashes, phase results and pending pin refresh.

No database, network, Native fixtures, shared product changes or nested agents were used in this counter.
