# Writer B takeover — 26 October 2026 WIB

Owner asked the new writer to recover the complete context of **Writer B** and
continue without questions. This is the active B entrypoint. Earlier checkpoints
in `HANDOFF_PRODUKSI_CLAUDE_20261023.md` remain history, with their failures intact.

## Business and non-negotiable behavior

VENI. VIDI. VICI. ERP. Reliable data adalah dewa. Keuangan termasuk laporan,
stok, dan HPP adalah raja. Owner runs garment manufacturing and wholesale;
the result must be usable by a non-programmer on a phone.

- Materials/rolls → flexible cutting groups → contractor sewing → laundry
  delivery/receipt → QC good/BS/stuck → FG → POS/customer invoice. Returns,
  rework, compensation, late invoices and corrections have downstream effects.
- One product usually represents three physical sizes; sizes and conversions
  stay explicit. A physical piece of WIP cannot supply several SKU targets.
- One daily invoice per store can remain open until posting at night; stock
  movement is immediate. Store access is isolated. Partial AR/AP and harmless
  cents must work without cross-offsetting documents.
- Material moving average, labor/accessory allocations, laundry GRNI/AP,
  retroactive invoice variances and actual HPP are financial truth owned by A.
  B must consume the official finance module, never invent alternative profit.
- Contractor Epi/Selo/Afat require attendance; Afui is exempt with different
  rates. Laundry invoices can arrive months after receipt. Rework pays only new
  work. BS/stuck/returns must remain visible in quantity and cost provenance.
- Posted history is immutable; correction/reversal appends a lineage. Latest
  corrected truth wins while filed snapshots survive. Physical time and input
  time are distinct; deterministic chronology, Jakarta business days, current
  access after waits, atomic effects, idempotency and fail-closed rules remain.
- Unknown data stays unknown. No silent rounding, fabricated configuration,
  forecast, completeness or policy value; no double stock/WIP/plan/buffer count.

Authoritative detail: `AGENTS.md`, `CLAUDE.md`, `docs/ERP_BEST_PRACTICES.md`,
`OWNER_DECISIONS_20261008.md` (especially D17-9/D17-14/D17-15/D17-16), and
`PEMBAGIAN_DUA_PENULIS_20261022.md` version 2. The older role split is superseded.

## Exact lane and present scope

Repository `Hanjay6688/-erp-garment-ux`; only B publication branch
`astra/d17-14-produksi`. Inherited head **712e01285c525f61de402b949de74201029d6cc6**.
The old checkout and all untracked work were preserved. The new isolated worktree
is `/workspace/scratch/b6947bc7a657/erp-writer-b` in the same Git object store.
No agents added. A remains the single integrator.

| B work | Required behavior | Remaining acceptance boundary |
|---|---|---|
| OW16 | Automatic completed-cut status by fabric + pattern + size range, factory-wide history; no WA | Component16 evidence exists; configured production values/default integration remain separate |
| OW10 | One target/reorder engine; distinguish when to start from how much; explicit stock/WIP/plan allocation and buffer | Exact caller/source integration and combined acceptance |
| OW11a | History-tested method selection with explained basic fallback | Actual activation requires approved policy and sufficient evidence; no invented winner |
| OW11b | Candidate similar products, explicit confirmation/scale/reason, labeled comparator estimate or insufficient data | Prepared readers/choice/UI/Auth evidence is source-bound; default adoption and combined acceptance open |
| OW12b | Faster factory analysis without changing results, calling A's official finance bridge | Complete factory/finance/after-use/default integration; previous8s failures remain open |
| OW13a | Start once when minimum data/config ready; explain missing inputs; no unchanged repeat | Combined/default qualification |
| OW13b | Yield history above200 groups | Component20 evidence exists; integration acceptance separate |
| OW13c | Same-engine cutting suggestion, dated source, editable quantity, fresh feasibility/access check at SAVE | Corrected frozen checked-cut Native6/Transport10 and complete actual UI flow pending |
| OW14a/b | Shared warehouse/formula source; legacy minimum reference and one explicitly active rule | Component99/113 evidence exists; A owns default install/legacy inventory steps |

