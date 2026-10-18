"""Record source/contract observations and existing results; no new probes."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
PIN = "b53b5acdf260b03ebac3474e9ae837fcef6f6eb1"


def source(path):
    p = REPO / path
    return dict(path=path, sha256=hashlib.sha256(p.read_bytes()).hexdigest(), candidate_sha=PIN)


cp17_path = ROOT / "ci_receipts/sol_artifacts/12143844276/files/CP7_CP17_FIXES.json"
cp17 = json.loads(cp17_path.read_text())
pool = cp17["native"]["cases"]["CP17_R3_04_HPP_POOL_FACADE_PRIVATE_AND_IMMUTABLE"]
old = pool["bundle"]["observation_cp4_wrappers_executable_by_authenticated"]
assert len(old) == 4
k3_path = ROOT / "ci_receipts/sol_artifacts/12144484681/files/CP7_K3_CLEANUP.json"
k3 = json.loads(k3_path.read_text())
ownership = k3["races"]["races"]["K3C_RACE_BACKUP_SCRATCH_OWNERSHIP_BY_OID"]
out = dict(candidate_sha=PIN, scope="SOURCE_CONTRACT_AND_EXISTING_OWN_RESULT_REVIEW_ONLY",
           new_sql_or_access_probe_executed=False, new_product_bug_claim=False,
           pool_public_entrypoints=dict(
               status="CONFIRMED_ENTRYPOINT_AND_EFFECTIVE_GRANT_WITH_MUTATING_IMPACT_UNTESTED",
               sources=[source("supabase/migrations/20260902043000_erp_v2_6_16_cp4_hpp_route_auth_boundary.sql"),
                        source("scripts/cp7_hpp_pool_bundle.py"), source("scripts/cp7-src/hpp-pool/pool.sql"),
                        source("docs/cp7/OWNER_DECISIONS_20261008.md")],
               existing_result=dict(run_id=39146521757, artifact_id=12143844276,
                   path=str(cp17_path.relative_to(ROOT)), sha256=hashlib.sha256(cp17_path.read_bytes()).hexdigest(),
                   case_id="CP17_R3_04_HPP_POOL_FACADE_PRIVATE_AND_IMMUTABLE",
                   raw_status=pool["status"], authenticated_execute_confirmed=old,
                   native_direct_refused=pool["native_writer_direct_refused"]),
               confirmed=["Four public SECURITY DEFINER wrappers exist with authenticated EXECUTE in reviewed migration and effective-grant observation in own existing run.",
                          "Their source checks Owner/Admin then calls Native; it does not pass through the new CP7 facade's closed-period/review/request-table checks.",
                          "New facade period refusal and UUID/review lifecycle have separate positive/refusal results."],
               untested=["Mutating closed-period execution through old wrapper and exact journal/HPP/period effect.",
                         "Old-wrapper end-to-end Data API execution and every current permission combination."],
               owner_disposition="D14-9 accepts deferred revoke for 82 private erp writers conditional on no internet reachability. It does not explicitly accept this public route difference.",
               next_action="Inventory all pool routes before CP7C; revoke obsolete public wrappers or apply the qualified effective date/review/UUID/authority contract on every retained route.",
               owner="WRITER_CP7C_IMPLEMENTER_THEN_AUDITOR", production_gate_closed=False),
           backup_replacement_boundary=dict(
               status="KNOWN_OPERATIONAL_RISK_NOT_EXPLICITLY_OWNER_ACCEPTED",
               sources=[source("scripts/cp7_nightly_backup.py"), source("docs/cp7/OWNER_DECISIONS_20261008.md")],
               existing_result=dict(run_id=39146762696, artifact_id=12144484681,
                   path=str(k3_path.relative_to(ROOT)), sha256=hashlib.sha256(k3_path.read_bytes()).hexdigest(),
                   case_id="K3C_RACE_BACKUP_SCRATCH_OWNERSHIP_BY_OID", raw_status=ownership["status"],
                   observed_boundary=ownership["B_replaced_before_restore"]["boundary"],
                   replacement_kept=ownership["B_replaced_before_restore"]["replacement_kept"],
                   verification_refused=True),
               confirmed="Original records a restore write to a replacement followed by mismatch detection; replacement not dropped. Source docstring declares the operating boundary, not assumed approved.",
               protection_proven_scope="Drop ownership, rejection of verification/pruning, and source unchanged are distinct from preventing every restore write to an unintended replacement.",
               owner_disposition="D13-8a..f and D13-9a govern encrypted Drive/restore/private-repo preparation and defer CP7C. No explicit acceptance of this replacement-write boundary was found in the current register.",
               next_action="Before operational use, writer/operations must define a fully disposable runner-owned restore server with no unrelated databases or concurrent administrative changes, or strengthen and qualify target-ownership guarantees. Retain this boundary until resolved or explicitly accepted in the proper operating scope.",
               owner="WRITER_OPERATIONS_CP7C_THEN_AUDITOR", production_gate_closed=False))
(ROOT / "BOUNDARY_REVIEW.json").write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
print("boundaries", 2, "new_probes", 0, "new_product_bug_claim", False)
