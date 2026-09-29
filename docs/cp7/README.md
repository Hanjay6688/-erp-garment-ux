# CP7 — entry after accepted CP6

Active branch: `cp7/integration`. Owner has instructed implementation to start.

**Keuangan (termasuk laporan), stok dan HPP adalah raja. Reliable data adalah dewa.**

## Read in this order

1. [Current state](CURRENT_STATE.json) and [entry receipt](P00_HANDOFF.md).
2. [Combined auditor handoff](acceptance/HANDOFF.md), [scope decision](acceptance/CLOSURE_R10_SCOPE.md), [evidence](acceptance/evidence.json).
3. [Owner rusuk](framework-v2/06_RUSUK_KEBUTUHAN_OWNER.md).
4. [Backbone](framework-v2/02_BACKBONE_TEKNIS.md) and [start runbook](framework-v2/05_RUNBOOK_MULAI_CP7.md).
5. [Complete framework](framework-v2/CP7_Framework_Lengkap_20260928.md), [22 work packets](framework-v2/registries/work_packets.json), [requirements](framework-v2/registries/requirements.json), [84 cases](framework-v2/registries/cases.json).
6. [Source map](source-map.json); shell in `src/cp7/`, contract and oracles in `docs/cp7/contracts/` and `framework-v2/contracts/`.
7. [P01 contract lock and fixture charter](P01_CONTRACT_HANDOFF.md), then [P02 source capture handoff](P02_SOURCE_HANDOFF.md) and [actor facade proof](P02_FACADE_HANDOFF.md).
8. [Six-family delivery plan](FAMILY_PLAN.md), [family 1 auditor checkpoint](F01_AUDITOR_HANDOFF.md), and [family 2 P03 contract](P03_IDENTITY_HANDOFF.md).

## Current scope

CP6 is CLOSED for the accepted contract. R10 remains an obligatory CP7/P11 connected sales/return browser flow. Production GO remains false. CP7 has started with receipt, shell integration and database source discovery; its operational engine is not connected yet.

Original framework documents are imported byte-for-byte. Their earlier HOLD/null/preparation-only fields are historical and are superseded by CURRENT_STATE.json, the final audit and the owner's start instruction. Prior test reports retain their original scope; no old NOT_RUN becomes a PASS by importing files.

The accepted S0 shell includes the audited financial projection fix. Six consumers still use the same typed example and no operational command is enabled by a successful example read. Independent final evidence is required for new runtime work.

The bounded P02 actor family is writer-verified at `735056db` (16 cases). Family 1 independent review is pending; family 2 implementation has started under the owner’s continuation instruction. See the checkpoint for exact scope and evidence.