A owns money/stock/HPP/reports, OW06/07/08/09/12a/15, shared registries/types,
default installation and final integration. B edits only allocated code; requests
to A are in `d17-14/KOORDINASI.md`. Shared docs need a separate `[bersama]` commit.
Never write main, frozen audit55c885d1, CP6/Native frozen sources, Enteng/hosted,
production or real WA. Formal overall completion stays **5/16**; independent
acceptance and production permission remain false.

## New complete Originals read during this takeover

All JSON files, ZIP byte/hash/CRC, exact committed source pins and declarations,
original case budgets, package gates, full Native boundaries/current public
catalog, CP6/advisors, WIB/session/Auth cleanup were checked. The three database
reports also match their exact old F05 source-only prefix; no database was run
by that comparison. Compact receipts are in `d17-14/ow12b/*takeover-original.json`.

- `ffc775d0`, run40227891855/job121273111656/art12614021677: Choice Native6 PASS6.
  Actual1200SKU×3sizes,3602compiled targets, cached/K3 SAVE4722.703/6840.128ms.
  These observations do not close earlier timeouts, prove a stable SLA or include
  official finance. Earlier98c/c1/ab failures remain retained.
- `712e0128`, run40230455121/job121280835136/art12613332417: controlled cutting
  Browser4 PASS4,61 actual module pins; existing form, desktop/mobile, real
  storage events and denied-replay recovery. Both original images inspected.
  Identity/RPC are controlled; no real Auth/Native SAVE credit.
- `716dc627`, run40229609556/job121278304478/art12613293073: controlled analog
  Browser4 PASS4,39pins. Desktop candidates and mobile review inspected; actual
  Auth-host visual repair still requires its own result.
- `ffc775d0`, run40227891688/job121273111013/art12613451656: checked cutting
  Native6 INCOMPLETE1PASS/5INCOMPLETE,94pins. All substantive cases stop in
  fixture preparation at null needed_pcs before actual SAVE.
- `6f69b761`, run40228962122/job121276369533/art12613568855: checked cutting
  Transport10 INCOMPLETE1PASS/9INCOMPLETE,97pins, same fixture failure before
  lock waits/HTTP flow. All six clone authority receipts and cleanup exact.

Full Originals are private; no raw bulk evidence or screenshots were added to
the public repository. First failure receipts retain writer_runtime=false.

## Current repair and immediate continuation

The inherited fixture reviewed work through legacy supply capture. Frozen v2
has a distinct work fingerprint. `reviewed_capture` now reviews the **same**
selected calendar using actual public frozen request/workspace/schedule SAVE,
requires exact saved config and unchanged physical hashes/reference, and starts
a **new** actual analysis after review. Native and transport share this helper.
Unknown needs are never replaced with numbers. Added null diagnostics preserve
the complete options/recommendation when preparation is still invalid.

Only two test-provider Python files and their two closed source declarations
change. Product SQL, math, guards, role grants, 8s timeout and every previous
case ID/expectation remain unchanged. Local preflights PASS94/97pins with98
missing/mixed routes refused each; changed transport budgets5 refused. Client
and form tests **134/134 across10files**; full app and prepared cutting TS PASS.
This is preparation, awaiting its own corrected Native6/Transport10 Originals.

Publish the correction with a non-forced expected-head lease on B only; retain
the exact candidate and read complete results. Continue other pending B proofs
while actual jobs run. Do not rerun an unchanged source just to obtain green.
The inherited712 head has choice/quantity/cutting/Auth runs queued; newer code
does not qualify those old jobs automatically. Reconcile each exact source.

Pending inherited runs include cutting Native6 run40230455064, choice Native6
40230455082, quantity UI40230455089, analog UI40230455109, actual choice
Auth40230455148, actual quantity Auth40230455055 and corrected transport
94a5b766/run40229831311. These still use the old cutting fixture where relevant;
do not discard their eventual first outcome or claim the new repair ran there.

Then continue actual source-bound recovery/access/visuals, measured factory
performance, full cutting UI and A integration boundaries. Checkpoints save work;
they are not a reason to stop or ask the owner to repeat 'continue'.
