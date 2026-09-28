import type { AnalysisResult } from './contract'

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
  "sources": [
    {
      "source_key": "fixture-batch-directed:size30",
      "size_id": "30",
      "stage": "LAUNDRY",
      "supply_kind": "DIRECTED",
      "physical_remaining": {
        "state": "KNOWN",
        "value": "12",
        "unit": "PCS",
        "refs": [
          {
            "kind": "WIP",
            "id": "directed",
            "revision": "fixture-r1"
          }
        ]
      },
      "eligible_projected": {
        "state": "ASSUMED",
        "value": "12",
        "unit": "PCS",
        "refs": [
          {
            "kind": "WIP",
            "id": "directed",
            "revision": "fixture-r1"
          }
        ],
        "assumption_ids": [
          "FIXTURE_POLICY_AND_ETA"
        ]
      },
      "allocated": {
        "state": "KNOWN",
        "value": "12",
        "unit": "PCS",
        "refs": [
          {
            "kind": "SCENARIO",
            "id": "directed",
            "revision": "fixture-r1"
          }
        ]
      },
      "eta": "2026-10-03T00:00:00+07:00",
      "eta_basis": "ASSUMED",
      "refs": [
        {
          "kind": "WIP",
          "id": "directed",
          "revision": "fixture-r1"
        }
      ],
      "eligible_input": {
        "state": "KNOWN",
        "value": "12",
        "unit": "PCS",
        "refs": [
          {
            "kind": "WIP",
            "id": "directed",
            "revision": "fixture-r1"
          }
        ]
      }
    },
    {
      "source_key": "fixture-batch-candidate:size30",
      "size_id": "30",
      "stage": "SEWING",
      "supply_kind": "CANDIDATE",
      "physical_remaining": {
        "state": "KNOWN",
        "value": "20",
        "unit": "PCS",
        "refs": [
          {
            "kind": "WIP",
            "id": "candidate",
            "revision": "fixture-r1"
          }
        ]
      },
      "eligible_projected": {
        "state": "ASSUMED",
        "value": "20",
        "unit": "PCS",
        "refs": [
          {
            "kind": "WIP",
            "id": "candidate",
            "revision": "fixture-r1"
          }
        ],
        "assumption_ids": [
          "FIXTURE_POLICY_AND_ETA"
        ]
      },
      "allocated": {
        "state": "ASSUMED",
        "value": "10",
        "unit": "PCS",
        "refs": [
          {
            "kind": "SCENARIO",
            "id": "candidate",
            "revision": "fixture-r1"
          }
        ],
        "assumption_ids": [
          "FIXTURE_POLICY_AND_ETA"
        ]
      },
      "eta": "2026-10-06T00:00:00+07:00",
      "eta_basis": "ASSUMED",
      "refs": [
        {
          "kind": "WIP",
          "id": "candidate",
          "revision": "fixture-r1"
        }
      ],
      "eligible_input": {
        "state": "KNOWN",
        "value": "20",
        "unit": "PCS",
        "refs": [
          {
            "kind": "WIP",
            "id": "candidate",
            "revision": "fixture-r1"
          }
        ]
      }
    }
  ],
  "recommendations": [
    {
      "target": {
        "kind": "PRODUCT",
        "key": "fixture-vivo:A:30",
        "brand_id": "fixture-vivo",
        "product_id": "fixture-A",
        "product_version_id": "fixture-A-v1",
        "size_id": "30",
        "commercial_identity": {
          "state": "RESOLVED",
          "sku_id": "fixture-commercial-A",
          "sku_version_id": "fixture-A-economics-v1",
          "membership_version_id": "fixture-A-members-v1",
          "grouping_basis": "AS_KNOWN"
        }
      },
      "production_state": "ACTIVE",
      "actual_fg": {
        "state": "KNOWN",
        "value": "18",
        "unit": "PCS",
        "refs": [
          {
            "kind": "FG_LEDGER",
            "id": "fg",
            "revision": "fixture-r1"
          }
        ]
      },
      "target_qty": {
        "state": "ASSUMED",
        "value": "48",
        "unit": "PCS",
        "refs": [
          {
            "kind": "POLICY",
            "id": "L7-R3-B2",
            "revision": "fixture-r1"
          }
        ],
        "assumption_ids": [
          "FIXTURE_POLICY_AND_ETA"
        ]
      },
      "q_base": {
        "state": "ASSUMED",
        "value": "18",
        "unit": "PCS",
        "refs": [
          {
            "kind": "ANALYSIS",
            "id": "q-base",
            "revision": "fixture-r1"
          }
        ],
        "assumption_ids": [
          "FIXTURE_POLICY_AND_ETA"
        ]
      },
      "q_conditional": {
        "state": "ASSUMED",
        "value": "8",
        "unit": "PCS",
        "refs": [
          {
            "kind": "ANALYSIS",
            "id": "q-conditional",
            "revision": "fixture-r1"
          }
        ],
        "assumption_ids": [
          "FIXTURE_POLICY_AND_ETA"
        ]
      },
      "suggested_new": {
        "state": "ASSUMED",
        "value": "8",
        "unit": "PCS",
        "refs": [
          {
            "kind": "ANALYSIS",
            "id": "suggested",
            "revision": "fixture-r1"
          }
        ],
        "assumption_ids": [
          "FIXTURE_POLICY_AND_ETA"
        ]
      },
      "rounding_extra": {
        "state": "KNOWN",
        "value": "0",
        "unit": "PCS",
        "refs": [
          {
            "kind": "POLICY",
            "id": "pcs",
            "revision": "fixture-r1"
          }
        ]
      },
      "reason_codes": [
        "CANDIDATE_NEEDS_CONFIRMATION",
        "FEASIBILITY_NOT_PROVEN"
      ],
      "assumption_ids": [
        "FIXTURE_POLICY_AND_ETA",
        "CANDIDATE_MATCH_AND_TIME",
        "NEW8_IS_HYPOTHETICAL_NOT_POSTED"
      ],
      "feasible_new": {
        "state": "UNKNOWN",
        "unit": "PCS",
        "reason": "CAPACITY_NOT_PROVEN",
        "refs": []
      },
      "unresolved_qty": {
        "state": "UNKNOWN",
        "unit": "PCS",
        "reason": "CAPACITY_NOT_PROVEN",
        "refs": []
      }
    }
  ],
  "timeline": [
    {
      "date": "2026-10-01",
      "target_key": "fixture-vivo:A:30",
      "demand": {
        "state": "ASSUMED",
        "value": "4",
        "unit": "PCS",
        "refs": [
          {
            "kind": "ANALYSIS",
            "id": "fixture-timeline",
            "revision": "v2"
          }
        ],
        "assumption_ids": [
          "FIXTURE_POLICY_AND_ETA"
        ]
      },
      "directed_supply": {
        "state": "ASSUMED",
        "value": "0",
        "unit": "PCS",
        "refs": [
          {
            "kind": "ANALYSIS",
            "id": "fixture-timeline",
            "revision": "v2"
          }
        ],
        "assumption_ids": [
          "FIXTURE_POLICY_AND_ETA"
        ]
      },
      "candidate_supply": {
        "state": "ASSUMED",
        "value": "0",
        "unit": "PCS",
        "refs": [
          {
            "kind": "ANALYSIS",
            "id": "fixture-timeline",
            "revision": "v2"
          }
        ],
        "assumption_ids": [
          "FIXTURE_POLICY_AND_ETA"
        ]
      },
      "proposed_new_supply": {
        "state": "ASSUMED",
        "value": "0",
        "unit": "PCS",
        "refs": [
          {
            "kind": "ANALYSIS",
            "id": "fixture-timeline",
            "revision": "v2"
          }
        ],
        "assumption_ids": [
          "FIXTURE_POLICY_AND_ETA"
        ]
      },
      "balance_end": {
        "state": "ASSUMED",
        "value": "14",
        "unit": "PCS",
        "refs": [
          {
            "kind": "ANALYSIS",
            "id": "fixture-timeline",
            "revision": "v2"
          }
        ],
        "assumption_ids": [
          "FIXTURE_POLICY_AND_ETA"
        ]
      },
      "mode": "BACKLOG",
      "assumed": true,
      "unmet_demand": {
        "state": "ASSUMED",
        "value": "0",
        "unit": "PCS",
        "refs": [
          {
            "kind": "ANALYSIS",
            "id": "fixture-timeline",
            "revision": "v2"
          }
        ],
        "assumption_ids": [
          "FIXTURE_POLICY_AND_ETA"
        ]
      },
      "backlog_qty": {
        "state": "ASSUMED",
        "value": "0",
        "unit": "PCS",
        "refs": [
          {
            "kind": "ANALYSIS",
            "id": "fixture-timeline",
            "revision": "v2"
          }
        ],
        "assumption_ids": [
          "FIXTURE_POLICY_AND_ETA"
        ]
      },
      "min_intraday_balance": {
        "state": "ASSUMED",
        "value": "14",
        "unit": "PCS",
        "refs": [
          {
            "kind": "ANALYSIS",
            "id": "fixture-timeline",
            "revision": "v2"
          }
        ],
        "assumption_ids": [
          "FIXTURE_POLICY_AND_ETA"
        ]
      },
      "first_gap_at": null,
      "timing_basis": "DATE_POLICY",
      "timing_policy_id": "FIXTURE_ARRIVALS_BEFORE_DAILY_DEMAND",
      "event_refs": []
    },
    {
      "date": "2026-10-02",
      "target_key": "fixture-vivo:A:30",
      "demand": {
        "state": "ASSUMED",
        "value": "4",
        "unit": "PCS",
        "refs": [
          {
            "kind": "ANALYSIS",
            "id": "fixture-timeline",
            "revision": "v2"
          }
        ],
        "assumption_ids": [
          "FIXTURE_POLICY_AND_ETA"
        ]
      },
      "directed_supply": {
        "state": "ASSUMED",
        "value": "0",
        "unit": "PCS",
        "refs": [
          {
            "kind": "ANALYSIS",
            "id": "fixture-timeline",
            "revision": "v2"
          }
        ],
        "assumption_ids": [
          "FIXTURE_POLICY_AND_ETA"
        ]
      },
      "candidate_supply": {
        "state": "ASSUMED",
        "value": "0",
        "unit": "PCS",
        "refs": [
          {
            "kind": "ANALYSIS",
            "id": "fixture-timeline",
            "revision": "v2"
          }
        ],
        "assumption_ids": [
          "FIXTURE_POLICY_AND_ETA"
        ]
      },
      "proposed_new_supply": {
        "state": "ASSUMED",
        "value": "0",
        "unit": "PCS",
        "refs": [
          {
            "kind": "ANALYSIS",
            "id": "fixture-timeline",
            "revision": "v2"
          }
        ],
        "assumption_ids": [
          "FIXTURE_POLICY_AND_ETA"
        ]
      },
      "balance_end": {
        "state": "ASSUMED",
        "value": "10",
        "unit": "PCS",
        "refs": [
          {
            "kind": "ANALYSIS",
            "id": "fixture-timeline",
            "revision": "v2"
          }
        ],
        "assumption_ids": [
          "FIXTURE_POLICY_AND_ETA"
        ]
      },
      "mode": "BACKLOG",
      "assumed": true,
      "unmet_demand": {
        "state": "ASSUMED",
        "value": "0",
        "unit": "PCS",
        "refs": [
          {
            "kind": "ANALYSIS",
            "id": "fixture-timeline",
            "revision": "v2"
          }
        ],
        "assumption_ids": [
          "FIXTURE_POLICY_AND_ETA"
        ]
      },
      "backlog_qty": {
        "state": "ASSUMED",
        "value": "0",
        "unit": "PCS",
        "refs": [
          {
            "kind": "ANALYSIS",
            "id": "fixture-timeline",
            "revision": "v2"
          }
        ],
        "assumption_ids": [
          "FIXTURE_POLICY_AND_ETA"
        ]
      },
      "min_intraday_balance": {
        "state": "ASSUMED",
        "value": "10",
        "unit": "PCS",
        "refs": [
          {
            "kind": "ANALYSIS",
            "id": "fixture-timeline",
            "revision": "v2"
          }
        ],
        "assumption_ids": [
          "FIXTURE_POLICY_AND_ETA"
        ]
      },
      "first_gap_at": null,
      "timing_basis": "DATE_POLICY",
      "timing_policy_id": "FIXTURE_ARRIVALS_BEFORE_DAILY_DEMAND",
      "event_refs": []
    },
    {
      "date": "2026-10-03",
      "target_key": "fixture-vivo:A:30",
      "demand": {
        "state": "ASSUMED",
        "value": "4",
        "unit": "PCS",
        "refs": [
          {
            "kind": "ANALYSIS",
            "id": "fixture-timeline",
            "revision": "v2"
          }
        ],
        "assumption_ids": [
          "FIXTURE_POLICY_AND_ETA"
        ]
      },
      "directed_supply": {
        "state": "ASSUMED",
        "value": "12",
        "unit": "PCS",
        "refs": [
          {
            "kind": "ANALYSIS",
            "id": "fixture-timeline",
            "revision": "v2"
          }
        ],
        "assumption_ids": [
          "FIXTURE_POLICY_AND_ETA"
        ]
      },
      "candidate_supply": {
        "state": "ASSUMED",
        "value": "0",
        "unit": "PCS",
        "refs": [
          {
            "kind": "ANALYSIS",
            "id": "fixture-timeline",
            "revision": "v2"
          }
        ],
        "assumption_ids": [
          "FIXTURE_POLICY_AND_ETA"
        ]
      },
      "proposed_new_supply": {
        "state": "ASSUMED",
        "value": "0",
        "unit": "PCS",
        "refs": [
          {
            "kind": "ANALYSIS",
            "id": "fixture-timeline",
            "revision": "v2"
          }
        ],
        "assumption_ids": [
          "FIXTURE_POLICY_AND_ETA"
        ]
      },
      "balance_end": {
        "state": "ASSUMED",
        "value": "18",
        "unit": "PCS",
        "refs": [
          {
            "kind": "ANALYSIS",
            "id": "fixture-timeline",
            "revision": "v2"
          }
        ],
        "assumption_ids": [
          "FIXTURE_POLICY_AND_ETA"
        ]
      },
      "mode": "BACKLOG",
      "assumed": true,
      "unmet_demand": {
        "state": "ASSUMED",
        "value": "0",
        "unit": "PCS",
        "refs": [
          {
            "kind": "ANALYSIS",
            "id": "fixture-timeline",
            "revision": "v2"
          }
        ],
        "assumption_ids": [
          "FIXTURE_POLICY_AND_ETA"
        ]
      },
      "backlog_qty": {
        "state": "ASSUMED",
        "value": "0",
        "unit": "PCS",
        "refs": [
          {
            "kind": "ANALYSIS",
            "id": "fixture-timeline",
            "revision": "v2"
          }
        ],
        "assumption_ids": [
          "FIXTURE_POLICY_AND_ETA"
        ]
      },
      "min_intraday_balance": {
        "state": "ASSUMED",
        "value": "10",
        "unit": "PCS",
        "refs": [
          {
            "kind": "ANALYSIS",
            "id": "fixture-timeline",
            "revision": "v2"
          }
        ],
        "assumption_ids": [
          "FIXTURE_POLICY_AND_ETA"
        ]
      },
      "first_gap_at": null,
      "timing_basis": "DATE_POLICY",
      "timing_policy_id": "FIXTURE_ARRIVALS_BEFORE_DAILY_DEMAND",
      "event_refs": []
    },
    {
      "date": "2026-10-04",
      "target_key": "fixture-vivo:A:30",
      "demand": {
        "state": "ASSUMED",
        "value": "4",
        "unit": "PCS",
        "refs": [
          {
            "kind": "ANALYSIS",
            "id": "fixture-timeline",
            "revision": "v2"
          }
        ],
        "assumption_ids": [
          "FIXTURE_POLICY_AND_ETA"
        ]
      },
      "directed_supply": {
        "state": "ASSUMED",
        "value": "0",
        "unit": "PCS",
        "refs": [
          {
            "kind": "ANALYSIS",
            "id": "fixture-timeline",
            "revision": "v2"
          }
        ],
        "assumption_ids": [
          "FIXTURE_POLICY_AND_ETA"
        ]
      },
      "candidate_supply": {
        "state": "ASSUMED",
        "value": "0",
        "unit": "PCS",
        "refs": [
          {
            "kind": "ANALYSIS",
            "id": "fixture-timeline",
            "revision": "v2"
          }
        ],
        "assumption_ids": [
          "FIXTURE_POLICY_AND_ETA"
        ]
      },
      "proposed_new_supply": {
        "state": "ASSUMED",
        "value": "0",
        "unit": "PCS",
        "refs": [
          {
            "kind": "ANALYSIS",
            "id": "fixture-timeline",
            "revision": "v2"
          }
        ],
        "assumption_ids": [
          "FIXTURE_POLICY_AND_ETA"
        ]
      },
      "balance_end": {
        "state": "ASSUMED",
        "value": "14",
        "unit": "PCS",
        "refs": [
          {
            "kind": "ANALYSIS",
            "id": "fixture-timeline",
            "revision": "v2"
          }
        ],
        "assumption_ids": [
          "FIXTURE_POLICY_AND_ETA"
        ]
      },
      "mode": "BACKLOG",
      "assumed": true,
      "unmet_demand": {
        "state": "ASSUMED",
        "value": "0",
        "unit": "PCS",
        "refs": [
          {
            "kind": "ANALYSIS",
            "id": "fixture-timeline",
            "revision": "v2"
          }
        ],
        "assumption_ids": [
          "FIXTURE_POLICY_AND_ETA"
        ]
      },
      "backlog_qty": {
        "state": "ASSUMED",
        "value": "0",
        "unit": "PCS",
        "refs": [
          {
            "kind": "ANALYSIS",
            "id": "fixture-timeline",
            "revision": "v2"
          }
        ],
        "assumption_ids": [
          "FIXTURE_POLICY_AND_ETA"
        ]
      },
      "min_intraday_balance": {
        "state": "ASSUMED",
        "value": "14",
        "unit": "PCS",
        "refs": [
          {
            "kind": "ANALYSIS",
            "id": "fixture-timeline",
            "revision": "v2"
          }
        ],
        "assumption_ids": [
          "FIXTURE_POLICY_AND_ETA"
        ]
      },
      "first_gap_at": null,
      "timing_basis": "DATE_POLICY",
      "timing_policy_id": "FIXTURE_ARRIVALS_BEFORE_DAILY_DEMAND",
      "event_refs": []
    },
    {
      "date": "2026-10-05",
      "target_key": "fixture-vivo:A:30",
      "demand": {
        "state": "ASSUMED",
        "value": "4",
        "unit": "PCS",
        "refs": [
          {
            "kind": "ANALYSIS",
            "id": "fixture-timeline",
            "revision": "v2"
          }
        ],
        "assumption_ids": [
          "FIXTURE_POLICY_AND_ETA"
        ]
      },
      "directed_supply": {
        "state": "ASSUMED",
        "value": "0",
        "unit": "PCS",
        "refs": [
          {
            "kind": "ANALYSIS",
            "id": "fixture-timeline",
            "revision": "v2"
          }
        ],
        "assumption_ids": [
          "FIXTURE_POLICY_AND_ETA"
        ]
      },
      "candidate_supply": {
        "state": "ASSUMED",
        "value": "0",
        "unit": "PCS",
        "refs": [
          {
            "kind": "ANALYSIS",
            "id": "fixture-timeline",
            "revision": "v2"
          }
        ],
        "assumption_ids": [
          "FIXTURE_POLICY_AND_ETA"
        ]
      },
      "proposed_new_supply": {
        "state": "ASSUMED",
        "value": "0",
        "unit": "PCS",
        "refs": [
          {
            "kind": "ANALYSIS",
            "id": "fixture-timeline",
            "revision": "v2"
          }
        ],
        "assumption_ids": [
          "FIXTURE_POLICY_AND_ETA"
        ]
      },
      "balance_end": {
        "state": "ASSUMED",
        "value": "10",
        "unit": "PCS",
        "refs": [
          {
            "kind": "ANALYSIS",
            "id": "fixture-timeline",
            "revision": "v2"
          }
        ],
        "assumption_ids": [
          "FIXTURE_POLICY_AND_ETA"
        ]
      },
      "mode": "BACKLOG",
      "assumed": true,
      "unmet_demand": {
        "state": "ASSUMED",
        "value": "0",
        "unit": "PCS",
        "refs": [
          {
            "kind": "ANALYSIS",
            "id": "fixture-timeline",
            "revision": "v2"
          }
        ],
        "assumption_ids": [
          "FIXTURE_POLICY_AND_ETA"
        ]
      },
      "backlog_qty": {
        "state": "ASSUMED",
        "value": "0",
        "unit": "PCS",
        "refs": [
          {
            "kind": "ANALYSIS",
            "id": "fixture-timeline",
            "revision": "v2"
          }
        ],
        "assumption_ids": [
          "FIXTURE_POLICY_AND_ETA"
        ]
      },
      "min_intraday_balance": {
        "state": "ASSUMED",
        "value": "10",
        "unit": "PCS",
        "refs": [
          {
            "kind": "ANALYSIS",
            "id": "fixture-timeline",
            "revision": "v2"
          }
        ],
        "assumption_ids": [
          "FIXTURE_POLICY_AND_ETA"
        ]
      },
      "first_gap_at": null,
      "timing_basis": "DATE_POLICY",
      "timing_policy_id": "FIXTURE_ARRIVALS_BEFORE_DAILY_DEMAND",
      "event_refs": []
    },
    {
      "date": "2026-10-06",
      "target_key": "fixture-vivo:A:30",
      "demand": {
        "state": "ASSUMED",
        "value": "4",
        "unit": "PCS",
        "refs": [
          {
            "kind": "ANALYSIS",
            "id": "fixture-timeline",
            "revision": "v2"
          }
        ],
        "assumption_ids": [
          "FIXTURE_POLICY_AND_ETA"
        ]
      },
      "directed_supply": {
        "state": "ASSUMED",
        "value": "0",
        "unit": "PCS",
        "refs": [
          {
            "kind": "ANALYSIS",
            "id": "fixture-timeline",
            "revision": "v2"
          }
        ],
        "assumption_ids": [
          "FIXTURE_POLICY_AND_ETA"
        ]
      },
      "candidate_supply": {
        "state": "ASSUMED",
        "value": "10",
        "unit": "PCS",
        "refs": [
          {
            "kind": "ANALYSIS",
            "id": "fixture-timeline",
            "revision": "v2"
          }
        ],
        "assumption_ids": [
          "FIXTURE_POLICY_AND_ETA"
        ]
      },
      "proposed_new_supply": {
        "state": "ASSUMED",
        "value": "0",
        "unit": "PCS",
        "refs": [
          {
            "kind": "ANALYSIS",
            "id": "fixture-timeline",
            "revision": "v2"
          }
        ],
        "assumption_ids": [
          "FIXTURE_POLICY_AND_ETA"
        ]
      },
      "balance_end": {
        "state": "ASSUMED",
        "value": "16",
        "unit": "PCS",
        "refs": [
          {
            "kind": "ANALYSIS",
            "id": "fixture-timeline",
            "revision": "v2"
          }
        ],
        "assumption_ids": [
          "FIXTURE_POLICY_AND_ETA"
        ]
      },
      "mode": "BACKLOG",
      "assumed": true,
      "unmet_demand": {
        "state": "ASSUMED",
        "value": "0",
        "unit": "PCS",
        "refs": [
          {
            "kind": "ANALYSIS",
            "id": "fixture-timeline",
            "revision": "v2"
          }
        ],
        "assumption_ids": [
          "FIXTURE_POLICY_AND_ETA"
        ]
      },
      "backlog_qty": {
        "state": "ASSUMED",
        "value": "0",
        "unit": "PCS",
        "refs": [
          {
            "kind": "ANALYSIS",
            "id": "fixture-timeline",
            "revision": "v2"
          }
        ],
        "assumption_ids": [
          "FIXTURE_POLICY_AND_ETA"
        ]
      },
      "min_intraday_balance": {
        "state": "ASSUMED",
        "value": "10",
        "unit": "PCS",
        "refs": [
          {
            "kind": "ANALYSIS",
            "id": "fixture-timeline",
            "revision": "v2"
          }
        ],
        "assumption_ids": [
          "FIXTURE_POLICY_AND_ETA"
        ]
      },
      "first_gap_at": null,
      "timing_basis": "DATE_POLICY",
      "timing_policy_id": "FIXTURE_ARRIVALS_BEFORE_DAILY_DEMAND",
      "event_refs": []
    },
    {
      "date": "2026-10-07",
      "target_key": "fixture-vivo:A:30",
      "demand": {
        "state": "ASSUMED",
        "value": "4",
        "unit": "PCS",
        "refs": [
          {
            "kind": "ANALYSIS",
            "id": "fixture-timeline",
            "revision": "v2"
          }
        ],
        "assumption_ids": [
          "FIXTURE_POLICY_AND_ETA"
        ]
      },
      "directed_supply": {
        "state": "ASSUMED",
        "value": "0",
        "unit": "PCS",
        "refs": [
          {
            "kind": "ANALYSIS",
            "id": "fixture-timeline",
            "revision": "v2"
          }
        ],
        "assumption_ids": [
          "FIXTURE_POLICY_AND_ETA"
        ]
      },
      "candidate_supply": {
        "state": "ASSUMED",
        "value": "0",
        "unit": "PCS",
        "refs": [
          {
            "kind": "ANALYSIS",
            "id": "fixture-timeline",
            "revision": "v2"
          }
        ],
        "assumption_ids": [
          "FIXTURE_POLICY_AND_ETA"
        ]
      },
      "proposed_new_supply": {
        "state": "ASSUMED",
        "value": "8",
        "unit": "PCS",
        "refs": [
          {
            "kind": "ANALYSIS",
            "id": "fixture-timeline",
            "revision": "v2"
          }
        ],
        "assumption_ids": [
          "FIXTURE_POLICY_AND_ETA"
        ]
      },
      "balance_end": {
        "state": "ASSUMED",
        "value": "20",
        "unit": "PCS",
        "refs": [
          {
            "kind": "ANALYSIS",
            "id": "fixture-timeline",
            "revision": "v2"
          }
        ],
        "assumption_ids": [
          "FIXTURE_POLICY_AND_ETA"
        ]
      },
      "mode": "BACKLOG",
      "assumed": true,
      "unmet_demand": {
        "state": "ASSUMED",
        "value": "0",
        "unit": "PCS",
        "refs": [
          {
            "kind": "ANALYSIS",
            "id": "fixture-timeline",
            "revision": "v2"
          }
        ],
        "assumption_ids": [
          "FIXTURE_POLICY_AND_ETA"
        ]
      },
      "backlog_qty": {
        "state": "ASSUMED",
        "value": "0",
        "unit": "PCS",
        "refs": [
          {
            "kind": "ANALYSIS",
            "id": "fixture-timeline",
            "revision": "v2"
          }
        ],
        "assumption_ids": [
          "FIXTURE_POLICY_AND_ETA"
        ]
      },
      "min_intraday_balance": {
        "state": "ASSUMED",
        "value": "16",
        "unit": "PCS",
        "refs": [
          {
            "kind": "ANALYSIS",
            "id": "fixture-timeline",
            "revision": "v2"
          }
        ],
        "assumption_ids": [
          "FIXTURE_POLICY_AND_ETA"
        ]
      },
      "first_gap_at": null,
      "timing_basis": "DATE_POLICY",
      "timing_policy_id": "FIXTURE_ARRIVALS_BEFORE_DAILY_DEMAND",
      "event_refs": []
    },
    {
      "date": "2026-10-08",
      "target_key": "fixture-vivo:A:30",
      "demand": {
        "state": "ASSUMED",
        "value": "4",
        "unit": "PCS",
        "refs": [
          {
            "kind": "ANALYSIS",
            "id": "fixture-timeline",
            "revision": "v2"
          }
        ],
        "assumption_ids": [
          "FIXTURE_POLICY_AND_ETA"
        ]
      },
      "directed_supply": {
        "state": "ASSUMED",
        "value": "0",
        "unit": "PCS",
        "refs": [
          {
            "kind": "ANALYSIS",
            "id": "fixture-timeline",
            "revision": "v2"
          }
        ],
        "assumption_ids": [
          "FIXTURE_POLICY_AND_ETA"
        ]
      },
      "candidate_supply": {
        "state": "ASSUMED",
        "value": "0",
        "unit": "PCS",
        "refs": [
          {
            "kind": "ANALYSIS",
            "id": "fixture-timeline",
            "revision": "v2"
          }
        ],
        "assumption_ids": [
          "FIXTURE_POLICY_AND_ETA"
        ]
      },
      "proposed_new_supply": {
        "state": "ASSUMED",
        "value": "0",
        "unit": "PCS",
        "refs": [
          {
            "kind": "ANALYSIS",
            "id": "fixture-timeline",
            "revision": "v2"
          }
        ],
        "assumption_ids": [
          "FIXTURE_POLICY_AND_ETA"
        ]
      },
      "balance_end": {
        "state": "ASSUMED",
        "value": "16",
        "unit": "PCS",
        "refs": [
          {
            "kind": "ANALYSIS",
            "id": "fixture-timeline",
            "revision": "v2"
          }
        ],
        "assumption_ids": [
          "FIXTURE_POLICY_AND_ETA"
        ]
      },
      "mode": "BACKLOG",
      "assumed": true,
      "unmet_demand": {
        "state": "ASSUMED",
        "value": "0",
        "unit": "PCS",
        "refs": [
          {
            "kind": "ANALYSIS",
            "id": "fixture-timeline",
            "revision": "v2"
          }
        ],
        "assumption_ids": [
          "FIXTURE_POLICY_AND_ETA"
        ]
      },
      "backlog_qty": {
        "state": "ASSUMED",
        "value": "0",
        "unit": "PCS",
        "refs": [
          {
            "kind": "ANALYSIS",
            "id": "fixture-timeline",
            "revision": "v2"
          }
        ],
        "assumption_ids": [
          "FIXTURE_POLICY_AND_ETA"
        ]
      },
      "min_intraday_balance": {
        "state": "ASSUMED",
        "value": "16",
        "unit": "PCS",
        "refs": [
          {
            "kind": "ANALYSIS",
            "id": "fixture-timeline",
            "revision": "v2"
          }
        ],
        "assumption_ids": [
          "FIXTURE_POLICY_AND_ETA"
        ]
      },
      "first_gap_at": null,
      "timing_basis": "DATE_POLICY",
      "timing_policy_id": "FIXTURE_ARRIVALS_BEFORE_DAILY_DEMAND",
      "event_refs": []
    },
    {
      "date": "2026-10-09",
      "target_key": "fixture-vivo:A:30",
      "demand": {
        "state": "ASSUMED",
        "value": "4",
        "unit": "PCS",
        "refs": [
          {
            "kind": "ANALYSIS",
            "id": "fixture-timeline",
            "revision": "v2"
          }
        ],
        "assumption_ids": [
          "FIXTURE_POLICY_AND_ETA"
        ]
      },
      "directed_supply": {
        "state": "ASSUMED",
        "value": "0",
        "unit": "PCS",
        "refs": [
          {
            "kind": "ANALYSIS",
            "id": "fixture-timeline",
            "revision": "v2"
          }
        ],
        "assumption_ids": [
          "FIXTURE_POLICY_AND_ETA"
        ]
      },
      "candidate_supply": {
        "state": "ASSUMED",
        "value": "0",
        "unit": "PCS",
        "refs": [
          {
            "kind": "ANALYSIS",
            "id": "fixture-timeline",
            "revision": "v2"
          }
        ],
        "assumption_ids": [
          "FIXTURE_POLICY_AND_ETA"
        ]
      },
      "proposed_new_supply": {
        "state": "ASSUMED",
        "value": "0",
        "unit": "PCS",
        "refs": [
          {
            "kind": "ANALYSIS",
            "id": "fixture-timeline",
            "revision": "v2"
          }
        ],
        "assumption_ids": [
          "FIXTURE_POLICY_AND_ETA"
        ]
      },
      "balance_end": {
        "state": "ASSUMED",
        "value": "12",
        "unit": "PCS",
        "refs": [
          {
            "kind": "ANALYSIS",
            "id": "fixture-timeline",
            "revision": "v2"
          }
        ],
        "assumption_ids": [
          "FIXTURE_POLICY_AND_ETA"
        ]
      },
      "mode": "BACKLOG",
      "assumed": true,
      "unmet_demand": {
        "state": "ASSUMED",
        "value": "0",
        "unit": "PCS",
        "refs": [
          {
            "kind": "ANALYSIS",
            "id": "fixture-timeline",
            "revision": "v2"
          }
        ],
        "assumption_ids": [
          "FIXTURE_POLICY_AND_ETA"
        ]
      },
      "backlog_qty": {
        "state": "ASSUMED",
        "value": "0",
        "unit": "PCS",
        "refs": [
          {
            "kind": "ANALYSIS",
            "id": "fixture-timeline",
            "revision": "v2"
          }
        ],
        "assumption_ids": [
          "FIXTURE_POLICY_AND_ETA"
        ]
      },
      "min_intraday_balance": {
        "state": "ASSUMED",
        "value": "12",
        "unit": "PCS",
        "refs": [
          {
            "kind": "ANALYSIS",
            "id": "fixture-timeline",
            "revision": "v2"
          }
        ],
        "assumption_ids": [
          "FIXTURE_POLICY_AND_ETA"
        ]
      },
      "first_gap_at": null,
      "timing_basis": "DATE_POLICY",
      "timing_policy_id": "FIXTURE_ARRIVALS_BEFORE_DAILY_DEMAND",
      "event_refs": []
    },
    {
      "date": "2026-10-10",
      "target_key": "fixture-vivo:A:30",
      "demand": {
        "state": "ASSUMED",
        "value": "4",
        "unit": "PCS",
        "refs": [
          {
            "kind": "ANALYSIS",
            "id": "fixture-timeline",
            "revision": "v2"
          }
        ],
        "assumption_ids": [
          "FIXTURE_POLICY_AND_ETA"
        ]
      },
      "directed_supply": {
        "state": "ASSUMED",
        "value": "0",
        "unit": "PCS",
        "refs": [
          {
            "kind": "ANALYSIS",
            "id": "fixture-timeline",
            "revision": "v2"
          }
        ],
        "assumption_ids": [
          "FIXTURE_POLICY_AND_ETA"
        ]
      },
      "candidate_supply": {
        "state": "ASSUMED",
        "value": "0",
        "unit": "PCS",
        "refs": [
          {
            "kind": "ANALYSIS",
            "id": "fixture-timeline",
            "revision": "v2"
          }
        ],
        "assumption_ids": [
          "FIXTURE_POLICY_AND_ETA"
        ]
      },
      "proposed_new_supply": {
        "state": "ASSUMED",
        "value": "0",
        "unit": "PCS",
        "refs": [
          {
            "kind": "ANALYSIS",
            "id": "fixture-timeline",
            "revision": "v2"
          }
        ],
        "assumption_ids": [
          "FIXTURE_POLICY_AND_ETA"
        ]
      },
      "balance_end": {
        "state": "ASSUMED",
        "value": "8",
        "unit": "PCS",
        "refs": [
          {
            "kind": "ANALYSIS",
            "id": "fixture-timeline",
            "revision": "v2"
          }
        ],
        "assumption_ids": [
          "FIXTURE_POLICY_AND_ETA"
        ]
      },
      "mode": "BACKLOG",
      "assumed": true,
      "unmet_demand": {
        "state": "ASSUMED",
        "value": "0",
        "unit": "PCS",
        "refs": [
          {
            "kind": "ANALYSIS",
            "id": "fixture-timeline",
            "revision": "v2"
          }
        ],
        "assumption_ids": [
          "FIXTURE_POLICY_AND_ETA"
        ]
      },
      "backlog_qty": {
        "state": "ASSUMED",
        "value": "0",
        "unit": "PCS",
        "refs": [
          {
            "kind": "ANALYSIS",
            "id": "fixture-timeline",
            "revision": "v2"
          }
        ],
        "assumption_ids": [
          "FIXTURE_POLICY_AND_ETA"
        ]
      },
      "min_intraday_balance": {
        "state": "ASSUMED",
        "value": "8",
        "unit": "PCS",
        "refs": [
          {
            "kind": "ANALYSIS",
            "id": "fixture-timeline",
            "revision": "v2"
          }
        ],
        "assumption_ids": [
          "FIXTURE_POLICY_AND_ETA"
        ]
      },
      "first_gap_at": null,
      "timing_basis": "DATE_POLICY",
      "timing_policy_id": "FIXTURE_ARRIVALS_BEFORE_DAILY_DEMAND",
      "event_refs": []
    }
  ],
  "actions": [
    {
      "key": "check-candidate:fixture-batch-candidate:scenario1",
      "intent": "CHECK_CANDIDATE",
      "source_keys": [
        "fixture-batch-candidate:size30"
      ],
      "target_keys": [
        "fixture-vivo:A:30"
      ],
      "primary_reason": "CANDIDATE_NEEDS_CONFIRMATION",
      "conditional": true,
      "source_links": [
        {
          "kind": "WIP",
          "id": "candidate",
          "revision": "fixture-r1"
        }
      ],
      "display_priority": {
        "rank": 1,
        "lane": "REVIEW_DATA",
        "basis": [
          "Confirm candidate compatibility and ETA before production planning"
        ],
        "rule_version": "fixture-priority-v2"
      }
    }
  ],
  "financial_readiness": "BLOCKED",
  "stale": {
    "is_stale": false,
    "reasons": []
  },
  "assumptions": [
    {
      "id": "FIXTURE_POLICY_AND_ETA",
      "label": "D4, L7, R3, B2 dan ETA hanya input contoh; bukan parameter pabrik",
      "origin": "SCENARIO",
      "confirmed_for_operation": false
    },
    {
      "id": "CANDIDATE_MATCH_AND_TIME",
      "label": "10 kandidat cocok dan tiba hari6 hanya pada skenario ini",
      "origin": "SCENARIO",
      "confirmed_for_operation": false
    },
    {
      "id": "NEW8_IS_HYPOTHETICAL_NOT_POSTED",
      "label": "8 produksi baru tiba hari7 disimulasikan; bahan/kapasitas belum terbukti",
      "origin": "SCENARIO",
      "confirmed_for_operation": false
    }
  ],
  "dependencies": [
    {
      "domain": "fixture_facts",
      "revision": "r1",
      "completeness": "COMPLETE",
      "fact_count": 7,
      "source_hash": "73ecf7d2f36750f89cd2d41db9e19e40ffce23612e81716035e4c8744938391e"
    }
  ],
  "policy_basis": {
    "lead_time_new_days": {
      "state": "ASSUMED",
      "value": "7",
      "unit": "DAY",
      "refs": [
        {
          "kind": "POLICY",
          "id": "fixture",
          "revision": "fixture-r1"
        }
      ],
      "assumption_ids": [
        "FIXTURE_POLICY_AND_ETA"
      ]
    },
    "review_days": {
      "state": "ASSUMED",
      "value": "3",
      "unit": "DAY",
      "refs": [
        {
          "kind": "POLICY",
          "id": "fixture",
          "revision": "fixture-r1"
        }
      ],
      "assumption_ids": [
        "FIXTURE_POLICY_AND_ETA"
      ]
    },
    "buffer_mode": "DAYS",
    "buffer_days": {
      "state": "ASSUMED",
      "value": "2",
      "unit": "DAY",
      "refs": [
        {
          "kind": "POLICY",
          "id": "fixture",
          "revision": "fixture-r1"
        }
      ],
      "assumption_ids": [
        "FIXTURE_POLICY_AND_ETA"
      ]
    },
    "service_target": {
      "state": "NOT_APPLICABLE",
      "unit": "RATIO",
      "reason": "Mode buffer hari, bukan statistical service target",
      "refs": []
    },
    "rounding_multiple": {
      "state": "KNOWN",
      "value": "1",
      "unit": "PCS",
      "refs": [
        {
          "kind": "POLICY",
          "id": "pcs",
          "revision": "fixture-r1"
        }
      ]
    }
  },
  "demand_models": [
    {
      "target_key": "fixture-vivo:A:30",
      "method_id": "MANUAL_TARGET_RATE",
      "version": "fixture-v1",
      "mode": "FALLBACK",
      "demand_rate": {
        "state": "ASSUMED",
        "value": "4",
        "unit": "PCS/DAY",
        "refs": [
          {
            "kind": "POLICY",
            "id": "fixture",
            "revision": "fixture-r1"
          }
        ],
        "assumption_ids": [
          "FIXTURE_POLICY_AND_ETA"
        ]
      },
      "observed_days": 0,
      "stockout_days": 0,
      "unknown_days": 0,
      "horizon_days": 10,
      "selection_reason": "Fixture manual input; no actual sales history or validated accuracy claimed",
      "validation_fold_ids": [],
      "scores": []
    }
  ],
  "material_needs": [
    {
      "target_key": "fixture-vivo:A:30",
      "material_key": null,
      "gross": {
        "state": "UNKNOWN",
        "unit": "PCS",
        "reason": "BOM_NOT_CAPTURED_FOR_THIS_NUMERIC_FIXTURE",
        "refs": []
      },
      "installed_proven": {
        "state": "UNKNOWN",
        "unit": "PCS",
        "reason": "CONSUMPTION_NOT_PROVEN",
        "refs": []
      },
      "unused_allocated_proven": {
        "state": "UNKNOWN",
        "unit": "PCS",
        "reason": "ALLOCATION_NOT_PROVEN",
        "refs": []
      },
      "additional_external": {
        "state": "UNKNOWN",
        "unit": "PCS",
        "reason": "MATERIAL_REMAINING_UNKNOWN",
        "refs": []
      },
      "reason": "MATERIAL_REMAINING_UNKNOWN"
    }
  ],
  "capacity_checks": [
    {
      "stage": "NEW_PRODUCTION",
      "calendar_version": "NOT_CONFIGURED_IN_FIXTURE",
      "available": {
        "state": "UNKNOWN",
        "unit": "PCS",
        "reason": "CAPACITY_NOT_PROVIDED",
        "refs": []
      },
      "existing_load": {
        "state": "UNKNOWN",
        "unit": "PCS",
        "reason": "LOAD_NOT_PROVIDED",
        "refs": []
      },
      "feasible_new": {
        "state": "UNKNOWN",
        "unit": "PCS",
        "reason": "FEASIBILITY_NOT_PROVEN",
        "refs": []
      },
      "status": "UNKNOWN"
    }
  ],
  "metrics": [
    {
      "metric_id": "GROSS_MARGIN",
      "version": "metric-v1",
      "value": {
        "state": "UNKNOWN",
        "unit": "RATIO",
        "reason": "COST_AND_REVENUE_NOT_CAPTURED",
        "refs": []
      },
      "formula_ref": "(net_revenue-eligible_COGS)/net_revenue",
      "operands": [
        {
          "state": "UNKNOWN",
          "unit": "IDR",
          "reason": "REVENUE_UNKNOWN",
          "refs": []
        },
        {
          "state": "UNKNOWN",
          "unit": "IDR",
          "reason": "COGS_UNKNOWN",
          "refs": []
        }
      ],
      "readiness": "BLOCKED",
      "scope_kind": "TARGET",
      "scope_key": "fixture-vivo:A:30",
      "period_start": "2026-10-01",
      "period_end": "2026-10-10",
      "knowledge_mode": "AS_KNOWN"
    }
  ],
  "plan_comparisons": [],
  "generation_warnings": [
    "SYNTHETIC_EXAMPLE_ONLY",
    "COMPLETE_MEANS_COMPUTATION_FINISHED_NOT_OPERATIONALLY_FEASIBLE",
    "NO_REAL_PLAN_EXISTS_FOR_PLAN_VERSUS_ACTUAL"
  ],
  "semantic_hash": "d40f1cedddb26e3103b8e7096257dbe17c14aacddf4bb89a379c85a4b0f368b9",
  "allocation_edges": [
    {
      "source_key": "fixture-batch-directed:size30",
      "target_key": "fixture-vivo:A:30",
      "size_id": "30",
      "input_qty": {
        "state": "KNOWN",
        "value": "12",
        "unit": "PCS",
        "refs": [
          {
            "kind": "SCENARIO",
            "id": "directed",
            "revision": "fixture-r1"
          }
        ]
      },
      "projected_output_qty": {
        "state": "KNOWN",
        "value": "12",
        "unit": "PCS",
        "refs": [
          {
            "kind": "SCENARIO",
            "id": "directed",
            "revision": "fixture-r1"
          }
        ]
      },
      "match": "CONFIRMED_TARGET",
      "eligible_at": "2026-10-03T00:00:00+07:00",
      "assumption_ids": [],
      "refs": [
        {
          "kind": "WIP",
          "id": "directed",
          "revision": "fixture-r1"
        }
      ]
    },
    {
      "source_key": "fixture-batch-candidate:size30",
      "target_key": "fixture-vivo:A:30",
      "size_id": "30",
      "input_qty": {
        "state": "ASSUMED",
        "value": "10",
        "unit": "PCS",
        "refs": [
          {
            "kind": "SCENARIO",
            "id": "candidate",
            "revision": "fixture-r1"
          }
        ],
        "assumption_ids": [
          "FIXTURE_POLICY_AND_ETA"
        ]
      },
      "projected_output_qty": {
        "state": "ASSUMED",
        "value": "10",
        "unit": "PCS",
        "refs": [
          {
            "kind": "SCENARIO",
            "id": "candidate",
            "revision": "fixture-r1"
          }
        ],
        "assumption_ids": [
          "FIXTURE_POLICY_AND_ETA"
        ]
      },
      "match": "CANDIDATE_MATCH",
      "eligible_at": "2026-10-06T00:00:00+07:00",
      "assumption_ids": [
        "FIXTURE_POLICY_AND_ETA"
      ],
      "refs": [
        {
          "kind": "WIP",
          "id": "candidate",
          "revision": "fixture-r1"
        }
      ]
    }
  ]
} satisfies AnalysisResult
