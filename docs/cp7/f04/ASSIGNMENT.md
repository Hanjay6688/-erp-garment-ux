# F04 contribution — P05–P07

Owner assignment: 29 September 2026. Hansen asked this session to take F04
while the existing writer continues F03. This is a separate contribution lane,
not a second writer on the canonical integration branch.

- Base: `5da1fb6106c7c72058ebd73a782a5155f59c258d` on `cp7/integration`.
- Contribution branch: `cp7/f04-planning-20260929`.
- Scope: P05 demand/availability, P06 dated baseline/feasibility, P07 model
  kernels and chronological evaluation against frozen, explicitly versioned input.
- Owned source paths: `scripts/cp7-src/demand/`, `scripts/cp7-src/baseline/`,
  `scripts/cp7-src/models/`; dedicated tests under `tests/cp7/families/`;
  contribution documents/evidence under `docs/cp7/f04/`.
- No changes to F03, CP6, shared contracts, CURRENT_STATE, source/release
  manifests, permissions, UI, or existing CI dispatch/qualification rules.
- Integrator owns canonical wiring, dependency refresh, source capture and
  public authorization. Integration deltas are documented here for review.
- P08 apply is excluded until planning and P10 dependencies are qualified.
- Production and hosted installation are not authorized by this assignment.

The accepted CP6 receipt is `10a834712e515af86c6d8baa89bbe40cff9793e3`.
CP6 is CLOSED_CONTRACT_SCOPE in the current integration state; earlier S0 HOLD
text is historical. F01/F02 independent acceptance and the composed X06
planner authorization/stale boundary remain open in the pinned state.

The original 48 framework digests and numeric oracles remain immutable.
Internal computation inputs added in this lane are versioned private contracts;
they are not claimed to be an already implemented CP6/F03 reader or public API.
There is one SQL implementation of business calculations, with all operational
roles denied direct execution. Test adapters do not implement another engine.

Expected tests cover O01–O12/O16/O17/O19/O20 and M/X model, timeline, and
matching cases relevant to these packets. A kernel PASS closes only the tested
numeric boundary; native source/Auth/browser/integrated cases keep their own
open statuses. Family-wide or independent acceptance is not claimed here.

State: PRIVATE_KERNEL_WRITER_PROOF. 138 local synthetic
kernel/ACL cases passed before submission, alongside the existing 716 Vitest
tests, static security checks, build and 48-file contract receipt. Native CI
and final source-bound evidence are recorded separately in this directory.
This does not change the integrator's CURRENT_STATE or close family acceptance.
