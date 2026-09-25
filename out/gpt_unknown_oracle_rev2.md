# Unknown-data retry rev2

## Unknown-data browser retry prepared — only two unresolved cases

CP6-05 native result committedcf01a09. Retry only Laundry/QC unknown2; keep original cases/INCOMPLETE. New manifest `audit/scenarios/unknown_round8/MANIFEST.json`: browsercf9dfb1e153bfd61dc660f23221de03ec5c000c3750690d9c51cb6e8c4020300; fixture0bd506536d68292dd957ecc6385c0b8967e6a807c35bd9d49f40b42b94359e1b. Exact workflow browser path validated locally before push.

Revision adds captured initial KPI/error and post-refetch response/UI error even when positive control fails. It also removes the fixture helper's unnecessary extra FG SKU: the GOOD-only laundry/receipt chain needs no product creation, while frontend parser forbids overlapping SKU identities (laundryQcModel.ts:628–650). This is a setup refinement, not a claimed diagnosis of rev1's missing error details, and not a product/guard/oracle change. Same real10pcs work→sewing→laundry/receipt commands, restored schema grants, actual Auth read, same unknown-vs-zero oracle. Scenario doc `out/gpt_unknown_oracle_rev2.md`.

LANGKAH BERIKUTNYA: capture push run/job IDs, record both results and cleanup. If control still fails, use retained UI/RPC diagnostic to locate cause; do not convert INCOMPLETE into product proof. CP6 HOLD.


Original oracle remains `out/gpt_recovery_unknown_oracle_freeze.md`, cases3–4. Rev2 does not rerun the two confirmed CP6-05 cases. A valid refetch must still render the real nonzero value; failed positive control remains INCOMPLETE and now preserves its diagnostics. No direct stock/value manipulation, no disabled validation, no browser response success fabricated.
