# P19 UTF-8 receiver bounds — 6 October2026

Source before repair: `e724c521de04e9e6c12ef3d799dc3d723f83e37b`. The completed UI/catalog/loading checkpoint remains pinned to its qualified product source56c48b6e; this is a separate frontend receiver change, not a relabel of that qualification.

## Reproduced defect

`parseNativeAnalysis` and copied Native financial documents counted JavaScript UTF-16 string units with `.length`, while SQL source bounds use UTF-8 bytes. A multibyte analysis of8,000,001 bytes and financial documents over9MB passed those supposed8MB guards. The complete condition-row receiver also lacked the producer's8MB row budget. Historical observation recovery needs its own document guard because its current source can be small while the retained earlier document is oversized.

The initial six adversarial receiver cases produced3 PASS/3 failures of expected refusal. A seventh predeclared historical-recovery case produced3 PASS/4 such failures, with a successful small-receipt positive control before the oversized historical document. Both complete first reports and exact test sources remain at `../evidence/p19/utf8-receiver-before-e724`. These are receiver stand-ins, not Native money/Auth, production data or volume qualification; zero Native case credit is added.

## Repair and qualification

- Analysis and copied financial documents now count the UTF-8 encoding of their complete serialized JSON against the same8,000,000 budget.
- Complete condition rows receive the same byte guard before per-row parsing or returning a usable source. Their15,000 row limit, exact completeness/count/coverage checks and current rights still apply.
- Historical receipt conditions use the corrected financial-document guard as well. The positive small historical receipt still parses; the oversized receipt is refused independently of the current source's row budget.
- Exact8,000,000-byte ASCII and multibyte analysis bodies still preserve their whole contents, quantities and labels. A whole under-budget Unicode condition source retains its Native financial document and current-AR-right refusal. There is no clipping, successful partial source or higher cap.

Local qualification passes all38 cases across analysis, rule source, both report receivers and the seven new capacity cases. Full local report and source hashes are retained separately. Local production build/typecheck,271 runtime/201 RPC ownership,111 permission/48 route/21 action ownership,53 CSS and client secret scan pass. The first local build reproduction is also retained: the Node-only byte oracle was initially under the browser compiler and the raw fixture financial document needed an explicit type. The seven assertions now live in the existing Node test lane `tests/cp7/nativeSourceCapacity.test.ts`; no compiler settings or assertion are weakened. Actual affected Native/Auth/browser qualification must still pass on the published candidate before writer qualification is declared. SQL producers, frozen analysis schema, Native financial formulas,15000/4000 entry limits,250000 nodes/depth30 and request/response recovery contracts are not changed.

## Capacity still open

This correction closes a byte-accounting defect. It does not transport or enable the30.97MB/5000-target source, prove factory-wide loading, or turn the source-stand-in13.15s kernel into a Native capture. Complete source segmentation/background computation still needs immutable run/request/hash binding, complete assembly, current authority and all declared large-source lifecycle proofs. Owner budgets remain routine<1s, ordinary save≤2s and heavy foreground work≤3s with progress. Full P18/P19/P20/P21 and production GO remain open.
