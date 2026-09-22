# CP6 initial-data import — proposed transport, native trial pending

VENI. VIDI. VICI. ERP. — I CONQUERED ERP.
Reliable data adalah dewa. Keuangan—termasuk laporan—stok, dan HPP adalah raja.

Continuation from `3767458fa571f3a6f8e20945ccd01bd7ce1ab47c` on the single writer branch. Owner decisions remain in `docs/cp6-ao-ap-owner-decisions.md`. CP6_HOLD; production_go: false; CP7 not started.

The proposed page uploads actual UTF-8 CSV/TSV files, keeps numeric text exact, offers editable rows and per-row validation, and uses the existing global writer lock and durable idempotency envelope. A revision fingerprint binds every action to the server draft. Finalization validates the latest locked rows and invokes the admitted master, open-PO and opening-balance writers in one transaction. Lost responses replay the same UUID and payload. Stale editor contents are retained visibly but cannot overwrite a changed server draft.

Opening detail rows require `control_key`. `OPENING_CONTROL` rows compare quantity and the sum of each posting line rounded to cents. They never create opening items, stock or journal entries. Missing, duplicate and mismatched controls prevent finalization. Replacement CSV files replace only the selected entity inside the unposted batch.

Scope is still **all initial data**, per the owner's approval. This first connected contract exposes the 12 existing domain types plus reconciliation controls. Laundry vendors, locations/accounts as newly imported masters, advances, uninvoiced receipts, partly settled documents and physical WIP per size still require complete domain mapping and implementation. Existing WIP opening posts value only; the proposed transport does not claim physical WIP support. Invoice-date propagation and manual retail pricing remain AO work. No historic invoice, quantity or price is rewritten by this patch.

Local verification: TypeScript compile clean; 58 targeted parser, connected-form and recovery tests pass. Source/access/CSS checks are required before checkpoint. The new native workflow reconstructs exact AC through AN from frozen code and runs proposed functions in one transaction which is rolled back, including fixture data and permissions. This is a writer trial, not an installed migration, independent acceptance, hosted change or production release. Earlier generic pipeline failures at the source gate remain failures and are not recast as business-test results.
