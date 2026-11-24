import type { AnalysisResult } from './contract'
import { planningResults } from './examples/planning'
import { exampleSupply } from './examples/supply'
import { exampleTimeline } from './examples/timeline'

// Exact framework v2 example. Synthetic only; never a connected fallback.
export const frameworkExample = {
  "contract_version": "cp7.analysis.v2",
  "fixture_kind": "SYNTHETIC_CONTRACT_ORACLE",
  "run_id": "fixture-O02-run1",
  "status": "COMPLETE",
  "snapshot": {
    "snapshot_id": "fixture-O02-snapshot1",
    "effective_as_of": "2026-09-30T23:59:59+07:00",
    "known_as_of": "2026-09-30T23:59:59+07:00",
    "generated_at": "2026-10-01T00:01:00+07:00",
    "timezone": "Asia/Jakarta",
    "knowledge_mode": "CURRENT",
    "capture_complete": true,
    "fact_count": 7,
    "source_hash": "73ecf7d2f36750f89cd2d41db9e19e40ffce23612e81716035e4c8744938391e"
  },
  "versions": {
    "engine": "proposed-v1",
    "policy": "fixture-only-L7-R3-B2",
    "models": "baseline-daily4",
    "template": "id-v1",
    "access_epoch": "fixture-owner-epoch1"
  },
  "scope": {
    "actor_scope_id": "fixture-owner",
    "allocation_scope_id": "fixture-whole-factory",
    "display_filter": "all"
  },
  "quality": {
    "quantity": "COMPLETE",
    "demand": "ASSUMED",
    "identity": "COMPLETE",
    "timing": "ASSUMED",
    "materials": "UNKNOWN",
    "capacity": "UNKNOWN",
    "financial": "UNKNOWN"
  },
  "scenario": {
    "id": "fixture-candidate10-new8",
    "version": 1,
    "kind": "CONDITIONAL",
    "assumption_ids": [
      "FIXTURE_POLICY_AND_ETA",
      "CANDIDATE_MATCH_AND_TIME",
      "NEW8_IS_HYPOTHETICAL_NOT_POSTED"
    ]
  },
  ...exampleSupply,
  timeline: exampleTimeline,
  ...planningResults,
} satisfies AnalysisResult
