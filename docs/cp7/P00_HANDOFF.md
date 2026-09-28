# P00 entry receipt and working handoff

## Base and authority

- Owner: start CP7 following combined CP6 acceptance in the current conversation.
- CP6 document base: `10a834712e515af86c6d8baa89bbe40cff9793e3`; product fingerprint: `434b18215f57dd7a361ca621341488d3c31e9703`.
- Auditor decision: `761f1bf33199519205248947b5fe2d86e25b2fa0`, copied unchanged under [acceptance](acceptance/HANDOFF.md).
- Accepted S0: `fa0ed346c322b8f24924f19f3a39f4117e6a0068` (PR31), imported over the accepted CP6 rather than using its earlier CP6 ancestor.
- Immutable original backbone archive SHA256: `184ef050b6462dbdde96cfc00a824a3978afbbfc80559f06c115cf92a45af6de`; all 48 listed file digests verified. The separate complete framework MD is also retained.
- Single writer in this session uses `cp7/integration`. Before publishing, recheck its ref and the known writer branch. A push can be observed; writing in another chat cannot be stopped by this repository workflow.

## Scope disposition

CP6 CLOSED_CONTRACT_SCOPE; production_go=false. Conversion history and CP7-DELTA-01 are closed within accepted proof. R10 stays OPEN_CP7 in P11: real browser → authenticated facade → database → readback for sale, cancellation/return and applicable cash effects. Do not substitute mocked shell tests for R10.

The vendor is the tariff authority. SKU wash history only assists selection. Empty cost remains UNKNOWN until invoiced; FREE/WAIVED needs explicit reason. Supplier/laundry credits can be split/reallocated within the same counterparty without reducing AP twice. Physical size, lot lineage and historical commercial identity remain distinct.

## Implemented entry work

1. Imported the complete original framework/backbone/rusuk, packet/requirement/case registries and oracles.
2. Applied the accepted S0 shell patch to accepted CP6 with a three-way merge. Updated stale CP6-HOLD labels and command refusal reason; kept connection/apply/publish/delivery gates false.
3. Added a P00 discovery runner and isolated native CI. It installs the unchanged accepted 30-file package with existing hash/ACL/advisor/restore gates, then captures functions, signatures, body hashes, ACLs, relations/columns/RLS, policies, triggers and six existing reader identities in one read-only repeatable-read transaction.
4. Read-only refusal is tested with a no-row DELETE; the business boundary must be identical before/after. PL/pgSQL textual calls are explicitly incomplete candidates, not a certified dependency graph.

## Evidence and limits

P00 native discovery passed on 5e227c4: 1009 functions, 409 relations/views, 531 user triggers, 190 policies. Six existing facade signatures resolved. The no-row write control refused with SQLSTATE 25006; business and primary database boundaries stayed unchanged. The 30-file install, existing advisor gate and backup/restore passed. Raw advisors remain REVIEW_REQUIRED for the previously accepted INFO class; this is not zero findings.

The same source passed 623 unit/DOM tests, 6 shell browser tests, build, security and both CodeQL languages. See [verification receipt](evidence/p00/VERIFICATION.json); the full captured catalogue is preserved as a deterministic gzip beside it. Native catalogue output is CP7_P00_CATALOGUE.json; compact result is CP7_P00_RESULT.json in the workflow artifact. This is administrative source discovery on an isolated database. It does not prove the future analysis actor permissions, coherent business facts, WIP/forecast correctness or R10.

P00's E14/E21 links preserve accepted predecessor evidence. New CP7 facade authorization and CP7 installation/recovery tests remain required in their implementing packets. Original 84 case contracts retain their own NOT_RUN status until exercised; shell/offline contract counts are reported separately.

## Next implementation

P01: resolve facts to the captured source catalogue; lock the contract, permission projection, reasons/metrics, fixture charter and requirement crosswalk. Then P02: persist one coherent authorized snapshot with completeness/dependency/known-at semantics. Keep missing source history AS_KNOWN_UNAVAILABLE. P09–P13 operational gaps, especially R10/P11 and mandor payroll/P12, remain explicit obligations.
