import type { AnalysisResult } from '../contract'

export const exampleSupply = {
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
  ]
} satisfies Pick<AnalysisResult,
  'sources' |
  'recommendations'
>
