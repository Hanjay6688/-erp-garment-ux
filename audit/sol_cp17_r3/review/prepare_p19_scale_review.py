"""Read completed scale measurements without running the product or benchmark."""
import collections
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
path = ROOT / "ci_receipts/sol_artifacts/12146221035/files/CP7_P19_SCALE.json"
copy = ROOT / "ci_receipts/sol_artifacts/12145453764/files/CP7_P19_SCALE.json"
raw = path.read_bytes()
assert raw == copy.read_bytes()
x = json.loads(raw)
declaration_path = REPO / "docs/cp7/p19/P19_SCALE.json"
declaration_bytes = declaration_path.read_bytes()
declaration = json.loads(declaration_bytes)
assert hashlib.sha256(declaration_bytes).hexdigest() == x["predeclared_case_sha256"]
assert declaration == x["predeclared_case_contract"]
cases, samples, sizes = [], [], []
for group in ("native", "browser"):
    node = x[group]
    assert set(node["cases"]) == set(declaration["required_case_ids"][group])
    for case_id, case in node["cases"].items():
        cases.append(dict(id=case_id, group=group, raw_status=case["status"],
                          protocol_scope="MEASUREMENT_RESULT_NOT_LATENCY_OR_FACTORY_ACCEPTANCE"))
        if group != "browser":
            continue
        own = []
        for row in case["measurements"]:
            budget = row["owner_budgets"]
            sample = dict(case_id=case_id, size=case["size"], history_days=row["history_days"], control=row["control"],
                verdict_kind=row["verdict"]["kind"], refusal_code=row.get("refusal_code"), cap=row["verdict"].get("cap"),
                first_visible_ack_ms=row["click_to_first_status_ms"], complete_or_refusal_ms=row["click_to_complete_ms"],
                heavy_limit_ms=budget["complete_or_refusal_rendered"]["limit_ms"],
                heavy_limit_met=budget["complete_or_refusal_rendered"]["meets_limit"],
                ack_limit_met=budget["first_visible_acknowledgement"]["meets_limit"],
                background_exception=budget["owner_named_background_exception"],
                progress_status_visible_by_3000ms=budget["progress_status_visible_by_3000ms"],
                original_sha256=row.get("original_sha256"), witness=row.get("witness"))
            samples.append(sample)
            own.append(sample)
        sizes.append(dict(size=case["size"], case_id=case_id, samples=len(own),
                          verdict_counts=dict(collections.Counter(s["verdict_kind"] for s in own)),
                          sql_ladder_verdict_counts=case["sql_ladder"]["verdict_counts"],
                          sql_measurement_business_unchanged=case["sql_ladder"]["Native_business_unchanged_by_measurement"],
                          sql_phase_observations={days: {k: value.get(k) for k in ("layer", "own_ms", "first_stopped_phase", "capture_path_estimate_ms")} for days, value in case["sql_ladder"]["dominant_layer_by_days"].items()},
                          seeding_ms_separate=case["seed"]["seed_ms_not_app_latency"],
                          limits_raised=case["limits_raised"], sampled_or_truncated=case["data_sampled_or_truncated"]))
assert len(cases) == 5 and len(samples) == 48 and all(s["ack_limit_met"] for s in samples)
direct_misses = [s for s in samples if not s["background_exception"] and not s["heavy_limit_met"]]
out = dict(run_id=39146762696, job_id=117732074520, artifact_id=12146221035,
    path=str(path.relative_to(ROOT)), sha256=hashlib.sha256(raw).hexdigest(), complete_json_alias_identical=True,
    oracle_origin="PREDECLARED_WRITER_MEASUREMENT_CONTRACT", fixture_origin="PUBLIC_SYNTHETIC_WRITERS_NO_DIRECT_BUSINESS_INSERTS",
    execution_origin="INDEPENDENT_SOL", expected_ids_exact=True, cases=cases, sizes=sizes, samples=samples,
    browser_measurement_counts=dict(collections.Counter(s["verdict_kind"] for s in samples)),
    direct_finance_heavy_budget_misses=direct_misses,
    statement_timeout="8s_UNCHANGED", ack_target="<1000ms", ordinary_save_target="<=2000ms",
    heavy_complete_target="<=3000ms_WITH_PROGRESS", owner_latency_acceptance=False, full_P19_acceptance=False,
    factory_capacity_or_SLA=False, production_go=False,
    contract_sources=["docs/cp7/p19/P19_LOADING_BUDGET_20261006.md", "docs/cp7/p19/P19_SCALE.json", "docs/cp7/OWNER_DECISIONS_20261008.md"],
    named_background_exceptions=["P19_PLANNING_ANALYSIS_BACKGROUND_20261007", "P19_PLANNING_ANALYSIS_STAGED_20261007"],
    disposition="KNOWN_MEASURED_PERFORMANCE_GAP_OPEN_NOT_NEW_BLIND_DISCOVERY",
    qualification="Five raw PASS cases qualify measurement/cap refusal, not all workloads completing quickly. Named background/staged exceptions allow longer work with responsive status/recovery; they do not turn the 3s measurement green. Direct/finance samples with no named exception miss the declared heavy target. Existing declared gap is retained; no newly designed probe was run.",
    next_action="Writer must profile the slow direct/finance phases and optimize repeated work/complete per-screen projections, or use a justified explicitly named background/staged flow with real progress and recovery. Preserve 8s statement limit, exact Native/source/authority/hash/completeness checks; no sampling/truncation or timeout increase as a fix. Qualify every sample against its predeclared journey class before latency acceptance.",
    next_action_owner="WRITER_PERFORMANCE_THEN_AUDITOR",
    restore=x["restore_components"], cp6_restored=x["cp6_restored"], advisor_gate=x["advisor_gate"],
    cleanup={k: x["browser"][k] for k in ("database_remaining", "cleanup", "auth_counts", "console_errors", "session_leaks")})
(ROOT / "P19_SCALE_RESULT_REVIEW.json").write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
print("scale cases", len(cases), "measurements", len(samples), out["browser_measurement_counts"], "direct/finance heavy misses", len(direct_misses))
